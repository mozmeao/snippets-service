from datetime import date
from django.test import TestCase
from django.test.utils import override_settings
from unittest.mock import patch

from snippets.base import etl
from snippets.base.models import DailyChannelMetrics, DailyCountryMetrics
from snippets.base.tests import ASRSnippetFactory, JobFactory


class ETLTests(TestCase):

    country_rows = [
        {'date': '2019-12-19', 'country_code': 'us', 'counts': '11',
         'event': 'IMPRESSION'},
        {'date': '2019-12-19', 'country_code': 'fr', 'counts': '22',
         'event': 'BLOCK'},
        {'date': '2019-12-19', 'country_code': 'de', 'counts': '33',
         'event': 'CLICK'}]
    message_rows = [
        {'date': '2019-12-19', 'message_id': '1', 'counts': '11',
         'event': 'IMPRESSION'},
        {'date': '2019-12-19', 'message_id': '2', 'counts': '22',
         'event': 'BLOCK'},
        {'date': '2019-12-19', 'message_id': '3', 'counts': '33',
         'event': 'CLICK'},
        {'date': '2019-12-19', 'message_id': '4', 'counts': '44',
         'event': 'IMPRESSION'},
        {'date': 'foo', 'message_id': 'bar', 'counts': 'baz', 'event': 'qux'}]
    channel_rows = [
        {'date': '2019-12-19', 'release_channel': 'release', 'counts': '11',
         'event': 'IMPRESSION'},
        {'date': '2019-12-19', 'release_channel': 'beta', 'counts': '22',
         'event': 'BLOCK'},
        {'date': '2019-12-19', 'release_channel': 'auroraa', 'counts': '33',
         'event': 'CLICK'},
        {'date': '2019-12-19', 'release_channel': 'foo', 'counts': '44',
         'event': 'IMPRESSION'},
        {'date': 'foo', 'release_channel': 'bar', 'counts': 'baz',
         'event': 'qux'}]

    def test_snippet_metrics_from_rows(self):
        snippet_ids = [1, 2, 3]
        metrics = etl.snippet_metrics_from_rows(self.message_rows, snippet_ids=snippet_ids)
        d = date(2019, 12, 19)
        assert metrics[d][1].impressions == 11
        assert metrics[d][2].blocks == 22
        assert metrics[d][3].clicks == 33
        assert metrics[d].get(4) is None
        assert metrics[d].get('foo') is None

        metrics = etl.snippet_metrics_from_rows(self.message_rows, metrics, snippet_ids)
        assert metrics[d][1].impressions == 22
        assert metrics[d][2].blocks == 44
        assert metrics[d][3].clicks == 66
        assert metrics[d].get(4) is None
        assert metrics[d].get('foo') is None

    def test_channel_metrics_from_rows(self):
        metrics = etl.channel_metrics_from_rows(self.channel_rows)
        d = date(2019, 12, 19)
        assert metrics[d]['release'].impressions == 11
        assert metrics[d]['beta'].blocks == 22
        assert metrics[d]['aurora'].clicks == 33
        assert metrics[d].get('foo') is None
        assert metrics[d].get('bar') is None

        metrics = etl.channel_metrics_from_rows(self.channel_rows, metrics)
        assert metrics[d]['release'].impressions == 22
        assert metrics[d]['beta'].blocks == 44
        assert metrics[d]['aurora'].clicks == 66
        assert metrics[d].get('foo') is None
        assert metrics[d].get('bar') is None

    def test_country_metrics_from_rows(self):
        metrics = etl.country_metrics_from_rows(self.country_rows)
        d = date(2019, 12, 19)
        assert metrics[d]['us'].impressions == 11
        assert metrics[d]['fr'].blocks == 22
        assert metrics[d]['de'].clicks == 33

        metrics = etl.country_metrics_from_rows(self.country_rows, metrics)
        assert metrics[d]['us'].impressions == 22
        assert metrics[d]['fr'].blocks == 44
        assert metrics[d]['de'].clicks == 66

    @patch('snippets.base.etl.redash_rows', return_value=channel_rows)
    def test_update_channel_metrics(self, redash_rows):
        etl.update_channel_metrics()
        dcm = {m.channel: m for m in DailyChannelMetrics.objects.all()}
        assert len(dcm) == 3
        assert dcm['release'].impressions == 22
        assert dcm['beta'].blocks == 44
        assert dcm['aurora'].clicks == 66

    @patch('snippets.base.etl.redash_rows', return_value=country_rows)
    def test_update_country_metrics(self, redash_rows):
        etl.update_country_metrics()
        dcm = {m.country: m for m in DailyCountryMetrics.objects.all()}
        assert len(dcm) == 3
        assert dcm['us'].impressions == 22
        assert dcm['fr'].blocks == 44
        assert dcm['de'].clicks == 66

    @patch('snippets.base.etl.redash_rows', return_value=message_rows)
    def test_update_message_metrics(self, redash_rows):
        snippet1 = ASRSnippetFactory()
        snippet2 = ASRSnippetFactory()
        job = JobFactory(id=3)
        etl.update_message_metrics()
        assert snippet1.dailysnippetmetrics_set.all()[0].impressions == 11
        assert snippet2.dailysnippetmetrics_set.all()[0].blocks == 22
        assert job.dailyjobmetrics_set.all()[0].clicks == 66

    @patch('snippets.base.etl.redash.query',
           return_value={'query_result': {'data': {'rows': ['mock rows']}}})
    def test_redash_rows(self, query):
        d = date(2019, 12, 19)
        query_name, query_id = next(iter(etl.REDASH_QUERY_IDS.items()))
        assert etl.redash_rows(query_name, d, d) == ['mock rows']
        bind_data = {'begin_date': str(d), 'end_date': str(d)}
        query.assert_called_with(query_id, bind_data)

    @override_settings(REDASH_ENDPOINT='https://sql.telemetry.mozilla.org')
    def test_redash_source_url(self):
        url = 'https://sql.telemetry.mozilla.org/queries/66850/source'
        assert etl.redash_source_url('bq-channel') == url
        url += '?p_begin_date_66850=2019-12-19&p_end_date_66850=2019-12-20'
        assert etl.redash_source_url('bq-channel', begin_date='2019-12-19',
                                     end_date='2019-12-20') == url

