from __future__ import print_function
import datetime
import os
import sys
from subprocess import check_call

from django.conf import settings
from django.db import connection

import babis
from apscheduler.schedulers.blocking import BlockingScheduler

from snippets.base.util import create_countries, create_locales


MANAGE = os.path.join(settings.ROOT, 'manage.py')
schedule = BlockingScheduler()


def call_command(command):
    check_call('python {0} {1}'.format(MANAGE, command), shell=True)


class scheduled_job(object):
    """Decorator for scheduled jobs. Takes same args as apscheduler.schedule_job."""
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __call__(self, fn):
        job_name = fn.__name__
        self.name = job_name
        self.callback = fn
        schedule.add_job(self.run, id=job_name, *self.args, **self.kwargs)
        self.log('Registered.')
        return self.run

    def run(self):
        self.log('starting')
        try:
            self.callback()
        except Exception as e:
            self.log('CRASHED: {}'.format(e))
            raise
        else:
            self.log('finished successfully')

    def log(self, message):
        msg = '[{}] Clock job {}@{}: {}'.format(
            datetime.datetime.utcnow(), self.name,
            os.getenv('K8S_NAMESPACE', 'default_app'), message)
        print(msg, file=sys.stderr)


@scheduled_job('cron', month='*', day='*', hour='*/12', minute='10', max_instances=1, coalesce=True)
@babis.decorator(ping_after=settings.DEAD_MANS_SNITCH_PRODUCT_DETAILS)
def job_update_product_details():
    call_command('update_product_details')
    connection.close()
    create_countries()
    create_locales()


@scheduled_job('cron', month='*', day='*', hour='*/12', minute='20', max_instances=1, coalesce=True)
@babis.decorator(ping_after=settings.DEAD_MANS_SNITCH_DISABLE_SNIPPETS)
def job_disable_snippets_past_publish_date():
    call_command('disable_snippets_past_publish_date')


@scheduled_job('cron', month='*', day='*', hour='*', minute='*', max_instances=1, coalesce=True)
@babis.decorator(ping_after=settings.DEAD_MANS_SNITCH_UPDATE_JOBS)
def job_update_jobs():
    call_command('update_jobs')


@scheduled_job('cron', month='*', day='*', hour='08', minute='20', max_instances=1, coalesce=True)
@babis.decorator(ping_after=settings.DEAD_MANS_SNITCH_CSV_EXPORT)
def job_export_to_csv():
    call_command('export_to_csv')


def run():
    try:
        schedule.start()
    except (KeyboardInterrupt, SystemExit):
        pass
