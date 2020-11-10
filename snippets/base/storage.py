from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.deconstruct import deconstructible

from storages.backends.s3boto3 import S3Boto3Storage


# TODO
class OverwriteStorage(FileSystemStorage):
    """
    Comes from http://www.djangosnippets.org/snippets/976/
    See also Django #4339, which might add this functionality to core.
    """

    def get_available_name(self, name, max_length=None):
        """
        Returns a filename that's free on the target storage system, and
        available for new content to be written to.
        """
        if self.exists(name):
            self.delete(name)
        return name


@deconstructible
class S3Storage(S3Boto3Storage):
    cache_control_headers = getattr(settings, 'AWS_CACHE_CONTROL_HEADERS', {})

    def _get_write_parameters(self, name, content):
        params = super()._get_write_parameters(name, content)
        encoding = getattr(content, 'content_encoding', params.get('ContentEncoding', None))
        if encoding:
            params['ContentEncoding'] = encoding

        for filename_start, value in self.cache_control_headers.items():
            if name.startswith(filename_start):
                params['CacheControl'] = value

        return params
