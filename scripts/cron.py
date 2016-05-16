from __future__ import print_function
import datetime
import os
import sys

from django.core.management import call_command
from django.conf import settings
from django.db import connections

import requests
from apscheduler.schedulers.blocking import BlockingScheduler

from snippets.base.util import create_countries, create_locales


schedule = BlockingScheduler()


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
            os.getenv('DEIS_APP', 'default_app'), message)
        print(msg, file=sys.stderr)


def ping_dms(function):
    """Pings Dead Man's Snitch after job completion if URL is set."""
    def _ping():
        function()
        if settings.DEAD_MANS_SNITCH_URL:
            utcnow = datetime.datetime.utcnow()
            payload = {'m': 'Run {} on {}'.format(function.__name__, utcnow.isoformat())}
            requests.get(settings.DEAD_MANS_SNITCH_URL, params=payload)
    _ping.__name__ = function.__name__
    return _ping


@scheduled_job('cron', month='*', day='*', hour='*/12', minute='10', max_instances=1, coalesce=True)
@ping_dms
def job_update_product_details():
    call_command('update_product_details')
    create_countries()
    create_locales()
    # Django won't close db connections after call_command. Close them manually
    # to prevent errors in case the DB goes away, e.g. during a failover event.
    connections.close_all()


def run():
    try:
        schedule.start()
    except (KeyboardInterrupt, SystemExit):
        pass
