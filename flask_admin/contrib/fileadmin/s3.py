from boto import s3
from boto.s3.prefix import Prefix
from boto.s3.key import Key
import dateutil.parser

from flask import abort, redirect, send_file

from flask_admin._compat import urljoin
from flask_admin.base import expose

from flask_admin.contrib.fileadmin.base import BaseFileAdmin

from flask_admin.babel import gettext


class S3FileAdmin(BaseFileAdmin):
    def __init__(self, bucket_name, bucket_prefix, region, aws_access_key_id,
                 aws_secret_access_key, *args, **kwargs):
        connection = s3.connect_to_region(region,
                                          aws_access_key_id=aws_access_key_id,
                                          aws_secret_access_key=aws_secret_access_key)
        self.bucket = connection.get_bucket(bucket_name)

        super(S3FileAdmin, self).__init__(bucket_prefix, *args, **kwargs)

    def get_files(self, path, directory):
        def _strip_path(name, path):
            if name.startswith(path):
                return name.replace(path, '', 1)
            return name

        def _remove_trailing_slash(name):
            return name[:-1]

        files = []
        directories = []
        if path and not path.endswith('/'):
            path += '/'
        for key in self.bucket.list(path, '/'):
            if key.name == path:
                continue
            if isinstance(key, Prefix):
                name = _remove_trailing_slash(_strip_path(key.name, path))
                key_name = _remove_trailing_slash(key.name)
                directories.append((name, key_name, True, 0, 0))
            else:
                last_modified = int(dateutil.parser.parse(key.last_modified)
                                    .strftime('%s'))
                name = _strip_path(key.name, path)
                files.append((name, key.name, False, key.size, last_modified))
        return directories + files

    def _get_bucket_list_prefix(self, path):
        parts = path.split('/')
        if len(parts) == 1:
            search = ''
        else:
            search = '/'.join(parts[:-1]) + '/'
        return search

    def _get_path_keys(self, path):
        search = self._get_bucket_list_prefix(path)
        return {key.name for key in self.bucket.list(search, '/')}

    def is_dir(self, path):
        keys = self._get_path_keys(path)
        return path + '/' in keys

    def path_exists(self, path):
        if path == '':
            return True
        keys = self._get_path_keys(path)
        return path in keys or path + '/' in keys

    def get_base_path(self):
        return ''

    def get_breadcrumbs(self, path):
        accumulator = []
        breadcrumbs = []
        for n in path.split('/'):
            accumulator.append(n)
            breadcrumbs.append((n, '/'.join(accumulator)))
        return breadcrumbs

    def send_file(self, file_path):
        key = self.bucket.get_key(file_path)
        if key is None:
            raise ValueError()
        return redirect(key.generate_url(3600))

    def save_file(self, path, file_data):
        key = Key(self.bucket, path)
        key.set_contents_from_file(file_data.stream)

    def delete_tree(self, directory):
        self._check_empty_directory(directory)
        self.bucket.delete_key(directory + '/')

    def delete_file(self, file_path):
        self.bucket.delete_key(file_path)

    def make_dir(self, path, directory):
        dir_path = '/'.join([path, directory + '/'])
        key = Key(self.bucket, dir_path)
        key.set_contents_from_string('')

    def _check_empty_directory(self, path):
        if not self._is_directory_empty(path):
            raise ValueError(gettext('Cannot operate on non empty directories'))
        return True

    def rename_path(self, src, dst):
        if self.is_dir(src):
            self._check_empty_directory(src)
            src += '/'
            dst += '/'
        self.bucket.copy_key(dst, self.bucket.name, src)
        self.delete_file(src)

    def _is_directory_empty(self, path):
        keys = self._get_path_keys(path + '/')
        return len(keys) == 1
