import json
from pathlib import Path
import unittest

from swinydl.discovery import _parse_classic_lessons, _parse_cloud_lessons, filter_lessons
from swinydl.models import CourseManifest, InspectOptions


FIXTURES = Path(__file__).parent / "fixtures"


class DiscoveryTests(unittest.TestCase):
    def test_parse_classic_lessons(self):
        payload = json.loads((FIXTURES / "classic_section.json").read_text(encoding="utf-8"))
        lessons, course_id, course_title = _parse_classic_lessons(payload)

        self.assertEqual(course_id, "INFO1001")
        self.assertEqual(course_title, "Intro to Echo360")
        self.assertEqual(len(lessons), 2)
        self.assertEqual(lessons[0].lesson_id, "classic-1")
        self.assertEqual(lessons[0].assets[0].kind, "caption")

    def test_parse_cloud_lessons(self):
        payload = json.loads((FIXTURES / "cloud_syllabus.json").read_text(encoding="utf-8"))
        lessons, course_title = _parse_cloud_lessons("https://swinydl.org.au", payload)

        self.assertEqual(course_title, "Cloud Course")
        self.assertEqual(len(lessons), 1)
        self.assertEqual(lessons[0].lesson_id, "cloud-lesson-1")
        self.assertEqual(lessons[0].assets[0].kind, "media")

    def test_filter_lessons_applies_selection_order(self):
        payload = json.loads((FIXTURES / "classic_section.json").read_text(encoding="utf-8"))
        lessons, course_id, course_title = _parse_classic_lessons(payload)
        course = CourseManifest(
            source_url="https://example.edu/course",
            hostname="https://example.edu",
            platform="classic",
            course_uuid="uuid",
            course_id=course_id,
            course_title=course_title,
            lessons=lessons,
        )

        filtered = filter_lessons(
            course,
            InspectOptions(title_match="week", after_date=None, before_date=None, latest=1),
        )

        self.assertEqual(len(filtered.lessons), 1)
        self.assertEqual(filtered.lessons[0].title, "Week 2 Lecture")
