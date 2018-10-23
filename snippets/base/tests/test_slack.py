from unittest.mock import patch

from django.test.utils import override_settings

from snippets.base import slack
from snippets.base.tests import TestCase


class SendSlackTests(TestCase):
    @override_settings(SLACK_ENABLE=False)
    def test_slack_disalbed(self):
        with patch('snippets.base.slack.requests') as requests_mock:
            slack._send_slack('foo')
        self.assertFalse(requests_mock.called)

    @override_settings(SLACK_ENABLE=True, SLACK_WEBHOOK='https://example.com')
    def test_slack_enabled(self):
        with patch('snippets.base.slack.requests') as requests_mock:
            slack._send_slack('foo')
        self.assertTrue(requests_mock.post.called)
        requests_mock.post.assert_called_with(
            'https://example.com', data='foo', timeout=4,
            headers={'Content-Type': 'application/json'})
