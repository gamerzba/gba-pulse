import json
import unittest
from gba_pulse.services.fetch_result import decode_fetch_result, decode_fetch_snapshot

SAMPLE = [
    {"key": "messages", "status": 200, "body": '{"unread":3,"notifications":6}'},
    {"key": "points", "status": 200, "body": '{"balance":1234,"last":987654,"gained":12,"lost":4,"notifications":6}'},
    {"key": "rss", "status": 200, "body": "<rss/>"},
    {"key": "home", "status": 200, "body": "Online 125"},
]


class FetchResultDecoderTests(unittest.TestCase):
    def test_json_string(self):
        self.assertEqual(decode_fetch_result(json.dumps(SAMPLE)), SAMPLE)

    def test_python_list_from_qt_variant(self):
        self.assertEqual(decode_fetch_result(SAMPLE), SAMPLE)

    def test_double_encoded_json(self):
        self.assertEqual(decode_fetch_result(json.dumps(json.dumps(SAMPLE))), SAMPLE)

    def test_wrapper_with_responses(self):
        self.assertEqual(decode_fetch_result({"responses": SAMPLE}), SAMPLE)

    def test_progressive_snapshot_preserves_token_and_completion_state(self):
        partial = {"token": "batch-123", "responses": SAMPLE[:2], "complete": False}
        decoded = decode_fetch_snapshot(json.dumps(partial))
        self.assertEqual(decoded["token"], "batch-123")
        self.assertFalse(decoded["complete"])
        self.assertEqual(len(decoded["responses"]), 2)

    def test_progressive_snapshot_accepts_mapping_of_responses(self):
        partial = {"token": "batch-456", "responses": {item["key"]: item for item in SAMPLE[:2]}, "complete": False}
        decoded = decode_fetch_snapshot(partial)
        self.assertEqual({item["key"] for item in decoded["responses"]}, {"messages", "points"})

    def test_rejects_unknown_shape_without_echoing_values(self):
        with self.assertRaises(ValueError):
            decode_fetch_result('{"private":"secret"}')

    def test_rejects_malformed_json(self):
        with self.assertRaises(ValueError):
            decode_fetch_result("{not-json")

    def test_rejects_entry_without_key(self):
        with self.assertRaises(ValueError):
            decode_fetch_result('[{"status":200,"body":"private"}]')


if __name__ == "__main__":
    unittest.main()
