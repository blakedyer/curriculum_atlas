"""Offline regressions for catalog-faithful program graph grouping.

Run with: python -m unittest discover -s tests -v
"""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from xml.etree import ElementTree

from scripts import build_static_site as atlas


def course(code):
    return {"kind": "course", "code": code, "text": code}


def group(label, *children):
    return {"kind": "group", "label": label, "children": list(children)}


class ProgramCourseGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.courses = atlas.build_course_lookup()
        cls.programs = atlas.build_program_lookup()
        atlas.augment_courses_with_program_placeholders(cls.courses, cls.programs)
        atlas.enrich_relationships(cls.programs, cls.courses)
        cls.full = atlas.build_course_groups(cls.courses)[0]
        cls.simple = atlas.build_course_groups(cls.courses, aggressive=True)[0]

    def scoped(self, program, *, stream=None, simplified=True):
        return atlas.scope_program_course_groups(
            program, self.courses, self.simple if simplified else self.full, stream=stream,
        )

    def synthetic(self, *rules, support=()):
        sections = [{"title": "Year 1", "rules": list(rules)}]
        codes, notes, sections_by_code = atlas.summarize_program_sections(sections)
        return atlas.ProgramRecord(
            "TEST", "Test", "Test", "", {}, sections, codes, notes, sections_by_code,
            support_codes=list(support),
        )

    def test_climate_requires_biol184_and_186_is_only_support(self):
        for code in ("BSC-CLSC", "BSC-CLSD"):
            program = self.programs[code]
            self.assertIn("BIOL184", program.explicit_course_codes)
            self.assertNotIn("BIOL186", program.explicit_course_codes)
            for stream in [None, *program.streams]:
                for simplified in (False, True):
                    with self.subTest(program=code, stream=stream and stream.slug, simplified=simplified):
                        groups, lookup = self.scoped(program, stream=stream, simplified=simplified)
                        self.assertEqual(lookup["BIOL184"], "BIOL184")
                        self.assertEqual(groups["BIOL184"].codes, ("BIOL184",))
                        self.assertEqual(groups["BIOL184"].label, "BIOL184")
                        analytics = atlas.build_program_mode_analytics(
                            program, self.courses, self.simple if simplified else self.full,
                            {}, [], stream=stream,
                        )
                        nodes = {node["id"]: node for node in analytics["nodes"]}
                        self.assertEqual(nodes["course__BIOL184"]["role"], "required")
                        self.assertEqual(nodes["course__BIOL186"]["role"], "support")

    def test_biology_programs_keep_both_required_biology_courses(self):
        for code in ("BSC-BESC", "BSC-BESD"):
            groups, lookup = self.scoped(self.programs[code])
            for biology in ("BIOL184", "BIOL186"):
                self.assertEqual(lookup[biology], biology)
                self.assertEqual(groups[biology].codes, (biology,))

    def test_earth_science_keeps_published_biology_choice(self):
        for code in ("BSC-EOSM", "BSC-EOSH"):
            program = self.programs[code]
            for stream in [None, *program.streams]:
                groups, lookup = self.scoped(program, stream=stream)
                self.assertEqual(lookup["BIOL150A"], lookup["BIOL184"])
                self.assertEqual(groups[lookup["BIOL184"]].codes, ("BIOL150A", "BIOL184"))
                self.assertEqual(groups[lookup["BIOL184"]].label, "Intro biology")

    def test_single_named_course_is_not_replaced_by_global_primary(self):
        program = self.synthetic(course("STAT260"), support=("STAT255",))
        for simplified in (False, True):
            groups, lookup = self.scoped(program, simplified=simplified)
            self.assertEqual(groups[lookup["STAT260"]].codes, ("STAT260",))
            self.assertNotIn("STAT254", lookup)

    def test_direct_single_choice_can_collapse(self):
        program = self.synthetic(group("Complete 1 of:", course("MATH100"), course("MATH109")))
        groups, lookup = self.scoped(program)
        self.assertEqual(lookup["MATH100"], lookup["MATH109"])
        self.assertEqual(groups[lookup["MATH100"]].codes, ("MATH100", "MATH109"))
        self.assertNotIn("MATH102", lookup)

    def test_required_courses_do_not_collapse(self):
        program = self.synthetic(group("Complete all of:", course("STAT255"), course("STAT260")))
        _, lookup = self.scoped(program)
        self.assertNotEqual(lookup["STAT255"], lookup["STAT260"])

    def test_choose_two_courses_do_not_collapse(self):
        program = self.synthetic(group("Complete 2 of:", course("STAT255"), course("STAT260")))
        _, lookup = self.scoped(program)
        self.assertNotEqual(lookup["STAT255"], lookup["STAT260"])

    def test_multi_course_choice_branches_do_not_collapse(self):
        program = self.synthetic(group("Complete 1 of the following",
            group("Complete all of:", course("PHYS110"), course("PHYS111")),
            group("Complete all of:", course("PHYS120"), course("PHYS130")),
        ))
        _, lookup = self.scoped(program)
        self.assertNotEqual(lookup["PHYS110"], lookup["PHYS120"])
        self.assertNotEqual(lookup["PHYS111"], lookup["PHYS130"])

    def test_separate_requirement_occurrence_prevents_collapse(self):
        program = self.synthetic(
            group("Complete 1 of:", course("STAT255"), course("STAT260")), course("STAT260"),
        )
        _, lookup = self.scoped(program)
        self.assertNotEqual(lookup["STAT255"], lookup["STAT260"])

    def test_all_programs_and_streams_preserve_named_and_support_membership(self):
        for program in self.programs.values():
            for stream in [None, *program.streams]:
                named = set(atlas.program_named_codes(
                    program, stream, include_stream_courses=stream is not None or not atlas.is_eos_base_program(program),
                ))
                visible = (named | set(atlas.program_support_codes(program, stream))) & self.courses.keys()
                for simplified in (False, True):
                    with self.subTest(program=program.code, stream=stream and stream.slug, simplified=simplified):
                        groups, lookup = self.scoped(program, stream=stream, simplified=simplified)
                        self.assertEqual(set(lookup), visible)
                        self.assertEqual({c for g in groups.values() for c in g.codes}, visible)
                        for item in groups.values():
                            members = set(item.codes)
                            self.assertTrue(members <= named or members.isdisjoint(named))
                        # Scoping again, as the renderer/analytics do, is stable.
                        self.assertEqual((groups, lookup), atlas.scope_program_course_groups(
                            program, self.courses, groups, stream=stream,
                        ))

    def test_rendered_climate_svg_labels_links_and_roles(self):
        program = self.programs["BSC-CLSC"]
        stream = program.streams[0]
        with tempfile.TemporaryDirectory() as tmp, patch.object(atlas, "PROGRAM_GRAPH_DIR", Path(tmp)):
            for mode in atlas.PROGRAM_GRAPH_MODES:
                source = self.full if mode.key == "full" else self.simple
                atlas.write_program_graph(program, self.courses, source, {}, mode=mode, stream=stream)
                path = Path(tmp) / (atlas.stream_asset_stem(program, stream) + mode.asset_suffix + ".svg")
                root = ElementTree.fromstring(path.read_text())
                ns = {"svg": "http://www.w3.org/2000/svg"}
                nodes = {node.find("svg:title", ns).text: node for node in root.findall(".//svg:g[@class='node']", ns)}
                node = nodes["course__BIOL184"]
                self.assertEqual([t.text for t in node.findall(".//svg:text", ns)], ["BIOL184"])
                anchor = node.find(".//svg:a", ns)
                self.assertEqual(anchor.attrib["{http://www.w3.org/1999/xlink}href"], "../../../courses/BIOL184.html")
                shape = node.find(".//svg:path", ns)
                self.assertEqual(shape.attrib["fill"], atlas.PROGRAM_REQUIRED_STYLE["fillcolor"])
                support = nodes["course__BIOL186"].find(".//svg:path", ns)
                self.assertEqual(support.attrib["fill"], atlas.PROGRAM_SUPPORT_STYLE["fillcolor"])

    def test_analytics_references_only_scoped_graph_nodes(self):
        checks = atlas.find_redundant_prerequisite_checks(
            self.courses, atlas.build_course_groups(self.courses)[1],
        )
        for program in self.programs.values():
            for stream in [None, *program.streams]:
                bundle = atlas.build_program_analytics_bundle(program, self.courses, checks, stream=stream)
                for mode, analytics in bundle["modes"].items():
                    with self.subTest(program=program.code, stream=stream and stream.slug, mode=mode):
                        groups, _ = self.scoped(program, stream=stream, simplified=mode != "full")
                        self.assertEqual({n["group"] for n in analytics["nodes"]}, set(groups))
                        for check in analytics["redundantPrerequisites"]:
                            for raw, key in (("course", "courseGroup"), ("redundant", "redundantGroup"), ("impliedBy", "impliedByGroup")):
                                self.assertIn(check[key], groups)
                                self.assertIn(check[raw], groups[check[key]].codes)


if __name__ == "__main__":
    unittest.main()
