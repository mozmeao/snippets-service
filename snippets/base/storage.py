import mimetypes
from datetime import datetime

from django.conf import settings
from django.core.files.storage import FileSystemStorage

from boto.utils import ISO8601
from storages.compat import deconstructible
from storages.backends.s3boto import S3BotoStorage


class OverwriteStorage(FileSystemStorage):

    def get_available_name(self, name):
        if self.exists(name):
            self.delete(name)
        return name


@deconstructible
class S3Storage(S3BotoStorage):
    cache_control_headers = getattr(settings, 'AWS_CACHE_CONTROL_HEADERS', {})

    def _save(self, name, content):
        cleaned_name = self._clean_name(name)
        name = self._normalize_name(cleaned_name)
        headers = self.headers.copy()
        for filename_start, value in self.cache_control_headers.iteritems():
            if name.startswith(filename_start):
                headers['Cache-Control'] = value

        content_type = getattr(content, 'content_type',
                               mimetypes.guess_type(name)[0] or self.key_class.DefaultContentType)

        # setting the content_type in the key object is not enough.
        headers.update({'Content-Type': content_type})

        if self.gzip and content_type in self.gzip_content_types:
            content = self._compress_content(content)
            headers.update({'Content-Encoding': 'gzip'})

        content.name = cleaned_name
        encoded_name = self._encode_name(name)
        key = self.bucket.get_key(encoded_name)
        if not key:
            key = self.bucket.new_key(encoded_name)
        if self.preload_metadata:
            self._entries[encoded_name] = key
            key.last_modified = datetime.utcnow().strftime(ISO8601)

        key.set_metadata('Content-Type', content_type)
        self._save_content(key, content, headers=headers)
        return cleaned_name
