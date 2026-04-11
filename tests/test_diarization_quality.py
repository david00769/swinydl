from __future__ import annotations

from pathlib import Path
import unittest
from unittest.mock import patch

from swinydl.models import TranscriptSegment, TranscriptWord
from swinydl.transcription import diarize_transcript


class DiarizationQualityTests(unittest.TestCase):
    def test_lecture_style_interjection_keeps_secondary_speaker(self):
        segments = [
            TranscriptSegment(start=0.0, end=8.0, text="Today we will cover the midterm review."),
            TranscriptSegment(start=8.0, end=9.6, text="Will this be on the exam?"),
            TranscriptSegment(start=9.6, end=16.0, text="Yes, the review topics are all examinable."),
        ]
        words = [
            TranscriptWord(start=0.0, end=1.5, word="Today", speaker=None),
            TranscriptWord(start=1.5, end=4.0, word="we will cover", speaker=None),
            TranscriptWord(start=4.0, end=8.0, word="the midterm review.", speaker=None),
            TranscriptWord(start=8.0, end=8.8, word="Will this", speaker=None),
            TranscriptWord(start=8.8, end=9.6, word="be on the exam?", speaker=None),
            TranscriptWord(start=9.6, end=12.0, word="Yes, the review", speaker=None),
            TranscriptWord(start=12.0, end=16.0, word="topics are all examinable.", speaker=None),
        ]

        diarizer_payload = {
            "segments": [
                {"speakerId": "LECTURER", "startTime": 0.0, "endTime": 8.0},
                {"speakerId": "AUDIENCE", "startTime": 8.0, "endTime": 9.6},
                {"speakerId": "LECTURER", "startTime": 9.6, "endTime": 16.0},
            ]
        }

        with patch("swinydl.transcription._run_diarizer_coreml", return_value=diarizer_payload):
            diarized_segments, diarized_words = diarize_transcript(Path("lecture.wav"), segments, words)

        self.assertEqual([segment.speaker for segment in diarized_segments], ["LECTURER", "AUDIENCE", "LECTURER"])
        self.assertEqual([word.speaker for word in diarized_words[:3]], ["LECTURER", "LECTURER", "LECTURER"])
        self.assertEqual([word.speaker for word in diarized_words[3:5]], ["AUDIENCE", "AUDIENCE"])
        self.assertEqual([word.speaker for word in diarized_words[5:]], ["LECTURER", "LECTURER"])

    def test_lecture_style_turns_assign_primary_speaker_to_most_words(self):
        segments = [
            TranscriptSegment(start=0.0, end=6.0, text="Let's start with last week's theorem."),
            TranscriptSegment(start=6.0, end=10.0, text="Sorry, can you slow down a bit?"),
            TranscriptSegment(start=10.0, end=18.0, text="Sure, I will go through the proof step by step."),
        ]
        words = [
            TranscriptWord(start=0.0, end=2.0, word="Let's start", speaker=None),
            TranscriptWord(start=2.0, end=6.0, word="with last week's theorem.", speaker=None),
            TranscriptWord(start=6.0, end=8.0, word="Sorry, can you", speaker=None),
            TranscriptWord(start=8.0, end=10.0, word="slow down a bit?", speaker=None),
            TranscriptWord(start=10.0, end=14.0, word="Sure, I will go", speaker=None),
            TranscriptWord(start=14.0, end=18.0, word="through the proof step by step.", speaker=None),
        ]

        diarizer_payload = {
            "segments": [
                {"speakerId": "S1", "startTime": 0.0, "endTime": 6.0},
                {"speakerId": "S2", "startTime": 6.0, "endTime": 10.0},
                {"speakerId": "S1", "startTime": 10.0, "endTime": 18.0},
            ]
        }

        with patch("swinydl.transcription._run_diarizer_coreml", return_value=diarizer_payload):
            diarized_segments, diarized_words = diarize_transcript(Path("lecture.wav"), segments, words)

        primary_words = [word for word in diarized_words if word.speaker == "S1"]
        secondary_words = [word for word in diarized_words if word.speaker == "S2"]

        self.assertGreater(len(primary_words), len(secondary_words))
        self.assertEqual(diarized_segments[0].speaker, "S1")
        self.assertEqual(diarized_segments[1].speaker, "S2")
        self.assertEqual(diarized_segments[2].speaker, "S1")
