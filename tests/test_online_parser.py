import unittest
from gba_pulse.services.online_parser import parse_online_count


class OnlineParserTests(unittest.TestCase):
    def test_parentheses_format(self):
        self.assertEqual(parse_online_count('<a href="/online/">Online (159)</a>'), 159)

    def test_plain_number_format(self):
        self.assertEqual(parse_online_count('<a>Online 42</a>'), 42)

    def test_does_not_parse_non_anchor_text(self):
        self.assertIsNone(parse_online_count('<div>Online 99</div><a>Members</a>'))

    def test_no_visible_number(self):
        self.assertIsNone(parse_online_count('<a>Online members</a>'))


if __name__ == "__main__":
    unittest.main()
