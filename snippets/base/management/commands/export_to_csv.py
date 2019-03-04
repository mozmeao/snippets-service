import csv
import os
from io import StringIO


from django.conf import settings
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils import timezone

from snippets.base.models import ASRSnippet


class Command(BaseCommand):
    args = '(no args)'
    help = 'Export snippets to CSV'

    def handle(self, *args, **options):
        snippets = ASRSnippet.objects.filter(for_qa=False).order_by('id')

        csvfile = StringIO()
        csvwriter = csv.writer(csvfile, dialect=csv.excel, quoting=csv.QUOTE_ALL)
        for snippet in snippets:
            csvwriter.writerow(snippet.analytics_export().values())

        now = timezone.now()
        filename = os.path.join(settings.CSV_EXPORT_ROOT,
                                now.strftime('snippets_metadata_%Y%m%d.csv'))
        default_storage.save(filename, csvfile)

        self.stdout.write('Done exporting')
