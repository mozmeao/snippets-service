from django.core.exceptions import ValidationError

from nose.tools import ok_

from snippets.base.models import Client, validate_regex
from snippets.base.tests import ClientMatchRuleFactory, TestCase


class ClientMatchRuleTests(TestCase):
    def _client(self, **kwargs):
        client_kwargs = dict((key, '') for key in Client._fields)
        client_kwargs.update(kwargs)
        return Client(**client_kwargs)

    def test_string_match(self):
        client = self._client(channel='aurora')
        pass_rule = ClientMatchRuleFactory(channel='aurora')
        fail_rule = ClientMatchRuleFactory(channel='nightly')

        ok_(pass_rule.matches(client))
        ok_(not fail_rule.matches(client))

    def test_regex_match(self):
        client = self._client(version='15.2.4')
        pass_rule = ClientMatchRuleFactory(version='/[\d\.]+/')
        fail_rule = ClientMatchRuleFactory(version='/\D+/')

        ok_(pass_rule.matches(client))
        ok_(not fail_rule.matches(client))

    def test_multi_match(self):
        client = self._client(version='1.0', locale='en-US')
        pass_rule = ClientMatchRuleFactory(version='1.0', locale='en-US')
        fail_rule = ClientMatchRuleFactory(version='1.0', locale='fr')

        ok_(pass_rule.matches(client))
        ok_(not fail_rule.matches(client))

    def test_empty_match(self):
        client = self._client(version='1.0', locale='fr')
        rule = ClientMatchRuleFactory()

        ok_(rule.matches(client))

    def test_exclusion_rule_match(self):
        client = self._client(channel='aurora')
        fail_rule = ClientMatchRuleFactory(channel='aurora', is_exclusion=True)
        pass_rule = ClientMatchRuleFactory(channel='nightly',
                                           is_exclusion=True)

        ok_(pass_rule.matches(client))
        ok_(not fail_rule.matches(client))


class RegexValidatorTests(TestCase):
    def test_valid_string(self):
        valid_string = 'foobar'
        self.assertEqual(validate_regex(valid_string), valid_string)

    def test_valid_regex(self):
        valid_regex = '/\d+/'
        self.assertEqual(validate_regex(valid_regex), valid_regex)

    def test_invalid_regex(self):
        bogus_regex = '/(?P\d+)/'
        self.assertRaises(ValidationError, validate_regex, bogus_regex)
