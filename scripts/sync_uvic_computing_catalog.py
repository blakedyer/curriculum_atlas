#!/usr/bin/env python3
"""Sync a computing-course prerequisite closure from UVic's calendar.

The output is intentionally separate from the SEOS catalog snapshot.  It is
used for the unlinked computing prerequisite graph page and should not expand
the public course directory.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

import requests
from bs4 import BeautifulSoup


UNDERGRAD_CALENDAR_URL = "https://www.uvic.ca/calendar/undergrad/index.php#/courses"
CATALOG_API_BASE = "https://uvic.kuali.co/api/v1/catalog"
SEARCH_PAGE_SIZE = 500
REQUEST_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Origin": "https://www.uvic.ca",
    "Referer": "https://www.uvic.ca/",
    "Accept": "application/json,text/plain,*/*",
}
COURSE_CODE_RE = re.compile(r"\b([A-Z]{2,5})\s?(\d{3}[A-Z]?)\b")

SCIENCE_UNITS = {
    "Department of Biochemistry and Microbiology",
    "Department of Biology",
    "Department of Chemistry",
    "Department of Geography",
    "Department of Mathematics and Statistics",
    "Department of Physics and Astronomy",
    "Faculty of Science",
    "School of Earth and Ocean Sciences",
}
ENGINEERING_UNITS = {
    "Biomedical Engineering",
    "Department of Civil Engineering",
    "Department of Computer Science",
    "Department of Electrical and Computer Engineering",
    "Department of Mechanical Engineering",
    "Faculty of Engineering and Computer Science",
    "Software Engineering",
}
DIRECT_COMPUTING_SUBJECTS = {"CSC", "ECS", "SENG"}
COMPUTING_KEYWORDS = (
    ("algorithm", "algorithms"),
    ("artificial intelligence", "artificial intelligence"),
    ("bioinformatics", "bioinformatics"),
    ("c++", "c++"),
    ("coding", "coding"),
    ("computational", "computational"),
    ("computer aided", "computer-aided work"),
    ("computer-aided", "computer-aided work"),
    ("computer architecture", "computer architecture"),
    ("computer assisted", "computer-assisted work"),
    ("computer-assisted", "computer-assisted work"),
    ("computer communication", "computer communications"),
    ("computer graphics", "computer graphics"),
    ("computer modeling", "computer modeling"),
    ("computer modelling", "computer modelling"),
    ("computer network", "computer networks"),
    ("computer program", "computer programming"),
    ("computer rendering", "computer rendering"),
    ("computer science", "computer science"),
    ("computer security", "computer security"),
    ("computer system", "computer systems"),
    ("computer vision", "computer vision"),
    ("computing", "computing"),
    ("cryptography", "cryptography"),
    ("cyber", "cyber systems/security"),
    ("data analysis", "data analysis"),
    ("data analytics", "data analytics"),
    ("data management", "data management"),
    ("data mining", "data mining"),
    ("data science", "data science"),
    ("data visualization", "data visualization"),
    ("database", "database"),
    ("digital design", "digital design"),
    ("digital health", "digital health"),
    ("digital mapping", "digital mapping"),
    ("digital signal", "digital signal processing"),
    ("digital system", "digital systems"),
    ("digital video", "digital video"),
    ("distributed", "distributed systems"),
    ("embedded", "embedded systems"),
    ("finite element", "finite element methods"),
    ("geographic information", "geographic information systems"),
    ("gis", "GIS"),
    ("graphics", "graphics"),
    ("image processing", "image processing"),
    ("internet of", "internet of things"),
    ("machine learning", "machine learning"),
    ("matlab", "MATLAB"),
    ("microprocessor", "microprocessor systems"),
    ("mobile application", "mobile applications"),
    ("mobile communication", "mobile communications"),
    ("neural network", "neural networks"),
    ("numerical", "numerical methods"),
    ("operating system", "operating systems"),
    ("optimization", "optimization"),
    ("parallel", "parallel computing"),
    ("programming", "programming"),
    ("python", "Python"),
    ("remote sensing", "remote sensing"),
    ("robot", "robotics"),
    ("scientific computing", "scientific computing"),
    ("signal processing", "signal processing"),
    ("simulation", "simulation"),
    ("software", "software"),
    ("statistical computing", "statistical computing"),
    ("systems analysis", "systems analysis"),
    ("vlsi", "VLSI"),
    ("visualization", "visualization"),
    ("web application", "web applications"),
    ("web mapping", "web mapping"),
    ("wireless network", "wireless networks"),
)


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


def fetch_detail(session: requests.Session, catalog_id: str, pid: str) -> dict:
    detail = fetch_json(session, f"{CATALOG_API_BASE}/course/{catalog_id}/{pid}")
    if not isinstance(detail, dict):
        raise RuntimeError(f"Unexpected course detail payload for {pid}.")
    return detail


def normalize_course_code(subject: str, number: str) -> str:
    return f"{subject}{number}".replace(" ", "")


def normalize_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def plain_text(*html_blobs: object) -> str:
    return normalize_text(
        " ".join(
            BeautifulSoup(str(blob), "html.parser").get_text(" ", strip=True)
            for blob in html_blobs
            if blob
        )
    )


def extract_course_codes(*html_blobs: object) -> set[str]:
    codes: set[str] = set()
    for blob in html_blobs:
        if not blob:
            continue
        text = plain_text(blob)
        for subject, number in COURSE_CODE_RE.findall(text):
            codes.add(normalize_course_code(subject, number))
    return codes


def department_name(course: dict) -> str:
    return (course.get("groupFilter1") or {}).get("name", "")


def subject_code(course: dict) -> str:
    return (course.get("subjectCode") or {}).get("name", "")


def course_code(course: dict) -> str:
    return course.get("code", "")


def is_science_or_engineering_course(course: dict) -> bool:
    department = department_name(course)
    return department in SCIENCE_UNITS or department in ENGINEERING_UNITS


def computing_keyword_hits(text: str) -> list[str]:
    lowered = text.lower()
    matches = []
    for token, label in COMPUTING_KEYWORDS:
        if re.search(rf"(?<![a-z0-9]){re.escape(token)}(?![a-z0-9])", lowered):
            matches.append(label)
    return sorted(set(matches), key=str.lower)


def computing_seed_reason(course: dict) -> str | None:
    subject = subject_code(course)
    if subject in DIRECT_COMPUTING_SUBJECTS:
        return f"{subject} subject"
    if not is_science_or_engineering_course(course):
        return None

    text = plain_text(course.get("title"), course.get("description"))
    hits = computing_keyword_hits(text)
    if not hits:
        return None
    visible_hits = ", ".join(hits[:4])
    if len(hits) > 4:
        visible_hits += f", +{len(hits) - 4} more"
    return f"keyword match: {visible_hits}"


def catalog_course_url(pid: str) -> str:
    return f"https://www.uvic.ca/calendar/undergrad/index.php#/courses/{pid}"


def build_course_manifest_row(
    course: dict,
    *,
    role: str,
    seed_reason: str = "",
) -> dict[str, str]:
    return {
        "course_code": course["code"],
        "course_name": course.get("title", "").strip(),
        "role": role,
        "seed_reason": seed_reason,
        "subject": subject_code(course),
        "department": department_name(course),
        "pid": course.get("pid", ""),
        "id": course.get("id", ""),
        "catalog_url": catalog_course_url(course.get("pid", "")),
    }


def ensure_empty_dir(path: Path) -> None:
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True, exist_ok=True)


def write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def write_csv(path: Path, rows: Iterable[dict[str, str]], fieldnames: Iterable[str]) -> None:
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(fieldnames), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def collect_prerequisite_codes(detail: dict) -> set[str]:
    return extract_course_codes(
        detail.get("preAndCorequisites"),
        detail.get("preOrCorequisites"),
        detail.get("corequisites"),
    )


def collect_cross_listed_codes(detail: dict) -> set[str]:
    codes = set()
    for cross_listed in detail.get("crossListedCourses") or []:
        code = cross_listed.get("__catalogCourseId")
        if code:
            codes.add(code)
    return codes


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
    output_root = repo_root / "data" / "catalog" / "computing"
    detail_root = output_root / "course_details"
    ensure_empty_dir(output_root)
    detail_root.mkdir(parents=True, exist_ok=True)

    session = requests.Session()
    meta = discover_catalog_meta(session)
    all_courses = paginate_search(session, meta.catalog_id, "courses")

    courses_by_code: dict[str, dict] = {}
    duplicate_course_codes: dict[str, list[str]] = {}
    for course in all_courses:
        code = course.get("code")
        if not code:
            continue
        if code in courses_by_code:
            duplicate_course_codes.setdefault(code, [courses_by_code[code].get("pid", "")]).append(
                course.get("pid", "")
            )
            continue
        courses_by_code[code] = course

    seed_reasons = {
        course["code"]: reason
        for course in all_courses
        for reason in [computing_seed_reason(course)]
        if course.get("code") and reason
    }
    seed_codes = set(seed_reasons)
    included_codes = set(seed_codes)
    missing_prereq_codes: set[str] = set()
    direct_prereq_edges: set[tuple[str, str]] = set()
    details: dict[str, dict] = {}

    queue = sorted(seed_codes)
    visited: set[str] = set()
    while queue:
        code = queue.pop(0)
        if code in visited:
            continue
        visited.add(code)
        summary = courses_by_code.get(code)
        if summary is None:
            missing_prereq_codes.add(code)
            continue

        detail = fetch_detail(session, meta.catalog_id, summary["pid"])
        details[code] = detail
        for prereq_code in sorted(collect_prerequisite_codes(detail)):
            direct_prereq_edges.add((prereq_code, code))
            if prereq_code not in courses_by_code:
                missing_prereq_codes.add(prereq_code)
                continue
            if prereq_code not in included_codes:
                included_codes.add(prereq_code)
                queue.append(prereq_code)

        for cross_listed_code in sorted(collect_cross_listed_codes(detail)):
            if cross_listed_code in courses_by_code and cross_listed_code not in included_codes:
                included_codes.add(cross_listed_code)
                queue.append(cross_listed_code)

    included_summaries = [courses_by_code[code] for code in sorted(included_codes) if code in courses_by_code]
    manifest_rows = [
        build_course_manifest_row(
            course,
            role="computing" if course["code"] in seed_codes else "prerequisite",
            seed_reason=seed_reasons.get(course["code"], ""),
        )
        for course in sorted(included_summaries, key=lambda item: item["code"])
    ]

    for code, detail in details.items():
        write_json(detail_root / f"{code}.json", detail)

    missing_detail_codes = sorted(code for code in included_codes if code not in details)
    manifest = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "catalog_id": meta.catalog_id,
            "term_code": meta.term_code,
            "publish_timetable": meta.publish_timetable,
            "undergrad_calendar_url": meta.source_url,
            "search_api_base": CATALOG_API_BASE,
            "scope_rule": (
                "Seed courses are current UVic undergraduate calendar courses in Science or "
                "Engineering and Computer Science that are direct computing subjects or match "
                "computing/data/software/numerical/GIS/systems keywords; prerequisite courses "
                "are then followed recursively."
            ),
            "science_units": sorted(SCIENCE_UNITS),
            "engineering_units": sorted(ENGINEERING_UNITS),
            "direct_computing_subjects": sorted(DIRECT_COMPUTING_SUBJECTS),
        },
        "counts": {
            "all_courses": len(all_courses),
            "seed_courses": len(seed_codes),
            "prerequisite_only_courses": len(included_codes - seed_codes),
            "total_courses": len(included_codes),
            "direct_prerequisite_edges": len(direct_prereq_edges),
            "missing_prereq_codes": len(missing_prereq_codes),
        },
        "seed_course_codes": sorted(seed_codes),
        "prerequisite_only_course_codes": sorted(included_codes - seed_codes),
        "missing_prereq_codes": sorted(missing_prereq_codes),
        "missing_detail_codes": missing_detail_codes,
        "duplicate_course_codes": duplicate_course_codes,
        "seed_reasons": seed_reasons,
        "direct_prerequisite_edges": [
            {"source": source, "target": target}
            for source, target in sorted(direct_prereq_edges)
            if source in included_codes and target in included_codes
        ],
    }

    write_json(output_root / "manifest.json", manifest)
    write_csv(
        output_root / "course_manifest.csv",
        manifest_rows,
        fieldnames=(
            "course_code",
            "course_name",
            "role",
            "seed_reason",
            "subject",
            "department",
            "pid",
            "id",
            "catalog_url",
        ),
    )

    print(f"Catalog ID: {meta.catalog_id}")
    print(f"Term code: {meta.term_code}")
    print(f"Computing seed courses: {len(seed_codes)}")
    print(f"Total courses in prerequisite closure: {len(included_codes)}")
    if missing_prereq_codes:
        print("Missing prerequisite course codes:", ", ".join(sorted(missing_prereq_codes)))


if __name__ == "__main__":
    main()
