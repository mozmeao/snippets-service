from mock import patch
from nose.tools import eq_

from snippets.base.encoders import SnippetEncoder
from snippets.base.tests import JSONSnippetFactory, TestCase


class SnippetEncoderTests(TestCase):
    def test_encode_jsonsnippet(self):
        encoder = SnippetEncoder()
        data = {'id': 99, 'text': 'test-text',
                'icon': 'test-icon', 'url': 'test-url',
                'country': 'us'}
        snippet = JSONSnippetFactory.build(**data)
        result = encoder.default(snippet)
        data['target_geo'] = data.pop('country').upper()
        eq_(result, data)

    def test_encode_without_country(self):
        encoder = SnippetEncoder()
        data = {'id': 99, 'text': 'test-text',
                'icon': 'test-icon', 'url': 'test-url'}
        snippet = JSONSnippetFactory.build(**data)
        result = encoder.default(snippet)
        eq_(result, data)

    @patch('snippets.base.encoders.json.JSONEncoder.default')
    def test_encode_other(self, default_mock):
        encoder = SnippetEncoder()
        data = {'id': 3}
        encoder.default(data)
        default_mock.assert_called_with(data)
