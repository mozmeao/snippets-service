import factory
from test_utils import TestCase as BaseTestCase

from snippets.base import models


class TestCase(BaseTestCase):
    pass


class SnippetTemplateFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.SnippetTemplate
    name = factory.Sequence(lambda n: 'Test Template {0}'.format(n))
    code = factory.Sequence(lambda n: '<p>Test Snippet {0}</p>'.format(n))

    @factory.post_generation
    def variable_set(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.variable_set.add(*extracted)


class SnippetTemplateVariableFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.SnippetTemplateVariable
    name = factory.Sequence(lambda n: 'test_var_{0}'.format(n))
    template = factory.SubFactory(SnippetTemplateFactory)


class BaseSnippetFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.Snippet
    name = factory.Sequence(lambda n: 'Test Snippet {0}'.format(n))
    disabled = False

    @factory.post_generation
    def client_match_rules(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.client_match_rules.add(*extracted)

    @factory.post_generation
    def locale_set(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted is not None:
            self.locale_set.add(*extracted)
        else:
            self.locale_set.create(locale='en-us')


class SnippetFactory(BaseSnippetFactory):
    FACTORY_FOR = models.Snippet
    template = factory.SubFactory(SnippetTemplateFactory)


class JSONSnippetFactory(BaseSnippetFactory):
    FACTORY_FOR = models.JSONSnippet


class ClientMatchRuleFactory(factory.DjangoModelFactory):
    FACTORY_FOR = models.ClientMatchRule
    description = factory.Sequence(lambda n: 'Client Match Rule {0}'.format(n))


class CONTAINS(object):
    """
    Helper object that is equal to any object that contains a specific
    value.

    If exclusive=True is passed to the constructor, sets will be used
    for comparison, meaning that an iterable is equal to this object
    only if it contains the same values given in the constructor,
    ignoring the order of values.
    """
    def __init__(self, *values, **kwargs):
        self.values = values
        self.exclusive = kwargs.get('exclusive', False)

    def __eq__(self, other):
        if self.exclusive:
            return set(v for v in other) == set(self.values)
        else:
            return all(v in other for v in self.values)

    def __ne__(self, other):
        return not self.__eq__(other)
