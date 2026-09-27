import unittest

from swinydl.captions import parse_srt, parse_webvtt


class CaptionParsingTests(unittest.TestCase):
    def test_srt_preserves_commas_in_caption_text(self):
        srt = (
            "1\n"
            "00:00:01,000 --> 00:00:03,000\n"
            "Well, however, this is one sentence.\n"
            "\n"
            "2\n"
            "00:00:04,000 --> 00:00:06,500\n"
            "Second cue, with a comma.\n"
        )
        segments = parse_srt(srt)
        self.assertEqual(len(segments), 2)
        # The comma decimal separator in timestamps is parsed correctly...
        self.assertAlmostEqual(segments[0].start, 1.0)
        self.assertAlmostEqual(segments[0].end, 3.0)
        self.assertAlmostEqual(segments[1].end, 6.5)
        # ...while commas inside the spoken text are left intact.
        self.assertEqual(segments[0].text, "Well, however, this is one sentence.")
        self.assertEqual(segments[1].text, "Second cue, with a comma.")

    def test_webvtt_accepts_minutes_seconds_only_timestamps(self):
        vtt = (
            "WEBVTT\n"
            "\n"
            "00:01.000 --> 00:03.000\n"
            "No hours field here.\n"
        )
        segments = parse_webvtt(vtt)
        self.assertEqual(len(segments), 1)
        self.assertAlmostEqual(segments[0].start, 1.0)
        self.assertAlmostEqual(segments[0].end, 3.0)
        self.assertEqual(segments[0].text, "No hours field here.")

    def test_cues_without_blank_separator_do_not_merge(self):
        # Two cues delimited only by an index line, with no blank line between.
        vtt = (
            "WEBVTT\n"
            "\n"
            "00:00:01.000 --> 00:00:02.000\n"
            "First cue.\n"
            "00:00:03.000 --> 00:00:04.000\n"
            "Second cue.\n"
        )
        segments = parse_webvtt(vtt)
        self.assertEqual(len(segments), 2)
        self.assertEqual(segments[0].text, "First cue.")
        self.assertAlmostEqual(segments[0].end, 2.0)
        self.assertEqual(segments[1].text, "Second cue.")
        self.assertAlmostEqual(segments[1].start, 3.0)


if __name__ == "__main__":
    unittest.main()
