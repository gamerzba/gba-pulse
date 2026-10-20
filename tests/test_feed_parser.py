import unittest
from gba_pulse.services.feed_parser import parse_feed, strip_html


class FeedParserTests(unittest.TestCase):
    def test_rss_two_items_and_link(self):
        xml = '''<?xml version="1.0"?><rss version="2.0"><channel>
          <item><title>Prva tema</title><link>https://www.gamerz.ba/threads/1</link><description>&lt;p&gt;Pozdrav &lt;b&gt;svima&lt;/b&gt;&lt;/p&gt;</description><pubDate>Tue, 20 Oct 2026 09:00:00 +0000</pubDate></item>
          <item><title>Druga tema</title><link>https://gamerz.ba/threads/2</link></item>
        </channel></rss>'''
        result = parse_feed(xml, "https://www.gamerz.ba/rss", 5)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].title, "Prva tema")
        self.assertEqual(result[0].summary, "Pozdrav svima")
        self.assertEqual(result[0].link, "https://www.gamerz.ba/threads/1")
        self.assertEqual(result[1].link, "https://gamerz.ba/threads/2")

    def test_atom_feed(self):
        xml = '''<feed xmlns="http://www.w3.org/2005/Atom"><entry><title>Atom tema</title><link href="https://www.gamerz.ba/t/42" rel="alternate"/><summary>Sažetak</summary></entry></feed>'''
        result = parse_feed(xml, "https://www.gamerz.ba/rss", 5)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].link, "https://www.gamerz.ba/t/42")
        self.assertEqual(result[0].summary, "Sažetak")

    def test_external_link_rejected(self):
        xml = '''<rss><channel><item><title>External</title><link>https://evil.example/path</link></item></channel></rss>'''
        self.assertEqual(parse_feed(xml, "https://www.gamerz.ba/rss", 5)[0].link, "")

    def test_non_url_guid_not_made_clickable(self):
        xml = '''<rss><channel><item><title>Guid</title><guid isPermaLink="false">thread-123</guid></item></channel></rss>'''
        self.assertEqual(parse_feed(xml, "https://www.gamerz.ba/rss", 5)[0].link, "")

    def test_bad_xml_safe_empty(self):
        self.assertEqual(parse_feed("<broken", "https://www.gamerz.ba/rss"), [])

    def test_limit_zero_and_html(self):
        self.assertEqual(parse_feed("<rss><channel><item><title>x</title></item></channel></rss>", "https://www.gamerz.ba/rss", 0), [])
        self.assertEqual(strip_html("<div>one <b>two</b><script>secret()</script></div>"), "one two")


if __name__ == "__main__":
    unittest.main()
