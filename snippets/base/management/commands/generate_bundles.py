from django.core.management.base import BaseCommand

from snippets.base import bundles


class Command(BaseCommand):
    args = '(no args)'
    help = 'Generate bundles'

    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument(
            '--timestamp',
            help='Parse Jobs last modified after <timestamp>',
        )

    def handle(self, *args, **options):
        bundles.generate_bundles(
            timestamp=options.get('timestamp', None),
            stdout=self.stdout,
        )
