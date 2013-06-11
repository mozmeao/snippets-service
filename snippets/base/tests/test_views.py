from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from mock import patch
from nose.tools import eq_, ok_

import snippets.base.models
from snippets.base.models import ClientMatchRule
from snippets.base.tests import (ClientMatchRuleFactory, SnippetFactory,
                                 SnippetTemplateFactory, TestCase)

snippets.base.models.CHANNELS = ('release', 'beta', 'aurora', 'nightly')
snippets.base.models.STARTPAGE_VERSIONS = ('1', '2', '3', '4')
snippets.base.models.CLIENT_NAMES = {'Firefox': 'firefox', 'fennec': 'fennec'}


class FetchSnippetsTests(TestCase):
    @patch('snippets.base.views.ClientMatchRule', wraps=ClientMatchRule)
    def test_base(self, ClientMatchRuleMock):
        client_match_rule_pass = ClientMatchRuleFactory(
            name='Firefox', channel='nightly', startpage_version='4')
        client_match_rule_fail = ClientMatchRuleFactory(
            name='Firefox', channel='release', startpage_version='4')

        snippet_pass_1 = SnippetFactory.create(on_nightly=True)
        snippet_pass_2 = SnippetFactory.create(
            on_nightly=True, client_match_rules=[client_match_rule_pass])

        snippet_fail_1 = SnippetFactory.create(on_nightly=False),
        snippet_fail_2 = SnippetFactory.create(
            on_nightly=False, client_match_rules=[client_match_rule_pass])
        snippet_fail_2 = SnippetFactory.create(
            on_nightly=False, client_match_rules=[client_match_rule_fail])
        snippet_fail_3 = SnippetFactory.create(
            on_nightly=True, client_match_rules=[client_match_rule_fail])
        snippet_fail_4 = SnippetFactory.create(
            on_nightly=True, client_match_rules=[client_match_rule_fail,
                                                 client_match_rule_pass])

        snippets_ok = [snippet_pass_1, snippet_pass_2]
        snippets_fail = [snippet_fail_1, snippet_fail_2, snippet_fail_3,
                         snippet_fail_4]
        snippets_pass_match_client = (snippets_ok + 
                                      [snippet_fail_3, snippet_fail_4])

        params = ('4', 'Firefox', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        response = self.client.get('/{0}/'.format('/'.join(params)))

        eq_(set(snippets_ok), set(response.context['snippets']))
        call_args = (ClientMatchRuleMock.objects
                     .filter.call_args[1]['snippet__in'])
        eq_(set(snippets_pass_match_client), set(call_args))
        
    @patch('snippets.base.views.ClientMatchRule.objects')
    def test_client_construction(self, mock_objects):
        evaluate = mock_objects.filter.return_value.evaluate
        evaluate.return_value = ([], [])

        params = ('4', 'Firefox', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        self.client.get('/{0}/'.format('/'.join(params)))

        # Test that the client was constructed correctly.
        client = evaluate.call_args[0][0]
        eq_('4', client.startpage_version)
        eq_('Firefox', client.name)
        eq_('23.0a1', client.version)
        eq_('20130510041606', client.appbuildid)
        eq_('Darwin_Universal-gcc3', client.build_target)
        eq_('en-US', client.locale)
        eq_('nightly', client.channel)
        eq_('Darwin 10.8.0', client.os_version)
        eq_('default', client.distribution)
        eq_('default_version', client.distribution_version)


class PreviewSnippetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'a@b.com', 'asdf')
        self.client.login(username='admin', password='asdf')

    def _preview_snippet(self, **kwargs):
        return self.client.get(reverse('base.preview'), kwargs)

    def test_invalid_template(self):
        """If template_id is missing or invalid, return a 400 Bad Request."""
        response = self._preview_snippet()
        eq_(response.status_code, 400)

        response = self._preview_snippet(template_id=99999999999999999999)
        eq_(response.status_code, 400)

    def test_invalid_data(self):
        """If data is missing or invalid, return a 400 Bad Request."""
        template = SnippetTemplateFactory.create()
        response = self._preview_snippet(template_id=template.id)
        eq_(response.status_code, 400)

        response = self._preview_snippet(template_id=template.id,
                                         data='{invalid."json]')
        eq_(response.status_code, 400)

    def test_valid_args(self):
        """If template_id and data are both valid, return the preview page."""
        template = SnippetTemplateFactory.create()
        data = '{"a": "b"}'

        response = self._preview_snippet(template_id=template.id, data=data)
        eq_(response.status_code, 200)

        snippet = response.context['snippet']
        eq_(snippet.template, template)
        eq_(snippet.data, data)
