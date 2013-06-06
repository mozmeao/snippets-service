from django.contrib.auth.models import User
from django.core.urlresolvers import reverse

from mock import patch
from nose.tools import eq_, ok_

from snippets.base.tests import (ClientMatchRuleFactory, SnippetFactory,
                                 SnippetTemplateFactory, TestCase)


class FetchSnippetsTests(TestCase):
    @patch('snippets.base.views.ClientMatchRule')
    def test_basic(self, ClientMatchRule):
        failrule1 = ClientMatchRuleFactory.create()
        failrule2 = ClientMatchRuleFactory.create()
        passrule1 = ClientMatchRuleFactory.create()
        passrule2 = ClientMatchRuleFactory.create()

        evaluate = ClientMatchRule.objects.all.return_value.evaluate
        evaluate.return_value = (
            [passrule1, passrule2], [failrule1, failrule2]
        )

        snippet_pass = SnippetFactory.create(client_match_rules=[passrule1])
        snippet_fail = SnippetFactory.create(client_match_rules=[failrule1])
        snippet_passfail = SnippetFactory.create(
            client_match_rules=[passrule2, failrule2]
        )

        params = ('4', 'Firefox', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        response = self.client.get('/{0}/'.format('/'.join(params)))

        ok_(snippet_pass in response.context['snippets'])
        ok_(snippet_fail not in response.context['snippets'])
        ok_(snippet_passfail not in response.context['snippets'])

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
