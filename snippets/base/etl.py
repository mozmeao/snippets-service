from datetime import date, datetime, timedelta
from django.conf import settings
from django.db.transaction import atomic
from redash_dynamic_query import RedashDynamicQuery
from snippets.base.models import (
    ASRSnippet, DailyChannelMetrics, DailyCountryMetrics, DailyJobMetrics,
    DailySnippetMetrics, Job)

BQ_DATA_BEGIN_DATE = date(2019, 12, 4)
JOBS_BEGIN_DATE = date(2019, 10, 1)

REDASH_QUERY_IDS = {
    'original-jobs': 63146,  # settings.REDASH_JOB_QUERY_ID
    'original-daily': 65755,  # settings.REDASH_DAILY_QUERY_ID
    'redshift-message-id': 66846,
    'bq-message-id': 66826,
    'redshift-country': 66816,
    'bq-country': 66849,
    'redshift-channel': 66815,
    'bq-channel': 66850}

redash = RedashDynamicQuery(
    endpoint=settings.REDASH_ENDPOINT,
    apikey=settings.REDASH_API_KEY,
    max_wait=settings.REDASH_MAX_WAIT)


def redash_source_url(query_id_or_name):
    query_id = REDASH_QUERY_IDS.get(query_id_or_name, query_id_or_name)
    return f'{settings.REDASH_ENDPOINT}/queries/{query_id}/source'


def redash_rows(query_name, begin_date, end_date):
    query_id = REDASH_QUERY_IDS[query_name]
    bind_data = {'begin_date': datetime.strftime(begin_date, '%Y-%m-%d'),
                 'end_date': datetime.strftime(end_date, '%Y-%m-%d')}
    result = redash.query(query_id, bind_data)
    return result['query_result']['data']['rows']


def add_metric_event_counts(metric, event, counts):
    if event == 'IMPRESSION':
        metric.impressions += counts
    elif event == 'BLOCK':
        metric.blocks += counts
    elif event in ('CLICK', 'CLICK_BUTTON'):
        metric.clicks += counts


def snippet_metrics_from_rows(rows, metrics=None, snippet_ids=None):
    if not snippet_ids:
        snippet_ids = set(ASRSnippet.objects.values_list('id', flat=True))
    if not metrics:
        metrics = {}
    for row in rows:
        try:
            date = datetime.strptime(row['date'], '%Y-%m-%d').date()
            message_id = int(row['message_id'])
            counts = int(row['counts'])
            event = row['event']
        except ValueError:
            continue
        if message_id not in snippet_ids:
            continue
        metrics.setdefault(date, {})
        metrics[date].setdefault(
            message_id, DailySnippetMetrics(
                snippet_id=message_id, date=date))
        add_metric_event_counts(metrics[date][message_id], event, counts)
    return metrics


def job_metrics_from_rows(rows, metrics=None, job_ids=None):
    if not job_ids:
        job_ids = set(Job.objects.values_list('id', flat=True))
    if not metrics:
        metrics = {}
    for row in rows:
        try:
            date = datetime.strptime(row['date'], '%Y-%m-%d').date()
            message_id = int(row['message_id'])
            counts = int(row['counts'])
            event = row['event']
        except ValueError:
            continue
        if message_id not in job_ids:
            continue
        metrics.setdefault(date, {})
        metrics[date].setdefault(
            message_id, DailyJobMetrics(
                job_id=message_id, date=date))
        add_metric_event_counts(metrics[date][message_id], event, counts)
    return metrics


def update_message_metrics(begin_date=None, end_date=None):
    if not end_date:
        end_date = date.today() - timedelta(days=1)
    if not begin_date:
        begin_date = end_date - timedelta(days=1)
    redshift_rows = redash_rows('redshift-message-id', begin_date, end_date)
    if end_date >= JOBS_BEGIN_DATE:
        job_ids = set(Job.objects.values_list('id', flat=True))
        metrics = job_metrics_from_rows(redshift_rows, job_ids=job_ids)
        if end_date >= BQ_DATA_BEGIN_DATE:
            bq_rows = redash_rows('bq-message-id', begin_date, end_date)
            metrics = job_metrics_from_rows(
                bq_rows, metrics=metrics, job_ids=job_ids)
        with atomic():
            DailyJobMetrics.objects.filter(date__gte=begin_date, date__lte=end_date).delete()
            DailyJobMetrics.objects.bulk_create(
                dm for mv in metrics.values() for dm in mv.values())
    metrics = snippet_metrics_from_rows(redshift_rows)
    with atomic():
        DailySnippetMetrics.objects.filter(date__gte=begin_date, date__lte=end_date).delete()
        DailySnippetMetrics.objects.bulk_create(
            dm for mv in metrics.values() for dm in mv.values())


def channel_metrics_from_rows(rows, metrics=None):
    valid_channels = ('release', 'beta', 'aurora', 'nightly', 'default')
    if metrics is None:
        metrics = {}
    for row in rows:
        release_channel = row['release_channel']
        if not release_channel:
            continue
        valid = False
        for c in valid_channels:
            if release_channel.startswith(c):
                release_channel = c
                valid = True
        if not valid:
            continue
        try:
            date = datetime.strptime(row['date'], '%Y-%m-%d').date()
            event = row['event']
            counts = int(row['counts'])
        except ValueError:
            continue
        metrics.setdefault(date, {})
        metrics[date].setdefault(
            release_channel,
            DailyChannelMetrics(
                channel=release_channel,
                date=date))
        add_metric_event_counts(metrics[date][release_channel], event, counts)
    return metrics


def update_channel_metrics(begin_date=None, end_date=None):
    if not end_date:
        end_date = date.today() - timedelta(days=1)
    if not begin_date:
        begin_date = end_date - timedelta(days=1)
    redshift_rows = redash_rows('redshift-channel', begin_date, end_date)
    metrics = channel_metrics_from_rows(redshift_rows)
    if end_date >= BQ_DATA_BEGIN_DATE:
        bq_rows = redash_rows('bq-channel', begin_date, end_date)
        metrics = channel_metrics_from_rows(bq_rows, metrics=metrics)
    with atomic():
        DailyChannelMetrics.objects.filter(date__gte=begin_date, date__lte=end_date).delete()
        DailyChannelMetrics.objects.bulk_create(
            dm for mv in metrics.values() for dm in mv.values())


def country_metrics_from_rows(rows, metrics=None):
    if metrics is None:
        metrics = {}
    for row in rows:
        try:
            date = datetime.strptime(row['date'], '%Y-%m-%d').date()
            country = row['country_code']
            event = row['event']
            counts = int(row['counts'])
        except ValueError:
            continue
        metrics.setdefault(date, {})
        metrics[date].setdefault(
            country, DailyCountryMetrics(
                country=country,
                date=date))
        add_metric_event_counts(metrics[date][country], event, counts)
    return metrics


def update_country_metrics(begin_date=None, end_date=None):
    if not end_date:
        end_date = date.today() - timedelta(days=1)
    if not begin_date:
        begin_date = end_date - timedelta(days=1)
    redshift_rows = redash_rows('redshift-country', begin_date, end_date)
    metrics = country_metrics_from_rows(redshift_rows)
    if end_date >= BQ_DATA_BEGIN_DATE:
        bq_rows = redash_rows('bq-country', begin_date, end_date)
        metrics = country_metrics_from_rows(bq_rows, metrics=metrics)
    with atomic():
        DailyCountryMetrics.objects.filter(date__gte=begin_date, date__lte=end_date).delete()
        DailyCountryMetrics.objects.bulk_create(
            dm for mv in metrics.values() for dm in mv.values())
