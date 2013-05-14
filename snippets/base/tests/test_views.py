from mock import patch
from nose.tools import eq_, ok_

from snippets.base.tests import (ClientMatchRuleFactory, SnippetFactory,
                                 TestCase)


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
