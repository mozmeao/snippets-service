from datetime import datetime

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from snippets.base.models import Job


class Command(BaseCommand):
    args = "(no args)"
    help = "Update Jobs"

    @transaction.atomic
    def handle(self, *args, **options):
        now = datetime.utcnow()
        user = get_user_model().objects.get_or_create(username='snippets_bot')[0]

        # Publish Scheduled Jobs with `publish_start` before now or without
        # publish_start.
        jobs = Job.objects.filter(status=Job.SCHEDULED).filter(
            Q(publish_start__lte=now) | Q(publish_start=None)
        )
        published = jobs.count()
        for job in jobs:
            job.change_status(status=job.PUBLISHED, user=user)

        # Disable Published Jobs with `publish_end` before now.
        jobs = Job.objects.filter(status__lte=Job.PUBLISHED, publish_end__lte=now)
        disabled = jobs.count()
        for job in jobs:
            job.change_status(status=job.COMPLETED, user=user)

        self.stdout.write(
            'Jobs Published: {published}\n'
            'Jobs Unpublished: {disabled}\n'
            'Total Jobs Running: {running}\n'.format(
                published=published,
                disabled=disabled,
                running=Job.objects.filter(status=Job.PUBLISHED).count(),
            )
        )
