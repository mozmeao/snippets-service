from mock import patch
from nose.tools import eq_

from snippets.base.models import ClientMatchRule
from snippets.base.tests import ClientMatchRuleFactory, TestCase


class ClientMatchRuleQuerySetTests(TestCase):
    manager = ClientMatchRule.objects

    @patch.object(ClientMatchRule, 'matches')
    def test_basic(self, match):
        rule1_pass = ClientMatchRuleFactory.create()
        rule2_pass = ClientMatchRuleFactory.create()
        rule3_fail = ClientMatchRuleFactory.create()
        rule4_pass = ClientMatchRuleFactory.create()
        rule5_fail = ClientMatchRuleFactory.create()

        # Return the specified return values in sequence.
        return_values = [True, True, False, True, False]
        match.side_effect = lambda client: return_values.pop(0)

        passed, failed = self.manager.all().evaluate('asdf')
        eq_([rule1_pass, rule2_pass, rule4_pass], passed)
        eq_([rule3_fail, rule5_fail], failed)
