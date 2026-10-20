import unittest
from gba_pulse.services.api_payload import (
    extract_numeric_value, parse_json_body, summarize_shape, value_at_path,
)


class ApiPayloadTests(unittest.TestCase):
    def test_direct_numeric_response(self):
        self.assertEqual(extract_numeric_value("123")[0], 123)
        self.assertEqual(extract_numeric_value('"123"')[0], None)

    def test_does_not_guess_object_key(self):
        value, schema = extract_numeric_value('{"total":12,"meta":{"page":1}}')
        self.assertIsNone(value)
        self.assertIn("total: number", schema)

    def test_explicit_path(self):
        value, _ = extract_numeric_value('{"data":{"unread":7}}', "data.unread")
        self.assertEqual(value, 7)

    def test_array_path(self):
        obj = {"data": [{"count": 8}]}
        self.assertEqual(value_at_path(obj, "data[0].count"), 8)

    def test_bool_not_number(self):
        self.assertIsNone(extract_numeric_value('{"count":true}', "count")[0])

    def test_shape_does_not_disclose_values(self):
        schema = summarize_shape({"username": "secret-user", "token": "top-secret", "count": 17})
        self.assertIn("username: string", schema)
        self.assertIn("token: string", schema)
        self.assertNotIn("secret-user", schema)
        self.assertNotIn("top-secret", schema)
        self.assertNotIn("17", schema)

    def test_invalid_path(self):
        value, schema = extract_numeric_value('{"data":{}}', "data.missing")
        self.assertIsNone(value)
        self.assertIn("Putanja nije riješena", schema)


if __name__ == "__main__":
    unittest.main()
