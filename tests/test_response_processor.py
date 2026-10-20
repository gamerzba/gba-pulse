import unittest
from gba_pulse.services.response_processor import process_responses


def response(key, status, body, content_type='application/json', redirected=False):
    return {'key': key, 'status': status, 'ok': 200 <= status < 300,
            'url': 'https://www.gamerz.ba/', 'requestedUrl': 'https://www.gamerz.ba/', 'redirected': redirected,
            'contentType': content_type, 'body': body, 'truncated': False}


class ResponseProcessorTests(unittest.TestCase):
    def _complete_fixture(self):
        return {
            'messages': response('messages', 200, '4'),
            'points': response('points', 200, '1250'),
            'rss': response('rss', 200, '<rss><channel><item><title>Test tema</title><link>https://www.gamerz.ba/t/1</link></item></channel></rss>', 'application/rss+xml'),
            'home': response('home', 200, '<a href="/online/">Online (27)</a>', 'text/html'),
        }

    def test_complete_mock_batch(self):
        data = process_responses(self._complete_fixture())
        self.assertEqual(data['messages']['value'], 4)
        self.assertEqual(data['points']['value'], 1250)
        self.assertEqual(data['online_count'], 27)
        self.assertEqual(data['rss_items'][0].title, 'Test tema')
        self.assertEqual(data['connection_state'], 'ok')
        self.assertNotIn('body', data['messages'])

    def test_unauthenticated_api_shows_no_fake_values(self):
        fixture = self._complete_fixture()
        fixture['messages'] = response('messages', 403, '<html>forbidden</html>', 'text/html')
        fixture['points'] = response('points', 403, '<html>forbidden</html>', 'text/html')
        data = process_responses(fixture)
        self.assertIsNone(data['messages']['value'])
        self.assertIsNone(data['points']['value'])
        self.assertEqual(data['connection_state'], 'warning')
        self.assertIn('403', data['messages']['status'])

    def test_unknown_json_schema_never_guesses(self):
        fixture = self._complete_fixture()
        fixture['messages'] = response('messages', 200, '{"unseen": 9, "meta": {"page": 1}}')
        data = process_responses(fixture)
        self.assertIsNone(data['messages']['value'])
        self.assertEqual(data['messages']['status'], 'Format primljen; potrebno mapirati polje')

    def test_explicit_mapping_works_with_mock_schema(self):
        fixture = self._complete_fixture()
        fixture['messages'] = response('messages', 200, '{"meta":{"unread": 9}}')
        data = process_responses(fixture, {'messages': 'meta.unread'})
        self.assertEqual(data['messages']['value'], 9)

    def test_redirected_api_not_treated_as_authenticated(self):
        fixture = self._complete_fixture()
        fixture['messages'] = response('messages', 200, '999', redirected=True)
        fixture['messages']['requestedUrl'] = 'https://www.gamerz.ba/api/poruke/broj/'
        data = process_responses(fixture)
        self.assertIsNone(data['messages']['value'])
        self.assertEqual(data['messages']['status'], 'Preusmjeren odgovor; provjeri prijavu')

    def test_confirmed_gamerz_payload_defaults_map_balance_unread_and_notifications(self):
        fixture = self._complete_fixture()
        fixture['points'] = response(
            'points', 200,
            '{"balance":1234,"last":987654,"gained":12,"lost":4,"notifications":6}'
        )
        fixture['messages'] = response(
            'messages', 200,
            '{"unread":3,"notifications":6}'
        )
        data = process_responses(fixture)
        self.assertEqual(data['points']['value'], 1234)
        self.assertEqual(data['messages']['value'], 3)
        self.assertEqual(data['notifications']['value'], 6)
        # Unknown semantics such as `last` are never surfaced as a dashboard count.
        self.assertNotIn('last', data)

    def test_notifications_fall_back_to_points_payload(self):
        fixture = self._complete_fixture()
        fixture['points'] = response(
            'points', 200,
            '{"balance":1234,"last":987654,"gained":12,"lost":4,"notifications":6}'
        )
        fixture['messages'] = response('messages', 200, '{"unread":3}')
        data = process_responses(fixture)
        self.assertEqual(data['points']['value'], 1234)
        self.assertEqual(data['messages']['value'], 3)
        self.assertEqual(data['notifications']['value'], 6)

    def test_explicit_user_paths_override_gamerz_defaults(self):
        fixture = self._complete_fixture()
        fixture['points'] = response('points', 200, '{"balance":1234,"custom_balance":99}')
        fixture['messages'] = response('messages', 200, '{"unread":3,"custom_unread":7}')
        data = process_responses(fixture, {'points': 'custom_balance', 'messages': 'custom_unread'})
        self.assertEqual(data['points']['value'], 99)
        self.assertEqual(data['messages']['value'], 7)


if __name__ == '__main__':
    unittest.main()
