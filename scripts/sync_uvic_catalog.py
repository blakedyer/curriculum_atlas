#!/usr/bin/env python3
"""Sync SEOS catalog data from UVic's public undergraduate calendar endpoints.

This script treats the UVic Kuali-backed undergraduate calendar as the
source of truth for the *approved current* state of SEOS curriculum data.
It pulls:

- all programs whose official description names the School of Earth and Ocean Sciences
- all EOS subject courses in the current catalog
- all supporting course codes referenced by those programs and EOS courses

Outputs are written into ``data/catalog`` as raw JSON plus a few lightweight
CSV manifests that are convenient for downstream graph-generation work.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup


UNDERGRAD_CALENDAR_URL = "https://www.uvic.ca/calendar/undergrad/index.php#/courses"
CATALOG_API_BASE = "https://uvic.kuali.co/api/v1/catalog"
SEOS_MARKER = "school of earth and ocean sciences"
SEARCH_PAGE_SIZE = 100
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.uvic.ca",
    "Referer": "https://www.uvic.ca/",
    "Accept": "application/json,text/plain,*/*",
}
COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,5})\s?(\d{3}[A-Z]?)\b")
TITLE_REPLACEMENTS = {
    " (Bachelor of Science - Combined Major)": "",
    " (Bachelor of Science - Major)": "",
    " (Bachelor of Science - Combined Honours)": " (Honours)",
    " (Bachelor of Science - Honours)": " (Honours)",
}


@dataclass(frozen=True)
class CatalogMeta:
    catalog_id: str
    term_code: str
    publish_timetable: str
    source_url: str


def fetch_text(session: requests.Session, url: str) -> str:
    response = session.get(url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    return response.text


def fetch_json(session: requests.Session, url: str) -> object:
    response = session.get(url, headers=REQUEST_HEADERS, timeout=30)
    response.raise_for_status()
    return response.json()


def discover_catalog_meta(session: requests.Session) -> CatalogMeta:
    html = fetch_text(session, UNDERGRAD_CALENDAR_URL)

    catalog_match = re.search(r"window\.catalogId='([^']+)'", html)
    term_match = re.search(r'<meta content="([^"]+)" name="term-code"', html)
    publish_match = re.search(r'<meta content="([^"]+)" name="publish-timetable"', html)
    if not catalog_match:
        raise RuntimeError("Could not locate the current UVic catalog ID.")

    return CatalogMeta(
        catalog_id=catalog_match.group(1),
        term_code=term_match.group(1) if term_match else "",
        publish_timetable=publish_match.group(1) if publish_match else "",
        source_url=UNDERGRAD_CALENDAR_URL,
    )


def paginate_search(
    session: requests.Session,
    catalog_id: str,
    item_type: str,
    query: str = "",
    limit: int = SEARCH_PAGE_SIZE,
) -> list[dict]:
    results: list[dict] = []
    skip = 0

    while True:
        url = (
            f"{CATALOG_API_BASE}/search/{catalog_id}"
            f"?q={requests.utils.quote(query)}"
            f"&itemTypes={item_type}"
            f"&limit={limit}"
            f"&skip={skip}"
        )
        page = fetch_json(session, url)
        if not isinstance(page, list) or not page:
            break
        results.extend(page)
        if len(page) < limit:
            break
        skip += limit

    return results


def fetch_detail(session: requests.Session, kind: str, catalog_id: str, pid: str) -> dict:
    return fetch_json(session, f"{CATALOG_API_BASE}/{kind}/{catalog_id}/{pid}")


def normalize_course_code(subject: str, number: str) -> str:
    return f"{subject}{number}".replace(" ", "")


def extract_course_codes(*html_blobs: object) -> set[str]:
    codes: set[str] = set()
    for blob in html_blobs:
        if not blob:
            continue
        text = BeautifulSoup(str(blob), "html.parser").get_text(" ", strip=True)
        for subject, number in COURSE_CODE_RE.findall(text):
            codes.add(normalize_course_code(subject, number))
    return codes


def extract_program_referenced_course_codes(detail: dict) -> set[str]:
    codes = extract_course_codes(
        detail.get("description"),
        detail.get("programRequirements"),
        detail.get("programRequirementsRtf"),
        detail.get("programNotes"),
        detail.get("admissionRequirementsRtf"),
    )
    for specialization in detail.get("specializations") or []:
        if not isinstance(specialization, dict):
            continue
        codes.update(
            extract_course_codes(
                specialization.get("description"),
                specialization.get("programRequirements"),
                specialization.get("requirements"),
                specialization.get("concentrationProgramNotes"),
            )
        )
    return codes


def simplify_program_title(title: str) -> str:
    simplified = title.strip()
    for old, new in TITLE_REPLACEMENTS.items():
        simplified = simplified.replace(old, new)
    return simplified


def is_seos_program(program_summary: dict) -> bool:
    description = (program_summary.get("description") or "").lower()
    return SEOS_MARKER in description


def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")


def write_detail_snapshot(directory: Path, details: dict[str, dict]) -> None:
    """Replace a complete, successfully fetched detail set, removing stale records."""
    for code, detail in details.items():
        write_json(directory / f"{code}.json", detail)
    for path in directory.glob("*.json"):
        if path.stem not in details:
            path.unlink()


def write_csv(path: Path, rows: Iterable[Iterable[str]], header: Iterable[str]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(header))
        writer.writerows(rows)


def build_program_manifest(programs: list[dict]) -> list[dict]:
    manifest = []
    for program in programs:
        manifest.append(
            {
                "program_code": program["code"],
                "program_name": simplify_program_title(program["title"]),
                "program_title": program["title"],
                "pid": program["pid"],
                "id": program["id"],
                "catalog_url": f"https://www.uvic.ca/calendar/undergrad/index.php#/programs/{program['pid']}",
                "api_url": f"{CATALOG_API_BASE}/program/{{catalog_id}}/{program['pid']}",
            }
        )
    return manifest


def build_course_manifest(courses: list[dict]) -> list[dict]:
    manifest = []
    for course in courses:
        manifest.append(
            {
                "course_code": course["code"],
                "course_name": course["title"].strip(),
                "subject": (course.get("subjectCode") or {}).get("name", ""),
                "pid": course["pid"],
                "id": course["id"],
                "catalog_url": f"https://www.uvic.ca/calendar/undergrad/index.php#/courses/{course['pid']}",
                "api_url": f"{CATALOG_API_BASE}/course/{{catalog_id}}/{course['pid']}",
            }
        )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        default=Path(__file__).resolve().parents[1],
        type=Path,
        help="program_guide repository root",
    )
    args = parser.parse_args()

    repo_root = args.root.resolve()
    data_root = repo_root / "data"
    catalog_root = data_root / "catalog"
    program_detail_root = catalog_root / "program_details"
    course_detail_root = catalog_root / "course_details"
    ensure_dir(catalog_root)
    ensure_dir(program_detail_root)
    ensure_dir(course_detail_root)

    session = requests.Session()
    meta = discover_catalog_meta(session)

    all_programs = paginate_search(session, meta.catalog_id, "programs")
    all_courses = paginate_search(session, meta.catalog_id, "courses")

    seos_program_summaries = sorted(
        [program for program in all_programs if is_seos_program(program)],
        key=lambda program: (simplify_program_title(program["title"]).lower(), program["code"]),
    )
    eos_course_summaries = sorted(
        [
            course
            for course in all_courses
            if (course.get("subjectCode") or {}).get("name") == "EOS"
        ],
        key=lambda course: (course["code"], course["title"].lower()),
    )

    courses_by_code: dict[str, dict] = {}
    duplicate_course_codes: dict[str, list[str]] = defaultdict(list)
    for course in all_courses:
        code = course.get("code")
        if not code:
            continue
        if code in courses_by_code:
            duplicate_course_codes[code].append(course.get("pid", ""))
            continue
        courses_by_code[code] = course

    program_details: dict[str, dict] = {}
    referenced_course_codes: set[str] = set()
    for program in seos_program_summaries:
        detail = fetch_detail(session, "program", meta.catalog_id, program["pid"])
        program_details[program["code"]] = detail
        referenced_course_codes.update(extract_program_referenced_course_codes(detail))

    eos_course_details: dict[str, dict] = {}
    for course in eos_course_summaries:
        detail = fetch_detail(session, "course", meta.catalog_id, course["pid"])
        eos_course_details[course["code"]] = detail
        referenced_course_codes.update(
            extract_course_codes(
                detail.get("description"),
                detail.get("preAndCorequisites"),
                detail.get("recommendations"),
                detail.get("supplementalNotes"),
            )
        )
        for cross_listed in detail.get("crossListedCourses") or []:
            code = cross_listed.get("__catalogCourseId")
            if code:
                referenced_course_codes.add(code)

    eos_course_codes = {course["code"] for course in eos_course_summaries}
    support_course_codes = sorted(code for code in referenced_course_codes if code not in eos_course_codes)

    missing_support_codes: list[str] = []
    support_course_summaries: list[dict] = []
    for code in support_course_codes:
        summary = courses_by_code.get(code)
        if summary is None:
            missing_support_codes.append(code)
            continue
        support_course_summaries.append(summary)
    support_course_summaries.sort(key=lambda course: (course["code"], course["title"].lower()))

    support_course_details: dict[str, dict] = {}
    for course in support_course_summaries:
        support_course_details[course["code"]] = fetch_detail(
            session, "course", meta.catalog_id, course["pid"]
        )

    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "catalog_id": meta.catalog_id,
            "term_code": meta.term_code,
            "publish_timetable": meta.publish_timetable,
            "undergrad_calendar_url": meta.source_url,
            "search_api_base": CATALOG_API_BASE,
            "scope_rule": "Programs whose official description names the School of Earth and Ocean Sciences, plus all EOS courses and supporting referenced courses.",
        },
        "counts": {
            "all_programs": len(all_programs),
            "all_courses": len(all_courses),
            "seos_programs": len(seos_program_summaries),
            "eos_courses": len(eos_course_summaries),
            "support_courses": len(support_course_summaries),
        },
        "program_codes": [program["code"] for program in seos_program_summaries],
        "eos_course_codes": [course["code"] for course in eos_course_summaries],
        "support_course_codes": [course["code"] for course in support_course_summaries],
        "missing_support_codes": missing_support_codes,
        "duplicate_course_codes": duplicate_course_codes,
    }

    write_json(catalog_root / "manifest.json", manifest)
    write_json(catalog_root / "seos_program_manifest.json", build_program_manifest(seos_program_summaries))
    write_json(catalog_root / "eos_course_manifest.json", build_course_manifest(eos_course_summaries))
    write_json(catalog_root / "support_course_manifest.json", build_course_manifest(support_course_summaries))
    write_json(catalog_root / "referenced_course_codes.json", sorted(referenced_course_codes))

    write_detail_snapshot(program_detail_root, program_details)
    write_detail_snapshot(course_detail_root, {**eos_course_details, **support_course_details})

    write_csv(
        data_root / "eos_program_list.csv",
        (
            (program["code"], simplify_program_title(program["title"]))
            for program in seos_program_summaries
        ),
        header=("program_code", "program_name"),
    )
    write_csv(
        data_root / "eos_course_list.csv",
        ((course["code"], course["title"].strip()) for course in eos_course_summaries),
        header=("course_code", "course_name"),
    )
    write_csv(
        catalog_root / "seos_program_manifest.csv",
        (
            (
                program["code"],
                simplify_program_title(program["title"]),
                program["title"],
                program["pid"],
                program["id"],
                f"https://www.uvic.ca/calendar/undergrad/index.php#/programs/{program['pid']}",
            )
            for program in seos_program_summaries
        ),
        header=("program_code", "program_name", "program_title", "pid", "id", "catalog_url"),
    )
    write_csv(
        catalog_root / "eos_course_manifest.csv",
        (
            (
                course["code"],
                course["title"].strip(),
                course["pid"],
                course["id"],
                f"https://www.uvic.ca/calendar/undergrad/index.php#/courses/{course['pid']}",
            )
            for course in eos_course_summaries
        ),
        header=("course_code", "course_name", "pid", "id", "catalog_url"),
    )
    write_csv(
        catalog_root / "support_course_manifest.csv",
        (
            (
                course["code"],
                course["title"].strip(),
                course["pid"],
                course["id"],
                f"https://www.uvic.ca/calendar/undergrad/index.php#/courses/{course['pid']}",
            )
            for course in support_course_summaries
        ),
        header=("course_code", "course_name", "pid", "id", "catalog_url"),
    )

    print(f"Catalog ID: {meta.catalog_id}")
    print(f"Term code: {meta.term_code}")
    print(f"SEOS programs: {len(seos_program_summaries)}")
    print(f"EOS courses: {len(eos_course_summaries)}")
    print(f"Supporting courses: {len(support_course_summaries)}")
    if missing_support_codes:
        print("Missing support course codes:", ", ".join(missing_support_codes))


if __name__ == "__main__":
    main()
