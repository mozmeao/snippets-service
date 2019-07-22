from datetime import datetime

from django.core.management.base import BaseCommand
from django.db import transaction

from snippets.base.models import Snippet


class Command(BaseCommand):
    args = '(no args)'
    help = 'Disable snippets past publish date'

    @transaction.atomic
    def handle(self, *args, **options):
        now = datetime.utcnow()
        snippets = Snippet.objects.filter(published=True, publish_end__lte=now)
        disabled = snippets.update(published=False)
        running = Snippet.objects.filter(published=True).count()

        self.stdout.write(
            'Snippets Unpublished: {disabled}\n'
            'Snippets Running: {running}\n'.format(disabled=disabled, running=running))
