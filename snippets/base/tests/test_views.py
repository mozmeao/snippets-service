from datetime import datetime

from django.contrib.auth.models import User
from django.core.urlresolvers import reverse
from django.test.utils import override_settings

from funfactory.helpers import urlparams
from mock import patch
from nose.tools import eq_, ok_

import snippets.base.models
from snippets.base.models import Client, ClientMatchRule
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

        # Matching snippets.
        snippet_pass_1 = SnippetFactory.create(on_nightly=True)
        snippet_pass_2 = SnippetFactory.create(
            on_nightly=True, client_match_rules=[client_match_rule_pass])

        # Matching but disabled snippet.
        SnippetFactory.create(on_nightly=True, disabled=True)

        # Snippets that do not match.
        SnippetFactory.create(on_nightly=False),
        SnippetFactory.create(on_nightly=False,
                              client_match_rules=[client_match_rule_pass])
        SnippetFactory.create(on_nightly=False,
                              client_match_rules=[client_match_rule_fail])
        snippet_fail_3 = SnippetFactory.create(
            on_nightly=True, client_match_rules=[client_match_rule_fail])
        snippet_fail_4 = SnippetFactory.create(
            on_nightly=True, client_match_rules=[client_match_rule_fail,
                                                 client_match_rule_pass])

        snippets_ok = [snippet_pass_1, snippet_pass_2]
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

    @patch('snippets.base.views.datetime')
    def test_publish_date_filters(self, mock_datetime):
        """
        If it is currently outside of the publish times for a snippet, it
        should not be included in the response.
        """
        mock_datetime.utcnow.return_value = datetime(2013, 4, 5)

        # Passing snippets.
        snippet_no_dates = SnippetFactory.create(on_release=True)
        snippet_after_start_date = SnippetFactory.create(
            on_release=True,
            publish_start=datetime(2013, 3, 6)
        )
        snippet_before_end_date = SnippetFactory.create(
            on_release=True,
            publish_end=datetime(2013, 6, 6)
        )
        snippet_within_range = SnippetFactory.create(
            on_release=True,
            publish_start=datetime(2013, 3, 6),
            publish_end=datetime(2013, 6, 6)
        )

        # Failing snippets.
        SnippetFactory.create(  # Before start date.
            on_release=True,
            publish_start=datetime(2013, 5, 6)
        )
        SnippetFactory.create(  # After end date.
            on_release=True,
            publish_end=datetime(2013, 3, 6)
        )
        SnippetFactory.create(  # Outside range.
            on_release=True,
            publish_start=datetime(2013, 6, 6),
            publish_end=datetime(2013, 7, 6)
        )

        params = ('4', 'Firefox', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'release',
                  'Darwin%2010.8.0', 'default', 'default_version')
        response = self.client.get('/{0}/'.format('/'.join(params)))

        expected = set([snippet_no_dates, snippet_after_start_date,
                       snippet_before_end_date, snippet_within_range])
        eq_(expected, set(response.context['snippets']))

    @patch('snippets.base.views.Client', wraps=Client)
    def test_client_construction(self, ClientMock):
        """
        Ensure that the client object is constructed correctly from the URL
        arguments.
        """
        params = ('4', 'Firefox', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        self.client.get('/{0}/'.format('/'.join(params)))

        ClientMock.assert_called_with(startpage_version='4',
                                      name='Firefox',
                                      version='23.0a1',
                                      appbuildid='20130510041606',
                                      build_target='Darwin_Universal-gcc3',
                                      locale='en-US',
                                      channel='nightly',
                                      os_version='Darwin 10.8.0',
                                      distribution='default',
                                      distribution_version='default_version')

    @override_settings(SNIPPET_HTTP_MAX_AGE=75)
    def test_cache_headers(self):
        """
        view_snippets should always have Cache-control set to
        'public, max-age={settings.SNIPPET_HTTP_MAX_AGE}' and no Vary header,
        even after middleware is executed.
        """
        params = ('4', 'Firefox', '23.0a1', '20130510041606',
                  'Darwin_Universal-gcc3', 'en-US', 'nightly',
                  'Darwin%2010.8.0', 'default', 'default_version')
        response = self.client.get('/{0}/'.format('/'.join(params)))
        eq_(response['Cache-control'], 'public, max-age=75')
        ok_('Vary' not in response)


class PreviewSnippetTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser('admin', 'a@b.com', 'asdf')
        self.client.login(username='admin', password='asdf')

    def _preview_snippet(self, **kwargs):
        return self.client.post(reverse('base.preview'), kwargs)

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


class ShowSnippetTests(TestCase):
    def test_valid_snippet(self):
        """Test show of snippet."""
        snippet = SnippetFactory.create()
        response = self.client.get(
            reverse('base.show', kwargs={'snippet_id': snippet.id}))
        eq_(response.status_code, 200)

    def test_invalid_snippet(self):
        """Test invalid snippet returns 404."""
        response = self.client.get(
            reverse('base.show', kwargs={'snippet_id': '100'}))
        eq_(response.status_code, 404)

    def test_valid_disabled_snippet(self):
        """Test disabled snippet returns 404."""
        snippet = SnippetFactory.create(disabled=True)
        response = self.client.get(
            reverse('base.show', kwargs={'snippet_id': snippet.id}))
        eq_(response.status_code, 404)


@patch('snippets.base.views.SNIPPETS_PER_PAGE', 1)
class IndexSnippetsTests(TestCase):
    def setUp(self):
        for i in range(10):
            SnippetFactory.create()

    def test_base(self):
        response = self.client.get(reverse('base.index'))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 1)

    def test_second_page(self):
        response = self.client.get(urlparams(reverse('base.index'), page=2))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 2)
        eq_(response.context['snippets'].paginator.num_pages, 10)

    def test_empty_page_number(self):
        """Test that empty page number returns the last page."""
        response = self.client.get(urlparams(reverse('base.index'), page=20))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 10)
        eq_(response.context['snippets'].paginator.num_pages, 10)

    def test_non_integer_page_number(self):
        """Test that a non integer page number returns the first page."""
        response = self.client.get(urlparams(reverse('base.index'), page='k'))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].number, 1)
        eq_(response.context['snippets'].paginator.num_pages, 10)

    def test_filter(self):
        SnippetFactory.create(on_nightly=True)
        response = self.client.get(urlparams(reverse('base.index'), on_nightly=2))
        eq_(response.status_code, 200)
        eq_(response.context['snippets'].paginator.count, 1)

    def test_pagination_range_first_page(self):
        response = self.client.get(reverse('base.index'))
        pagination_range = response.context['pagination_range']
        eq_(pagination_range[0], 1)
        eq_(pagination_range[-1], 3)
        eq_(len(pagination_range), 3)

    def test_pagination_range_last_page(self):
        response = self.client.get(urlparams(reverse('base.index'), page=10))
        pagination_range = response.context['pagination_range']
        eq_(pagination_range[0], 8)
        eq_(pagination_range[-1], 10)
        eq_(len(pagination_range), 3)

    def test_pagination_range_middle_page(self):
        response = self.client.get(urlparams(reverse('base.index'), page=5))
        pagination_range = response.context['pagination_range']
        eq_(pagination_range[0], 3)
        eq_(pagination_range[-1], 7)
        eq_(len(pagination_range), 5)
