# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2011 Justin Santa Barbara
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""Utilities and helper functions."""
from __future__ import print_function
from __future__ import division
from __future__ import absolute_import

import contextlib
import functools
import json
import os
import shutil
import tempfile

from oslo_config import cfg
from oslo_log import log as logging
import six

LOG = logging.getLogger(__name__)

utils_opts = [
    cfg.StrOpt('tempdir',
               help='Explicitly specify the temporary working directory'),
]
CONF = cfg.CONF
CONF.register_opts(utils_opts)


# Note(thread-safety): blocking function
@contextlib.contextmanager
def tempdir(**kwargs):
    argdict = kwargs.copy()
    if 'dir' not in argdict:
        argdict['dir'] = CONF.tempdir
    tmpdir = tempfile.mkdtemp(**argdict)
    try:
        yield tmpdir
    finally:
        try:
            shutil.rmtree(tmpdir)
        except OSError as e:
            LOG.error(_('Could not remove tmpdir: %s'), e)


def value_to_congress(value):
    if isinstance(value, six.string_types):
        # TODO(ayip): This throws away high unicode data because congress does
        # not have full support for unicode yet.  We'll need to fix this to
        # handle unicode coming from datasources.
        try:
            six.text_type(value).encode('ascii')
        except UnicodeEncodeError:
            LOG.warning('Ignoring non-ascii characters')
        # Py3: decode back into str for compat (bytes != str)
        return six.text_type(value).encode('ascii', 'ignore').decode('ascii')
    # Check for bool before int, because True and False are also ints.
    elif isinstance(value, bool):
        return str(value)
    elif (isinstance(value, six.integer_types) or
          isinstance(value, float)):
        return value
    return str(value)


# Note(thread-safety): blocking function
def create_datasource_policy(bus, datasource, engine):
    # Get the schema for the datasource using
    # Note(thread-safety): blocking call
    schema = bus.rpc(datasource, 'get_datasource_schema',
                     {'source_id': datasource})
    # Create policy and sets the schema once datasource is created.
    args = {'name': datasource, 'schema': schema}
    # Note(thread-safety): blocking call
    bus.rpc(engine, 'initialize_datasource', args)


def get_root_path():
    return os.path.dirname(os.path.dirname(__file__))


def removed_in_dse2(wrapped):
    @functools.wraps(wrapped)
    def wrapper(*args, **kwargs):
        if cfg.CONF.distributed_architecture:
            LOG.error('%s is called in dse2', wrapped.__name__)
            raise Exception('inappropriate function is called.')
        else:
            return wrapped(*args, **kwargs)
    return wrapper


class Location (object):
    """A location in the program source code."""

    __slots__ = ['line', 'col']

    def __init__(self, line=None, col=None, obj=None):
        try:
            self.line = obj.location.line
            self.col = obj.location.col
        except AttributeError:
            pass
        self.col = col
        self.line = line

    def __str__(self):
        s = ""
        if self.line is not None:
            s += " line: {}".format(self.line)
        if self.col is not None:
            s += " col: {}".format(self.col)
        return s

    def __repr__(self):
        return "Location(line={}, col={})".format(
            repr(self.line), repr(self.col))

    def __hash__(self):
        return hash(('Location', hash(self.line), hash(self.col)))


def pretty_json(data):
    print(json.dumps(data, sort_keys=True,
                     indent=4, separators=(',', ': ')))
