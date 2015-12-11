import os
import shutil
import os.path as op
import platform
import re

from datetime import datetime
from operator import itemgetter
from werkzeug import secure_filename

from flask import flash, redirect, abort, request, send_file

from wtforms import fields, validators

from flask_admin import form, helpers
from flask_admin._compat import urljoin, as_unicode
from flask_admin.base import BaseView, expose
from flask_admin.actions import action, ActionsMixin
from flask_admin.babel import gettext, lazy_gettext
from flask_admin.contrib.fileadmin.base import BaseFileAdmin


class LocalFileAdmin(BaseFileAdmin):

    def __init__(self, base_path, *args, **kwargs):
        super(LocalFileAdmin, self).__init__(base_path, *args, **kwargs)

        self.directory_separator = os.sep

        # Check if path exists
        if not self.path_exists(base_path):
            raise IOError('FileAdmin path "%s" does not exist or is not accessible' % base_path)

    def get_files(self, path, directory):
        items = []
        for f in os.listdir(directory):
            fp = op.join(directory, f)
            rel_path = op.join(path, f)

            if self.is_accessible_path(rel_path):
                is_dir = self.is_dir(fp)
                last_modified = op.getmtime(fp)
                if is_dir:
                    last_modified = 0
                items.append((f, rel_path, is_dir, op.getsize(fp),
                              last_modified))
        return items

    def make_dir(self, path, directory):
        os.mkdir(op.join(path, directory))

    def delete_tree(self, directory):
        shutil.rmtree(directory)

    def delete_file(self, file_path):
        os.remove(file_path)

    def rename_path(self, src, dst):
        os.rename(src, dst)

    def path_exists(self, path):
        return op.exists(path)

    def is_dir(self, path):
        return op.isdir(path)

    def get_breadcrumbs(self, path):
        accumulator = []
        breadcrumbs = []
        for n in path.split(os.sep):
            accumulator.append(n)
            breadcrumbs.append((n, op.join(*accumulator)))
        return breadcrumbs

    def send_file(self, file_path):
        return send_file(file_path)

    def save_file(self, path, file_data):
        file_data.save(path)
