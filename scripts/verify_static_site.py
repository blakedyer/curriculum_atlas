#!/usr/bin/env python3
"""Verify rebuilt program SVGs, links, and embedded analytics without a browser."""
from __future__ import annotations

import json
from xml.etree import ElementTree

from bs4 import BeautifulSoup

import build_static_site as atlas


SVG = {"svg": "http://www.w3.org/2000/svg"}
HREF = "{http://www.w3.org/1999/xlink}href"


def verify() -> None:
    courses = atlas.build_course_lookup()
    programs = atlas.build_program_lookup()
    atlas.augment_courses_with_program_placeholders(courses, programs)
    atlas.enrich_relationships(programs, courses)
    candidates = {
        mode.key: atlas.build_course_groups(courses, aggressive=mode.key != "full")[0]
        for mode in atlas.PROGRAM_GRAPH_MODES
    }
    graph_count = 0
    for program in programs.values():
        page_path = atlas.BUILD_DIR / "programs" / f"PR_{program.code}.html"
        page = BeautifulSoup(page_path.read_text(), "html.parser")
        embedded = {
            bundle["streamSlug"]: bundle
            for tag in page.select("script[data-graph-analytics-data]")
            for bundle in [json.loads(tag.string)]
        }
        expected_paths = {stream.slug for stream in program.streams}
        if not program.streams or atlas.is_eos_base_program(program):
            expected_paths.add("")
        assert set(embedded) == expected_paths, (program.code, "page graph paths")
        for stream in [None, *program.streams]:
            stem = atlas.stream_asset_stem(program, stream) if stream else program.code
            for mode in atlas.PROGRAM_GRAPH_MODES:
                groups, _ = atlas.scope_program_course_groups(
                    program, courses, candidates[mode.key], stream=stream,
                )
                svg_path = atlas.PROGRAM_GRAPH_DIR / f"{stem}{mode.asset_suffix}.svg"
                svg = ElementTree.fromstring(svg_path.read_text())
                nodes = {
                    node.find("svg:title", SVG).text: node
                    for node in svg.findall(".//svg:g[@class='node']", SVG)
                    if node.find("svg:title", SVG).text.startswith("course__")
                }
                expected_ids = {atlas.course_group_id(code) for code in groups}
                assert set(nodes) == expected_ids, (stem, mode.key, "graph nodes")
                for code, item in groups.items():
                    node = nodes[atlas.course_group_id(code)]
                    labels = [text.text for text in node.findall(".//svg:text", SVG)]
                    assert labels == item.label.split("\\n"), (stem, mode.key, code, labels)
                    anchor = node.find(".//svg:a", SVG)
                    href = anchor.attrib[HREF]
                    assert href == f"../../../courses/{code}.html", (stem, code, href)
                    assert (svg_path.parent / href).resolve().is_file(), (stem, code, "missing course page")
                bundle = embedded.get(stream.slug if stream else "")
                if bundle:
                    analytics = bundle["modes"][mode.key]
                    assert {node["id"] for node in analytics["nodes"]} == expected_ids, (stem, mode.key, "analytics nodes")
                graph_count += 1
        for anchor in page.select('svg a[href]'):
            assert (page_path.parent / anchor["href"]).resolve().is_file(), (program.code, anchor["href"])
    print(f"Verified {graph_count} program SVGs and {len(programs)} program pages: labels, links, nodes, and analytics agree.")


if __name__ == "__main__":
    verify()
