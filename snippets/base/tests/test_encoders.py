from unittest.mock import patch

from snippets.base.encoders import JSONSnippetEncoder
from snippets.base.tests import JSONSnippetFactory, TestCase


class JSONSnippetEncoderTests(TestCase):
    def test_encode_jsonsnippet(self):
        encoder = JSONSnippetEncoder()
        data = {'id': 99, 'text': 'test-text',
                'icon': 'test-icon', 'url': 'test-url',
                'countries': ['US', 'GR'], 'weight': 100}
        snippet = JSONSnippetFactory.create(**data)
        result = encoder.default(snippet)
        self.assertEqual(result.pop('target_geo'), result.get('countries')[0])
        self.assertEqual(set(result.pop('countries')), set(data.pop('countries')))
        self.assertEqual(result, data)

    def test_encode_without_country(self):
        encoder = JSONSnippetEncoder()
        data = {'id': 99, 'text': 'test-text',
                'icon': 'test-icon', 'url': 'test-url',
                'weight': 100}
        snippet = JSONSnippetFactory(**data)
        result = encoder.default(snippet)
        self.assertEqual(result, data)

    @patch('snippets.base.encoders.json.JSONEncoder.default')
    def test_encode_other(self, default_mock):
        encoder = JSONSnippetEncoder()
        data = {'id': 3}
        encoder.default(data)
        default_mock.assert_called_with(data)
