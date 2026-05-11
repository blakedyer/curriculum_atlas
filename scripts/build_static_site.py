#!/usr/bin/env python3
from __future__ import annotations

import csv
import html
import json
import re
import shutil
import textwrap
from collections import Counter, deque
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable

from bs4 import BeautifulSoup
from graphviz import Digraph

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data" / "catalog"
BUILD_DIR = ROOT / "build" / "html"
STYLE_SOURCE = ROOT / "site_assets" / "program-guide.css"
SCRIPT_SOURCE = ROOT / "site_assets" / "program-guide.js"
HERO_SOURCE_DIR = ROOT / "site_assets" / "heroes"
PROGRAM_GRAPH_DIR = BUILD_DIR / "assets" / "graphs" / "programs"
COURSE_GRAPH_DIR = BUILD_DIR / "assets" / "graphs" / "courses"
HERO_BUILD_DIR = BUILD_DIR / "assets" / "heroes"
SITE_NAME = "SEOS Curriculum Atlas"
RESEARCH_SITE_URL = "https://blakedyer.github.io/"
TEACHING_SITE_URL = "https://eos-courses.readthedocs.io/en/latest/"
ATLAS_SITE_URL = "https://blakedyer.github.io/curriculum_atlas/"
CURRICULUM_SITE_URL = "https://blakedyer.github.io/seos_curriculum/"
HERO_ASSET_URL = f"{ATLAS_SITE_URL}assets/heroes/"

SUBJECT_NAMES = {
    "EOS": "Earth and Ocean Sciences",
    "BIOL": "Biology",
    "BIOC": "Biochemistry",
    "CHEM": "Chemistry",
    "CSC": "Computer Science",
    "GEOG": "Geography",
    "MATH": "Mathematics",
    "PHYS": "Physics",
    "STAT": "Statistics",
}

SUBJECT_COLORS = {
    "EOS": "#d7e9ef",
    "BIOL": "#dbe8d2",
    "BIOC": "#e2e8d5",
    "CHEM": "#ead9b8",
    "CSC": "#e7ddec",
    "GEOG": "#e7e2d8",
    "MATH": "#dfe3f4",
    "PHYS": "#efd8cf",
    "STAT": "#e6dde9",
}

PROGRAM_REQUIRED_STYLE = {
    "fillcolor": "#d7e9ef",
    "color": "#1f4f66",
    "fontcolor": "#17232b",
    "penwidth": "1.6",
}

PROGRAM_SUPPORT_STYLE = {
    "fillcolor": "#f9f9f9",
    "color": "#363636",
    "fontcolor": "#363636",
    "penwidth": "1.0",
}

PROGRAM_OPTION_STYLES = [
    {"fillcolor": "#ead9b8", "color": "#8f6a3b", "fontcolor": "#3f3120", "penwidth": "1.3"},
    {"fillcolor": "#dbe8d2", "color": "#567447", "fontcolor": "#24311e", "penwidth": "1.3"},
    {"fillcolor": "#efd8cf", "color": "#8f5945", "fontcolor": "#3f251d", "penwidth": "1.3"},
    {"fillcolor": "#e2deef", "color": "#665683", "fontcolor": "#2f2741", "penwidth": "1.3"},
    {"fillcolor": "#e7e2d8", "color": "#746554", "fontcolor": "#342d25", "penwidth": "1.3"},
    {"fillcolor": "#dfe3f4", "color": "#576989", "fontcolor": "#263246", "penwidth": "1.3"},
]

SIMPLIFIED_ROLE_GROUPS = (
    {
        "label": "Programming I",
        "codes": ("CSC110", "CSC111"),
    },
    {
        "label": "Intro biology",
        "codes": ("BIOL150A", "BIOL184"),
    },
    {
        "label": "Calculus I",
        "codes": ("MATH100", "MATH102", "MATH109"),
    },
    {
        "label": "Physics I",
        "codes": ("PHYS102A", "PHYS110", "PHYS120", "PHYS122"),
    },
    {
        "label": "Physics II",
        "codes": ("PHYS102B", "PHYS111", "PHYS130", "PHYS125"),
    },
    {
        "label": "Intro statistics",
        "codes": ("STAT255", "STAT260"),
    },
    {
        "label": "Intro geophysics",
        "codes": ("EOS210", "PHYS210"),
    },
)

PROGRAM_CATEGORY_LABELS = {
    "seos-only": "SEOS only",
    "honours": "Honours",
    "major": "Major",
    "minor": "Minor",
    "general": "General",
    "combined": "Combined",
}

SIMPLIFIED_BLOCK_LABELS = {
    frozenset({"BIOL150A", "BIOL186"}): "Intro biology",
    frozenset({"CSC110", "CSC111"}): "Programming I",
    frozenset({"CHEM101", "CHEM150"}): "Chemistry I",
    frozenset({"GEOG328", "GEOG329"}): "GIS",
    frozenset({"BIOL150A", "BIOL184"}): "Intro biology",
    frozenset({"MATH100", "MATH102", "MATH109"}): "Calculus I",
    frozenset({"MATH100", "MATH109"}): "Calculus I",
    frozenset({"MATH100", "MATH101", "MATH102", "MATH109", "MATH151"}): "First-year calculus",
    frozenset({"MATH100", "MATH101", "MATH102", "MATH109"}): "First-year calculus",
    frozenset({"MATH100", "MATH101", "MATH109"}): "First-year calculus",
    frozenset({"MATH110", "MATH211"}): "Linear algebra I",
    frozenset({"MATH200", "MATH202", "MATH204"}): "Second-year calculus",
    frozenset({"MATH202", "MATH204"}): "Advanced calculus",
    frozenset({"MATH200", "MATH204"}): "Calculus III-IV",
    frozenset({"MATH248", "PHYS248"}): "Computational methods",
    frozenset({"EOS325", "MATH204"}): "Modelling or calculus",
    frozenset({"STAT255", "STAT260"}): "Intro statistics",
    frozenset({"STAT254", "STAT255", "STAT260"}): "Intro statistics",
    frozenset({"EOS210", "PHYS210"}): "Intro geophysics",
    frozenset({"PHYS110", "PHYS120"}): "Physics I",
    frozenset({"PHYS102A", "PHYS110", "PHYS120"}): "Physics I",
    frozenset({"PHYS102B", "PHYS111", "PHYS130"}): "Physics II",
    frozenset({"PHYS102A", "PHYS102B", "PHYS110", "PHYS111", "PHYS120", "PHYS130"}): "First-year physics",
    frozenset({"PHYS110", "PHYS111", "PHYS120", "PHYS130"}): "First-year physics",
}

DEPARTMENT_LABELS = {
    "seos": "SEOS",
    "bioc": "Biochemistry",
    "biol": "Biology",
    "chem": "Chemistry",
    "csc": "Computer Science",
    "geog": "Geography",
    "math": "Mathematics",
    "phys": "Physics",
    "stat": "Statistics",
}

COURSE_THEME_RULES = (
    ("field", "Field", ("field school", "field course", "field trip", "field component", "fieldwork", "field work", "mapping", "expedition", "outcrop")),
    ("climate", "Climate", ("climate", "weather", "atmospher", "meteorolog", "cryospher")),
    ("ocean", "Ocean", ("ocean", "marine", "oceanograph", "hydrospher", "coast")),
    ("earth", "Earth", ("earth", "geolog", "tecton", "mineral", "sediment", "stratigraph", "petrolog", "rock", "geomorph")),
    ("geophysics", "Geophysics", ("geophys", "seism", "gravity", "geomagnet", "paleomagnet", "heat flow")),
    ("chemistry", "Chemistry", ("chemistry", "chemical", "geochem", "isotope", "aqueous", "ore", "mining")),
    ("biology", "Biology", ("biology", "biological", "ecolog", "ecosystem", "biodivers", "organism")),
    ("math", "Mathematics", ()),
    ("programming", "Computing", ("program", "coding", "software", "algorithm", "data", "model", "modelling", "numerical", "statistic", "analysis", "comput", "gis", "remote sensing")),
    ("environment", "Environment and Resources", ("environment", "environmental", "hazard", "sustainab", "resource", "pollution")),
    ("physics", "Physics", ("physics", "mechanic", "dynamics", "thermodynam", "optics", "quantum", "fluid")),
)

CONTACT_SUMMARY_BUCKETS = (
    ("year-1", "Year 1"),
    ("year-2", "Year 2"),
    ("years-3-4", "Years 3 + 4"),
)

THEME_COLORS = {
    "field": "oklch(76% 0.13 73)",
    "climate": "oklch(76% 0.12 206)",
    "ocean": "oklch(57% 0.16 255)",
    "earth": "oklch(62% 0.11 47)",
    "geophysics": "oklch(62% 0.15 286)",
    "chemistry": "oklch(68% 0.15 28)",
    "biology": "oklch(65% 0.14 142)",
    "math": "oklch(72% 0.15 120)",
    "programming": "oklch(66% 0.15 325)",
    "environment": "oklch(61% 0.13 178)",
    "physics": "oklch(64% 0.16 16)",
}

COURSE_THEME_OVERRIDES = {
    "EOS300": ("earth",),
    "EOS330": ("earth",),
    "EOS400": ("earth",),
    "EOS401": ("ocean",),
}


@dataclass
class CourseRecord:
    code: str
    name: str
    catalog_url: str
    detail: dict
    rule_nodes: list[dict]
    prereq_codes: list[str]
    placeholder: bool = False
    used_by_programs: set[str] = field(default_factory=set)
    dependents: set[str] = field(default_factory=set)

    @property
    def subject(self) -> str:
        return subject_from_code(self.code)


@dataclass
class ProgramRecord:
    code: str
    name: str
    title: str
    catalog_url: str
    detail: dict
    sections: list[dict]
    explicit_course_codes: list[str]
    text_requirements: list[str]
    section_course_map: dict[str, str]
    streams: list["ProgramStreamRecord"] = field(default_factory=list)
    support_codes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class CourseGroupRecord:
    primary_code: str
    codes: tuple[str, ...]
    label: str
    tooltip: str


@dataclass
class ProgramStreamRecord:
    slug: str
    title: str
    description: str
    sections: list[dict]
    explicit_course_codes: list[str]
    text_requirements: list[str]
    section_course_map: dict[str, str]
    support_codes: list[str] = field(default_factory=list)


@dataclass
class ContactPathRecord:
    slug: str
    title: str
    note: str
    sections: list[dict]
    stream: ProgramStreamRecord | None = None


@dataclass(frozen=True)
class GraphModeRecord:
    key: str
    asset_suffix: str
    button_label: str
    copy_text: str
    year_ordered: bool = False


PROGRAM_GRAPH_MODES = (
    GraphModeRecord(
        key="simplified",
        asset_suffix="--simplified",
        button_label="Simplified view",
        copy_text="Simplified view: collapse recurring early-sequence options and keep the prerequisite flow readable.",
    ),
    GraphModeRecord(
        key="full",
        asset_suffix="",
        button_label="Full view",
        copy_text="Full view: keep the complete prerequisite structure and the separate course variants named in the last UVic calendar sync.",
    ),
)


COURSE_CODE_PATTERN = re.compile(r"\b([A-Z]{2,5})\s*([0-9]{3}[A-Z]?)\b")
CREDIT_ONLY_ONE_OF_PATTERN = re.compile(
    r"Credit will be granted for only one of ([^.]+)\.",
    re.IGNORECASE,
)
MINIMUM_STAT_PREREQ_PATTERN = re.compile(
    r"^1\.?5\s+units?\s+minimum\s+200\s+level\s+stat\s+or\s+equivalent$",
    re.IGNORECASE,
)
SUMMER_FIELD_COURSE_CODES = {"EOS300", "EOS400", "EOS401"}


def e(text: str | None) -> str:
    return html.escape(text or "")


def normalize_text(text: str | None) -> str:
    return re.sub(r"\s+", " ", text or "").strip(" :\n\t")


def unique_ordered(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        if value and value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def read_csv_rows(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def subject_from_code(code: str) -> str:
    match = re.match(r"[A-Z]+", code)
    return match.group(0) if match else "OTHER"


def subject_name(code: str) -> str:
    return SUBJECT_NAMES.get(subject_from_code(code), subject_from_code(code))


def subject_color(code: str, *, missing: bool = False) -> str:
    if missing:
        return "#f6efe5"
    return SUBJECT_COLORS.get(subject_from_code(code), "#f2ece3")


def normalize_course_code(code: str | None) -> str:
    return re.sub(r"\s+", "", (code or "").upper())


def extract_course_codes_from_text(text: str | None) -> list[str]:
    plain_text = BeautifulSoup(text or "", "html.parser").get_text(" ", strip=True)
    return unique_ordered(
        f"{match.group(1).upper()}{match.group(2).upper()}"
        for match in COURSE_CODE_PATTERN.finditer(plain_text)
    )


def slugify_token(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def strip_course_title_from_rule(text: str, code: str) -> str:
    cleaned = normalize_text(text)
    cleaned = re.sub(rf"^{re.escape(code)}\s*[-:]\s*", "", cleaned)
    cleaned = re.sub(r"\s*\([0-9.]+\)\s*$", "", cleaned)
    return cleaned or code


def iter_program_course_entries(nodes: list[dict]) -> Iterable[tuple[str, str]]:
    for node in nodes:
        if node["kind"] == "course":
            yield node["code"], strip_course_title_from_rule(node.get("text") or node["code"], node["code"])
            continue
        if node["kind"] == "group":
            yield from iter_program_course_entries(node["children"])


def is_eos_base_program(program: ProgramRecord) -> bool:
    return program.code in {"BSC-EOSM", "BSC-EOSH"} and bool(program.streams)


def program_named_codes(
    program: ProgramRecord,
    stream: ProgramStreamRecord | None = None,
    *,
    include_stream_courses: bool = True,
) -> list[str]:
    if stream is not None:
        return unique_ordered(program.explicit_course_codes + stream.explicit_course_codes)
    if not program.streams or include_stream_courses:
        return unique_ordered(
            program.explicit_course_codes
            + [code for current_stream in program.streams for code in current_stream.explicit_course_codes]
        )
    return list(program.explicit_course_codes)


def program_section_lookup(program: ProgramRecord, stream: ProgramStreamRecord | None = None) -> dict[str, str]:
    mapping = dict(program.section_course_map)
    if stream is not None:
        for code, title in stream.section_course_map.items():
            mapping.setdefault(code, title)
        return mapping
    for current_stream in program.streams:
        for code, title in current_stream.section_course_map.items():
            mapping.setdefault(code, title)
    return mapping


def program_support_codes(program: ProgramRecord, stream: ProgramStreamRecord | None = None) -> list[str]:
    return stream.support_codes if stream is not None else program.support_codes


def program_graph_sections(program: ProgramRecord, stream: ProgramStreamRecord | None = None) -> list[dict]:
    return program.sections + (stream.sections if stream is not None else [])


def section_bucket_key(title: str) -> str | None:
    reference_key = section_reference_key(title)
    if reference_key == "year-1":
        return "year-1"
    if reference_key == "year-2":
        return "year-2"
    if reference_key in {"year-3", "year-4", "years-3-4"}:
        return "years-3-4"
    return None


def build_program_year_group_lookup(
    program: ProgramRecord,
    course_group_lookup: dict[str, str],
    stream: ProgramStreamRecord | None = None,
) -> dict[str, str]:
    grouped: dict[str, str] = {}

    for section in program_graph_sections(program, stream):
        bucket_key = section_bucket_key(section["title"])
        if bucket_key is None:
            continue
        for code in collect_course_codes(section["rules"]):
            group_code = course_group_lookup.get(code, code)
            grouped.setdefault(group_code, bucket_key)

    return grouped


def build_program_elective_year_group_lookup(
    program: ProgramRecord,
    *,
    courses: dict[str, CourseRecord],
    visible_groups: set[str],
    explicit_year_groups: dict[str, str],
    course_group_lookup: dict[str, str],
    stream: ProgramStreamRecord | None = None,
) -> dict[str, str]:
    inferred: dict[str, str] = {}

    for section in program_graph_sections(program, stream):
        bucket_key = section_bucket_key(section["title"])
        if bucket_key is None:
            continue
        note_lines = collect_graph_note_lines(section["rules"])
        for note_line in note_lines:
            candidate_codes, _note = resolve_elective_candidate_codes(
                note_line,
                section_title=section["title"],
                program=program,
                stream=stream,
                courses=courses,
                path_codes=set(),
            )
            for code in candidate_codes:
                group_code = course_group_lookup.get(code, code)
                if group_code not in visible_groups:
                    continue
                if group_code in explicit_year_groups or group_code in inferred:
                    continue
                inferred[group_code] = bucket_key

    return inferred


def infer_flexible_group_bucket_preferences(
    *,
    visible_groups: set[str],
    slotted_groups: dict[str, str],
    dependent_map: dict[str, set[str]],
) -> dict[str, str]:
    bucket_order = {"year-1": 0, "year-2": 1, "years-3-4": 2}
    preferences: dict[str, str] = {}

    for start_group in visible_groups:
        if start_group in slotted_groups:
            continue
        queue = deque([(start_group, 0)])
        visited = {start_group}
        matches: list[tuple[int, int, str]] = []
        while queue:
            current_group, depth = queue.popleft()
            for next_group in dependent_map.get(current_group, set()):
                if next_group in visited:
                    continue
                visited.add(next_group)
                next_depth = depth + 1
                bucket_key = slotted_groups.get(next_group)
                if bucket_key in bucket_order:
                    matches.append((next_depth, bucket_order[bucket_key], bucket_key))
                queue.append((next_group, next_depth))
        if matches:
            _depth, _order, bucket_key = min(matches)
            preferences[start_group] = bucket_key

    return preferences


def stream_asset_stem(program: ProgramRecord, stream: ProgramStreamRecord) -> str:
    return f"{program.code}--{stream.slug}"


def program_graph_note_lines(program: ProgramRecord, stream: ProgramStreamRecord | None = None) -> list[str]:
    lines = unique_ordered(
        note
        for section in program_graph_sections(program, stream)
        for note in collect_graph_note_lines(section["rules"])
    )
    return condense_graph_note_lines(lines)


def course_graph_note_lines(
    course: CourseRecord,
    courses: dict[str, CourseRecord],
    course_groups: dict[str, CourseGroupRecord],
    course_group_lookup: dict[str, str],
) -> list[str]:
    focus_group = course_group_lookup.get(course.code, course.code)
    group_record = course_groups.get(focus_group)
    if group_record is None:
        return condense_graph_note_lines(collect_graph_note_lines(course.rule_nodes))

    lines = unique_ordered(
        note
        for group_code in group_record.codes
        if group_code in courses
        for note in collect_graph_note_lines(courses[group_code].rule_nodes)
    )
    return condense_graph_note_lines(lines)


def build_program_option_sets(
    sections: list[dict],
    *,
    explicit_groups: set[str],
    course_group_lookup: dict[str, str],
) -> tuple[set[str], list[dict]]:
    required_groups: set[str] = set()
    raw_option_sets: list[dict] = []
    section_option_totals: dict[str, int] = {}

    def visible_groups(node: dict) -> set[str]:
        if node["kind"] == "course":
            group_code = course_group_lookup.get(node["code"], node["code"])
            return {group_code} if group_code in explicit_groups else set()
        if node["kind"] != "group":
            return set()
        groups: set[str] = set()
        for child in node["children"]:
            groups.update(visible_groups(child))
        return groups

    def walk(node: dict, section_title: str, *, inside_choice: bool = False) -> None:
        if node["kind"] == "course":
            group_code = course_group_lookup.get(node["code"], node["code"])
            if inside_choice or group_code not in explicit_groups:
                return
            required_groups.add(group_code)
            return

        if node["kind"] != "group":
            return

        kind, count = requirement_group_kind(node["label"])
        if kind == "choose":
            raw_option_sets.append(
                {
                    "section": section_title,
                    "count": count,
                    "branches": [],
                }
            )
            section_option_totals[section_title] = section_option_totals.get(section_title, 0) + 1
            option_index = len(raw_option_sets) - 1
            for child in node["children"]:
                branch_groups = visible_groups(child)
                if branch_groups:
                    raw_option_sets[option_index]["branches"].append(branch_groups)
                walk(child, section_title, inside_choice=True)
            return

        for child in node["children"]:
            walk(child, section_title, inside_choice=inside_choice)

    for section in sections:
        for rule in section["rules"]:
            walk(rule, section["title"])

    section_seen: dict[str, int] = {}
    cleaned_option_sets: list[dict] = []
    for option_set in raw_option_sets:
        branches = [set(branch) - required_groups for branch in option_set["branches"] if branch]
        branches = [branch for branch in branches if branch]
        if not branches:
            continue

        common_groups = set.intersection(*branches) if branches else set()
        if common_groups:
            required_groups.update(common_groups)
            branches = [branch - common_groups for branch in branches]
            branches = [branch for branch in branches if branch]

        if not branches:
            continue

        unique_branches: list[tuple[str, ...]] = []
        seen_signatures: set[tuple[str, ...]] = set()
        for branch in branches:
            signature = tuple(sorted(branch, key=course_sort_key))
            if signature in seen_signatures:
                continue
            seen_signatures.add(signature)
            unique_branches.append(signature)

        if not unique_branches:
            continue

        if len(unique_branches) == 1:
            required_groups.update(unique_branches[0])
            continue

        groups = sorted({code for branch in unique_branches for code in branch}, key=course_sort_key)
        section_title = option_set["section"]
        section_seen[section_title] = section_seen.get(section_title, 0) + 1
        if section_option_totals.get(section_title, 0) > 1:
            label = f"{section_title} option {chr(64 + section_seen[section_title])}"
        else:
            label = f"{section_title} options"
        if option_set["count"]:
            label = f"{label} (choose {option_set['count']})"
        cleaned_option_sets.append(
            {
                "label": label,
                "groups": groups,
            }
        )

    return required_groups, cleaned_option_sets


def build_program_node_styles(
    program: ProgramRecord,
    stream: ProgramStreamRecord | None,
    *,
    course_group_lookup: dict[str, str],
    include_stream_courses: bool = True,
) -> tuple[dict[str, dict[str, str]], list[tuple[str, dict[str, str]]]]:
    explicit_groups = {
        course_group_lookup.get(code, code)
        for code in program_named_codes(program, stream, include_stream_courses=include_stream_courses)
    }
    support_groups = {
        course_group_lookup.get(code, code)
        for code in program_support_codes(program, stream)
    }
    required_groups, option_sets = build_program_option_sets(
        program_graph_sections(program, stream),
        explicit_groups=explicit_groups,
        course_group_lookup=course_group_lookup,
    )

    style_map: dict[str, dict[str, str]] = {}
    for group_code in explicit_groups:
        style_map[group_code] = dict(PROGRAM_REQUIRED_STYLE)

    legend_items: list[tuple[str, dict[str, str]]] = [
        ("Required program course", PROGRAM_REQUIRED_STYLE),
        ("Related prerequisite course", PROGRAM_SUPPORT_STYLE),
    ]

    for index, option_set in enumerate(option_sets):
        option_style = PROGRAM_OPTION_STYLES[index % len(PROGRAM_OPTION_STYLES)]
        legend_items.append((option_set["label"], option_style))
        for group_code in option_set["groups"]:
            if group_code in required_groups:
                continue
            style_map[group_code] = dict(option_style)

    for group_code in support_groups - explicit_groups:
        style_map[group_code] = dict(PROGRAM_SUPPORT_STYLE)

    return style_map, legend_items


def course_sort_key(code: str) -> tuple:
    prefix = subject_from_code(code)
    digits = re.findall(r"\d+", code)
    number = int(digits[0]) if digits else 0
    return (prefix, number, code)


def format_date_label(raw_iso: str) -> str:
    dt = datetime.fromisoformat(raw_iso)
    return f"{dt.strftime('%B')} {dt.day}, {dt.year}"


def child_list_items(ul_tag) -> list:
    items = []
    for child in ul_tag.children:
        if not getattr(child, "name", None):
            continue
        if child.name == "li":
            items.append(child)
        else:
            items.extend(child.find_all("li", recursive=False))
    return items


def parse_equivalent_stat_prereq(text: str | None) -> dict | None:
    cleaned = normalize_text(text).lower()
    if not MINIMUM_STAT_PREREQ_PATTERN.fullmatch(cleaned):
        return None

    def stat_course(code: str) -> dict:
        return {"kind": "course", "code": code, "text": code}

    return {
        "kind": "group",
        "label": "Complete 1 of: 200 level STAT or equivalent",
        "children": [stat_course("STAT254"), stat_course("STAT255"), stat_course("STAT260")],
    }


def parse_rule_item(li_tag) -> dict:
    nested_ul = li_tag.find("ul")
    if nested_ul is None:
        anchor = li_tag.find("a")
        if anchor:
            code = normalize_text(anchor.get_text(" ", strip=True))
            return {
                "kind": "course",
                "code": code,
                "text": normalize_text(li_tag.get_text(" ", strip=True)),
            }
        text = normalize_text(li_tag.get_text(" ", strip=True))
        synthetic = parse_equivalent_stat_prereq(text)
        if synthetic is not None:
            return synthetic
        return {"kind": "text", "text": text}

    clone = BeautifulSoup(str(li_tag), "html.parser").find("li")
    for nested in clone.find_all("ul"):
        nested.decompose()
    label = normalize_text(clone.get_text(" ", strip=True))
    return {
        "kind": "group",
        "label": label,
        "children": [parse_rule_item(child) for child in child_list_items(nested_ul)],
    }


def parse_rule_fragment(fragment: str | None) -> list[dict]:
    soup = BeautifulSoup(fragment or "", "html.parser")
    root_ul = soup.find("ul")
    if root_ul is None:
        text = normalize_text(soup.get_text(" ", strip=True))
        return [{"kind": "text", "text": text}] if text else []
    return [parse_rule_item(li_tag) for li_tag in child_list_items(root_ul)]


def parse_course_requirement_nodes(detail: dict) -> list[dict]:
    nodes: list[dict] = []
    for field_name in ("preAndCorequisites", "preOrCorequisites", "corequisites"):
        nodes.extend(parse_rule_fragment(detail.get(field_name)))
    return nodes


def parse_program_sections(fragment: str | None) -> list[dict]:
    soup = BeautifulSoup(fragment or "", "html.parser")
    sections = [section for section in soup.find_all("section") if section.find_parent("section") is None]
    if not sections:
        rules = parse_rule_fragment(fragment)
        return [{"title": "Program requirements", "rules": rules}] if rules else []

    parsed_sections = []
    for section in sections:
        heading = section.find("h2")
        title = normalize_text(heading.get_text(" ", strip=True)) if heading else "Program requirements"
        if not title:
            title = "Program requirements"
        rules = parse_rule_fragment(str(section))
        parsed_sections.append({"title": title, "rules": rules})
    return parsed_sections


def summarize_program_sections(sections: list[dict]) -> tuple[list[str], list[str], dict[str, str]]:
    explicit_codes: list[str] = []
    text_requirements: list[str] = []
    section_course_map: dict[str, str] = {}
    for section in sections:
        section_codes = collect_course_codes(section["rules"])
        explicit_codes.extend(section_codes)
        text_requirements.extend(collect_text_requirements(section["rules"]))
        for course_code in section_codes:
            section_course_map.setdefault(course_code, section["title"])
    return (
        unique_ordered(explicit_codes),
        unique_ordered(text_requirements),
        section_course_map,
    )


def parse_program_streams(detail: dict) -> list["ProgramStreamRecord"]:
    streams: list[ProgramStreamRecord] = []
    for stream_detail in detail.get("specializations") or []:
        stream_title = normalize_text(stream_detail.get("title")) or "Stream"
        stream_sections = parse_program_sections(
            stream_detail.get("requirements") or stream_detail.get("programRequirements")
        )
        stream_codes, stream_notes, stream_section_map = summarize_program_sections(stream_sections)
        stream_description = (
            normalize_text(
                BeautifulSoup(
                    stream_detail.get("description")
                    or stream_detail.get("programRequirements")
                    or "",
                    "html.parser",
                ).get_text(" ", strip=True)
            )
            if stream_detail.get("description") or stream_detail.get("programRequirements")
            else ""
        )
        streams.append(
            ProgramStreamRecord(
                slug=slugify_token(stream_title),
                title=stream_title,
                description=stream_description,
                sections=stream_sections,
                explicit_course_codes=stream_codes,
                text_requirements=stream_notes,
                section_course_map=stream_section_map,
            )
        )
    return streams


def course_credit_value(code: str, courses: dict[str, CourseRecord]) -> float:
    course = courses.get(code)
    if course is None:
        return 1.5
    credits = course.detail.get("credits") or {}
    if isinstance(credits, dict):
        value = credits.get("value")
        if value is not None:
            try:
                return float(value)
            except (TypeError, ValueError):
                pass
        nested = credits.get("credits")
        if isinstance(nested, dict):
            for key in ("max", "min"):
                raw = nested.get(key)
                if raw is None:
                    continue
                try:
                    return float(raw)
                except (TypeError, ValueError):
                    continue
    return 1.5


def parse_hours_catalog_text(raw_text: str | None) -> tuple[float, float, float] | None:
    if not raw_text:
        return None
    match = re.match(r"^\s*([0-9.]+)\s*-\s*([0-9.]+)\s*-\s*([0-9.]+)\s*$", raw_text)
    if not match:
        return None
    return tuple(float(match.group(index)) for index in range(1, 4))


def format_hours_pattern(lecture: float, lab: float, tutorial: float) -> str:
    return (
        f"{format_unit_count(lecture)}-"
        f"{format_unit_count(lab)}-"
        f"{format_unit_count(tutorial)}"
    )


def infer_contact_hours_from_calendar_text(code: str, courses: dict[str, CourseRecord]) -> dict:
    course = courses.get(code)
    if course is None:
        lecture = 3.0
        lab = 0.0
        tutorial = 0.0
        return {
            "lecture": lecture,
            "lab": lab,
            "tutorial": tutorial,
            "total": lecture + lab + tutorial,
            "pattern": format_hours_pattern(lecture, lab, tutorial),
            "source": "assumed",
            "label": "assumed lecture",
            "note": "Course detail is not in the current sync, so the estimate falls back to a lecture-only 3 contact hours per week.",
        }

    parsed_pattern = parse_hours_catalog_text(course.detail.get("hoursCatalogText"))
    if parsed_pattern is not None:
        lecture, lab, tutorial = parsed_pattern
        return {
            "lecture": lecture,
            "lab": lab,
            "tutorial": tutorial,
            "total": lecture + lab + tutorial,
            "pattern": format_hours_pattern(lecture, lab, tutorial),
            "source": "calendar",
            "label": "official calendar hours",
            "note": (
                f"UVic publishes {format_hours_pattern(lecture, lab, tutorial)} in the current calendar snapshot."
            ),
        }

    title = course.name or course.code
    detail_text = normalize_text(
        " ".join(
            part
            for part in (
                title,
                BeautifulSoup(course.detail.get("description") or "", "html.parser").get_text(" ", strip=True),
                BeautifulSoup(course.detail.get("supplementalNotes") or "", "html.parser").get_text(" ", strip=True),
            )
            if part
        )
    ).lower()
    has_lab = bool(
        re.search(
            r"\b(lab|labs|laboratory|laboratories|field course|field school|field trip|field component|field work|fieldwork|mapping)\b",
            detail_text,
        )
    )
    has_tutorial = bool(
        re.search(r"\b(tutorial|tutorials|seminar|seminars|colloquium|colloquia)\b", detail_text)
    )
    lecture = 3.0
    lab = 3.0 if has_lab else 0.0
    tutorial = 2.0 if has_tutorial else 0.0
    assumption_bits = ["3 lecture hours"]
    if has_lab:
        assumption_bits.append("3 lab/field hours")
    if has_tutorial:
        assumption_bits.append("2 tutorial/seminar hours")
    if len(assumption_bits) == 1:
        assumption_note = "No calendar hour pattern is published, so the estimate assumes a lecture-only 3 contact hours per week."
    else:
        assumption_note = (
            "No calendar hour pattern is published, so the estimate assumes "
            + ", ".join(assumption_bits[:-1])
            + (" and " + assumption_bits[-1] if len(assumption_bits) > 1 else assumption_bits[-1])
            + " based on the course title/description."
        )
    return {
        "lecture": lecture,
        "lab": lab,
        "tutorial": tutorial,
        "total": lecture + lab + tutorial,
        "pattern": format_hours_pattern(lecture, lab, tutorial),
        "source": "assumed",
        "label": "assumed hours",
        "note": assumption_note,
    }


def course_level_number(code: str) -> int | None:
    match = re.search(r"[A-Z]{2,5}\s*([0-9])", code)
    if not match:
        return None
    return int(match.group(1))


def is_summer_field_course(code: str, courses: dict[str, CourseRecord]) -> bool:
    if code in SUMMER_FIELD_COURSE_CODES:
        return True
    course = courses.get(code)
    if course is None:
        return False
    haystack = normalize_text(
        " ".join(
            part
            for part in (
                course.name,
                BeautifulSoup(course.detail.get("description") or "", "html.parser").get_text(" ", strip=True),
                BeautifulSoup(course.detail.get("supplementalNotes") or "", "html.parser").get_text(" ", strip=True),
            )
            if part
        )
    ).lower()
    return any(
        marker in haystack
        for marker in (
            "outside of the normal term time",
            "late april",
            "mid-to-late may",
            "after examinations",
            "after the conclusion of eos 300",
        )
    )


def assumed_elective_contact_hours(required_units: float) -> tuple[float, float]:
    return (required_units * 2.0, required_units * 4.0)


def section_year_levels(title: str) -> set[int]:
    lowered = normalize_text(title).lower()
    numbers = [int(value) for value in re.findall(r"\b([1-4])\b", lowered)]
    if not numbers:
        return set()
    return set(numbers)


def section_reference_key(text: str) -> str:
    lowered = normalize_text(text).lower()
    if "year 1" in lowered:
        return "year-1"
    if "year 2" in lowered:
        return "year-2"
    if "year 3 and 4" in lowered or "years 3 and 4" in lowered:
        return "years-3-4"
    if "year 3" in lowered:
        return "year-3"
    if "year 4" in lowered:
        return "year-4"
    return slugify_token(lowered or "program-requirements")


def section_is_combined_years(title: str) -> bool:
    lowered = normalize_text(title).lower()
    return "years " in lowered or "year 3 and 4" in lowered


def extract_grouped_subject_codes(text: str) -> set[str]:
    codes: set[str] = set()
    for match in re.finditer(
        r"\b([A-Z]{2,5})\s+((?:[0-9]{3}[A-Z]?(?:\s*,\s*)?){2,})",
        text,
    ):
        subject = match.group(1)
        for number in re.findall(r"[0-9]{3}[A-Z]?", match.group(2)):
            codes.add(f"{subject}{number}")
    return codes


def extract_excluded_course_codes(text: str) -> set[str]:
    exclusions: set[str] = set()
    for match in re.finditer(r"excluding\s+([^)]+)", text, re.IGNORECASE):
        exclusions.update(extract_course_codes_from_text(match.group(1)))
        exclusions.update(extract_grouped_subject_codes(match.group(1)))
    return exclusions


def course_matches_subject_level_filters(
    code: str,
    text: str,
    course: CourseRecord | None,
) -> bool:
    number_match = re.search(r"([0-9]{3})", code)
    if number_match is None:
        return False
    subject = subject_from_code(code)
    number = int(number_match.group(1))
    level = course_level_number(code)
    if level is None:
        return False

    for match in re.finditer(
        r"\b((?:[A-Z]{2,5}\s*(?:or\s+)?)*)\s*([0-9]{3})\s*-\s*([0-9]{3})",
        text,
    ):
        subjects = re.findall(r"[A-Z]{2,5}", match.group(1))
        if subject in subjects and int(match.group(2)) <= number <= int(match.group(3)):
            return True

    if re.search(rf"\b{re.escape(subject)}\s*{level}00-level\b", text):
        return True

    if re.search(r"300-\s*or\s*400-level", text, re.IGNORECASE):
        subjects = set(re.findall(r"\b[A-Z]{2,5}\b", text))
        if subject in subjects and level in {3, 4}:
            return True

    lowered = text.lower()
    if subject == "EOS" and ("oceanograph" in lowered or "ocean science" in lowered):
        haystack = normalize_text(
            " ".join(
                part
                for part in (
                    course.name if course is not None else code,
                    BeautifulSoup(course.detail.get("description") or "", "html.parser").get_text(" ", strip=True)
                    if course is not None
                    else "",
                )
                if part
            )
        ).lower()
        return "ocean" in haystack or "marine" in haystack

    return False


def program_uses_stream_placeholders(program: ProgramRecord) -> bool:
    return any(
        "stream requirements" in note.lower()
        for note in program.text_requirements
    )


def resolve_elective_candidate_codes(
    text: str,
    *,
    section_title: str,
    program: ProgramRecord,
    stream: ProgramStreamRecord | None,
    courses: dict[str, CourseRecord],
    path_codes: set[str],
) -> tuple[list[str], str]:
    normalized = normalize_text(text)
    lowered = normalized.lower()
    explicit_codes = set(extract_course_codes_from_text(normalized))
    explicit_codes.update(extract_grouped_subject_codes(normalized))
    excluded_codes = extract_excluded_course_codes(normalized)

    if "stream requirements" in lowered and stream is not None:
        target_key = section_reference_key(normalized)
        stream_sections = [
            section
            for section in stream.sections
            if section_reference_key(section["title"]) == target_key
        ]
        candidate_codes = unique_ordered(
            code
            for section in stream_sections
            for code in collect_course_codes(section["rules"])
        )
        note = f"Resolved from the published {stream.title} section referenced by this rule."
        return candidate_codes, note

    candidate_codes: set[str] = set(explicit_codes)
    for code, course in courses.items():
        if code in excluded_codes:
            continue
        if course_matches_subject_level_filters(code, normalized, course):
            candidate_codes.add(code)

    filtered_codes = [
        code
        for code in unique_ordered(sorted(candidate_codes, key=course_sort_key))
        if code not in excluded_codes and course_credit_value(code, courses) > 0
    ]
    available_after_exclusion = [code for code in filtered_codes if code not in path_codes]
    if available_after_exclusion:
        filtered_codes = available_after_exclusion
    elif filtered_codes:
        filtered_codes = filtered_codes

    if filtered_codes:
        missing_codes = [code for code in filtered_codes if code not in courses]
        note_bits = ["Range uses the eligible published candidates that this guide can identify from the rule text."]
        if excluded_codes:
            note_bits.append(
                "Excluded "
                + ", ".join(sorted(excluded_codes, key=course_sort_key))
                + " because the rule marks them as exclusions."
            )
        if missing_codes:
            note_bits.append(
                "Some candidates are not in the current course-detail sync and therefore use the fallback assumption."
            )
        return filtered_codes, " ".join(note_bits)

    generic_levels = section_year_levels(section_title)
    fallback_codes = [
        code
        for code, course in sorted(courses.items(), key=lambda item: course_sort_key(item[0]))
        if course_credit_value(code, courses) > 0
        and code not in excluded_codes
        and (not generic_levels or course_level_number(code) in generic_levels)
    ]
    available_after_exclusion = [code for code in fallback_codes if code not in path_codes]
    if available_after_exclusion:
        fallback_codes = available_after_exclusion
    note = (
        "The rule does not publish a concrete candidate list, so the range falls back to the course pool captured in this guide"
        + (
            f" for year level{'s' if len(generic_levels) > 1 else ''} {', '.join(str(level) for level in sorted(generic_levels))}."
            if generic_levels
            else "."
        )
    )
    return fallback_codes, note


def choose_items_by_count(
    items: list[dict],
    required_count: int,
) -> tuple[list[int], list[int]]:
    if required_count <= 0 or not items:
        return ([], [])
    capped = min(required_count, len(items))
    min_indices = sorted(
        range(len(items)),
        key=lambda index: (
            items[index]["min_regular_hours"],
            items[index]["min_summer_hours"],
            items[index]["min_hours"],
            items[index]["label"],
        ),
    )[:capped]
    max_indices = sorted(
        range(len(items)),
        key=lambda index: (
            items[index]["max_regular_hours"],
            items[index]["max_summer_hours"],
            items[index]["max_hours"],
            items[index]["label"],
        ),
        reverse=True,
    )[:capped]
    return (sorted(min_indices), sorted(max_indices))


def choose_items_by_units(
    items: list[dict],
    required_units: float,
) -> tuple[list[int], list[int], float, float]:
    target = int(round(required_units * 10))
    min_states: dict[int, tuple[float, list[int]]] = {0: (0.0, [])}
    max_states: dict[int, tuple[float, list[int]]] = {0: (0.0, [])}

    for index, item in enumerate(items):
        credit_value = item["max_credits"] if item["max_credits"] > 0 else item["min_credits"]
        credit_steps = int(round(credit_value * 10))
        if credit_steps <= 0:
            continue
        new_min_states = dict(min_states)
        for credit_total, (hours_total, selected) in min_states.items():
            next_credit_total = credit_total + credit_steps
            next_hours_total = hours_total + item["min_regular_hours"]
            next_selected = selected + [index]
            existing = new_min_states.get(next_credit_total)
            if existing is None or next_hours_total < existing[0]:
                new_min_states[next_credit_total] = (next_hours_total, next_selected)
        min_states = new_min_states

        new_max_states = dict(max_states)
        for credit_total, (hours_total, selected) in max_states.items():
            next_credit_total = credit_total + credit_steps
            next_hours_total = hours_total + item["max_regular_hours"]
            next_selected = selected + [index]
            existing = new_max_states.get(next_credit_total)
            if existing is None or next_hours_total > existing[0]:
                new_max_states[next_credit_total] = (next_hours_total, next_selected)
        max_states = new_max_states

    valid_credit_totals = [
        credit_total
        for credit_total in set(min_states) | set(max_states)
        if credit_total >= target
    ]
    if not valid_credit_totals:
        return ([], [], 0.0, 0.0)

    min_overrun = min(credit_total - target for credit_total in valid_credit_totals)
    exactish_credits = [
        credit_total for credit_total in valid_credit_totals if credit_total - target == min_overrun
    ]
    valid_min_credits = [credit_total for credit_total in exactish_credits if credit_total in min_states]
    valid_max_credits = [credit_total for credit_total in exactish_credits if credit_total in max_states]
    min_credit_total = min(
        valid_min_credits,
        key=lambda credit_total: (
            min_states[credit_total][0],
            len(min_states[credit_total][1]),
        ),
    )
    max_credit_total = max(
        valid_max_credits,
        key=lambda credit_total: (
            max_states[credit_total][0],
            -len(max_states[credit_total][1]),
        ),
    )
    return (
        sorted(min_states[min_credit_total][1]),
        sorted(max_states[max_credit_total][1]),
        min_credit_total / 10,
        max_credit_total / 10,
    )


def build_contact_node(
    *,
    kind: str,
    label: str,
    min_hours: float,
    max_hours: float,
    min_credits: float,
    max_credits: float,
    min_regular_hours: float | None = None,
    max_regular_hours: float | None = None,
    min_summer_hours: float = 0.0,
    max_summer_hours: float = 0.0,
    children: list[dict] | None = None,
    meta: dict | None = None,
) -> dict:
    return {
        "kind": kind,
        "label": label,
        "min_hours": min_hours,
        "max_hours": max_hours,
        "min_credits": min_credits,
        "max_credits": max_credits,
        "min_regular_hours": min_hours if min_regular_hours is None else min_regular_hours,
        "max_regular_hours": max_hours if max_regular_hours is None else max_regular_hours,
        "min_summer_hours": min_summer_hours,
        "max_summer_hours": max_summer_hours,
        "children": children or [],
        "meta": meta or {},
    }


def evaluate_contact_rule(
    node: dict,
    *,
    section_title: str,
    program: ProgramRecord,
    stream: ProgramStreamRecord | None,
    courses: dict[str, CourseRecord],
    path_codes: set[str],
) -> dict:
    if node["kind"] == "course":
        code = node["code"]
        estimate = infer_contact_hours_from_calendar_text(code, courses)
        summer_field = is_summer_field_course(code, courses)
        return build_contact_node(
            kind="course",
            label=code,
            min_hours=estimate["total"],
            max_hours=estimate["total"],
            min_credits=course_credit_value(code, courses),
            max_credits=course_credit_value(code, courses),
            min_regular_hours=0.0 if summer_field else estimate["total"],
            max_regular_hours=0.0 if summer_field else estimate["total"],
            min_summer_hours=estimate["total"] if summer_field else 0.0,
            max_summer_hours=estimate["total"] if summer_field else 0.0,
            meta={
                "code": code,
                "title": courses[code].name if code in courses else strip_course_title_from_rule(node.get("text") or code, code),
                "pattern": estimate["pattern"],
                "source": estimate["source"],
                "source_label": estimate["label"],
                "source_note": estimate["note"],
                "season": "summer" if summer_field else "regular",
            },
        )

    if node["kind"] == "text":
        text = normalize_text(node["text"])
        lowered = text.lower()
        if "stream requirements" in lowered and stream is not None:
            target_key = section_reference_key(text)
            matched_sections = [
                section
                for section in stream.sections
                if section_reference_key(section["title"]) == target_key
            ]
            referenced_children = [
                evaluate_contact_section(
                    section,
                    program=program,
                    stream=stream,
                    courses=courses,
                    path_codes=path_codes,
                )
                for section in matched_sections
            ]
            return build_contact_node(
                kind="stream-reference",
                label=text,
                min_hours=sum(child["min_hours"] for child in referenced_children),
                max_hours=sum(child["max_hours"] for child in referenced_children),
                min_credits=sum(child["min_credits"] for child in referenced_children),
                max_credits=sum(child["max_credits"] for child in referenced_children),
                min_regular_hours=sum(child["min_regular_hours"] for child in referenced_children),
                max_regular_hours=sum(child["max_regular_hours"] for child in referenced_children),
                min_summer_hours=sum(child["min_summer_hours"] for child in referenced_children),
                max_summer_hours=sum(child["max_summer_hours"] for child in referenced_children),
                children=referenced_children,
                meta={
                    "source_note": f"Resolved against the published {stream.title} requirements.",
                },
            )

        unit_match = re.search(r"([0-9.]+)\s+units?", lowered)
        if unit_match and ("elective" in lowered or " from " in lowered or " of:" in lowered):
            required_units = float(unit_match.group(1))
            min_regular_hours, max_regular_hours = assumed_elective_contact_hours(required_units)
            return build_contact_node(
                kind="elective-assumption",
                label=text,
                min_hours=min_regular_hours,
                max_hours=max_regular_hours,
                min_credits=required_units,
                max_credits=required_units,
                min_regular_hours=min_regular_hours,
                max_regular_hours=max_regular_hours,
                meta={
                    "required_units": required_units,
                    "eligible_codes": [],
                    "source_note": (
                        "Electives are simplified to 3-0-0 at the low end and 3-3-0 at the high end, scaled to the published unit count."
                    ),
                },
            )

        return build_contact_node(
            kind="note",
            label=text,
            min_hours=0.0,
            max_hours=0.0,
            min_credits=0.0,
            max_credits=0.0,
        )

    child_nodes = [
        evaluate_contact_rule(
            child,
            section_title=section_title,
            program=program,
            stream=stream,
            courses=courses,
            path_codes=path_codes,
        )
        for child in node["children"]
    ]
    cleaned_label = clean_requirement_label(node["label"])
    lowered = cleaned_label.lower()
    choose_match = re.search(r"([0-9.]+)\s+of", lowered)
    units_match = re.search(r"([0-9.]+)\s+units?", lowered)

    if choose_match:
        required_count = max(1, int(round(float(choose_match.group(1)))))
        min_indices, max_indices = choose_items_by_count(child_nodes, required_count)
        return build_contact_node(
            kind="choice-group",
            label=cleaned_label,
            min_hours=sum(child_nodes[index]["min_hours"] for index in min_indices),
            max_hours=sum(child_nodes[index]["max_hours"] for index in max_indices),
            min_credits=sum(child_nodes[index]["min_credits"] for index in min_indices),
            max_credits=sum(child_nodes[index]["max_credits"] for index in max_indices),
            min_regular_hours=sum(child_nodes[index]["min_regular_hours"] for index in min_indices),
            max_regular_hours=sum(child_nodes[index]["max_regular_hours"] for index in max_indices),
            min_summer_hours=sum(child_nodes[index]["min_summer_hours"] for index in min_indices),
            max_summer_hours=sum(child_nodes[index]["max_summer_hours"] for index in max_indices),
            children=child_nodes,
            meta={
                "required_count": required_count,
                "min_selected_indices": min_indices,
                "max_selected_indices": max_indices,
            },
        )

    if units_match and (" from" in lowered or lowered.startswith("complete ")) and child_nodes:
        required_units = float(units_match.group(1))
        min_regular_hours, max_regular_hours = assumed_elective_contact_hours(required_units)
        return build_contact_node(
            kind="elective-assumption",
            label=cleaned_label,
            min_hours=min_regular_hours,
            max_hours=max_regular_hours,
            min_credits=required_units,
            max_credits=required_units,
            min_regular_hours=min_regular_hours,
            max_regular_hours=max_regular_hours,
            meta={
                "required_units": required_units,
                "eligible_codes": sorted(set(collect_course_codes(node["children"])), key=course_sort_key),
                "source_note": (
                    "Electives are simplified to 3-0-0 at the low end and 3-3-0 at the high end, scaled to the published unit count."
                ),
            },
        )

    return build_contact_node(
        kind="group",
        label=cleaned_label,
        min_hours=sum(child["min_hours"] for child in child_nodes),
        max_hours=sum(child["max_hours"] for child in child_nodes),
        min_credits=sum(child["min_credits"] for child in child_nodes),
        max_credits=sum(child["max_credits"] for child in child_nodes),
        min_regular_hours=sum(child["min_regular_hours"] for child in child_nodes),
        max_regular_hours=sum(child["max_regular_hours"] for child in child_nodes),
        min_summer_hours=sum(child["min_summer_hours"] for child in child_nodes),
        max_summer_hours=sum(child["max_summer_hours"] for child in child_nodes),
        children=child_nodes,
    )


def evaluate_contact_section(
    section: dict,
    *,
    program: ProgramRecord,
    stream: ProgramStreamRecord | None,
    courses: dict[str, CourseRecord],
    path_codes: set[str],
) -> dict:
    children = [
        evaluate_contact_rule(
            rule,
            section_title=section["title"],
            program=program,
            stream=stream,
            courses=courses,
            path_codes=path_codes,
        )
        for rule in section["rules"]
    ]
    return build_contact_node(
        kind="section",
        label=section["title"],
        min_hours=sum(child["min_hours"] for child in children),
        max_hours=sum(child["max_hours"] for child in children),
        min_credits=sum(child["min_credits"] for child in children),
        max_credits=sum(child["max_credits"] for child in children),
        min_regular_hours=sum(child["min_regular_hours"] for child in children),
        max_regular_hours=sum(child["max_regular_hours"] for child in children),
        min_summer_hours=sum(child["min_summer_hours"] for child in children),
        max_summer_hours=sum(child["max_summer_hours"] for child in children),
        children=children,
        meta={
            "combined_years": section_is_combined_years(section["title"]),
        },
    )


def build_contact_paths(program: ProgramRecord) -> list[ContactPathRecord]:
    base_path = ContactPathRecord(
        slug="program",
        title=program.name,
        note="Published program requirements only.",
        sections=program.sections,
        stream=None,
    )
    if not program.streams:
        return [base_path]

    if program_uses_stream_placeholders(program):
        paths: list[ContactPathRecord] = []
        if is_eos_base_program(program):
            paths.append(base_path)
        paths.extend(
            ContactPathRecord(
                slug=stream.slug,
                title=stream.title,
                note=(
                    stream.description
                    or "Combines the shared program core with the published stream-specific requirement bundle."
                ),
                sections=program.sections,
                stream=stream,
            )
            for stream in program.streams
        )
        return paths

    paths = [base_path]
    for stream in program.streams:
        extra_sections = [
            {
                "title": (
                    f"{stream.title} add-on"
                    if section["title"] == "Program requirements"
                    else f"{stream.title} {section['title']}"
                ),
                "rules": section["rules"],
            }
            for section in stream.sections
        ]
        paths.append(
            ContactPathRecord(
                slug=stream.slug,
                title=stream.title,
                note=(
                    stream.description
                    or "Adds the published option-specific requirements to the base program totals."
                ),
                sections=program.sections + extra_sections,
                stream=stream,
            )
        )
    return paths


def iter_rule_nodes(nodes: list[dict]) -> Iterable[dict]:
    for node in nodes:
        yield node
        if node["kind"] == "group":
            yield from iter_rule_nodes(node["children"])


def collect_course_codes(nodes: list[dict]) -> list[str]:
    return unique_ordered(
        node["code"] for node in iter_rule_nodes(nodes) if node["kind"] == "course"
    )


def collect_text_requirements(nodes: list[dict]) -> list[str]:
    notes = []
    for node in iter_rule_nodes(nodes):
        if node["kind"] == "text" and node["text"]:
            notes.append(node["text"])
    return unique_ordered(notes)


def requirement_group_kind(label: str) -> tuple[str, str | None]:
    cleaned = clean_requirement_label(label)
    lower = cleaned.lower()
    choice_match = re.search(r"([0-9.]+)\s+of", lower)
    if choice_match:
        return ("choose", choice_match.group(1))
    if "all of" in lower:
        return ("all", None)
    return ("other", None)


def clean_requirement_label(label: str) -> str:
    cleaned = normalize_text(label)
    if cleaned.startswith("Complete "):
        cleaned = cleaned[len("Complete ") :]
    return cleaned


def format_note_label(title: str, lines: list[str], *, width: int = 42) -> str:
    formatted = [title]
    for line in lines:
        wrapped = textwrap.wrap(line, width=width) or [line]
        formatted.extend(wrapped)
    return "\\l".join(formatted) + "\\l"


def format_unit_count(value: float) -> str:
    rounded = round(value, 2)
    if abs(rounded - int(rounded)) < 1e-9:
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def condense_graph_note_lines(lines: list[str]) -> list[str]:
    grouped_units: dict[str, float] = {}
    grouped_order: list[str] = []
    passthrough: list[str] = []
    pattern = re.compile(r"^Complete\s+([0-9.]+)\s+units?\s+(.+)$", re.IGNORECASE)

    for line in lines:
        cleaned = normalize_text(line).rstrip(".")
        match = pattern.match(cleaned)
        if not match:
            passthrough.append(cleaned)
            continue
        remainder = normalize_text(match.group(2))
        if remainder not in grouped_units:
            grouped_units[remainder] = 0.0
            grouped_order.append(remainder)
        grouped_units[remainder] += float(match.group(1))

    combined = [
        f"Complete {format_unit_count(grouped_units[remainder])} units {remainder}"
        for remainder in grouped_order
    ]
    return unique_ordered(combined + passthrough)


def summarize_nonflow_rule(node: dict) -> str | None:
    if node["kind"] == "text":
        return node["text"]

    if node["kind"] != "group":
        return None

    cleaned = clean_requirement_label(node["label"])
    lower = cleaned.lower()
    kind, _ = requirement_group_kind(node["label"])
    if kind == "other" or "elective" in lower or "permission" in lower:
        return cleaned or None
    return None


def collect_graph_note_lines(nodes: list[dict]) -> list[str]:
    notes: list[str] = []
    for node in nodes:
        if node["kind"] == "text":
            if node["text"]:
                notes.append(node["text"])
            continue

        if node["kind"] != "group":
            continue

        summary = summarize_nonflow_rule(node)
        if summary:
            notes.append(summary)
        notes.extend(collect_graph_note_lines(node["children"]))

    return unique_ordered(notes)


def choose_group_primary(codes: Iterable[str]) -> str:
    ordered_codes = sorted(unique_ordered(codes), key=course_sort_key)
    eos_codes = [code for code in ordered_codes if subject_from_code(code) == "EOS"]
    if eos_codes:
        return eos_codes[0]
    return ordered_codes[0]


def format_course_group_label(codes: Iterable[str]) -> str:
    ordered_codes = sorted(unique_ordered(codes), key=course_sort_key)
    if len(ordered_codes) == 1:
        return ordered_codes[0]
    rows = [
        " / ".join(ordered_codes[index : index + 2])
        for index in range(0, len(ordered_codes), 2)
    ]
    return "\\n".join(rows)


def build_course_groups(
    courses: dict[str, CourseRecord],
    *,
    aggressive: bool = False,
) -> tuple[dict[str, CourseGroupRecord], dict[str, str]]:
    adjacency: dict[str, set[str]] = {code: {code} for code in courses}
    custom_labels: dict[str, str] = {}

    for code, course in courses.items():
        for entry in course.detail.get("crossListedCourses") or []:
            other_code = normalize_course_code(entry.get("__catalogCourseId"))
            if other_code in courses:
                adjacency[code].add(other_code)
                adjacency[other_code].add(code)

        for match in CREDIT_ONLY_ONE_OF_PATTERN.finditer(course.detail.get("supplementalNotes") or ""):
            codes_in_note = [
                note_code
                for note_code in extract_course_codes_from_text(match.group(1))
                if note_code in courses
            ]
            for left_code in codes_in_note:
                adjacency.setdefault(left_code, {left_code})
                for right_code in codes_in_note:
                    adjacency[left_code].add(right_code)

    if aggressive:
        for group in SIMPLIFIED_ROLE_GROUPS:
            existing_codes = [code for code in group["codes"] if code in courses]
            if len(existing_codes) < 2:
                continue
            for left_code in existing_codes:
                custom_labels[left_code] = group["label"]
                adjacency.setdefault(left_code, {left_code})
                for right_code in existing_codes:
                    adjacency[left_code].add(right_code)

    visited: set[str] = set()
    groups: dict[str, CourseGroupRecord] = {}
    code_to_group: dict[str, str] = {}

    for code in sorted(courses, key=course_sort_key):
        if code in visited:
            continue
        stack = [code]
        component: set[str] = set()
        while stack:
            current = stack.pop()
            if current in visited:
                continue
            visited.add(current)
            component.add(current)
            stack.extend(adjacency.get(current, set()) - visited)

        primary_code = choose_group_primary(component)
        ordered_codes = tuple(sorted(component, key=course_sort_key))
        tooltip_rows = [f"{group_code}: {courses[group_code].name}" for group_code in ordered_codes]
        label = format_course_group_label(ordered_codes)
        custom_label = next((custom_labels[group_code] for group_code in ordered_codes if group_code in custom_labels), None)
        if custom_label:
            label = custom_label
        tooltip = " | ".join(tooltip_rows)
        if len(ordered_codes) > 1:
            tooltip = (
                "Collapsed in simplified view: " + tooltip
                if custom_label
                else "Equivalent or cross-listed: " + tooltip
            )
        group_record = CourseGroupRecord(
            primary_code=primary_code,
            codes=ordered_codes,
            label=label,
            tooltip=tooltip,
        )
        groups[primary_code] = group_record
        for group_code in ordered_codes:
            code_to_group[group_code] = primary_code

    return groups, code_to_group


def compute_dependency_depths(codes: set[str], courses: dict[str, CourseRecord]) -> dict[str, int]:
    memo: dict[str, int] = {}
    visiting: set[str] = set()

    def depth(code: str) -> int:
        if code in memo:
            return memo[code]
        if code in visiting:
            return 0
        visiting.add(code)
        prereqs = [
            prereq
            for prereq in courses.get(code, CourseRecord(code, code, "", {}, [], [])).prereq_codes
            if prereq in codes
        ]
        value = 0 if not prereqs else 1 + max(depth(prereq) for prereq in prereqs)
        visiting.remove(code)
        memo[code] = value
        return value

    for code in codes:
        if code in courses:
            depth(code)

    return memo


def course_level_index(code: str) -> int:
    digits = re.findall(r"\d+", code)
    if not digits:
        return 0
    return max(0, (int(digits[0]) // 100) - 1)


def infer_support_stage(
    support_code: str,
    *,
    dependent_stage_indexes: list[int],
    max_stage_index: int,
) -> int:
    if not dependent_stage_indexes:
        return 0
    earliest_dependent = min(dependent_stage_indexes)
    level_stage = min(course_level_index(support_code), max_stage_index)
    return max(0, min(earliest_dependent, level_stage))


def program_course_label(code: str, courses: dict[str, CourseRecord]) -> str:
    return code


def add_program_course_node(
    graph: Digraph,
    code: str,
    courses: dict[str, CourseRecord],
    *,
    emphasis: bool,
) -> None:
    node_kwargs = {
        "label": program_course_label(code, courses),
        "fillcolor": subject_color(code, missing=code not in courses),
        "tooltip": courses[code].name if code in courses else code,
        "penwidth": "1.6" if emphasis else "1.0",
        "style": "filled,rounded" if emphasis else "filled,rounded,dashed",
        "fontsize": "10" if emphasis else "9",
        "fontcolor": "#17232b" if emphasis else "#41515b",
    }
    svg_href = svg_course_href(code, courses)
    if svg_href:
        node_kwargs["URL"] = svg_href
        node_kwargs["target"] = "_top"
    graph.node(code, **node_kwargs)


def ordered_codes_for_column(
    codes: list[str],
    depth_map: dict[str, int],
) -> list[str]:
    return sorted(
        unique_ordered(codes),
        key=lambda code: (depth_map.get(code, 0), subject_from_code(code), course_sort_key(code)),
    )


def collect_ancestor_codes(code: str, courses: dict[str, CourseRecord], seen: set[str] | None = None) -> set[str]:
    seen = set() if seen is None else seen
    if code not in courses:
        return seen
    for prereq in courses[code].prereq_codes:
        if prereq in courses and prereq not in seen:
            seen.add(prereq)
            collect_ancestor_codes(prereq, courses, seen)
    return seen


def collect_descendant_codes(code: str, courses: dict[str, CourseRecord], seen: set[str] | None = None) -> set[str]:
    seen = set() if seen is None else seen
    if code not in courses:
        return seen
    for dependent in courses[code].dependents:
        if dependent in courses and dependent not in seen:
            seen.add(dependent)
            collect_descendant_codes(dependent, courses, seen)
    return seen


def compute_relative_course_depths(code: str, courses: dict[str, CourseRecord]) -> dict[str, int]:
    depths = {code: 0}
    active_up: set[str] = set()
    active_down: set[str] = set()

    def walk_up(current: str, depth: int) -> None:
        if current not in courses or current in active_up:
            return
        active_up.add(current)
        for prereq in courses[current].prereq_codes:
            if prereq not in courses:
                continue
            next_depth = depth - 1
            if prereq not in depths or next_depth < depths[prereq]:
                depths[prereq] = next_depth
                walk_up(prereq, next_depth)
        active_up.remove(current)

    def walk_down(current: str, depth: int) -> None:
        if current not in courses or current in active_down:
            return
        active_down.add(current)
        for dependent in courses[current].dependents:
            if dependent not in courses:
                continue
            next_depth = depth + 1
            if dependent not in depths or next_depth > depths[dependent]:
                depths[dependent] = next_depth
                walk_down(dependent, next_depth)
        active_down.remove(current)

    walk_up(code, 0)
    walk_down(code, 0)
    return depths


def course_group_id(primary_code: str) -> str:
    return f"course__{primary_code}"


def course_group_href(
    primary_code: str,
    course_groups: dict[str, CourseGroupRecord],
    *,
    preferred_code: str | None = None,
) -> str:
    target_code = preferred_code if preferred_code in course_groups[primary_code].codes else primary_code
    return f"../../../courses/{target_code}.html"


def add_course_group_node(
    graph: Digraph,
    primary_code: str,
    course_groups: dict[str, CourseGroupRecord],
    courses: dict[str, CourseRecord],
    *,
    emphasis: bool,
    focus: bool = False,
    focus_name: str | None = None,
    preferred_code: str | None = None,
    style_overrides: dict[str, str] | None = None,
) -> None:
    group = course_groups[primary_code]
    label = group.label
    if focus and focus_name:
        label = f"{group.label}\\n{focus_name}"
    node_kwargs = {
        "label": label,
        "fillcolor": subject_color(primary_code, missing=primary_code not in courses),
        "tooltip": group.tooltip,
        "penwidth": "2.0" if focus else ("1.6" if emphasis else "1.0"),
        "style": "filled,rounded",
        "fontsize": "10" if emphasis or focus else "9",
        "fontcolor": "#17232b" if emphasis or focus else "#41515b",
        "color": "#1f4f66" if focus else ("#1b2730" if emphasis else "#7e8d96"),
        "URL": course_group_href(primary_code, course_groups, preferred_code=preferred_code),
        "target": "_top",
    }
    if style_overrides:
        node_kwargs.update(style_overrides)
    graph.node(course_group_id(primary_code), **node_kwargs)


def build_group_dependency_maps(
    visible_codes: set[str],
    courses: dict[str, CourseRecord],
    course_group_lookup: dict[str, str],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    prereq_map: dict[str, set[str]] = {}
    dependent_map: dict[str, set[str]] = {}

    for raw_code in visible_codes:
        if raw_code not in courses:
            continue
        group_code = course_group_lookup.get(raw_code, raw_code)
        prereq_map.setdefault(group_code, set())
        dependent_map.setdefault(group_code, set())

    for raw_target in visible_codes:
        if raw_target not in courses:
            continue
        target_group = course_group_lookup.get(raw_target, raw_target)
        for raw_prereq in courses[raw_target].prereq_codes:
            if raw_prereq not in visible_codes or raw_prereq not in courses:
                continue
            prereq_group = course_group_lookup.get(raw_prereq, raw_prereq)
            if prereq_group == target_group:
                continue
            prereq_map.setdefault(target_group, set()).add(prereq_group)
            prereq_map.setdefault(prereq_group, set())
            dependent_map.setdefault(prereq_group, set()).add(target_group)
            dependent_map.setdefault(target_group, set())

    return prereq_map, dependent_map


def compute_group_prereq_closure(prereq_map: dict[str, set[str]]) -> dict[str, set[str]]:
    memo: dict[str, set[str]] = {}
    visiting: set[str] = set()

    def closure(group_code: str) -> set[str]:
        if group_code in memo:
            return memo[group_code]
        if group_code in visiting:
            return set()
        visiting.add(group_code)
        reachable: set[str] = set()
        for prereq_group in prereq_map.get(group_code, set()):
            reachable.add(prereq_group)
            reachable.update(closure(prereq_group))
        visiting.remove(group_code)
        memo[group_code] = reachable
        return reachable

    for group_code in prereq_map:
        closure(group_code)

    return memo


def compute_group_depths(prereq_map: dict[str, set[str]]) -> dict[str, int]:
    memo: dict[str, int] = {}
    visiting: set[str] = set()

    def depth(node: str) -> int:
        if node in memo:
            return memo[node]
        if node in visiting:
            return 0
        visiting.add(node)
        prereqs = prereq_map.get(node, set())
        value = 0 if not prereqs else 1 + max(depth(prereq) for prereq in prereqs)
        visiting.remove(node)
        memo[node] = value
        return value

    for node in prereq_map:
        depth(node)

    return memo


def compute_relative_group_depths(
    focus_group: str,
    prereq_map: dict[str, set[str]],
    dependent_map: dict[str, set[str]],
) -> dict[str, int]:
    depths = {focus_group: 0}
    active_up: set[str] = set()
    active_down: set[str] = set()

    def walk_up(node: str, depth: int) -> None:
        if node in active_up:
            return
        active_up.add(node)
        for prereq in prereq_map.get(node, set()):
            next_depth = depth - 1
            if prereq not in depths or next_depth < depths[prereq]:
                depths[prereq] = next_depth
                walk_up(prereq, next_depth)
        active_up.remove(node)

    def walk_down(node: str, depth: int) -> None:
        if node in active_down:
            return
        active_down.add(node)
        for dependent in dependent_map.get(node, set()):
            next_depth = depth + 1
            if dependent not in depths or next_depth > depths[dependent]:
                depths[dependent] = next_depth
                walk_down(dependent, next_depth)
        active_down.remove(node)

    walk_up(focus_group, 0)
    walk_down(focus_group, 0)
    return depths


def compute_group_dependent_closure(dependent_map: dict[str, set[str]]) -> dict[str, set[str]]:
    memo: dict[str, set[str]] = {}
    visiting: set[str] = set()

    def closure(group_code: str) -> set[str]:
        if group_code in memo:
            return memo[group_code]
        if group_code in visiting:
            return set()
        visiting.add(group_code)
        reachable: set[str] = set()
        for dependent_group in dependent_map.get(group_code, set()):
            reachable.add(dependent_group)
            reachable.update(closure(dependent_group))
        visiting.remove(group_code)
        memo[group_code] = reachable
        return reachable

    for group_code in dependent_map:
        closure(group_code)

    return memo


def compute_group_downstream_depths(dependent_map: dict[str, set[str]]) -> dict[str, int]:
    memo: dict[str, int] = {}
    visiting: set[str] = set()

    def depth(node: str) -> int:
        if node in memo:
            return memo[node]
        if node in visiting:
            return 0
        visiting.add(node)
        dependents = dependent_map.get(node, set())
        value = 0 if not dependents else 1 + max(depth(dependent) for dependent in dependents)
        visiting.remove(node)
        memo[node] = value
        return value

    for node in dependent_map:
        depth(node)

    return memo


def compute_longest_group_path(
    prereq_map: dict[str, set[str]],
    dependent_map: dict[str, set[str]],
) -> list[str]:
    memo: dict[str, list[str]] = {}
    visiting: set[str] = set()

    def best_from(node: str) -> list[str]:
        if node in memo:
            return memo[node]
        if node in visiting:
            return [node]
        visiting.add(node)
        dependents = sorted(dependent_map.get(node, set()), key=course_sort_key)
        if not dependents:
            result = [node]
        else:
            result = max(
                ([node, *best_from(dependent)] for dependent in dependents),
                key=lambda path: (len(path), tuple(reversed([course_sort_key(code) for code in path]))),
            )
        visiting.remove(node)
        memo[node] = result
        return result

    sources = sorted(
        (node for node in prereq_map if not prereq_map.get(node)),
        key=course_sort_key,
    )
    candidates = sources or sorted(prereq_map, key=course_sort_key)
    if not candidates:
        return []
    return max(
        (best_from(node) for node in candidates),
        key=lambda path: (len(path), tuple(reversed([course_sort_key(code) for code in path]))),
    )


def parse_requirement_count(count: str | None) -> float | None:
    if not count:
        return None
    try:
        return float(count)
    except ValueError:
        return None


def required_course_codes_from_rule_node(node: dict) -> set[str]:
    if node["kind"] == "course":
        return {node["code"]}
    if node["kind"] == "text":
        return set()

    child_sets = [required_course_codes_from_rule_node(child) for child in node.get("children", [])]
    kind, count = requirement_group_kind(node.get("label", ""))
    if kind == "choose":
        numeric_count = parse_requirement_count(count)
        if numeric_count is not None and numeric_count >= len(child_sets):
            return set().union(*child_sets) if child_sets else set()
        nonempty_sets = [child_set for child_set in child_sets if child_set]
        return set.intersection(*nonempty_sets) if nonempty_sets else set()

    return set().union(*child_sets) if child_sets else set()


def required_course_codes_from_rule_nodes(nodes: Iterable[dict]) -> set[str]:
    required_codes: set[str] = set()
    for node in nodes:
        required_codes.update(required_course_codes_from_rule_node(node))
    return required_codes


def find_required_prereq_path(
    start_code: str,
    target_code: str,
    *,
    required_prereq_lookup: dict[str, set[str]],
    course_group_lookup: dict[str, str],
) -> list[str] | None:
    target_group = course_group_lookup.get(target_code, target_code)
    queue = deque([(start_code, [start_code])])
    visited = {start_code}

    while queue:
        current_code, path = queue.popleft()
        for prereq_code in sorted(required_prereq_lookup.get(current_code, set()), key=course_sort_key):
            if prereq_code in visited:
                continue
            next_path = [*path, prereq_code]
            if course_group_lookup.get(prereq_code, prereq_code) == target_group:
                return next_path
            visited.add(prereq_code)
            queue.append((prereq_code, next_path))
    return None


def find_redundant_prerequisite_checks(
    courses: dict[str, CourseRecord],
    course_group_lookup: dict[str, str],
) -> list[dict]:
    required_prereq_lookup = {
        code: required_course_codes_from_rule_nodes(course.rule_nodes)
        for code, course in courses.items()
    }
    checks: list[dict] = []
    seen: set[tuple[str, str, str]] = set()

    for course in sorted(courses.values(), key=lambda item: course_sort_key(item.code)):
        direct_codes = sorted(
            (code for code in required_prereq_lookup.get(course.code, set()) if code in courses),
            key=course_sort_key,
        )
        for redundant_code in direct_codes:
            redundant_group = course_group_lookup.get(redundant_code, redundant_code)
            for implied_by_code in direct_codes:
                if implied_by_code == redundant_code:
                    continue
                implied_by_group = course_group_lookup.get(implied_by_code, implied_by_code)
                if implied_by_group == redundant_group:
                    continue
                chain = find_required_prereq_path(
                    implied_by_code,
                    redundant_code,
                    required_prereq_lookup=required_prereq_lookup,
                    course_group_lookup=course_group_lookup,
                )
                if not chain:
                    continue
                key = (course.code, redundant_group, implied_by_group)
                if key in seen:
                    continue
                seen.add(key)
                checks.append(
                    {
                        "course": course.code,
                        "courseName": course.name,
                        "courseGroup": course_group_lookup.get(course.code, course.code),
                        "redundant": redundant_code,
                        "redundantGroup": redundant_group,
                        "impliedBy": implied_by_code,
                        "impliedByGroup": implied_by_group,
                        "chain": chain,
                        "message": (
                            f"{course.code} names {redundant_code}, but {implied_by_code} already requires "
                            f"{redundant_code} through {' -> '.join(chain)}."
                        ),
                    }
                )
                break

    return checks


def group_display_label(group_code: str, course_groups: dict[str, CourseGroupRecord]) -> str:
    group = course_groups.get(group_code)
    if group is None:
        return group_code
    return group.label.replace("\\n", " / ")


def group_course_codes(group_code: str, course_groups: dict[str, CourseGroupRecord]) -> tuple[str, ...]:
    group = course_groups.get(group_code)
    return group.codes if group is not None else (group_code,)


def group_has_eos_code(group_code: str, course_groups: dict[str, CourseGroupRecord]) -> bool:
    return any(subject_from_code(code) == "EOS" for code in group_course_codes(group_code, course_groups))


def filter_dependency_maps_to_groups(
    prereq_map: dict[str, set[str]],
    dependent_map: dict[str, set[str]],
    included_groups: set[str],
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    filtered_prereq_map = {
        group_code: {
            prereq_group
            for prereq_group in prereq_map.get(group_code, set())
            if prereq_group in included_groups
        }
        for group_code in included_groups
    }
    filtered_dependent_map = {
        group_code: {
            dependent_group
            for dependent_group in dependent_map.get(group_code, set())
            if dependent_group in included_groups
        }
        for group_code in included_groups
    }
    return filtered_prereq_map, filtered_dependent_map


def group_theme_tokens(group_code: str, course_groups: dict[str, CourseGroupRecord], courses: dict[str, CourseRecord]) -> list[str]:
    counts: Counter[str] = Counter()
    for code in group_course_codes(group_code, course_groups):
        if code not in courses:
            continue
        for token, score in course_theme_scores(courses[code]):
            counts[token] += score
    if not counts:
        return []
    return [token for token, _count in counts.most_common(3)]


def theme_label(token: str) -> str:
    return next((label for current_token, label, _keywords in COURSE_THEME_RULES if current_token == token), token.title())


def theme_color(token: str) -> str:
    return THEME_COLORS.get(token, "oklch(72% 0.03 85)")


def theme_palette_items() -> list[dict[str, str]]:
    return [
        {
            "token": token,
            "label": label,
            "color": theme_color(token),
        }
        for token, label, _keywords in COURSE_THEME_RULES
    ]


def analytics_score_level(value: int, maximum: int) -> int:
    if maximum <= 0 or value <= 0:
        return 0
    return min(4, max(1, int(round((value / maximum) * 4))))


def program_path_codes(
    program: ProgramRecord,
    stream: ProgramStreamRecord | None = None,
    *,
    include_stream_courses: bool = True,
) -> set[str]:
    return {
        code
        for code in unique_ordered(
            program_named_codes(program, stream, include_stream_courses=include_stream_courses) + program_support_codes(program, stream)
        )
    }


def build_program_mode_analytics(
    program: ProgramRecord,
    courses: dict[str, CourseRecord],
    course_groups: dict[str, CourseGroupRecord],
    course_group_lookup: dict[str, str],
    redundant_checks: list[dict],
    *,
    stream: ProgramStreamRecord | None = None,
) -> dict:
    include_stream_courses = not is_eos_base_program(program) if stream is None else True
    explicit_codes = {code for code in program_named_codes(program, stream, include_stream_courses=include_stream_courses) if code in courses}
    visible_codes = explicit_codes | {code for code in program_support_codes(program, stream) if code in courses}
    prereq_map, dependent_map = build_group_dependency_maps(visible_codes, courses, course_group_lookup)
    prereq_closure = compute_group_prereq_closure(prereq_map)
    dependent_closure = compute_group_dependent_closure(dependent_map)
    upstream_depths = compute_group_depths(prereq_map)
    downstream_depths = compute_group_downstream_depths(dependent_map)
    seos_groups = {
        group_code
        for group_code in prereq_map
        if group_has_eos_code(group_code, course_groups)
    }
    seos_prereq_map, seos_dependent_map = filter_dependency_maps_to_groups(
        prereq_map,
        dependent_map,
        seos_groups,
    )
    seos_dependent_closure = compute_group_dependent_closure(seos_dependent_map)
    seos_upstream_depths = compute_group_depths(seos_prereq_map)
    seos_downstream_depths = compute_group_downstream_depths(seos_dependent_map)
    longest_path = compute_longest_group_path(seos_prereq_map, seos_dependent_map)
    longest_prerequisite_chain = compute_longest_group_path(prereq_map, dependent_map)
    explicit_groups = {course_group_lookup.get(code, code) for code in explicit_codes}
    support_groups = {course_group_lookup.get(code, code) for code in program_support_codes(program, stream)}
    required_groups, option_sets = build_program_option_sets(
        program_graph_sections(program, stream),
        explicit_groups=explicit_groups,
        course_group_lookup=course_group_lookup,
    )
    option_group_labels = {
        group_code: option_set["label"]
        for option_set in option_sets
        for group_code in option_set["groups"]
    }
    year_group_lookup = build_program_year_group_lookup(program, course_group_lookup, stream)
    year_labels = dict(CONTACT_SUMMARY_BUCKETS)
    relevant_redundant_checks = [
        check
        for check in redundant_checks
        if check["courseGroup"] in prereq_map
    ]
    redundant_count_by_group: Counter[str] = Counter()
    for check in relevant_redundant_checks:
        redundant_count_by_group[check["courseGroup"]] += 1
        redundant_count_by_group[check["redundantGroup"]] += 1
        redundant_count_by_group[check["impliedByGroup"]] += 1

    raw_nodes: list[dict] = []
    for group_code in sorted(prereq_map, key=course_sort_key):
        blocking_factor = len(dependent_closure.get(group_code, set()))
        prerequisite_chain_depth = upstream_depths.get(group_code, 0)
        chain_depth = prerequisite_chain_depth + 1
        delay_factor = upstream_depths.get(group_code, 0) + downstream_depths.get(group_code, 0) + 1
        is_seos_course = group_code in seos_groups
        seos_blocking_factor = len(seos_dependent_closure.get(group_code, set())) if is_seos_course else 0
        seos_delay_factor = (
            seos_upstream_depths.get(group_code, 0) + seos_downstream_depths.get(group_code, 0) + 1
            if is_seos_course
            else 0
        )
        complexity = blocking_factor + delay_factor
        role = "support"
        role_label = "Related prerequisite"
        if group_code in required_groups:
            role = "required"
            role_label = "Required program course"
        elif group_code in option_group_labels:
            role = "option"
            role_label = option_group_labels[group_code]
        elif group_code in explicit_groups:
            role = "named"
            role_label = "Named program course"
        elif group_code in support_groups:
            role = "support"

        themes = group_theme_tokens(group_code, course_groups, courses)
        raw_nodes.append(
            {
                "id": course_group_id(group_code),
                "group": group_code,
                "label": group_display_label(group_code, course_groups),
                "role": role,
                "roleLabel": role_label,
                "subject": subject_from_code(group_code),
                "themes": themes,
                "themeLabels": [theme_label(token) for token in themes],
                "themeColor": theme_color(themes[0]) if themes else subject_color(group_code),
                "year": year_group_lookup.get(group_code, ""),
                "yearLabel": year_labels.get(year_group_lookup.get(group_code, ""), ""),
                "isSeosCourse": is_seos_course,
                "prereqCount": len(prereq_map.get(group_code, set())),
                "dependentCount": len(dependent_map.get(group_code, set())),
                "blockingFactor": blocking_factor,
                "seosBlockingFactor": seos_blocking_factor,
                "prerequisiteChainDepth": prerequisite_chain_depth,
                "chainDepth": chain_depth,
                "delayFactor": delay_factor,
                "seosDelayFactor": seos_delay_factor,
                "centrality": len(prereq_closure.get(group_code, set())) * len(dependent_closure.get(group_code, set())),
                "complexity": complexity,
                "onLongestPath": group_code in longest_path,
                "onDeepestPrerequisiteChain": group_code in longest_prerequisite_chain,
                "redundantFlagCount": redundant_count_by_group.get(group_code, 0),
            }
        )

    max_blocking = max((node["seosBlockingFactor"] for node in raw_nodes), default=0)
    max_delay = max((node["chainDepth"] for node in raw_nodes), default=0)
    max_complexity = max((node["complexity"] for node in raw_nodes), default=0)
    for node in raw_nodes:
        node["levels"] = {
            "blocking": analytics_score_level(node["seosBlockingFactor"], max_blocking),
            "delay": analytics_score_level(node["chainDepth"], max_delay),
            "complexity": analytics_score_level(node["complexity"], max_complexity),
        }

    theme_counts: Counter[str] = Counter(
        token
        for node in raw_nodes
        for token in node["themes"][:1]
    )
    year_counts: Counter[str] = Counter(
        node["year"]
        for node in raw_nodes
        if node["year"]
    )
    top_bottlenecks = sorted(
        (node for node in raw_nodes if node["isSeosCourse"]),
        key=lambda node: (-node["seosBlockingFactor"], -node["seosDelayFactor"], course_sort_key(node["group"])),
    )[:6]
    top_chain_depths = sorted(
        raw_nodes,
        key=lambda node: (-node["chainDepth"], -node["blockingFactor"], course_sort_key(node["group"])),
    )[:6]
    return {
        "metrics": {
            "nodes": len(prereq_map),
            "edges": sum(len(prereqs) for prereqs in prereq_map.values()),
            "seosNodes": len(seos_groups),
            "maxDepth": max(upstream_depths.values(), default=0),
            "seosMaxDepth": max(seos_upstream_depths.values(), default=0),
            "maxDelay": max_delay,
            "maxPrerequisiteChainDepth": max_delay,
            "totalBlocking": sum(node["blockingFactor"] for node in raw_nodes),
            "totalSeosBlocking": sum(node["seosBlockingFactor"] for node in raw_nodes),
            "totalDelay": sum(node["delayFactor"] for node in raw_nodes),
            "totalSeosDelay": sum(node["seosDelayFactor"] for node in raw_nodes),
            "totalPrerequisiteChainDepth": sum(node["chainDepth"] for node in raw_nodes),
            "totalComplexity": sum(node["complexity"] for node in raw_nodes),
            "redundantPrerequisiteFlags": len(relevant_redundant_checks),
        },
        "nodes": raw_nodes,
        "longestPath": [
            {
                "group": group_code,
                "id": course_group_id(group_code),
                "label": group_display_label(group_code, course_groups),
            }
            for group_code in longest_path
        ],
        "longestPrerequisiteChain": [
            {
                "group": group_code,
                "id": course_group_id(group_code),
                "label": group_display_label(group_code, course_groups),
            }
            for group_code in longest_prerequisite_chain
        ],
        "topBottlenecks": [
            {
                "group": node["group"],
                "id": node["id"],
                "label": node["label"],
                "blockingFactor": node["seosBlockingFactor"],
                "delayFactor": node["seosDelayFactor"],
                "allCourseBlockingFactor": node["blockingFactor"],
                "allCourseDelayFactor": node["delayFactor"],
                "complexity": node["complexity"],
            }
            for node in top_bottlenecks
            if node["seosBlockingFactor"] > 0
        ],
        "topChainDepths": [
            {
                "group": node["group"],
                "id": node["id"],
                "label": node["label"],
                "chainDepth": node["chainDepth"],
                "prerequisiteChainDepth": node["prerequisiteChainDepth"],
                "isSeosCourse": node["isSeosCourse"],
            }
            for node in top_chain_depths
            if node["chainDepth"] > 1
        ],
        "themeCounts": {
            token: {
                "label": theme_label(token),
                "count": count,
                "color": theme_color(token),
            }
            for token, count in theme_counts.most_common()
        },
        "yearCounts": {
            token: {
                "label": year_labels.get(token, token),
                "count": count,
            }
            for token, count in year_counts.items()
        },
        "redundantPrerequisites": relevant_redundant_checks,
    }


def build_program_analytics_bundle(
    program: ProgramRecord,
    courses: dict[str, CourseRecord],
    redundant_checks: list[dict],
    *,
    stream: ProgramStreamRecord | None = None,
) -> dict:
    course_groups, course_group_lookup = build_course_groups(courses, aggressive=False)
    simplified_course_groups, simplified_course_group_lookup = build_course_groups(courses, aggressive=True)
    title = f"{program.name}: {stream.title}" if stream is not None else program.name
    return {
        "programCode": program.code,
        "programName": program.name,
        "pathTitle": title,
        "streamSlug": stream.slug if stream is not None else "",
        "themePalette": theme_palette_items(),
        "modes": {
            "simplified": build_program_mode_analytics(
                program,
                courses,
                simplified_course_groups,
                simplified_course_group_lookup,
                redundant_checks,
                stream=stream,
            ),
            "full": build_program_mode_analytics(
                program,
                courses,
                course_groups,
                course_group_lookup,
                redundant_checks,
                stream=stream,
            ),
        },
    }


def collect_related_groups(
    start_group: str,
    adjacency_map: dict[str, set[str]],
    max_depth: int | None,
) -> set[str]:
    visited = {start_group}
    queue = deque([(start_group, 0)])

    while queue:
        current_group, depth = queue.popleft()
        if max_depth is not None and depth >= max_depth:
            continue
        for next_group in adjacency_map.get(current_group, set()):
            if next_group in visited:
                continue
            visited.add(next_group)
            queue.append((next_group, depth + 1))

    visited.discard(start_group)
    return visited


def visible_codes_for_groups(
    groups: set[str],
    course_groups: dict[str, CourseGroupRecord],
) -> set[str]:
    return {
        code
        for group_code in groups
        for code in course_groups[group_code].codes
    }


def infer_simplified_block_label(codes: Iterable[str], courses: dict[str, CourseRecord]) -> str | None:
    code_set = frozenset(code for code in unique_ordered(codes) if code in courses)
    if len(code_set) < 2:
        return None
    if code_set in SIMPLIFIED_BLOCK_LABELS:
        return SIMPLIFIED_BLOCK_LABELS[code_set]

    subjects = {subject_from_code(code) for code in code_set}
    allowed_subjects = {"BIOL", "CSC", "EOS", "MATH", "PHYS", "STAT"}
    if not subjects.issubset(allowed_subjects):
        return None
    if len(subjects) != 1:
        return None

    numeric_levels = [
        int(level)
        for code in code_set
        for level in [course_level_token(code)]
        if level.isdigit()
    ]
    if not numeric_levels:
        return None
    max_level = max(numeric_levels)
    if max_level > 200 and not (subjects == {"STAT"} and max_level <= 300):
        return None

    text = normalize_text(
        " ".join(
            f"{courses[code].name} {BeautifulSoup(courses[code].detail.get('description') or '', 'html.parser').get_text(' ', strip=True)}"
            for code in sorted(code_set, key=course_sort_key)
        )
    ).lower()
    per_course_text = {
        code: normalize_text(
            f"{courses[code].name} {BeautifulSoup(courses[code].detail.get('description') or '', 'html.parser').get_text(' ', strip=True)}"
        ).lower()
        for code in code_set
    }

    def all_courses_match(*keywords: str) -> bool:
        return all(
            any(theme_keyword_hits(per_course_text[code], keyword) for keyword in keywords)
            for code in code_set
        )

    subject = next(iter(subjects))
    if subject == "CSC" and max_level <= 100:
        return "Programming I" if all_courses_match("program", "comput") else None
    if subject == "EOS" and max_level <= 200 and any(theme_keyword_hits(text, keyword) for keyword in ("geophys", "seism", "geomagnet", "heat flow")):
        return "Intro geophysics"
    if subject == "MATH" and all_courses_match("matrix algebra", "linear algebra"):
        return "Linear algebra I"
    if subject == "MATH" and all_courses_match("calculus"):
        if max_level <= 100:
            return "Calculus I"
        if max_level <= 200:
            return "Second-year calculus"
        return "Calculus path"
    if subject == "STAT" and max_level <= 200 and all_courses_match("statistics", "probability"):
        return "Intro statistics"
    if subject == "PHYS" and max_level <= 100 and all_courses_match("physics"):
        return "First-year physics"
    if subject == "BIOL" and max_level <= 100 and all_courses_match("biology", "evolution", "ecology"):
        return "Intro biology"
    return None


def canonical_requirement_signature(
    node: dict,
    *,
    visible_codes: set[str],
    courses: dict[str, CourseRecord],
    course_group_lookup: dict[str, str],
    target_group: str,
) -> tuple | None:
    if node.get("kind") == "text":
        return None

    if node.get("kind") == "course":
        course_code = node.get("code")
        if course_code not in visible_codes or course_code not in courses:
            return None
        group_code = course_group_lookup.get(course_code, course_code)
        if group_code == target_group:
            return None
        return ("course", group_code)

    kind, count = requirement_group_kind(node.get("label", ""))
    child_signatures = [
        signature
        for child in node.get("children", [])
        for signature in [
            canonical_requirement_signature(
                child,
                visible_codes=visible_codes,
                courses=courses,
                course_group_lookup=course_group_lookup,
                target_group=target_group,
            )
        ]
        if signature is not None
    ]
    if not child_signatures:
        return None

    ordered_children = tuple(sorted(child_signatures, key=repr))
    if kind == "choose" and count is not None:
        return ("choose", count, ordered_children)
    if kind == "all":
        return ("all", ordered_children)
    return ("group", ordered_children)


def dedupe_requirement_nodes(
    rule_nodes: Iterable[dict],
    *,
    visible_codes: set[str],
    courses: dict[str, CourseRecord],
    course_group_lookup: dict[str, str],
    target_group: str,
) -> list[dict]:
    unique_nodes: list[dict] = []
    seen_signatures: set[tuple] = set()

    for node in rule_nodes:
        signature = canonical_requirement_signature(
            node,
            visible_codes=visible_codes,
            courses=courses,
            course_group_lookup=course_group_lookup,
            target_group=target_group,
        )
        if signature is None or signature in seen_signatures:
            continue
        seen_signatures.add(signature)
        unique_nodes.append(node)

    return unique_nodes


def simplified_block_tooltip(label: str, codes: Iterable[str], courses: dict[str, CourseRecord]) -> str:
    rows = [
        f"{code}: {courses[code].name}"
        for code in sorted(unique_ordered(code for code in codes if code in courses), key=course_sort_key)
    ]
    return "Collapsed in simplified program view: " + label + " | " + " | ".join(rows)


def add_simplified_requirement_flow(
    graph: Digraph,
    *,
    target_code: str,
    rule_nodes: list[dict],
    visible_codes: set[str],
    courses: dict[str, CourseRecord],
    course_groups: dict[str, CourseGroupRecord],
    course_group_lookup: dict[str, str],
    drawn_edges: set[tuple[str, str, str]],
    created_aux_nodes: set[str],
    summaries_enabled: bool = False,
    bundle_registry: dict[tuple[tuple[str, str], ...], str] | None = None,
    choice_registry: dict[tuple[str, tuple[tuple[str, str], ...]], str] | None = None,
    group_prereq_closure: dict[str, set[str]] | None = None,
) -> None:
    if target_code not in courses:
        return

    target_group = course_group_lookup.get(target_code, target_code)
    target_id = course_group_id(target_group)
    summary_metadata: dict[str, tuple[str, tuple[str, ...]]] = {}

    def add_edge(source_id: str, target_id: str, *, style_key: str, **kwargs: str) -> None:
        edge_key = (source_id, target_id, style_key)
        if edge_key in drawn_edges:
            return
        drawn_edges.add(edge_key)
        graph.edge(source_id, target_id, **kwargs)

    def ensure_choice_node(node_id: str, count: str, source_ids: Iterable[str] | None = None) -> str:
        if choice_registry is not None and source_ids is not None:
            signature = tuple(sorted(anchor_semantic_key(source_id) for source_id in source_ids))
            existing_id = choice_registry.get((count, signature))
            if existing_id is not None:
                return existing_id
        if node_id not in created_aux_nodes:
            created_aux_nodes.add(node_id)
            graph.node(
                node_id,
                label=f"{count} of",
                shape="box",
                style="filled,rounded",
                fillcolor="#fff7ee",
                color="#b7793f",
                fontsize="9",
                margin="0.06,0.04",
            )
        if choice_registry is not None and source_ids is not None:
            signature = tuple(sorted(anchor_semantic_key(source_id) for source_id in source_ids))
            choice_registry[(count, signature)] = node_id
        return node_id

    def ensure_bundle_node(node_id: str, anchor_ids: Iterable[str] | None = None) -> str:
        if bundle_registry is not None and anchor_ids is not None:
            signature = tuple(sorted(anchor_semantic_key(anchor_id) for anchor_id in anchor_ids))
            existing_id = bundle_registry.get(signature)
            if existing_id is not None:
                return existing_id
        if node_id not in created_aux_nodes:
            created_aux_nodes.add(node_id)
            graph.node(
                node_id,
                label="",
                shape="circle",
                style="filled",
                fillcolor="#7a8790",
                color="#667780",
                width="0.16",
                height="0.16",
                fixedsize="true",
                penwidth="1.0",
                tooltip="Grouped requirement junction",
            )
        if bundle_registry is not None and anchor_ids is not None:
            signature = tuple(sorted(anchor_semantic_key(anchor_id) for anchor_id in anchor_ids))
            bundle_registry[signature] = node_id
        return node_id

    def ensure_summary_node(node_id: str, label: str, tooltip: str, codes: Iterable[str]) -> str:
        summary_codes = tuple(sorted(unique_ordered(code for code in codes if code in courses), key=course_sort_key))
        summary_metadata[node_id] = (label, summary_codes)
        if node_id not in created_aux_nodes:
            created_aux_nodes.add(node_id)
            graph.node(
                node_id,
                label=label,
                shape="box",
                style="filled,rounded",
                fillcolor="#f6efe5",
                color="#8f6a3b",
                fontsize="9",
                margin="0.08,0.05",
                tooltip=tooltip,
            )
        return node_id

    def anchor_codes(anchor_ids: list[str]) -> list[str]:
        codes: list[str] = []
        for anchor_id in anchor_ids:
            if not anchor_id.startswith("course__"):
                if anchor_id in summary_metadata:
                    codes.extend(summary_metadata[anchor_id][1])
                continue
            group_code = anchor_id[len("course__") :]
            if group_code in course_groups:
                codes.extend(course_groups[group_code].codes)
        return unique_ordered(codes)

    def anchor_semantic_key(anchor_id: str) -> tuple[str, str]:
        if anchor_id in summary_metadata:
            return ("summary", summary_metadata[anchor_id][0])
        if anchor_id.startswith("course__"):
            return ("course", anchor_id[len("course__") :])
        return ("aux", anchor_id)

    def prune_redundant_anchor_ids(anchor_ids: list[str]) -> list[str]:
        if not group_prereq_closure:
            return unique_ordered(anchor_ids)

        ordered_anchor_ids = unique_ordered(anchor_ids)
        pruned: list[str] = []
        for anchor_id in ordered_anchor_ids:
            if not anchor_id.startswith("course__"):
                pruned.append(anchor_id)
                continue

            group_code = anchor_id[len("course__") :]
            redundant = False
            for other_anchor_id in ordered_anchor_ids:
                if other_anchor_id == anchor_id or not other_anchor_id.startswith("course__"):
                    continue
                other_group = other_anchor_id[len("course__") :]
                if group_code in group_prereq_closure.get(other_group, set()):
                    redundant = True
                    break
            if not redundant:
                pruned.append(anchor_id)
        return pruned

    def subtree_visible_codes(node: dict) -> list[str]:
        if node["kind"] == "text":
            return []
        if node["kind"] == "course":
            course_code = node["code"]
            if course_code not in visible_codes or course_code not in courses:
                return []
            group_code = course_group_lookup.get(course_code, course_code)
            if group_code == target_group:
                return []
            if group_code in course_groups:
                return list(course_groups[group_code].codes)
            return [course_code]

        codes: list[str] = []
        for child in node.get("children", []):
            codes.extend(subtree_visible_codes(child))
        return unique_ordered(codes)

    def branch_anchors(node: dict, namespace: str, *, collapse_all: bool) -> list[str]:
        if node["kind"] == "text":
            return []

        if node["kind"] == "course":
            course_code = node["code"]
            if course_code not in visible_codes or course_code not in courses:
                return []
            group_code = course_group_lookup.get(course_code, course_code)
            if group_code == target_group:
                return []
            return [course_group_id(group_code)]

        kind, count = requirement_group_kind(node["label"])

        if kind == "choose" and count is not None:
            if summaries_enabled:
                flattened_codes = unique_ordered(
                    code
                    for child in node["children"]
                    for code in subtree_visible_codes(child)
                )
                summary_label = infer_simplified_block_label(flattened_codes, courses)
                if summary_label:
                    return [
                        ensure_summary_node(
                            f"summary_{namespace}",
                            summary_label,
                            simplified_block_tooltip(summary_label, flattened_codes, courses),
                            flattened_codes,
                        )
                    ]

            option_anchor_sets: list[list[str]] = []
            seen_option_signatures: set[tuple] = set()
            for child_index, child in enumerate(node["children"]):
                option_signature = canonical_requirement_signature(
                    child,
                    visible_codes=visible_codes,
                    courses=courses,
                    course_group_lookup=course_group_lookup,
                    target_group=target_group,
                )
                if option_signature is None or option_signature in seen_option_signatures:
                    continue
                seen_option_signatures.add(option_signature)
                child_anchors = unique_ordered(
                    branch_anchors(
                        child,
                        f"{namespace}_{child_index}",
                        collapse_all=True,
                    )
                )
                child_anchors = prune_redundant_anchor_ids(child_anchors)
                if not child_anchors:
                    continue
                option_anchor_sets.append(child_anchors)

            if not option_anchor_sets:
                return []

            if summaries_enabled:
                flattened_codes = unique_ordered(
                    code
                    for anchors in option_anchor_sets
                    for code in anchor_codes(anchors)
                )
                summary_label = infer_simplified_block_label(flattened_codes, courses)
                if summary_label:
                    summary_id = ensure_summary_node(
                        f"summary_{namespace}",
                        summary_label,
                        simplified_block_tooltip(summary_label, flattened_codes, courses),
                        flattened_codes,
                    )
                    return [summary_id]

            option_sources: list[str] = []
            seen_option_anchor_signatures: set[tuple[str, ...]] = set()
            seen_option_semantics: set[tuple[str, str]] = set()
            for child_index, child_anchors in enumerate(option_anchor_sets):
                signature = tuple(sorted(child_anchors))
                if signature in seen_option_anchor_signatures:
                    continue
                seen_option_anchor_signatures.add(signature)

                if len(child_anchors) == 1:
                    semantic_key = anchor_semantic_key(child_anchors[0])
                    if semantic_key in seen_option_semantics:
                        continue
                    seen_option_semantics.add(semantic_key)
                    option_sources.append(child_anchors[0])
                    continue

                child_codes = anchor_codes(child_anchors)
                if summaries_enabled:
                    summary_label = infer_simplified_block_label(child_codes, courses)
                    if summary_label:
                        semantic_key = ("summary", summary_label)
                        if semantic_key in seen_option_semantics:
                            continue
                        seen_option_semantics.add(semantic_key)
                        option_sources.append(
                            ensure_summary_node(
                                f"summary_{namespace}_{child_index}",
                                summary_label,
                                simplified_block_tooltip(summary_label, child_codes, courses),
                                child_codes,
                            )
                        )
                        continue

                bundle_id = ensure_bundle_node(
                    f"bundle_{namespace}_{child_index}",
                    child_anchors,
                )
                for anchor_id in child_anchors:
                    add_edge(
                        anchor_id,
                        bundle_id,
                        style_key=f"{anchor_id}:{bundle_id}:bundle",
                        color="#7a8389",
                        penwidth="1.0",
                    )
                option_sources.append(bundle_id)

            option_sources = unique_ordered(option_sources)
            if not option_sources:
                return []
            if len(option_sources) == 1:
                return option_sources

            choice_id = ensure_choice_node(
                f"choice_{namespace}",
                count,
                option_sources,
            )
            for source_id in option_sources:
                add_edge(
                    source_id,
                    choice_id,
                    style_key=f"{source_id}:{choice_id}:choice",
                    color="#7a8389",
                    penwidth="1.0",
                )
            return [choice_id]

        child_anchors: list[str] = []
        if summaries_enabled and collapse_all:
            child_codes = unique_ordered(
                code
                for child in node.get("children", [])
                for code in subtree_visible_codes(child)
            )
            summary_label = infer_simplified_block_label(child_codes, courses)
            if summary_label:
                return [
                    ensure_summary_node(
                        f"summary_{namespace}",
                        summary_label,
                        simplified_block_tooltip(summary_label, child_codes, courses),
                        child_codes,
                    )
                ]
        for child_index, child in enumerate(node.get("children", [])):
            child_anchors.extend(
                branch_anchors(
                    child,
                    f"{namespace}_{child_index}",
                    collapse_all=False,
                )
            )

        child_anchors = unique_ordered(child_anchors)
        child_anchors = prune_redundant_anchor_ids(child_anchors)
        if not child_anchors:
            return []
        if collapse_all and len(child_anchors) > 1:
            child_codes = anchor_codes(child_anchors)
            if summaries_enabled:
                summary_label = infer_simplified_block_label(child_codes, courses)
                if summary_label:
                    return [
                        ensure_summary_node(
                            f"summary_{namespace}",
                            summary_label,
                            simplified_block_tooltip(summary_label, child_codes, courses),
                            child_codes,
                        )
                    ]
            bundle_id = ensure_bundle_node(
                f"bundle_{namespace}",
                child_anchors,
            )
            for anchor_id in child_anchors:
                add_edge(
                    anchor_id,
                    bundle_id,
                    style_key=f"{anchor_id}:{bundle_id}:bundle",
                    color="#7a8389",
                    penwidth="1.0",
                )
            return [bundle_id]
        return child_anchors

    for index, rule_node in enumerate(rule_nodes):
        for anchor_id in unique_ordered(
            branch_anchors(
                rule_node,
                f"{target_code}_{index}",
                collapse_all=False,
            )
        ):
            add_edge(
                anchor_id,
                target_id,
                style_key=f"{anchor_id}:{target_id}:target",
                color="#5d6972",
                penwidth="1.2",
            )


def short_group_label(label: str) -> str:
    cleaned = normalize_text(label)
    lower = cleaned.lower()
    match = re.search(r"complete ([0-9.]+) of", lower)
    if match:
        return f"{match.group(1)} of"
    if "complete all" in lower:
        return "All"
    match = re.search(r"complete ([0-9.]+) units? of electives?", lower)
    if match:
        return f"{match.group(1)} units"
    if "permission" in lower:
        return "Permission"
    if "elective" in lower:
        return "Electives"
    return cleaned[:14] if len(cleaned) > 14 else cleaned


def display_group_label(label: str) -> str:
    cleaned = normalize_text(label)
    if not cleaned:
        return "Requirement"
    return cleaned if cleaned.endswith(".") else f"{cleaned}."


def course_page_href(prefix: str, code: str, courses: dict[str, CourseRecord]) -> str | None:
    if code not in courses:
        return None
    return f"{prefix}{code}.html"


def program_page_href(prefix: str, code: str) -> str:
    return f"{prefix}PR_{code}.html"


def svg_course_href(code: str, courses: dict[str, CourseRecord]) -> str | None:
    if code not in courses:
        return None
    return f"../../../courses/{code}.html"


def render_subject_pill(code: str) -> str:
    return (
        f'<span class="subject-pill" style="--pill-color: {subject_color(code)}">'
        f"{e(subject_name(code))}</span>"
    )


def render_theme_swatch(token: str) -> str:
    return f'<span class="theme-swatch" style="--theme-color: {e(theme_color(token))}"></span>'


def render_theme_pill(token: str) -> str:
    return (
        f'<span class="theme-pill" style="--theme-color: {e(theme_color(token))}">'
        f"{render_theme_swatch(token)}{e(theme_label(token))}</span>"
    )


def render_theme_filter_button(label: str, *, group: str, value: str, active: bool = False) -> str:
    class_name = "filter-chip filter-chip--theme is-active" if active else "filter-chip filter-chip--theme"
    pressed = "true" if active else "false"
    swatch = "" if value == "all" else render_theme_swatch(value)
    return (
        f'<button class="{class_name}" type="button" data-filter-group="{e(group)}" '
        f'data-filter-value="{e(value)}" aria-pressed="{pressed}">{swatch}<span>{e(label)}</span></button>'
    )


def render_course_chip(code: str, prefix: str, courses: dict[str, CourseRecord]) -> str:
    title = courses.get(code).name if code in courses else "Not found in the last UVic calendar sync"
    href = course_page_href(prefix, code, courses)
    classes = "course-pill" if href else "course-pill course-pill--ghost"
    if href:
        return f'<a class="{classes}" href="{href}" title="{e(title)}">{e(code)}</a>'
    return f'<span class="{classes}" title="{e(title)}">{e(code)}</span>'


def render_rule_node_html(node: dict, prefix: str, courses: dict[str, CourseRecord]) -> str:
    if node["kind"] == "course":
        return render_course_chip(node["code"], prefix, courses)

    if node["kind"] == "text":
        return f'<div class="rule-note">{e(node["text"])}</div>'

    child_courses = all(child["kind"] == "course" for child in node["children"])
    if child_courses:
        body = (
            '<div class="pill-row">'
            + "".join(render_rule_node_html(child, prefix, courses) for child in node["children"])
            + "</div>"
        )
    else:
        body = (
            '<div class="rule-group__body">'
            + "".join(render_rule_node_html(child, prefix, courses) for child in node["children"])
            + "</div>"
        )
    return (
        '<details class="rule-group" open>'
        f"<summary>{e(display_group_label(node['label']))}</summary>"
        f"{body}"
        "</details>"
    )


def rewrite_catalog_fragment(fragment: str, prefix: str, courses: dict[str, CourseRecord]) -> str:
    soup = BeautifulSoup(fragment, "html.parser")
    pid_lookup = {
        course.detail.get("pid"): course.code
        for course in courses.values()
        if course.detail.get("pid")
    }
    for anchor in soup.find_all("a"):
        href = anchor.get("href", "")
        if href.startswith("#/courses/"):
            pid = href.rsplit("/", 1)[-1]
            course_code = pid_lookup.get(pid)
            if course_code and course_code in courses:
                anchor["href"] = course_page_href(prefix, course_code, courses) or "#"
            else:
                anchor.unwrap()
            continue
        if href.startswith("#/"):
            anchor.unwrap()
            continue
        anchor["target"] = "_blank"
        anchor["rel"] = "noreferrer"
    return str(soup)


def render_rich_text(fragment: str | None, prefix: str, courses: dict[str, CourseRecord]) -> str:
    if not fragment:
        return '<p class="empty-state">Nothing published for this field in the current snapshot.</p>'
    return f'<div class="rich-text">{rewrite_catalog_fragment(fragment, prefix, courses)}</div>'


def build_course_lookup() -> dict[str, CourseRecord]:
    manifest_rows = {}
    for manifest_name in ("eos_course_manifest.csv", "support_course_manifest.csv"):
        manifest_path = DATA_DIR / manifest_name
        if not manifest_path.exists():
            continue
        for row in read_csv_rows(manifest_path):
            manifest_rows[row["course_code"]] = row

    courses = {}
    course_detail_dir = DATA_DIR / "course_details"
    for path in sorted(course_detail_dir.glob("*.json"), key=lambda item: course_sort_key(item.stem)):
        code = path.stem
        detail = read_json(path)
        manifest = manifest_rows.get(code, {})
        requirement_nodes = parse_course_requirement_nodes(detail)
        courses[code] = CourseRecord(
            code=code,
            name=manifest.get("course_name") or detail.get("title") or code,
            catalog_url=manifest.get("catalog_url", ""),
            detail=detail,
            rule_nodes=requirement_nodes,
            prereq_codes=collect_course_codes(requirement_nodes),
        )
    return courses


def build_program_lookup() -> dict[str, ProgramRecord]:
    manifest_rows = {
        row["program_code"]: row for row in read_csv_rows(DATA_DIR / "seos_program_manifest.csv")
    }
    programs = {}
    detail_dir = DATA_DIR / "program_details"
    for path in sorted(detail_dir.glob("*.json"), key=lambda item: item.stem):
        code = path.stem
        detail = read_json(path)
        manifest = manifest_rows.get(code, {})
        sections = parse_program_sections(detail.get("programRequirements"))
        explicit_codes, text_requirements, section_course_map = summarize_program_sections(sections)
        streams = parse_program_streams(detail)
        programs[code] = ProgramRecord(
            code=code,
            name=manifest.get("program_name") or detail.get("title") or code,
            title=manifest.get("program_title") or detail.get("title") or code,
            catalog_url=manifest.get("catalog_url", ""),
            detail=detail,
            sections=sections,
            explicit_course_codes=explicit_codes,
            text_requirements=text_requirements,
            section_course_map=section_course_map,
            streams=streams,
        )
    return programs


def augment_courses_with_program_placeholders(
    courses: dict[str, CourseRecord],
    programs: dict[str, ProgramRecord],
) -> None:
    discovered_names: dict[str, str] = {}
    for program in programs.values():
        for section in program_graph_sections(program):
            for code, title in iter_program_course_entries(section["rules"]):
                discovered_names.setdefault(code, title)
        for stream in program.streams:
            for section in stream.sections:
                for code, title in iter_program_course_entries(section["rules"]):
                    discovered_names.setdefault(code, title)

    for code, name in discovered_names.items():
        if code in courses:
            continue
        courses[code] = CourseRecord(
            code=code,
            name=name,
            catalog_url="",
            detail={"description": ""},
            rule_nodes=[],
            prereq_codes=[],
            placeholder=True,
        )


def enrich_relationships(programs: dict[str, ProgramRecord], courses: dict[str, CourseRecord]) -> None:
    for program in programs.values():
        include_stream_courses = not is_eos_base_program(program)
        named_codes = program_named_codes(program, include_stream_courses=include_stream_courses)
        section_lookup = program_section_lookup(program)
        for code in named_codes:
            if code in courses:
                courses[code].used_by_programs.add(program.code)

        support_codes: list[str] = []
        for code in named_codes:
            if code not in courses:
                continue
            for prereq_code in courses[code].prereq_codes:
                if prereq_code not in section_lookup:
                    support_codes.append(prereq_code)
        program.support_codes = sorted(unique_ordered(support_codes), key=course_sort_key)

        for stream in program.streams:
            stream_named_codes = program_named_codes(program, stream)
            stream_section_lookup = program_section_lookup(program, stream)
            stream_support_codes: list[str] = []
            for code in stream_named_codes:
                if code not in courses:
                    continue
                for prereq_code in courses[code].prereq_codes:
                    if prereq_code not in stream_section_lookup:
                        stream_support_codes.append(prereq_code)
            stream.support_codes = sorted(unique_ordered(stream_support_codes), key=course_sort_key)

    for course in courses.values():
        for prereq_code in course.prereq_codes:
            if prereq_code in courses:
                courses[prereq_code].dependents.add(course.code)


def prepare_output_directory() -> None:
    if BUILD_DIR.exists():
        shutil.rmtree(BUILD_DIR)
    PROGRAM_GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    COURSE_GRAPH_DIR.mkdir(parents=True, exist_ok=True)
    shutil.copy2(STYLE_SOURCE, BUILD_DIR / "program-guide.css")
    shutil.copy2(SCRIPT_SOURCE, BUILD_DIR / "program-guide.js")
    if HERO_SOURCE_DIR.exists():
        shutil.copytree(HERO_SOURCE_DIR, HERO_BUILD_DIR)
    (BUILD_DIR / ".nojekyll").write_text("", encoding="utf-8")


def graph_base(name: str) -> Digraph:
    graph = Digraph(name=name, format="svg")
    graph.attr(
        rankdir="LR",
        bgcolor="transparent",
        splines="spline",
        nodesep="0.28",
        ranksep="0.85",
        pad="0.3",
        fontname="Avenir Next",
    )
    graph.attr(
        "node",
        shape="box",
        style="filled,rounded",
        color="#1b2730",
        penwidth="1.1",
        fontname="Avenir Next",
        fontsize="10",
        margin="0.11,0.08",
    )
    graph.attr(
        "edge",
        color="#5d6972",
        penwidth="1.1",
        arrowsize="0.7",
        fontname="Avenir Next",
        fontsize="9",
    )
    return graph


def add_graph_rule_tree(
    graph: Digraph,
    node: dict,
    parent_id: str,
    namespace: str,
    courses: dict[str, CourseRecord],
    explicit_codes: set[str],
    seen_nodes: set[str],
) -> None:
    if node["kind"] == "course":
        code = node["code"]
        if code not in seen_nodes:
            node_kwargs = {
                "label": code,
                "fillcolor": subject_color(code, missing=code not in courses),
                "tooltip": courses[code].name if code in courses else code,
            }
            svg_href = svg_course_href(code, courses)
            if svg_href:
                node_kwargs["URL"] = svg_href
                node_kwargs["target"] = "_top"
            graph.node(code, **node_kwargs)
            seen_nodes.add(code)
        graph.edge(parent_id, code, color="#7a8389")
        return

    if node["kind"] == "text":
        note_id = f"note_{namespace}"
        graph.node(
            note_id,
            label=node["text"],
            shape="note",
            fillcolor="#fff3e4",
            color="#b7793f",
        )
        graph.edge(parent_id, note_id, color="#b7793f")
        return

    rule_id = f"rule_{namespace}"
    graph.node(
        rule_id,
        label=short_group_label(node["label"]),
        shape="circle",
        width="0.82",
        height="0.82",
        fillcolor="#fffdf8",
        color="#1f4f66",
        fontsize="9",
    )
    graph.edge(parent_id, rule_id, color="#1f4f66")
    for index, child in enumerate(node["children"]):
        add_graph_rule_tree(
            graph,
            child,
            rule_id,
            f"{namespace}_{index}",
            courses,
            explicit_codes,
            seen_nodes,
        )


def write_program_graph(
    program: ProgramRecord,
    courses: dict[str, CourseRecord],
    course_groups: dict[str, CourseGroupRecord],
    course_group_lookup: dict[str, str],
    *,
    mode: GraphModeRecord,
    stream: ProgramStreamRecord | None = None,
) -> None:
    graph_id = stream_asset_stem(program, stream) if stream is not None else program.code
    graph = graph_base(graph_id)
    if mode.key == "simplified":
        graph.attr(nodesep="0.18", ranksep="0.58", pad="0.16")
    elif mode.year_ordered:
        graph.attr(
            nodesep="0.34",
            ranksep="1.15",
            pad="0.45",
        )
    include_stream_courses = not is_eos_base_program(program) if stream is None else True
    explicit_codes = {code for code in program_named_codes(program, stream, include_stream_courses=include_stream_courses) if code in courses}
    visible_codes = explicit_codes | {code for code in program_support_codes(program, stream) if code in courses}
    node_styles, _legend_items = build_program_node_styles(
        program,
        stream,
        course_group_lookup=course_group_lookup,
        include_stream_courses=stream is not None or not is_eos_base_program(program),
    )
    prereq_map, dependent_map = build_group_dependency_maps(visible_codes, courses, course_group_lookup)
    prereq_closure = compute_group_prereq_closure(prereq_map)
    depth_map = compute_group_depths(prereq_map)
    explicit_groups = {course_group_lookup.get(code, code) for code in explicit_codes}
    year_group_lookup = build_program_year_group_lookup(program, course_group_lookup, stream) if mode.year_ordered else {}
    visible_groups_set = set(prereq_map)
    inferred_year_groups = (
        build_program_elective_year_group_lookup(
            program,
            courses=courses,
            visible_groups=visible_groups_set,
            explicit_year_groups=year_group_lookup,
            course_group_lookup=course_group_lookup,
            stream=stream,
        )
        if mode.year_ordered
        else {}
    )
    year_group_lookup = {**inferred_year_groups, **year_group_lookup}
    year_bucket_order = {"year-1": 0, "year-2": 1, "years-3-4": 2}
    visible_groups = sorted(
        prereq_map,
        key=lambda group_code: (
            year_bucket_order.get(year_group_lookup.get(group_code, ""), 99) if mode.year_ordered else depth_map.get(group_code, 0),
            depth_map.get(group_code, 0),
            0 if group_code in explicit_groups else 1,
            subject_from_code(group_code),
            course_sort_key(group_code),
        ),
    )

    for group_code in visible_groups:
        add_course_group_node(
            graph,
            group_code,
            course_groups,
            courses,
            emphasis=group_code in explicit_groups,
            style_overrides=node_styles.get(group_code),
        )

    depth_groups: dict[int, list[str]] = {}
    for group_code in visible_groups:
        depth_groups.setdefault(depth_map.get(group_code, 0), []).append(group_code)

    if mode.year_ordered:
        slotted_groups = {
            group_code
            for group_code, bucket_key in year_group_lookup.items()
            if bucket_key in year_bucket_order
        }
        flexible_bucket_preferences = infer_flexible_group_bucket_preferences(
            visible_groups=visible_groups_set,
            slotted_groups={group_code: year_group_lookup[group_code] for group_code in slotted_groups},
            dependent_map=dependent_map,
        )
        bucket_groups: dict[str, list[str]] = {"year-1": [], "year-2": [], "years-3-4": []}
        for group_code in visible_groups:
            bucket_key = year_group_lookup.get(group_code)
            if bucket_key in bucket_groups:
                bucket_groups[bucket_key].append(group_code)

        previous_anchor: str | None = None
        previous_exit: str | None = None
        for bucket_key, bucket_label in CONTACT_SUMMARY_BUCKETS:
            cluster_groups = bucket_groups[bucket_key]
            if not cluster_groups:
                continue
            entry_id = f"year_band__{bucket_key}__entry"
            exit_id = f"year_band__{bucket_key}__exit"
            label_id = f"year_band__{bucket_key}__label"
            with graph.subgraph(name=f"cluster_{bucket_key}") as cluster:
                cluster.attr(
                    label="",
                    style="rounded",
                    color="#d8dde1",
                    pencolor="#d8dde1",
                    penwidth="1.2",
                    bgcolor="#fbfcfd",
                    margin="28",
                )
                cluster.node(
                    label_id,
                    label=bucket_label,
                    shape="box",
                    style="filled,rounded",
                    fillcolor="#eef2f4",
                    color="#c8d0d5",
                    penwidth="0.8",
                    fontname="Avenir Next",
                    fontsize="13",
                    fontcolor="#4e5f68",
                    margin="0.08,0.04",
                )
                cluster.node(entry_id, label="", shape="point", width="0.01", height="0.01", style="invis")
                cluster.node(exit_id, label="", shape="point", width="0.01", height="0.01", style="invis")
                cluster.edge(label_id, entry_id, style="invis", weight="40", minlen="1")
                for depth in sorted({depth_map.get(group_code, 0) for group_code in cluster_groups}):
                    with cluster.subgraph(name=f"rank_{bucket_key}_{depth}") as rank_subgraph:
                        rank_subgraph.attr(rank="same")
                        for group_code in cluster_groups:
                            if depth_map.get(group_code, 0) == depth:
                                rank_subgraph.node(course_group_id(group_code))
                cluster.edge(entry_id, exit_id, style="invis", weight="120", minlen="5")
            if previous_anchor is not None:
                graph.edge(previous_anchor, entry_id, style="invis", weight="180", minlen="7")
            if previous_exit is not None:
                graph.edge(previous_exit, label_id, style="invis", weight="120", minlen="3")
            previous_anchor = label_id
            previous_exit = exit_id

        for group_code in sorted(slotted_groups, key=course_sort_key):
            bucket_key = year_group_lookup.get(group_code)
            if bucket_key not in year_bucket_order:
                continue
            node_id = course_group_id(group_code)
            graph.edge(
                f"year_band__{bucket_key}__entry",
                node_id,
                style="invis",
                weight="18" if group_code in explicit_groups else "8",
                minlen="1",
            )
            if group_code in explicit_groups:
                graph.edge(
                    node_id,
                    f"year_band__{bucket_key}__exit",
                    style="invis",
                    weight="10",
                    minlen="1",
                )

        for group_code in sorted(flexible_bucket_preferences, key=course_sort_key):
            bucket_key = flexible_bucket_preferences[group_code]
            if bucket_key not in year_bucket_order:
                continue
            graph.edge(
                f"year_band__{bucket_key}__entry",
                course_group_id(group_code),
                style="invis",
                weight="3",
                minlen="2",
            )
    else:
        for depth in sorted(depth_groups):
            rank_nodes = [course_group_id(group_code) for group_code in depth_groups[depth]]
            with graph.subgraph(name=f"rank_program_depth_{depth}") as rank_subgraph:
                rank_subgraph.attr(rank="same")
                for node_id in rank_nodes:
                    rank_subgraph.node(node_id)

    drawn_edges: set[tuple[str, str, str]] = set()
    created_aux_nodes: set[str] = set()
    bundle_registry: dict[tuple[tuple[str, str], ...], str] | None = {} if mode.key != "full" else None
    choice_registry: dict[tuple[str, tuple[tuple[str, str], ...]], str] | None = {} if mode.key != "full" else None
    for target_group in sorted(visible_groups, key=course_sort_key):
        target_rule_nodes = dedupe_requirement_nodes(
            (
                rule_node
                for target_code in course_groups[target_group].codes
                if target_code in courses
                for rule_node in courses[target_code].rule_nodes
            ),
            visible_codes=visible_codes,
            courses=courses,
            course_group_lookup=course_group_lookup,
            target_group=target_group,
        )
        if not target_rule_nodes:
            continue
        add_simplified_requirement_flow(
            graph,
            target_code=target_group,
            rule_nodes=target_rule_nodes,
            visible_codes=visible_codes,
            courses=courses,
            course_groups=course_groups,
            course_group_lookup=course_group_lookup,
            drawn_edges=drawn_edges,
            created_aux_nodes=created_aux_nodes,
            summaries_enabled=False,
            bundle_registry=bundle_registry,
            choice_registry=choice_registry,
            group_prereq_closure=prereq_closure,
        )

    svg_bytes = graph.pipe(format="svg")
    (PROGRAM_GRAPH_DIR / f"{graph_id}{mode.asset_suffix}.svg").write_bytes(svg_bytes)


def write_course_graph(
    course: CourseRecord,
    courses: dict[str, CourseRecord],
    course_groups: dict[str, CourseGroupRecord],
    course_group_lookup: dict[str, str],
    *,
    simplified: bool,
) -> None:
    graph = graph_base(course.code)
    focus_group = course_group_lookup.get(course.code, course.code)
    focus_codes = {code for code in course_groups[focus_group].codes if code in courses}
    all_codes = set(courses)
    all_prereq_map, all_dependent_map = build_group_dependency_maps(
        all_codes,
        courses,
        course_group_lookup,
    )
    if simplified:
        visible_groups = {focus_group}
        visible_groups.update(collect_related_groups(focus_group, all_prereq_map, 1))
        visible_groups.update(collect_related_groups(focus_group, all_dependent_map, 1))
    else:
        visible_groups = {focus_group}
        visible_groups.update(collect_related_groups(focus_group, all_prereq_map, None))
        visible_groups.update(collect_related_groups(focus_group, all_dependent_map, None))

    visible_codes = visible_codes_for_groups(visible_groups, course_groups)
    prereq_map, dependent_map = build_group_dependency_maps(visible_codes, courses, course_group_lookup)
    prereq_closure = compute_group_prereq_closure(prereq_map)
    relative_depths = compute_relative_group_depths(focus_group, prereq_map, dependent_map)
    ordered_visible_groups = sorted(
        prereq_map,
        key=lambda group_code: (
            relative_depths.get(group_code, 0),
            0 if group_code == focus_group else 1,
            subject_from_code(group_code),
            course_sort_key(group_code),
        ),
    )
    focus_prereqs = prereq_map.get(focus_group, set())
    focus_dependents = dependent_map.get(focus_group, set())

    for group_code in ordered_visible_groups:
        add_course_group_node(
            graph,
            group_code,
            course_groups,
            courses,
            emphasis=group_code in focus_prereqs or group_code in focus_dependents,
            focus=group_code == focus_group,
            focus_name=course.name if group_code == focus_group else None,
            preferred_code=course.code if group_code == focus_group else None,
        )

    depth_groups: dict[int, list[str]] = {}
    for group_code in ordered_visible_groups:
        depth_groups.setdefault(relative_depths.get(group_code, 0), []).append(group_code)

    for depth in sorted(depth_groups):
        rank_nodes = [course_group_id(group_code) for group_code in depth_groups[depth]]
        with graph.subgraph(name=f"rank_course_depth_{depth}") as rank_subgraph:
            rank_subgraph.attr(rank="same")
            for node_id in rank_nodes:
                rank_subgraph.node(node_id)

    drawn_edges: set[tuple[str, str, str]] = set()
    created_aux_nodes: set[str] = set()
    for target_group in sorted(visible_groups, key=course_sort_key):
        target_rule_nodes = dedupe_requirement_nodes(
            (
                rule_node
                for target_code in course_groups[target_group].codes
                if target_code in courses
                for rule_node in courses[target_code].rule_nodes
            ),
            visible_codes=visible_codes,
            courses=courses,
            course_group_lookup=course_group_lookup,
            target_group=target_group,
        )
        if not target_rule_nodes:
            continue
        add_simplified_requirement_flow(
            graph,
            target_code=target_group,
            rule_nodes=target_rule_nodes,
            visible_codes=visible_codes,
            courses=courses,
            course_groups=course_groups,
            course_group_lookup=course_group_lookup,
            drawn_edges=drawn_edges,
            created_aux_nodes=created_aux_nodes,
            summaries_enabled=False,
            bundle_registry=None,
            choice_registry=None,
            group_prereq_closure=prereq_closure,
        )

    svg_bytes = graph.pipe(format="svg")
    suffix = "--simplified" if simplified else ""
    (COURSE_GRAPH_DIR / f"{course.code}{suffix}.svg").write_bytes(svg_bytes)


def render_nav(base: str, active: str) -> str:
    local_items = [
        ("Overview", f"{base}index.html", "home"),
        ("Programs", f"{base}programs/overview.html", "programs"),
        ("Courses", f"{base}courses/overview.html", "courses"),
        ("Workflow", f"{base}curriculum_workflow.html", "workflow"),
    ]
    ecosystem_items = [
        ("Earth History Research", RESEARCH_SITE_URL),
        ("Curriculum Work", CURRICULUM_SITE_URL),
        ("Teaching", TEACHING_SITE_URL),
    ]
    links = []
    links.append('<span class="site-nav__label">This site</span>')
    for label, href, key in local_items:
        is_active = key == active
        class_attr = ' class="is-active"' if is_active else ""
        current = ' aria-current="page"' if is_active else ""
        links.append(f"<a{class_attr} href=\"{href}\"{current}>{e(label)}</a>")
    links.append('<span class="nav-divider" aria-hidden="true">|</span>')
    links.append('<span class="site-nav__label">Other sites</span>')
    for label, href in ecosystem_items:
        links.append(f'<a href="{href}" target="_blank" rel="noopener">{e(label)}</a>')
    return "".join(links)


def program_hero_image(base: str, program: ProgramRecord) -> str:
    return f"{HERO_ASSET_URL}program-overview.jpg"


def course_hero_image(base: str, course: CourseRecord) -> str:
    return f"{HERO_ASSET_URL}course-overview.jpg"


def render_layout(
    *,
    base: str,
    active: str,
    active_site: str,
    title: str,
    description: str,
    eyebrow: str,
    hero_title: str,
    hero_lede: str,
    hero_actions: str,
    content: str,
    hero_image: str | None = None,
    body_class: str = "",
) -> str:
    hero_class = "hero hero--guide hero--photo" if hero_image else "hero hero--guide"
    hero_style = f' style="--hero-image: url(\'{hero_image}\')"' if hero_image else ""
    body_class_attr = f' class="{e(body_class)}"' if body_class else ""
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{e(title)}</title>
  <meta name="description" content="{e(description)}">
  <meta name="theme-color" content="#f4f1eb">
  <link rel="stylesheet" href="{base}program-guide.css">
  <script defer src="{base}program-guide.js"></script>
</head>
<body{body_class_attr}>
  <header class="site-header">
    <div class="nav-shell">
      <a class="site-mark" href="{base}index.html">{e(SITE_NAME)}</a>
      <nav class="site-nav" aria-label="Sections">
        {render_nav(base, active)}
      </nav>
    </div>
  </header>

  <main class="page-shell">
    <section class="{hero_class}"{hero_style}>
      <div class="hero__content">
        <p class="hero__eyebrow">{e(eyebrow)}</p>
        <h1 class="hero__title hero__title--wide">{e(hero_title)}</h1>
        <p class="hero__lede">{e(hero_lede)}</p>
        {hero_actions}
      </div>
    </section>
    {content}
  </main>

  <footer>
    <div class="footer-shell">
      <div>
        <p class="footer-brand">{e(SITE_NAME)}</p>
        <p class="footer-copy">Static curriculum maps generated from current UVic undergraduate calendar data. Pages and graphs are rebuilt together so the published site stays aligned with the catalog snapshot.</p>
      </div>
      <div class="footer-links">
        <a href="{base}programs/overview.html">Programs</a>
        <a href="{base}courses/overview.html">Courses</a>
        <a href="{base}curriculum_workflow.html">Workflow</a>
        <a href="{RESEARCH_SITE_URL}" target="_blank" rel="noopener">Earth History Research</a>
        <a href="{TEACHING_SITE_URL}" target="_blank" rel="noopener">Teaching</a>
        <a href="{CURRICULUM_SITE_URL}" target="_blank" rel="noopener">Curriculum work</a>
      </div>
    </div>
  </footer>
</body>
</html>
"""


def render_metric_card(value: str, label: str) -> str:
    return (
        '<article class="metric-card">'
        f'<p class="metric-card__value">{value}</p>'
        f'<p class="metric-card__label">{e(label)}</p>'
        "</article>"
    )


def render_filter_search(
    label: str,
    placeholder: str,
    *,
    autocomplete_id: str | None = None,
    autocomplete_options: list[tuple[str, str]] | None = None,
) -> str:
    list_attr = f' list="{e(autocomplete_id)}"' if autocomplete_id else ""
    datalist = ""
    if autocomplete_id and autocomplete_options:
        seen_values: set[str] = set()
        option_markup = []
        for value, option_label in autocomplete_options:
            normalized = value.strip()
            if not normalized or normalized.lower() in seen_values:
                continue
            seen_values.add(normalized.lower())
            label_attr = f' label="{e(option_label)}"' if option_label else ""
            option_markup.append(f'<option value="{e(normalized)}"{label_attr}></option>')
        datalist = f'<datalist id="{e(autocomplete_id)}">{"".join(option_markup)}</datalist>'
    return (
        '<label class="search-field filter-search">'
        f'<span>{e(label)}</span>'
        f'<input type="search" data-filter-search-input placeholder="{e(placeholder)}" autocomplete="off"{list_attr}>'
        f"{datalist}"
        "</label>"
    )


def render_filter_disclosure(title: str, body: str, *, open: bool = False) -> str:
    open_attr = " open" if open else ""
    return (
        f'<details class="filter-disclosure"{open_attr}>'
        f'<summary>{e(title)}</summary>'
        f'{body}'
        "</details>"
    )


def render_graph_key_item(title: str, body: str, sample: str) -> str:
    return (
        '<article class="graph-key__item">'
        f'{sample}'
        '<div>'
        f'<p class="graph-key__title">{e(title)}</p>'
        f'<p class="graph-key__copy">{e(body)}</p>'
        '</div>'
        '</article>'
    )


def render_graph_key_sample(label: str, modifier: str) -> str:
    contents = e(label) if label else "&nbsp;"
    return f'<span class="graph-key__sample graph-key__sample--{modifier}">{contents}</span>'


def render_program_graph_key() -> str:
    items = [
        render_graph_key_item(
            "Choice point",
            "A shared published requirement such as choose 1 of, 2 of, or 3 of.",
            render_graph_key_sample("1 of", "choice"),
        ),
        render_graph_key_item(
            "Grouping junction",
            "A small circular join keeps shared required branches tidy without repeating full connectors.",
            render_graph_key_sample("", "junction"),
        ),
        render_graph_key_item(
            "Published notes",
            "Merged narrative requirements such as electives or standing notes that are useful context but do not form a prerequisite branch.",
            render_graph_key_sample("Notes", "support"),
        ),
        render_graph_key_item(
            "Merged course node",
            "Equivalent or cross-listed courses are collapsed into one shared node.",
            render_graph_key_sample("EOS431 / PHYS441", "merged"),
        ),
    ]
    return '<div class="graph-key">' + "".join(items) + "</div>"


def render_course_graph_key() -> str:
    items = [
        render_graph_key_item(
            "Focus course",
            "The course page you are viewing.",
            render_graph_key_sample("EOS311", "focus"),
        ),
        render_graph_key_item(
            "Connected course",
            "A prerequisite or downstream course included in the current view.",
            render_graph_key_sample("CHEM102", "named"),
        ),
        render_graph_key_item(
            "Choice point",
            "A shared requirement such as choose 1 of, 2 of, or 3 of.",
            render_graph_key_sample("2 of", "choice"),
        ),
        render_graph_key_item(
            "Grouping junction",
            "A small circular join keeps shared requirement branches tidy.",
            render_graph_key_sample("", "junction"),
        ),
        render_graph_key_item(
            "Merged course node",
            "Equivalent or cross-listed courses are collapsed into one shared node.",
            render_graph_key_sample("BIOL311 / EOS311", "merged"),
        ),
    ]
    return '<div class="graph-key">' + "".join(items) + "</div>"


def render_subject_legend(codes: Iterable[str]) -> str:
    return "".join(
        f'<span class="legend-item"><span class="legend-swatch" style="--swatch-color: {subject_color(code)}"></span>{e(subject_name(code))}</span>'
        for code in unique_ordered(subject_from_code(course_code) for course_code in codes)[:6]
        for code in [code]
    )


def render_program_role_legend(items: list[tuple[str, dict[str, str]]]) -> str:
    return "".join(
        f'<span class="legend-item"><span class="legend-swatch" style="--swatch-color: {e(style["fillcolor"])}; --swatch-border: {e(style["color"])}"></span>{e(label)}</span>'
        for label, style in items
    )


def graph_overlay_legend_data(
    *,
    title: str,
    note: str,
    items: list[tuple[str, dict[str, str]]],
) -> dict:
    return {
        "title": title,
        "note": note,
        "items": [
            {
                "label": label,
                "color": style["fillcolor"],
                "borderColor": style["color"],
            }
            for label, style in items
        ],
    }


def render_graph_overlay_legend_body(legend: dict | None) -> str:
    if not legend:
        return ""
    items_html = "".join(
        (
            '<div class="graph-overlay-legend__item">'
            f'<span class="graph-overlay-legend__swatch" style="--legend-color: {e(str(item.get("color") or ""))}; --legend-border: {e(str(item.get("borderColor") or ""))}"></span>'
            '<span class="graph-overlay-legend__copy">'
            f'<span class="graph-overlay-legend__label">{e(str(item.get("label") or ""))}</span>'
            "</span>"
            "</div>"
        )
        for item in legend.get("items", [])
    )
    return f'<div class="graph-overlay-legend__list">{items_html}</div>'


def render_graph_guide(
    *,
    summary: str,
    preview_samples: list[tuple[str, str]] | None,
    legend_html: str,
    graph_key_html: str,
    preview_html: str | None = None,
    title: str = "Graph key and legend",
) -> str:
    if preview_html is not None:
        preview = preview_html
    else:
        preview = "".join(render_graph_key_sample(label, modifier) for label, modifier in (preview_samples or []))
    legend_block = f'<div class="legend">{legend_html}</div>' if legend_html else ""
    return f"""
    <details class="graph-guide">
      <summary class="graph-guide__summary">
        <span class="graph-guide__summary-copy">
          <span class="graph-guide__title">{e(title)}</span>
          <span class="graph-guide__caption">{e(summary)}</span>
        </span>
        <span class="graph-guide__preview">{preview}</span>
      </summary>
      <div class="graph-guide__body">
        {legend_block}
        {graph_key_html}
      </div>
    </details>
    """


def render_graph_preview(
    *,
    title: str,
    summary: str,
    preview_html: str,
) -> str:
    return f"""
    <div class="graph-guide graph-guide--static">
      <div class="graph-guide__summary">
        <span class="graph-guide__summary-copy">
          <span class="graph-guide__title">{e(title)}</span>
          <span class="graph-guide__caption">{e(summary)}</span>
        </span>
        <span class="graph-guide__preview">{preview_html}</span>
      </div>
    </div>
    """


def render_additional_requirements(note_lines: list[str], *, title: str) -> str:
    if not note_lines:
        return ""
    items = "".join(f"<li>{e(line)}</li>" for line in note_lines)
    return f"""
    <div class="graph-followup">
      <p class="detail-card__eyebrow">{e(title)}</p>
      <ul class="graph-followup__list">{items}</ul>
    </div>
    """


def graph_asset_path_for_url(svg_path: str) -> Path:
    normalized = svg_path
    while normalized.startswith("../"):
        normalized = normalized[3:]
    normalized = normalized.lstrip("/")
    return BUILD_DIR / normalized


def rewrite_inline_svg_course_links(svg_markup: str, course_href_prefix: str) -> str:
    def rewrite_course_href(match: re.Match[str]) -> str:
        attr = match.group("attr")
        quote = match.group("quote")
        code = match.group("code")
        return f'{attr}={quote}{course_href_prefix}{code}.html{quote}'

    svg_markup = re.sub(
        r'(?P<attr>\b(?:xlink:href|href))=(?P<quote>["\'])\.\./\.\./\.\./courses/(?P<code>[A-Z]{2,5}[0-9]{3}[A-Z]?)\.html(?P=quote)',
        rewrite_course_href,
        svg_markup,
    )

    def add_plain_href(match: re.Match[str]) -> str:
        tag = match.group(0)
        if re.search(r"(?<!:)href=", tag):
            return tag
        xlink_href = re.search(r'xlink:href=(["\'])([^"\']+)\1', tag)
        if not xlink_href:
            return tag
        return f'{tag[:-1]} href="{xlink_href.group(2)}">'

    return re.sub(r"<a\b[^>]*>", add_plain_href, svg_markup)


def inline_graph_svg(svg_path: str, aria_label: str, *, course_href_prefix: str) -> str:
    asset_path = graph_asset_path_for_url(svg_path)
    try:
        svg_markup = asset_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return (
            f'<p class="empty-state">Graph file unavailable. '
            f'<a class="text-link" href="{e(svg_path)}">Open the SVG file</a>.</p>'
        )

    svg_markup = re.sub(r"^\s*<\?xml[^>]*>\s*", "", svg_markup)
    svg_markup = re.sub(r"^\s*<!DOCTYPE[\s\S]*?>\s*", "", svg_markup).strip()
    svg_markup = rewrite_inline_svg_course_links(svg_markup, course_href_prefix)
    svg_markup = re.sub(
        r"<svg\b",
        (
            '<svg class="atlas-graph-svg" role="img" '
            f'aria-label="{e(aria_label)}" focusable="false" '
            'preserveAspectRatio="xMidYMid meet"'
        ),
        svg_markup,
        count=1,
    )
    return svg_markup


def json_for_script(data: dict | list) -> str:
    return json.dumps(data, ensure_ascii=False).replace("<", "\\u003c").replace("</", "<\\/")


def render_program_graph_analytics(analytics: dict) -> str:
    return f"""
      <div class="graph-analytics" data-graph-analytics>
        <script type="application/json" data-graph-analytics-data>{json_for_script(analytics)}</script>
        <label class="graph-overlay-select">
          <span>Overlay</span>
          <select data-analytics-mode-select aria-label="Graph analytics overlay">
            <option value="base" selected>No overlay</option>
            <option value="year">Program year</option>
            <option value="theme">Subject themes</option>
            <option value="bottleneck">Bottlenecks</option>
            <option value="delay">Chain depth</option>
            <option value="cleanup">Cleanup</option>
          </select>
        </label>
      </div>
    """


def render_graph_shell(
    *,
    shell_id: str,
    section_kicker: str,
    heading: str,
    note: str,
    default_svg: str,
    aria_label: str,
    guide_html: str,
    graph_modes: list[tuple[GraphModeRecord, str]],
    course_href_prefix: str,
    footer_html: str = "",
    analytics_html: str = "",
    overlay_legend: dict | None = None,
) -> str:
    toolbar_buttons = []
    graph_templates = []
    default_graph_markup = ""
    guide_html = guide_html.rstrip()
    footer_html = footer_html.rstrip()
    analytics_html = analytics_html.rstrip()
    overlay_legend_html = (
        f'<script type="application/json" data-graph-overlay-legend-data>{json_for_script(overlay_legend)}</script>'
        if overlay_legend
        else ""
    )
    overlay_legend_body_html = render_graph_overlay_legend_body(overlay_legend)
    overlay_legend_hidden = "" if overlay_legend_body_html else " hidden"
    for index, (mode, svg_path) in enumerate(graph_modes):
        active_class = " is-active" if index == 0 else ""
        toolbar_buttons.append(
            f'<button class="toggle-button{active_class}" type="button" data-graph-mode="{e(mode.key)}" '
            f'data-graph-src="{svg_path}" data-graph-download="{svg_path}" data-graph-copy="{e(mode.copy_text)}">{e(mode.button_label)}</button>'
        )
        graph_markup = inline_graph_svg(svg_path, aria_label, course_href_prefix=course_href_prefix)
        graph_templates.append(f'<template data-graph-template="{e(mode.key)}">{graph_markup}</template>')
        if index == 0:
            default_graph_markup = graph_markup
    return f"""
    <div class="graph-shell" id="{e(shell_id)}" data-graph-switcher>
      <div class="graph-shell__head">
        <div>
          <p class="section-kicker">{e(section_kicker)}</p>
          <h2>{e(heading)}</h2>
          <p class="graph-note">{e(note)}</p>
        </div>
        <a class="text-link graph-open-link" data-graph-link href="{default_svg}">Open SVG</a>
      </div>
      {guide_html}
      <div class="graph-frame">
        {overlay_legend_html}
        <div class="graph-frame__left-rail">
          <details class="graph-search-dock">
            <summary class="graph-overlay-summary">Find</summary>
            <div class="graph-search-dock__body">
              <label class="search-field graph-search graph-search--overlay">
                <span>Find a course</span>
                <input type="search" data-graph-search-input placeholder="Course code or title" autocomplete="off">
              </label>
              <button class="filter-clear graph-reset" type="button" data-graph-reset>Reset view</button>
              <p class="panel-note graph-search__status" data-graph-search-status>Search highlights matching branches.</p>
            </div>
          </details>
        </div>
        <div class="graph-frame__right-rail">
          <details class="graph-control-dock">
            <summary class="graph-overlay-summary">Overlays</summary>
            <div class="graph-control-dock__body">
              <div class="graph-control-dock__group">
                <p class="detail-card__eyebrow">View</p>
                <div class="segmented-control" role="group" aria-label="{e(heading)} graph mode">
                  {"".join(toolbar_buttons)}
                </div>
              </div>
              {analytics_html}
            </div>
          </details>
          <details class="graph-overlay-legend" data-graph-overlay-legend{overlay_legend_hidden}>
            <summary class="graph-overlay-summary" data-graph-overlay-legend-summary>Legend</summary>
            <div class="graph-overlay-legend__body" data-graph-overlay-legend-body>{overlay_legend_body_html}</div>
          </details>
        </div>
        <div class="graph-svg-stage" data-graph-stage aria-label="{e(aria_label)}">
          {default_graph_markup}
        </div>
        <div class="graph-template-bank" hidden>
          {"".join(graph_templates)}
        </div>
      </div>
      {footer_html}
    </div>
    """


def filter_token_string(values: Iterable[str]) -> str:
    return " ".join(unique_ordered(value for value in values if value))


def subject_department_token(subject_code: str) -> str | None:
    mapping = {
        "EOS": "seos",
        "BIOC": "bioc",
        "BIOL": "biol",
        "CHEM": "chem",
        "CSC": "csc",
        "GEOG": "geog",
        "MATH": "math",
        "PHYS": "phys",
        "STAT": "stat",
    }
    return mapping.get(subject_code)


def department_label_from_token(token: str) -> str:
    return DEPARTMENT_LABELS.get(token, token.replace("-", " ").title())


def program_category_tokens(program: ProgramRecord) -> list[str]:
    lower_text = f"{program.name} {program.title}".lower()
    if "minor" in lower_text:
        tokens = ["minor"]
    elif "general" in lower_text:
        tokens = ["general"]
    elif "honours" in lower_text:
        tokens = ["honours"]
    else:
        tokens = ["major"]
    if "combined" in lower_text:
        tokens.append("combined")
    else:
        tokens.append("seos-only")
    return tokens


def program_primary_category_label(program: ProgramRecord) -> str:
    tokens = program_category_tokens(program)
    if "combined" in tokens and "honours" in tokens:
        return "Combined Honours"
    if "combined" in tokens and "major" in tokens:
        return "Combined Major"
    if "honours" in tokens:
        return "Honours"
    if "minor" in tokens:
        return "Minor"
    if "general" in tokens:
        return "General"
    return "Major"


def program_department_tokens(program: ProgramRecord, courses: dict[str, CourseRecord]) -> list[str]:
    tokens = {"seos"}
    visible_codes = unique_ordered(program.explicit_course_codes + program.support_codes)
    for code in visible_codes:
        subject_code = subject_from_code(code)
        token = subject_department_token(subject_code)
        if token and token != "seos":
            tokens.add(token)
    return sorted(tokens)


def course_level_token(code: str) -> str:
    digits = re.findall(r"\d+", code)
    if not digits:
        return "other"
    number = int(digits[0])
    return str((number // 100) * 100)


def course_level_label(code: str) -> str:
    level = course_level_token(code)
    return f"{level}-level" if level != "other" else "Other level"


def theme_keyword_hits(text: str, keyword: str) -> int:
    normalized_keyword = keyword.lower()
    if " " in normalized_keyword:
        parts = [re.escape(part) + r"\w*" for part in normalized_keyword.split()]
        pattern = r"\b" + r"\s+".join(parts) + r"\b"
    elif normalized_keyword.isalpha() and len(normalized_keyword) <= 3:
        pattern = rf"\b{re.escape(normalized_keyword)}\b"
    else:
        pattern = rf"\b{re.escape(normalized_keyword)}\w*\b"
    return len(re.findall(pattern, text))


def course_theme_scores(course: CourseRecord) -> list[tuple[str, int]]:
    if course.code in COURSE_THEME_OVERRIDES:
        override_tokens = COURSE_THEME_OVERRIDES[course.code]
        override_rank = {token: len(override_tokens) - index for index, token in enumerate(override_tokens)}
        return [(token, override_rank[token]) for token in override_tokens]
    plain_description = BeautifulSoup(course.detail.get("description") or "", "html.parser").get_text(" ", strip=True)
    text = normalize_text(f"{course.name} {plain_description}").lower()
    scored: list[tuple[str, int, int]] = []
    for index, (token, _label, keywords) in enumerate(COURSE_THEME_RULES):
        score = sum(theme_keyword_hits(text, keyword) for keyword in keywords)
        if token == "math" and course.code in {"MATH248", "PHYS248"}:
            score = 0
        elif token == "math" and course.code.startswith("MATH"):
            score = max(score, 100)
        if score > 0:
            scored.append((token, score, index))
    scored.sort(key=lambda item: (-item[1], item[2]))
    return [(token, score) for token, score, _index in scored]


def course_theme_tokens(course: CourseRecord) -> list[str]:
    return [token for token, _score in course_theme_scores(course)]


def course_theme_labels(course: CourseRecord) -> list[str]:
    token_to_label = {token: label for token, label, _ in COURSE_THEME_RULES}
    return [token_to_label[token] for token in course_theme_tokens(course)]


def render_filter_button(label: str, *, group: str, value: str, active: bool = False) -> str:
    class_name = "filter-chip is-active" if active else "filter-chip"
    pressed = "true" if active else "false"
    return (
        f'<button class="{class_name}" type="button" data-filter-group="{e(group)}" '
        f'data-filter-value="{e(value)}" aria-pressed="{pressed}">{e(label)}</button>'
    )


def render_filter_group(title: str, buttons: list[str]) -> str:
    return (
        '<div class="filter-group">'
        f'<p class="detail-card__eyebrow">{e(title)}</p>'
        '<div class="filter-chip-row">'
        + "".join(buttons)
        + "</div></div>"
    )


def render_program_card(program: ProgramRecord, base: str, courses: dict[str, CourseRecord]) -> str:
    include_stream_courses = not is_eos_base_program(program)
    named_codes = program_named_codes(program, include_stream_courses=include_stream_courses)
    eos_count = sum(1 for code in named_codes if subject_from_code(code) == "EOS")
    partner_prereq_count = len(program.support_codes)
    category = program_primary_category_label(program)
    category_tokens = program_category_tokens(program)
    search_text = " ".join(unique_ordered([program.code, program.name, program.title, category, *category_tokens]))
    metadata_pills = "".join(
        f'<span class="meta-pill">{e(label)}</span>'
        for label in [category]
    )
    official_link = (
        f'<a class="text-link" href="{e(program.catalog_url)}">Official calendar</a>'
        if program.catalog_url
        else ""
    )
    return (
        '<article class="directory-card"'
        f' data-filter-category="{e(filter_token_string(category_tokens))}"'
        f' data-filter-search="{e(search_text.lower())}">'
        f'<p class="directory-card__eyebrow">{e(program.code)} | {e(category)}</p>'
        f'<h3><a href="{program_page_href(base, program.code)}">{e(program.name)}</a></h3>'
        f'<p>{e(program.title)}</p>'
        f'<p class="meta-line">{len(named_codes)} named courses | {eos_count} EOS | {partner_prereq_count} related prerequisite courses outside the named list</p>'
        f'<div class="pill-row">{metadata_pills}</div>'
        '<div class="link-row">'
        f'<a class="text-link" href="{program_page_href(base, program.code)}">Open graph</a>'
        f'{official_link}'
        "</div>"
        "</article>"
    )


def render_contact_overview_summary_value(summary: dict | None) -> str:
    if not summary:
        return '<span class="program-hours-cell__value">—</span>'
    if summary.get("has_field_course"):
        visible_value = e(summary["average_range"])
        spoken_value = e(summary["average_range"].replace(" (+F)", ""))
        return (
            '<span class="program-hours-cell__value" title="Includes summer field course">'
            f'<span aria-hidden="true">{visible_value}</span>'
            f'<span class="sr-only">{spoken_value}, includes summer field course</span>'
            "</span>"
        )
    return f'<span class="program-hours-cell__value">{e(summary["average_range"])}</span>'


def render_contact_overview_cell(paths: list[dict], bucket_key: str) -> str:
    if not paths:
        return '<div class="program-hours-cell"><span class="program-hours-cell__value">—</span></div>'
    if len(paths) == 1:
        return (
            '<div class="program-hours-cell">'
            f'{render_contact_overview_summary_value(paths[0]["summaries"].get(bucket_key))}'
            "</div>"
        )

    entries = []
    for path in paths:
        path_label = "Program path" if not path["is_stream"] else path["title"]
        entries.append(
            '<div class="program-hours-cell__entry">'
            f'<span class="program-hours-cell__path">{e(path_label)}</span>'
            f'{render_contact_overview_summary_value(path["summaries"].get(bucket_key))}'
            "</div>"
        )
    return '<div class="program-hours-cell program-hours-cell--stacked">' + "".join(entries) + "</div>"


def render_program_overview_row(program: ProgramRecord, courses: dict[str, CourseRecord]) -> str:
    category = program_primary_category_label(program)
    category_tokens = program_category_tokens(program)
    search_text = " ".join(unique_ordered([program.code, program.name, program.title, category, *category_tokens]))
    contact_paths = build_program_contact_overview_paths(program, courses)
    official_link = (
        f'<a class="text-link" href="{e(program.catalog_url)}">UVic Calendar</a>'
        if program.catalog_url
        else '<span class="meta-line">Official calendar unavailable</span>'
    )
    return (
        '<tr class="program-overview-row"'
        f' data-filter-category="{e(filter_token_string(category_tokens))}"'
        f' data-filter-search="{e(search_text.lower())}">'
        '<td class="program-overview-table__program" data-label="Program">'
        f'<a class="program-overview-table__primary-link" href="{program_page_href("", program.code)}">{e(program.name)}</a>'
        "</td>"
        '<td class="program-overview-table__type" data-label="Type">'
        f'<span class="program-overview-table__type-label">{e(category)}</span>'
        "</td>"
        f'<td class="program-overview-table__hours" data-label="Year 1">{render_contact_overview_cell(contact_paths, "year-1")}</td>'
        f'<td class="program-overview-table__hours" data-label="Year 2">{render_contact_overview_cell(contact_paths, "year-2")}</td>'
        f'<td class="program-overview-table__hours" data-label="Years 3 + 4">{render_contact_overview_cell(contact_paths, "years-3-4")}</td>'
        '<td class="program-overview-table__details" data-label="Details">'
        '<div class="program-overview-table__links">'
        f'<a class="text-link" href="{program_page_href("", program.code)}">Open graph</a>'
        f"{official_link}"
        "</div>"
        "</td>"
        "</tr>"
    )


def render_course_card(course: CourseRecord, base: str, *, support: bool = False) -> str:
    card_type = "Partner-department course" if support else "EOS course"
    level_label = course_level_label(course.code)
    theme_tokens = course_theme_tokens(course)
    theme_labels = [theme_label(token) for token in theme_tokens]
    search_text = " ".join(unique_ordered([course.code, course.name, subject_name(course.code), *theme_labels]))
    official_link = (
        f'<a class="text-link" href="{e(course.catalog_url)}">Official calendar</a>'
        if course.catalog_url
        else ""
    )
    tag_pills = f'<span class="meta-pill">{e(level_label)}</span>' + "".join(
        render_theme_pill(token)
        for token in theme_tokens[:3]
    )
    return (
        '<article class="directory-card"'
        f' data-filter-track="{e("support" if support else "eos")}"'
        f' data-filter-subject="{e(subject_from_code(course.code).lower())}"'
        f' data-filter-level="{e(course_level_token(course.code))}"'
        f' data-filter-theme="{e(filter_token_string(theme_tokens))}"'
        f' data-filter-search="{e(search_text.lower())}">'
        f'<p class="directory-card__eyebrow">{e(card_type)} | {e(course.code)}</p>'
        f'<h3><a href="{base}{course.code}.html">{e(course.name)}</a></h3>'
        f'<p class="meta-line">{e(subject_name(course.code))}</p>'
        f'<p class="meta-line">{len(course.prereq_codes)} prerequisite links | {len(course.used_by_programs)} programs | {len(course.dependents)} downstream courses</p>'
        f'<div class="pill-row">{render_subject_pill(course.code)}{tag_pills}</div>'
        '<div class="link-row">'
        f'<a class="text-link" href="{base}{course.code}.html">Open graph</a>'
        f'{official_link}'
        "</div>"
        "</article>"
    )


def render_program_section(section: dict, courses: dict[str, CourseRecord]) -> str:
    course_codes = collect_course_codes(section["rules"])
    stats = f"{len(course_codes)} named courses" if course_codes else "Narrative guidance only"
    body = "".join(render_rule_node_html(rule, "../courses/", courses) for rule in section["rules"])
    if not body:
        body = '<p class="empty-state">No structured rule data captured for this section.</p>'
    return (
        '<article class="section-block">'
        '<div class="section-block__head">'
        f"<h3>{e(section['title'])}</h3>"
        f'<p class="meta-line">{e(stats)}</p>'
        "</div>"
        f'<div class="rule-stack">{body}</div>'
        "</article>"
    )


def format_contact_hours_range(min_hours: float, max_hours: float) -> str:
    if abs(min_hours - max_hours) < 1e-9:
        return f"{format_unit_count(min_hours)} h/wk"
    return f"{format_unit_count(min_hours)}-{format_unit_count(max_hours)} h/wk"


def collect_contact_codes(node: dict, *, season: str | None = None) -> list[str]:
    if node["kind"] == "course":
        node_season = node.get("meta", {}).get("season")
        if season is not None and node_season != season:
            return []
        return [node.get("meta", {}).get("code", node["label"])]
    codes: list[str] = []
    for child in node.get("children", []):
        codes.extend(collect_contact_codes(child, season=season))
    return unique_ordered(codes)


def contact_term_count(node: dict) -> int:
    section_levels = sorted(section_year_levels(node["label"]))
    if section_levels:
        return max(2, len(section_levels) * 2)
    course_levels = sorted(
        {
            level
            for code in collect_contact_codes(node)
            if (level := course_level_number(code)) is not None
        }
    )
    return max(2, len(course_levels) * 2) if course_levels else 2


def format_per_term_contact_range(node: dict) -> str:
    term_count = contact_term_count(node)
    return format_contact_hours_range(
        node["min_regular_hours"] / term_count,
        node["max_regular_hours"] / term_count,
    )


def format_summer_contact_range(node: dict) -> str:
    if node["max_summer_hours"] <= 0:
        return "None"
    return format_contact_hours_range(node["min_summer_hours"], node["max_summer_hours"])


def format_compact_contact_range(min_value: float, max_value: float, *, suffix: str = "") -> str:
    if abs(min_value - max_value) < 1e-9:
        return f"{format_unit_count(min_value)}{suffix}"
    return f"{format_unit_count(min_value)}-{format_unit_count(max_value)}{suffix}"


def contact_bucket_key(node: dict) -> str | None:
    reference_key = section_reference_key(node["label"])
    if reference_key == "year-1":
        return "year-1"
    if reference_key == "year-2":
        return "year-2"
    if reference_key in {"year-3", "year-4", "years-3-4"}:
        return "years-3-4"

    levels = sorted(section_year_levels(node["label"]))
    if not levels:
        levels = sorted(
            {
                level
                for code in collect_contact_codes(node)
                if (level := course_level_number(code)) is not None
            }
        )
    if not levels:
        return None
    if max(levels) <= 1:
        return "year-1"
    if max(levels) == 2:
        return "year-2"
    return "years-3-4"


def contact_row_pattern(node: dict) -> str:
    meta = node.get("meta") or {}
    if node["kind"] == "elective-assumption":
        return "3-0-0 to 3-3-0"
    pattern = meta.get("pattern")
    if pattern:
        return pattern
    return format_compact_contact_range(node["min_hours"], node["max_hours"])


def contact_row_label(node: dict) -> str:
    meta = node.get("meta") or {}
    if node["kind"] == "elective-assumption":
        required_units = meta.get("required_units")
        if required_units:
            return f"Electives ({format_unit_count(required_units)} units)"
        return "Electives"
    return meta.get("title") or node["label"]


def collect_contact_display_rows(
    node: dict,
    *,
    flags: set[str] | None = None,
) -> list[dict]:
    meta = node.get("meta") or {}
    if node["kind"] in {"course", "elective-assumption"}:
        row_flags = []
        if flags:
            if "min" in flags:
                row_flags.append("min")
            if "max" in flags:
                row_flags.append("max")
        return [
            {
                "key": (
                    node["kind"],
                    meta.get("code") or node["label"],
                    meta.get("season", "regular"),
                    contact_row_pattern(node),
                ),
                "kind": node["kind"],
                "code": meta.get("code"),
                "label": contact_row_label(node),
                "pattern": contact_row_pattern(node),
                "season": meta.get("season", "regular"),
                "source": meta.get("source"),
                "source_note": meta.get("source_note"),
                "flags": row_flags,
            }
        ]

    if node["kind"] == "note":
        return []

    child_flag_map: dict[int, set[str]] = {}
    for key, marker in (("min_selected_indices", "min"), ("max_selected_indices", "max")):
        for index in meta.get(key, []):
            child_flag_map.setdefault(index, set()).add(marker)

    rows: list[dict] = []
    for index, child in enumerate(node.get("children", [])):
        rows.extend(
            collect_contact_display_rows(
                child,
                flags=(child_flag_map.get(index) or flags),
            )
        )
    return rows


def merge_contact_display_rows(rows: list[dict]) -> list[dict]:
    merged: dict[tuple, dict] = {}
    order: list[tuple] = []
    for row in rows:
        key = row["key"]
        existing = merged.get(key)
        if existing is None:
            merged[key] = dict(row)
            order.append(key)
            continue
        for marker in row["flags"]:
            if marker not in existing["flags"]:
                existing["flags"].append(marker)
    return [merged[key] for key in order]


def build_contact_year_summaries(
    path: ContactPathRecord,
    program: ProgramRecord,
    courses: dict[str, CourseRecord],
) -> list[dict]:
    include_stream_courses = path.stream is not None or not is_eos_base_program(program)
    path_codes = set(program_named_codes(program, path.stream, include_stream_courses=include_stream_courses))
    bucket_nodes: dict[str, list[dict]] = {"year-1": [], "year-2": [], "years-3-4": []}

    for section in path.sections:
        section_node = evaluate_contact_section(
            section,
            program=program,
            stream=path.stream,
            courses=courses,
            path_codes=path_codes,
        )
        bucket_key = contact_bucket_key(section_node)
        if bucket_key is None:
            continue
        bucket_nodes[bucket_key].append(section_node)

    summaries = []
    for bucket_key, bucket_label in CONTACT_SUMMARY_BUCKETS:
        nodes = bucket_nodes[bucket_key]
        if not nodes:
            continue
        regular_rows = merge_contact_display_rows(
            [
                row
                for node in nodes
                for row in collect_contact_display_rows(node)
                if row["season"] != "summer"
            ]
        )
        field_rows = merge_contact_display_rows(
            [
                row
                for node in nodes
                for row in collect_contact_display_rows(node)
                if row["season"] == "summer"
            ]
        )
        term_count = sum(contact_term_count(node) for node in nodes) or 2
        min_regular = sum(node["min_regular_hours"] for node in nodes)
        max_regular = sum(node["max_regular_hours"] for node in nodes)
        min_summer = sum(node["min_summer_hours"] for node in nodes)
        max_summer = sum(node["max_summer_hours"] for node in nodes)
        has_field_course = bool(field_rows or max_summer > 0)
        summaries.append(
            {
                "key": bucket_key,
                "label": bucket_label,
                "average_range": format_compact_contact_range(
                    min_regular / term_count,
                    max_regular / term_count,
                    suffix=" hrs/wk/term",
                )
                + (" (+F)" if has_field_course else ""),
                "has_field_course": has_field_course,
                "term_count": term_count,
                "regular_rows": regular_rows,
                "field_rows": field_rows,
                "min_regular_hours": min_regular,
                "max_regular_hours": max_regular,
                "min_summer_hours": min_summer,
                "max_summer_hours": max_summer,
            }
        )
    return summaries


def build_program_contact_overview_paths(
    program: ProgramRecord,
    courses: dict[str, CourseRecord],
) -> list[dict]:
    overview_paths = []
    for path in build_contact_paths(program):
        summary_lookup = {
            summary["key"]: {
                "label": summary["label"],
                "average_range": summary["average_range"],
                "has_field_course": summary["has_field_course"],
                "term_count": summary["term_count"],
            }
            for summary in build_contact_year_summaries(path, program, courses)
        }
        overview_paths.append(
            {
                "slug": path.slug,
                "title": path.title,
                "note": path.note,
                "is_stream": path.stream is not None,
                "summaries": summary_lookup,
            }
        )
    return overview_paths


def render_contact_selection_flags(flags: set[str] | None) -> str:
    if not flags:
        return ""
    ordered = []
    if "min" in flags:
        ordered.append(
            '<span class="contact-flag" title="Used in the lower regular-term estimate.">Min</span>'
        )
    if "max" in flags:
        ordered.append(
            '<span class="contact-flag" title="Used in the higher regular-term estimate.">Max</span>'
        )
    return "".join(ordered)


def render_contact_source_badge(meta: dict) -> str:
    source = meta.get("source")
    if source == "calendar":
        return (
            f'<span class="contact-source contact-source--calendar" title="{e(meta.get("source_note"))}">'
            f'calendar {e(meta.get("pattern"))}</span>'
        )
    if source == "assumed":
        return (
            f'<span class="contact-source contact-source--assumed" title="{e(meta.get("source_note"))}">'
            f'assumed {e(meta.get("pattern"))}</span>'
        )
    return ""


def render_contact_compact_row(row: dict, prefix: str, courses: dict[str, CourseRecord]) -> str:
    code = row.get("code")
    if code:
        label_html = (
            f'{render_course_chip(code, prefix, courses)}'
            f'<span class="contact-compact-row__name">{e(row["label"])}</span>'
        )
    else:
        label_html = f'<span class="contact-compact-row__name">{e(row["label"])}</span>'

    field_marker = (
        '<span class="contact-compact-row__marker" aria-label="Summer field course">field</span>'
        if row.get("season") == "summer"
        else ""
    )
    flag_markers = render_contact_selection_flags(set(row.get("flags") or []))
    row_classes = "contact-compact-row"
    if row.get("season") == "summer":
        row_classes += " contact-compact-row--field"
    return (
        f'<div class="{row_classes}">'
        f'<div class="contact-compact-row__course">{label_html}{field_marker}{flag_markers}</div>'
        '<div class="contact-compact-row__pattern">'
        f'<span class="contact-compact-row__pattern-text" title="{e(row.get("source_note"))}">{e(row["pattern"])}</span>'
        "</div>"
        "</div>"
    )


def render_contact_compact_column(summary: dict, courses: dict[str, CourseRecord]) -> str:
    regular_rows_html = "".join(
        render_contact_compact_row(row, "../courses/", courses) for row in summary["regular_rows"]
    )
    field_rows_html = "".join(
        render_contact_compact_row(row, "../courses/", courses) for row in summary["field_rows"]
    )
    return (
        '<section class="contact-compact-column">'
        '<div class="contact-compact-column__head">'
        f'<h3>{e(summary["label"])}</h3>'
        f'<p>{e(summary["average_range"])}</p>'
        "</div>"
        '<div class="contact-compact-column__table" role="table" '
        f'aria-label="{e(summary["label"])} contact hours">'
        '<div class="contact-compact-column__labels" role="row">'
        '<span role="columnheader">Course</span>'
        '<span role="columnheader">L-L-T</span>'
        "</div>"
        f'<div class="contact-compact-column__rows">{regular_rows_html}{field_rows_html}</div>'
        "</div>"
        '<div class="contact-compact-column__calc">'
        '<p><span>Sum</span>'
        f'<strong>{e(format_compact_contact_range(summary["min_regular_hours"], summary["max_regular_hours"], suffix=" hrs/wk"))}</strong></p>'
        '<p><span>÷ number of terms</span>'
        f'<strong>{e(str(summary["term_count"]))}</strong></p>'
        '<p class="contact-compact-column__average"><span>Average per term</span>'
        f'<strong>{e(summary["average_range"])}</strong></p>'
        "</div>"
        '</section>'
    )


def render_contact_compact_path(
    path: ContactPathRecord,
    program: ProgramRecord,
    courses: dict[str, CourseRecord],
    *,
    show_path_meta: bool,
) -> str:
    summaries = build_contact_year_summaries(path, program, courses)
    if not summaries:
        return ""
    summary_tiles = "".join(
        '<span class="contact-compact__summary-cell">'
        f'<span class="contact-compact__summary-label">{e(summary["label"])}</span>'
        f'<span class="contact-compact__summary-value">{e(summary["average_range"])}</span>'
        "</span>"
        for summary in summaries
    )
    column_html = "".join(render_contact_compact_column(summary, courses) for summary in summaries)
    panel_id = f"contact-hours-panel-{path.slug}"
    button_id = f"contact-hours-toggle-{path.slug}"
    path_meta_html = ""
    if show_path_meta:
        eyebrow = "Stream path" if path.stream is not None else "Program path"
        path_meta_html = (
            '<div class="contact-compact-path__meta">'
            f'<p class="detail-card__eyebrow">{e(eyebrow)}</p>'
            f'<p class="contact-compact-path__title">{e(path.title)}</p>'
            f'<p class="meta-line">{e(path.note)}</p>'
            "</div>"
        )
    return (
        '<article class="contact-compact-path">'
        f"{path_meta_html}"
        '<div class="contact-compact" data-contact-toggle>'
        f'<button class="contact-compact__button" id="{e(button_id)}" type="button" aria-expanded="false" aria-controls="{e(panel_id)}">'
        '<span class="contact-compact__intro">'
        '<span class="contact-compact__title">Contact hours by year</span>'
        '<span class="contact-compact__affordance">'
        '<span class="contact-compact__affordance-closed">Show details</span>'
        '<span class="contact-compact__affordance-open">Hide details</span>'
        "</span>"
        "</span>"
        f'<span class="contact-compact__summary-grid">{summary_tiles}</span>'
        '<span class="contact-compact__chevron" aria-hidden="true"></span>'
        "</button>"
        f'<div class="contact-compact__panel" id="{e(panel_id)}" role="region" aria-labelledby="{e(button_id)}" hidden>'
        '<div class="contact-compact__details">'
        f"{column_html}"
        "</div>"
        '<p class="contact-compact__legend">L = Lecture • L = Lab • T = Tutorial. Rows marked field are summer field courses listed separately and not folded into the per-term average.</p>'
        "</div>"
        "</div>"
        "</article>"
    )


def render_contact_course_row(
    node: dict,
    prefix: str,
    courses: dict[str, CourseRecord],
    *,
    flags: set[str] | None = None,
) -> str:
    meta = node.get("meta") or {}
    code = meta.get("code") or node["label"]
    title = meta.get("title") or (courses[code].name if code in courses else code)
    source_badge = render_contact_source_badge(meta)
    season_badge = (
        '<span class="contact-source contact-source--note">summer field</span>'
        if meta.get("season") == "summer"
        else ""
    )
    return (
        '<div class="contact-row">'
        '<div class="contact-row__label">'
        f'{render_course_chip(code, prefix, courses)}'
        f'<span class="contact-course-name">{e(title)}</span>'
        f'{render_contact_selection_flags(flags)}'
        "</div>"
        '<div class="contact-row__meta">'
        f"{season_badge}"
        f"{source_badge}"
        f'<span class="contact-total">{e(format_contact_hours_range(node["min_hours"], node["max_hours"]))}</span>'
        "</div>"
        "</div>"
    )


def render_contact_node_html(
    node: dict,
    prefix: str,
    courses: dict[str, CourseRecord],
    *,
    flags: set[str] | None = None,
) -> str:
    meta = node.get("meta") or {}
    flags_html = render_contact_selection_flags(flags)

    if node["kind"] == "course":
        return render_contact_course_row(node, prefix, courses, flags=flags)

    if node["kind"] == "note":
        return (
            '<div class="contact-row contact-row--note">'
            f'<div class="contact-row__label"><span class="contact-note">{e(node["label"])}</span></div>'
            "</div>"
        )

    if node["kind"] == "elective-assumption":
        eligible_codes = meta.get("eligible_codes") or []
        eligible_html = (
            '<div class="pill-row">'
            + "".join(render_course_chip(code, prefix, courses) for code in eligible_codes)
            + "</div>"
            if eligible_codes
            else ""
        )
        return (
            '<details class="contact-node">'
            '<summary class="contact-node__summary">'
            f'<span class="contact-row__label"><span class="contact-node__title">{e(node["label"])}</span>{flags_html}</span>'
            f'<span class="contact-row__meta"><span class="contact-total">{e(format_contact_hours_range(node["min_regular_hours"], node["max_regular_hours"]))}</span></span>'
            '</summary>'
            f'<p class="contact-help">{e(meta.get("source_note"))}</p>'
            f'{eligible_html}'
            '</details>'
        )

    child_flag_map: dict[int, set[str]] = {}
    for key, marker in (("min_selected_indices", "min"), ("max_selected_indices", "max")):
        for index in meta.get(key, []):
            child_flag_map.setdefault(index, set()).add(marker)
    child_html = "".join(
        render_contact_node_html(
            child,
            prefix,
            courses,
            flags=child_flag_map.get(index),
        )
        for index, child in enumerate(node["children"])
    )
    help_lines: list[str] = []
    if meta.get("source_note"):
        help_lines.append(meta["source_note"])
    if node["kind"] == "section" and meta.get("combined_years"):
        help_lines.append("The calendar publishes this as one combined section rather than separate Year 3 and Year 4 totals.")
    help_html = (
        '<p class="contact-help">' + " ".join(e(line) for line in help_lines) + "</p>"
        if help_lines
        else ""
    )
    return (
        '<details class="contact-node">'
        '<summary class="contact-node__summary">'
        '<span class="contact-row__label">'
        f'<span class="contact-node__title">{e(node["label"])}</span>'
        f"{flags_html}"
        "</span>"
        f'<span class="contact-row__meta"><span class="contact-total">{e(format_contact_hours_range(node["min_hours"], node["max_hours"]))}</span></span>'
        "</summary>"
        f'{help_html}'
        f'<div class="contact-node__body">{child_html}</div>'
        "</details>"
    )


def render_contact_path_card(
    path: ContactPathRecord,
    program: ProgramRecord,
    courses: dict[str, CourseRecord],
) -> str:
    include_stream_courses = path.stream is not None or not is_eos_base_program(program)
    path_codes = set(program_named_codes(program, path.stream, include_stream_courses=include_stream_courses))
    section_rows = []
    for section in path.sections:
        section_node = evaluate_contact_section(
            section,
            program=program,
            stream=path.stream,
            courses=courses,
            path_codes=path_codes,
        )
        section_rows.append(render_contact_section_summary(section_node, courses))

    eyebrow = "Stream path" if path.stream is not None else "Program path"
    return (
        '<article class="section-block contact-path">'
        '<div class="contact-path__head">'
        f'<p class="detail-card__eyebrow">{e(eyebrow)}</p>'
        f'<h3>{e(path.title)}</h3>'
        f'<p class="meta-line">{e(path.note)}</p>'
        "</div>"
        f'<div class="contact-list">{"".join(section_rows)}</div>'
        "</article>"
    )


def render_contact_section_summary(
    section_node: dict,
    courses: dict[str, CourseRecord],
) -> str:
    summer_codes = collect_contact_codes(section_node, season="summer")
    summer_html = (
        '<div class="pill-row">'
        + "".join(render_course_chip(code, "../courses/", courses) for code in summer_codes)
        + "</div>"
        if summer_codes
        else ""
    )
    help_lines = ["Regular-term totals are averaged across the published terms in this section."]
    if section_node["meta"].get("combined_years"):
        help_lines.append("The calendar publishes this as one combined section rather than separate year totals.")
    if section_node["max_summer_hours"] > 0:
        help_lines.append("Summer field courses are listed separately instead of being folded into the regular-term average.")
    breakdown_html = "".join(
        render_contact_node_html(child, "../courses/", courses)
        for child in section_node["children"]
        if child["min_hours"] > 0 or child["max_hours"] > 0
    )
    return (
        '<details class="contact-summary">'
        '<summary class="contact-summary__summary">'
        f'<span class="contact-summary__title">{e(section_node["label"])}</span>'
        f'<span class="contact-summary__metric"><strong>Regular term avg</strong> {e(format_per_term_contact_range(section_node))}</span>'
        f'<span class="contact-summary__metric"><strong>Summer field</strong> {e(format_summer_contact_range(section_node))}</span>'
        "</summary>"
        f'<p class="contact-help">{" ".join(e(line) for line in help_lines)}</p>'
        f'{summer_html}'
        f'<div class="contact-stack">{breakdown_html}</div>'
        "</details>"
    )


def render_contact_hours_section(program: ProgramRecord, courses: dict[str, CourseRecord]) -> str:
    paths = build_contact_paths(program)
    if not paths:
        return ""
    path_html = "".join(
        render_contact_compact_path(
            path,
            program,
            courses,
            show_path_meta=(len(paths) > 1),
        )
        for path in paths
    )
    return (
        '<section class="section">'
        '<p class="contact-brief">Contact hours are calculated using the listed lecture-lab-tutorial information in calendar. Hour ranges for electives are calculated assuming all 3-0-0 (min) and 3-3-0 (max).</p>'
        f'<div class="section-stack">{path_html}</div>'
        '</section>'
    )


def render_program_page(
    program: ProgramRecord,
    courses: dict[str, CourseRecord],
    redundant_checks: list[dict],
) -> str:
    include_stream_courses = not is_eos_base_program(program)
    named_codes = program_named_codes(program, include_stream_courses=include_stream_courses)
    metric_items = [
        render_metric_card(program_primary_category_label(program), "Program type"),
        render_metric_card(str(len(named_codes)), "Named courses in the published structure"),
        render_metric_card(str(len(program.support_codes)), "Related prerequisite courses outside the named list"),
    ]
    if program.streams:
        metric_items.append(render_metric_card(str(len(program.streams)), "Named stream progressions"))
    else:
        metric_items.append(
            render_metric_card(
                str(sum(1 for code in named_codes if subject_from_code(code) == "EOS")),
                "EOS courses named directly in the program",
            )
        )
    metric_cards = "".join(metric_items)

    details_cards = [
        (
            "Official Source",
            "Calendar entry",
            (
                f'<p><a class="text-link" href="{e(program.catalog_url)}">Open the UVic calendar entry</a></p>'
                if program.catalog_url
                else '<p class="empty-state">Official calendar link not available in the current snapshot.</p>'
            ),
        ),
        (
            "Published Description",
            "Catalog text",
            render_rich_text(program.detail.get("description"), "../courses/", courses),
        ),
    ]
    if program.detail.get("programNotes"):
        details_cards.append(
            (
                "Program Notes",
                "Catalog notes",
                render_rich_text(program.detail.get("programNotes"), "../courses/", courses),
            )
        )

    detail_html = "".join(
        '<article class="detail-card">'
        f'<p class="detail-card__eyebrow">{e(eyebrow)}</p>'
        f"<h3>{e(title)}</h3>"
        f"{body}"
        "</article>"
        for eyebrow, title, body in details_cards
    )

    support_body = (
        '<div class="pill-row">'
        + "".join(render_course_chip(code, "../courses/", courses) for code in program.support_codes)
        + "</div>"
        if program.support_codes
        else '<p class="empty-state">No additional prerequisite courses fall outside the named program structure in this snapshot.</p>'
    )

    graph_key_html = render_program_graph_key()
    simplified_program_group_lookup = build_course_groups(courses, aggressive=True)[1]
    program_graph_modes = [
        (mode, "../assets/graphs/programs/{asset_stem}" + mode.asset_suffix + ".svg")
        for mode in PROGRAM_GRAPH_MODES
    ]
    if program.streams:
        is_eos_base = is_eos_base_program(program)
        show_base_graph = is_eos_base
        graph_intro = (
            '<div class="section-heading">'
            '<p class="section-kicker">Program Graphs</p>'
            '<h2>Program requirements arranged by prerequisite flow.</h2>'
            f'<p>{"This program includes a base map, plus any published option maps. " if show_base_graph else ""}Courses with no direct prerequisite links in the database are shown as isolated nodes; some may have prerequisites outside the pulled course set.</p>'
            '</div>'
        )
        graph_shells = []
        if show_base_graph:
            _program_node_styles, program_legend_items = build_program_node_styles(
                program,
                None,
                course_group_lookup=simplified_program_group_lookup,
                include_stream_courses=not is_eos_base,
            )
            overlay_legend = graph_overlay_legend_data(
                title="Program legend",
                note="Node colours show required courses, related prerequisites, and distinct option sets used in the program map.",
                items=program_legend_items,
            )
            additional_requirements_html = render_additional_requirements(
                program_graph_note_lines(program, None),
                title="Additional program requirements",
            )
            page_graph_modes = [
                (mode, path_template.format(asset_stem=program.code))
                for mode, path_template in program_graph_modes
            ]
            graph_shells.append(
                render_graph_shell(
                    shell_id="program-graph",
                    section_kicker="Program Graph",
                    heading="Program requirements arranged by prerequisite flow.",
                    note="The graph is driven by prerequisites from left to right (instead of year suggestions). The simplified view keeps the sequence readable while the full view is closer to the real data structure.",
                    default_svg=page_graph_modes[0][1],
                    aria_label=f"{program.name} program graph",
                    guide_html="",
                    graph_modes=page_graph_modes,
                    course_href_prefix="../courses/",
                    footer_html=additional_requirements_html,
                    overlay_legend=overlay_legend,
                    analytics_html=render_program_graph_analytics(
                        build_program_analytics_bundle(
                            program,
                            courses,
                            redundant_checks,
                        )
                    ),
                )
            )
            graph_anchor = "#program-graph"
        else:
            graph_anchor = "#program-streams"

        for stream in program.streams:
            _stream_node_styles, stream_legend_items = build_program_node_styles(
                program,
                stream,
                course_group_lookup=simplified_program_group_lookup,
            )
            overlay_legend = graph_overlay_legend_data(
                title="Program legend",
                note=f"Node colours show required courses, related prerequisites, and distinct option sets used in the {stream.title.lower()} map.",
                items=stream_legend_items,
            )
            stream_heading = stream.title
            if stream.description:
                stream_note = stream.description
            else:
                stream_note = "This map combines the shared program structure with the published requirements for this stream."
            asset_stem = stream_asset_stem(program, stream)
            stream_graph_modes = [
                (mode, path_template.format(asset_stem=asset_stem))
                for mode, path_template in program_graph_modes
            ]
            additional_requirements_html = render_additional_requirements(
                program_graph_note_lines(program, stream),
                title="Additional program requirements",
            )
            graph_shells.append(
                render_graph_shell(
                    shell_id=f"program-graph-{stream.slug}",
                    section_kicker="Stream Map",
                    heading=stream_heading,
                    note=stream_note,
                    default_svg=stream_graph_modes[0][1],
                    aria_label=f"{program.name} {stream.title} graph",
                    guide_html="",
                    graph_modes=stream_graph_modes,
                    course_href_prefix="../courses/",
                    footer_html=additional_requirements_html,
                    overlay_legend=overlay_legend,
                    analytics_html=render_program_graph_analytics(
                        build_program_analytics_bundle(
                            program,
                            courses,
                            redundant_checks,
                            stream=stream,
                        )
                    ),
                )
            )
        graphs_html = (
            f'{graph_intro}<div class="section-stack" id="program-streams">{"".join(graph_shells)}</div>'
        )
    else:
        _program_node_styles, program_legend_items = build_program_node_styles(
            program,
            None,
            course_group_lookup=simplified_program_group_lookup,
        )
        overlay_legend = graph_overlay_legend_data(
            title="Program legend",
            note="Node colours show required courses, related prerequisites, and distinct option sets used in the program map.",
            items=program_legend_items,
        )
        additional_requirements_html = render_additional_requirements(
            program_graph_note_lines(program, None),
            title="Additional program requirements",
        )
        page_graph_modes = [
            (mode, path_template.format(asset_stem=program.code))
            for mode, path_template in program_graph_modes
        ]
        graphs_html = render_graph_shell(
            shell_id="program-graph",
            section_kicker="Program Graph",
            heading="Program requirements arranged by prerequisite flow.",
            note="The graph is driven by prerequisites from left to right (instead of year suggestions). The simplified view keeps the sequence readable while the full view is closer to the real data structure.",
            default_svg=page_graph_modes[0][1],
            aria_label=f"{program.name} program graph",
            guide_html="",
            graph_modes=page_graph_modes,
            course_href_prefix="../courses/",
            footer_html=additional_requirements_html,
            overlay_legend=overlay_legend,
            analytics_html=render_program_graph_analytics(
                build_program_analytics_bundle(program, courses, redundant_checks)
            ),
        )
        graph_anchor = "#program-graph"

    content = f"""
    <section class="section section--tight">
      {graphs_html}
    </section>

    <section class="section">
      <div class="metric-grid">{metric_cards}</div>
    </section>

    <section class="section">
      <div class="detail-grid">{detail_html}</div>
    </section>

    {render_contact_hours_section(program, courses)}

    <section class="section">
      <div class="section-heading">
        <p class="section-kicker">Related Courses</p>
        <h2>Prerequisite courses outside the named program list.</h2>
        <p>These courses are not listed directly in the published program requirements, but they appear in the prerequisite chains that make the flow map readable.</p>
      </div>
      <div class="section-block">{support_body}</div>
    </section>
    """

    official_calendar_button = (
        f'<a class="button button--ghost" href="{e(program.catalog_url)}">Official calendar</a>'
        if program.catalog_url
        else ""
    )
    hero_actions = (
        '<div class="hero__actions">'
        f'<a class="button" href="{graph_anchor}">Graph</a>'
        '<a class="button button--ghost" href="overview.html">Back to programs</a>'
        f'{official_calendar_button}'
        "</div>"
    )

    return render_layout(
        base="../",
        active="programs",
        active_site="atlas",
        title=f"{program.name} | {SITE_NAME}",
        description=f"Published program map for {program.name} at UVic, with generated prerequisite-flow graphs.",
        eyebrow=f"Programs | {program.code}",
        hero_title=program.name,
        hero_lede=(
            "Published program structure, rebuilt as a static map with stream-aware prerequisite graphs."
            if program.streams
            else "Published program structure, rebuilt as a static map with generated prerequisite-flow graphs."
        ),
        hero_actions=hero_actions,
        content=content,
        hero_image=program_hero_image("../", program),
        body_class="page--program-detail",
    )


def render_course_page(
    course: CourseRecord,
    courses: dict[str, CourseRecord],
    programs: dict[str, ProgramRecord],
    course_groups: dict[str, CourseGroupRecord],
    course_group_lookup: dict[str, str],
) -> str:
    metric_cards = "".join(
        [
            render_metric_card(e(subject_name(course.code)), "Subject area"),
            render_metric_card(course_level_label(course.code), "Course level"),
            render_metric_card(str(len(course.used_by_programs)), "Programs that name this course"),
            render_metric_card(str(len(course.prereq_codes)), "Published prerequisite links"),
        ]
    )

    used_by_body = (
        '<div class="pill-row">'
        + "".join(
            f'<a class="course-pill" href="{program_page_href("../programs/", program_code)}">{e(programs[program_code].name if program_code in programs else program_code)}</a>'
            for program_code in sorted(
                course.used_by_programs,
                key=lambda item: programs[item].name if item in programs else item,
            )
        )
        + "</div>"
        if course.used_by_programs
        else '<p class="empty-state">This course is not named directly in the current SEOS program set.</p>'
    )

    detail_cards = [
        (
            "Official Source",
            "Calendar entry",
            (
                f'<p><a class="text-link" href="{e(course.catalog_url)}">Open the UVic calendar entry</a></p>'
                if course.catalog_url
                else '<p class="empty-state">Detailed catalog link not available in the current snapshot.</p>'
            ),
        ),
        (
            "Description",
            "Catalog description",
            render_rich_text(course.detail.get("description"), "", courses),
        ),
    ]
    if course.detail.get("supplementalNotes"):
        detail_cards.append(
            (
                "Supplemental Notes",
                "Catalog notes",
                render_rich_text(course.detail.get("supplementalNotes"), "", courses),
            )
        )
    if course.detail.get("restrictions"):
        detail_cards.append(
            (
                "Restrictions",
                "Catalog text",
                render_rich_text(course.detail.get("restrictions"), "", courses),
            )
        )

    details_html = "".join(
        '<article class="detail-card">'
        f'<p class="detail-card__eyebrow">{e(eyebrow)}</p>'
        f"<h3>{e(title)}</h3>"
        f"{body}"
        "</article>"
        for eyebrow, title, body in detail_cards
    )
    course_note_lines = course_graph_note_lines(
        course,
        courses,
        course_groups,
        course_group_lookup,
    )
    graph_key_html = render_course_graph_key()
    guide_html = render_graph_guide(
        summary="Expand for department colours, choice nodes, and merged-course labels used in the course map.",
        preview_samples=[(course.code, "focus"), ("1 of", "choice"), ("", "junction"), ("Merged", "merged")],
        legend_html=render_subject_legend([course.code, *course.prereq_codes, *course.dependents]),
        graph_key_html=graph_key_html,
        title="Graph key and legend",
    )

    additional_requirements_html = render_additional_requirements(
        course_note_lines,
        title="Additional course requirements",
    )
    graph_html = render_graph_shell(
        shell_id="course-graph",
        section_kicker="Course Graph",
        heading="Prerequisite flow into the course, and dependencies flow out from it.",
        note="Co-requisites are treated as prerequisite links, and equivalent or cross-listed courses are merged into shared course nodes. The simplified view shows one prerequisite level above the course and one dependency level downstream.",
        default_svg=f"../assets/graphs/courses/{course.code}--simplified.svg",
        aria_label=f"{course.code} course graph",
        guide_html=guide_html,
        graph_modes=[
            (
                GraphModeRecord(
                    key="simplified",
                    asset_suffix="--simplified",
                    button_label="Simplified view",
                    copy_text="Simplified view: direct prerequisites for the course, then one dependency step downstream.",
                ),
                f"../assets/graphs/courses/{course.code}--simplified.svg",
            ),
            (
                GraphModeRecord(
                    key="full",
                    asset_suffix="",
                    button_label="Full view",
                    copy_text="Full view: the entire connected prerequisite and dependency progression captured in the last UVic calendar sync.",
                ),
                f"../assets/graphs/courses/{course.code}.svg",
            ),
        ],
        course_href_prefix="",
        footer_html=additional_requirements_html,
    )

    content = f"""
    <section class="section section--tight">
      {graph_html}
    </section>

    <section class="section">
      <div class="metric-grid">{metric_cards}</div>
    </section>

    <section class="section">
      <div class="detail-grid">{details_html}</div>
    </section>

    <section class="section">
      <div class="detail-grid detail-grid--single">
        <article class="detail-card">
          <p class="detail-card__eyebrow">Program Use</p>
          <h3>Programs that name this course</h3>
          {used_by_body}
        </article>
      </div>
    </section>
    """

    official_calendar_button = (
        f'<a class="button button--ghost" href="{e(course.catalog_url)}">Official calendar</a>'
        if course.catalog_url
        else ""
    )
    hero_actions = (
        '<div class="hero__actions">'
        '<a class="button" href="#course-graph">Graph</a>'
        '<a class="button button--ghost" href="overview.html">Back to courses</a>'
        f'{official_calendar_button}'
        "</div>"
    )

    return render_layout(
        base="../",
        active="courses",
        active_site="atlas",
        title=f"{course.code} | {SITE_NAME}",
        description=f"Published course map for {course.code} at UVic, with generated prerequisite and downstream graphs.",
        eyebrow=f"Courses | {course.code}",
        hero_title=f"{course.code}: {course.name}",
        hero_lede=(
            "Course page generated from current catalog data and related program references."
            if course.placeholder
            else "Published course information, generated as a static page and SVG graph."
        ),
        hero_actions=hero_actions,
        content=content,
        hero_image=course_hero_image("../", course),
        body_class="page--course-detail",
    )


def render_program_overview(programs: dict[str, ProgramRecord], courses: dict[str, CourseRecord], generated_at: str) -> str:
    programs_sorted = sorted(programs.values(), key=lambda item: item.name)
    rows = "".join(render_program_overview_row(program, courses) for program in programs_sorted)
    search_options = []
    for program in programs_sorted:
        category = program_primary_category_label(program)
        search_options.extend(
            [
                (program.name, f"{program.code} | {category}"),
                (program.code, f"{program.name} | {category}"),
            ]
        )
    category_filters = render_filter_group(
        "Category",
        [
            render_filter_button("All", group="category", value="all", active=True),
            render_filter_button("SEOS only", group="category", value="seos-only"),
            render_filter_button("Honours", group="category", value="honours"),
            render_filter_button("Major", group="category", value="major"),
            render_filter_button("Minor", group="category", value="minor"),
            render_filter_button("General", group="category", value="general"),
            render_filter_button("Combined", group="category", value="combined"),
        ],
    )
    content = f"""
    <section class="section section--program-overview">
      <div class="section-heading section-heading--compact">
        <p class="section-kicker">SEOS Programs</p>
        <p>Search or filter, then open a graph page for the full prerequisite map.</p>
      </div>
      <div class="filter-panel filter-panel--compact" data-card-filter>
        {render_filter_search("Search programs", "Program name, code, or type", autocomplete_id="program-search-options", autocomplete_options=search_options)}
        <div class="filter-panel__status">
          <span data-filter-count>{len(programs_sorted)} programs</span>
          <button class="filter-clear" type="button" data-filter-clear>Clear filters</button>
        </div>
        <div class="filter-panel__groups">
          {category_filters}
        </div>
        <p class="filter-panel__note">Filter by program category. <span aria-hidden="true">(+F)</span><span class="sr-only"> plus F</span> means the year group includes a summer field course.</p>
      </div>
      <div class="table-shell">
        <table class="program-overview-table">
          <caption class="sr-only">SEOS program overview with program links, program type, contact hour summaries for Year 1, Year 2, and Years 3 plus 4, and detail links.</caption>
          <thead>
            <tr>
              <th scope="col">Program</th>
              <th scope="col">Type</th>
              <th scope="col">Year 1</th>
              <th scope="col">Year 2</th>
              <th scope="col">Years 3 + 4</th>
              <th scope="col">Details</th>
            </tr>
          </thead>
          <tbody data-filter-grid>{rows}</tbody>
        </table>
      </div>
      <p class="empty-state empty-state--filtered is-hidden" data-filter-empty>No programs match the current filters.</p>
    </section>
    """
    hero_actions = (
        '<div class="hero__actions">'
        '<a class="button" href="../index.html">Guide home</a>'
        '<a class="button button--ghost" href="../curriculum_workflow.html">Build workflow</a>'
        "</div>"
    )
    return render_layout(
        base="../",
        active="programs",
        active_site="atlas",
        title=f"Programs | {SITE_NAME}",
        description="Published SEOS and related program structures at UVic, generated as static curriculum maps with node graphs.",
        eyebrow="Programs",
        hero_title="Program overview",
        hero_lede="Compare program type and contact-hour load at a glance, then open the full guide page for any program.",
        hero_actions=hero_actions,
        content=content,
        hero_image=f"{HERO_ASSET_URL}program-overview.jpg",
        body_class="page--program-overview",
    )


def render_course_overview(courses: dict[str, CourseRecord], generated_at: str) -> str:
    eos_courses = [
        course
        for course in courses.values()
        if subject_from_code(course.code) == "EOS" and not course.placeholder
    ]
    support_courses = [
        course
        for course in courses.values()
        if subject_from_code(course.code) != "EOS" and not course.placeholder
    ]

    eos_cards = "".join(render_course_card(course, "", support=False) for course in sorted(eos_courses, key=lambda item: course_sort_key(item.code)))
    support_cards = "".join(render_course_card(course, "", support=True) for course in sorted(support_courses, key=lambda item: course_sort_key(item.code)))

    metric_cards = "".join(
        [
            render_metric_card(str(len(eos_courses)), "EOS course pages"),
            render_metric_card(str(len(support_courses)), "Partner-department course pages"),
            render_metric_card(str(sum(len(course.dependents) for course in eos_courses)), "Direct dependencies across EOS courses"),
            render_metric_card(e(generated_at), "Last UVic calendar sync"),
        ]
    )
    department_codes = unique_ordered(
        subject_from_code(course.code)
        for course in sorted(eos_courses + support_courses, key=lambda item: course_sort_key(item.code))
    )
    department_filters = render_filter_group(
        "Department",
        [render_filter_button("All", group="subject", value="all", active=True)]
        + [
            render_filter_button(subject_name(code), group="subject", value=code.lower())
            for code in department_codes
        ],
    )
    level_filters = render_filter_group(
        "Level",
        [
            render_filter_button("All", group="level", value="all", active=True),
            render_filter_button("100-level", group="level", value="100"),
            render_filter_button("200-level", group="level", value="200"),
            render_filter_button("300-level", group="level", value="300"),
            render_filter_button("400-level", group="level", value="400"),
        ],
    )
    theme_filters = render_filter_group(
        "Theme",
        [render_theme_filter_button("All", group="theme", value="all", active=True)]
        + [
            render_theme_filter_button(label, group="theme", value=token)
            for token, label, _ in COURSE_THEME_RULES
        ],
    )

    content = f"""
    <section class="section section--tight">
      <div class="metric-grid">{metric_cards}</div>
    </section>

    <section class="section">
      <div class="section-heading">
        <p class="section-kicker">Course Directory</p>
        <h2>EOS courses and partner-department prerequisites.</h2>
        <p>Search by code or title first; open a course graph when you find the dependency chain you need.</p>
      </div>
      <div class="filter-panel" data-card-filter>
        {render_filter_search("Search courses", "Course code, title, department, or theme")}
        <div class="filter-panel__status">
          <span data-filter-count>{len(eos_courses) + len(support_courses)} courses</span>
          <button class="filter-clear" type="button" data-filter-clear>Clear filters</button>
        </div>
        <div class="filter-panel__groups">
          {level_filters}
          {render_filter_disclosure("Department filters", department_filters)}
          {render_filter_disclosure("Theme filters", theme_filters)}
        </div>
      </div>
      <div class="directory-grid" data-filter-grid>{eos_cards}{support_cards}</div>
      <p class="empty-state empty-state--filtered is-hidden" data-filter-empty>No courses match the current filters.</p>
    </section>
    """

    hero_actions = (
        '<div class="hero__actions">'
        '<a class="button" href="../index.html">Guide home</a>'
        '<a class="button button--ghost" href="../programs/overview.html">Programs</a>'
        "</div>"
    )

    return render_layout(
        base="../",
        active="courses",
        active_site="atlas",
        title=f"Courses | {SITE_NAME}",
        description="Published SEOS and supporting course structures at UVic, generated as static curriculum maps with node graphs.",
        eyebrow="Courses",
        hero_title="Courses covered in SEOS programs",
        hero_lede="Published course information, rebuilt as static pages and SVG graphs from the last UVic calendar sync.",
        hero_actions=hero_actions,
        content=content,
        hero_image=f"{HERO_ASSET_URL}course-overview.jpg",
        body_class="page--course-overview",
    )


def render_workflow_page(manifest: dict) -> str:
    generated_at = format_date_label(manifest["generated_at_utc"])
    missing_support = "".join(
        f'<span class="course-pill course-pill--ghost">{e(code)}</span>'
        for code in manifest.get("missing_support_codes", [])
    )
    content = f"""
    <section class="section">
      <div class="split-callout">
        <div>
          <p class="section-kicker">Build Model</p>
          <h2>Scripted static generation of HTML.</h2>
          <p>This guide built as static HTML and SVG from the synced catalog JSON. The intended workflow is a data pull, a full graph and page rebuild, and then a publish step.</p>
        </div>
        <div>
          <p class="section-kicker">Last UVic calendar sync</p>
          <p class="panel-note">{e(generated_at)} | {e(str(manifest['counts']['seos_programs']))} programs | {e(str(manifest['counts']['eos_courses']))} EOS courses | {e(str(manifest['counts']['support_courses']))} supporting courses</p>
        </div>
      </div>
    </section>

    <section class="section">
      <div class="detail-grid">
        <article class="command-card">
          <p class="detail-card__eyebrow">Update data and rebuild</p>
          <h3>Recommended maintenance command</h3>
          <div class="code-block"><code>python3 scripts/update_program_guide.py</code></div>
          <p class="meta-line">Runs the UVic catalog sync, then regenerates every graph and every static page into <code>build/html</code>.</p>
        </article>
        <article class="command-card">
          <p class="detail-card__eyebrow">Rebuild only</p>
          <h3>When the snapshot is already current</h3>
          <div class="code-block"><code>python3 scripts/build_static_site.py</code></div>
          <p class="meta-line">Useful after local styling or page-template edits when the data files themselves have not changed.</p>
        </article>
        <article class="command-card">
          <p class="detail-card__eyebrow">Publish</p>
          <h3>Push the generated site</h3>
          <div class="code-block"><code>git push</code></div>
          <p class="meta-line">Publishes the freshly generated <code>build/html</code> output to the repository’s <code>gh-pages</code> branch.</p>
        </article>
      </div>
    </section>

    <section class="section">
      <div class="detail-grid">
        <article class="detail-card">
          <p class="detail-card__eyebrow">Scope</p>
          <h3>What gets regenerated</h3>
          <div class="rich-text">
            <ul>
              <li>Guide home page and workflow page</li>
              <li>Program overview plus one page and one SVG graph for every SEOS program in the synced set</li>
              <li>Course overview plus one page and one SVG graph for every EOS and partner-department course with detail data</li>
            </ul>
          </div>
        </article>
        <article class="detail-card">
          <p class="detail-card__eyebrow">Known Gaps</p>
          <h3>Referenced codes missing from the live snapshot</h3>
          <div class="pill-row">{missing_support or '<p class="empty-state">No missing referenced partner-department course codes in the current snapshot.</p>'}</div>
        </article>
      </div>
    </section>
    """

    hero_actions = (
        '<div class="hero__actions">'
        '<a class="button" href="index.html">Guide home</a>'
        '<a class="button button--ghost" href="programs/overview.html">Programs</a>'
        '<a class="button button--ghost" href="courses/overview.html">Courses</a>'
        "</div>"
    )

    return render_layout(
        base="",
        active="workflow",
        active_site="atlas",
        title=f"Workflow | {SITE_NAME}",
        description=f"Maintenance workflow for the {SITE_NAME} static site and graph generation pipeline.",
        eyebrow="Workflow",
        hero_title="Static build workflow for the curriculum atlas.",
        hero_lede="Sync the catalog data, generate every graph and page, then publish by pushing to the repository.",
        hero_actions=hero_actions,
        content=content,
        hero_image=f"{HERO_ASSET_URL}workflow-overview.jpg",
        body_class="page--workflow",
    )


def render_index_page(programs: dict[str, ProgramRecord], courses: dict[str, CourseRecord], manifest: dict) -> str:
    generated_at = format_date_label(manifest["generated_at_utc"])
    metric_cards = "".join(
        [
            render_metric_card(str(manifest["counts"]["seos_programs"]), "Programs in the current SEOS snapshot"),
            render_metric_card(str(manifest["counts"]["eos_courses"]), "EOS course pages"),
            render_metric_card(str(manifest["counts"]["support_courses"]), "Partner-department course pages"),
            render_metric_card(e(generated_at), "Last UVic calendar sync"),
        ]
    )

    content = f"""
    <section class="section section--tight">
      <div class="metric-grid">{metric_cards}</div>
    </section>

    <section class="section">
      <div class="split-callout">
        <div>
          <p class="section-kicker">How To Use This Guide</p>
          <h2>Program and Course pre-requisite graphs, based directly on the UVic Calendar.</h2>
          <p>This site maps the current calendar structure for SEOS programs and related courses. Start with the <a class="text-link" href="programs/overview.html">program directory</a> when you want to explore programs, then use the <a class="text-link" href="courses/overview.html">course directory</a> to zoom in on specific course requirements.</p>
        </div>
        <div>
          <p class="section-kicker">Regeneration</p>
          <ol class="process-list">
            <li>Pull the latest UVic catalog data.</li>
            <li>Rebuild every graph and every page as static HTML and SVG.</li>
            <li>Publish the generated output to the site branch.</li>
          </ol>
          <p class="panel-note"><a class="text-link" href="curriculum_workflow.html">Open the maintenance workflow</a></p>
        </div>
      </div>
    </section>
    """

    hero_actions = (
        '<div class="hero__actions">'
        '<a class="button" href="programs/overview.html">Open programs</a>'
        '<a class="button button--ghost" href="courses/overview.html">Open courses</a>'
        "</div>"
    )

    return render_layout(
        base="",
        active="home",
        active_site="atlas",
        title=SITE_NAME,
        description="Static atlas for the published UVic SEOS curriculum structure, with generated program and course node graphs.",
        eyebrow="School of Earth and Ocean Sciences | UVic",
        hero_title="An atlas of SEOS programs and courses",
        hero_lede="Current published programs and course progressions visualized as SVG node graphs.",
        hero_actions=hero_actions,
        content=content,
        hero_image=f"{HERO_ASSET_URL}rockies-program.jpg",
    )


def write_site(
    programs: dict[str, ProgramRecord],
    courses: dict[str, CourseRecord],
    manifest: dict,
    course_groups: dict[str, CourseGroupRecord],
    course_group_lookup: dict[str, str],
    redundant_checks: list[dict],
) -> None:
    (BUILD_DIR / "programs").mkdir(parents=True, exist_ok=True)
    (BUILD_DIR / "courses").mkdir(parents=True, exist_ok=True)

    (BUILD_DIR / "index.html").write_text(
        render_index_page(programs, courses, manifest),
        encoding="utf-8",
    )
    (BUILD_DIR / "curriculum_workflow.html").write_text(
        render_workflow_page(manifest),
        encoding="utf-8",
    )
    (BUILD_DIR / "programs" / "overview.html").write_text(
        render_program_overview(programs, courses, format_date_label(manifest["generated_at_utc"])),
        encoding="utf-8",
    )
    (BUILD_DIR / "courses" / "overview.html").write_text(
        render_course_overview(courses, format_date_label(manifest["generated_at_utc"])),
        encoding="utf-8",
    )

    for program in programs.values():
        (BUILD_DIR / "programs" / f"PR_{program.code}.html").write_text(
            render_program_page(program, courses, redundant_checks),
            encoding="utf-8",
        )

    for course in courses.values():
        (BUILD_DIR / "courses" / f"{course.code}.html").write_text(
            render_course_page(
                course,
                courses,
                programs,
                course_groups,
                course_group_lookup,
            ),
            encoding="utf-8",
        )


def main() -> None:
    manifest = read_json(DATA_DIR / "manifest.json")
    courses = build_course_lookup()
    programs = build_program_lookup()
    augment_courses_with_program_placeholders(courses, programs)
    course_groups, course_group_lookup = build_course_groups(courses, aggressive=False)
    simplified_course_groups, simplified_course_group_lookup = build_course_groups(courses, aggressive=True)
    enrich_relationships(programs, courses)
    redundant_checks = find_redundant_prerequisite_checks(courses, course_group_lookup)

    prepare_output_directory()

    for program in programs.values():
        for mode in PROGRAM_GRAPH_MODES:
            write_program_graph(
                program,
                courses,
                simplified_course_groups if mode.key != "full" else course_groups,
                simplified_course_group_lookup if mode.key != "full" else course_group_lookup,
                mode=mode,
            )
        for stream in program.streams:
            for mode in PROGRAM_GRAPH_MODES:
                write_program_graph(
                    program,
                    courses,
                    simplified_course_groups if mode.key != "full" else course_groups,
                    simplified_course_group_lookup if mode.key != "full" else course_group_lookup,
                    mode=mode,
                    stream=stream,
                )

    for course in courses.values():
        write_course_graph(
            course,
            courses,
            simplified_course_groups,
            simplified_course_group_lookup,
            simplified=True,
        )
        write_course_graph(
            course,
            courses,
            course_groups,
            course_group_lookup,
            simplified=False,
        )

    write_site(
        programs,
        courses,
        manifest,
        course_groups,
        course_group_lookup,
        redundant_checks,
    )

    print(
        f"Built static guide with {len(programs)} program pages, {len(courses)} course pages, "
        f"and regenerated graphs in {BUILD_DIR}"
    )


if __name__ == "__main__":
    main()
