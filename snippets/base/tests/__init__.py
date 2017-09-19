from django.test import TransactionTestCase

import factory

from snippets.base import models


class TestCase(TransactionTestCase):
    pass


class SnippetTemplateFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Test Template {0}'.format(n))
    code = factory.Sequence(lambda n: '<p>Test Snippet {0}</p>'.format(n))

    @factory.post_generation
    def variable_set(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.variable_set.add(*extracted)

    class Meta:
        model = models.SnippetTemplate


class SnippetTemplateVariableFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'test_var_{0}'.format(n))
    template = factory.SubFactory(SnippetTemplateFactory)

    class Meta:
        model = models.SnippetTemplateVariable


class BaseSnippetFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Test Snippet {0}'.format(n))
    disabled = False
    on_release = True

    @factory.post_generation
    def client_match_rules(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            self.client_match_rules.add(*extracted)

    @factory.post_generation
    def locales(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted is None:
            extracted = ['en-us']

        locales = [models.TargetedLocale.objects.get_or_create(code=code, name=code)[0]
                   for code in extracted]
        self.locales.add(*locales)

    @factory.post_generation
    def countries(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            countries = [
                models.TargetedCountry.objects.get_or_create(code=code, name=code)[0]
                for code in extracted]
            self.countries.add(*countries)


class SnippetFactory(BaseSnippetFactory):
    template = factory.SubFactory(SnippetTemplateFactory)

    class Meta:
        model = models.Snippet


class JSONSnippetFactory(BaseSnippetFactory):
    class Meta:
        model = models.JSONSnippet


class ClientMatchRuleFactory(factory.django.DjangoModelFactory):
    description = factory.Sequence(lambda n: 'Client Match Rule {0}'.format(n))

    class Meta:
        model = models.ClientMatchRule


class UploadedFileFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Uploaded File {0}'.format(n))
    # factory.django.FileField is broken and doesn't save filename. We
    # set file to None to prevent factory from taking any action and mock
    # it as needed in the tests.
    file = None

    class Meta:
        model = models.UploadedFile


class SearchProviderFactory(factory.django.DjangoModelFactory):
    name = factory.Sequence(lambda n: 'Search Provider {0}'.format(n))
    identifier = factory.Sequence(lambda n: 'search-provider-{0}'.format(n))

    class Meta:
        model = models.SearchProvider
