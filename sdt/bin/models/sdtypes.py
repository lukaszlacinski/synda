#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

##################################
#  @program        synda
#  @description    climate models data transfer program
#  @copyright      Copyright (c)2009 Centre National de la Recherche Scientifique CNRS.
#                             All Rights Reserved
#  @license        CeCILL (https://raw.githubusercontent.com/Prodiguer/synda/master/sdt/doc/LICENSE)
##################################

"""This module contains core classes.

Note
    This module contains only instantiable classes (i.e. no static class)
"""

import os
import sys
import re
import copy
import json

from sdt.bin.commons.utils import sdconfig
from sdt.bin.commons.utils import sdconst
from sdt.bin.commons.utils import sdtools
from sdt.bin.commons.utils import sdmts
from sdt.bin.commons.utils.sdexception import SDException


def build_full_local_path(local_path, prefix=sdconfig.data_folder):
    add_prefix = True

    if len(local_path) > 0:
        if local_path[0] == '/':
            add_prefix = False

    if add_prefix:
        path = os.path.join(prefix, local_path)
    else:
        path = local_path

    return path


class Variable():
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)


class Event():
    def __init__(self, **kwargs):
        self.status = sdconst.EVENT_STATUS_NEW
        self.__dict__.update(kwargs)

    def __str__(self):
        return self.name


class Buffer():
    def __init__(self, **kw):
        # outer attributes
        self.filename = kw['filename']  # filename
        self.path = kw['path']  # file path (including filename)

        # inner attributes
        self.lines = kw.get('lines', [])

    def __str__(self):
        return ",".join(['{}={}'.format(k, str(v)) for (k, v) in self.__dict__.items()])


class Selection():
    def __init__(self, **kw):
        self.childs = []  # sub-selections list (a selection can contain facets groups, but can also contain other selections)
        self.parent = None  # parent selection (a selection can be the parent of another selection (e.g. default selection is the parent of project default selection))

        # inner attributes
        self.facets = kw.get("facets", {})  # contains search-API facets

        # outer attributes
        self.filename = kw.get("filename")  # selection filename
        self.path = kw.get("path")  # selection file path (fullpath)
        self.selection_id = kw.get("selection_id")  # database identifier
        self.checksum = kw.get("checksum")
        self.status = kw.get("status")

    def __str__(self):
        return "filename={}\nfacets={}".format(self.filename, self.facets)

    def get_root(self):
        """
        Returns
            top level selection (i.e. default selection)
        """
        if self.parent is None:
            return self
        else:
            return self.parent.get_root()

    def merge_facets(self):
        """This func merge facets starting from root level."""
        return self.get_root().merge_facets_downstream()

    def to_stream(self):
        """Alias."""
        return self.merge_facets()

    def merge_facets_downstream(self):
        """Merge and return facets corresponding to this selection

        This func merge facets of this selection and all descendant selections,
        down the selections tree.

        Returns
            facets_groups (List)

        note
            recursive func
        """

        if len(self.childs) > 0:
            # processes sub-selection (Synda specific realm&freq&vars lines (e.g. variables[atmos][mon]="tas psl")).
            #
            # notes
            #  - if some facets exist in both place (in sub-selection and in main selection),
            #    sub-selection ones override main selection ones (in update() method below)
            #  - a new query (aka facets group) is created for each line.
            #  - we can't retrieve all frequencies/realms in one search-API call because variables are grouped by realm/frequency..

            # beware: tricky code
            #
            # we need to recursively override parent parameters with child
            # parameter.  so we need create a copy of parent facets (and then
            # update it with child facets), for each child and for each facets
            # group.
            #
            facets_groups = []
            for s in self.childs:
                for facets_group in s.merge_facets_downstream():
                    cpy = copy.deepcopy(self.facets)
                    cpy.update(facets_group)

                    facets_groups.append(cpy)

            return facets_groups

        else:
            # this loop processes main selection facets
            return [self.facets]


class BaseType():
    def get_full_local_path(self, prefix=sdconfig.data_folder):
        return build_full_local_path(self.local_path, prefix)


class File(BaseType):
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)

    def __str__(self):
        if self.status == sdconst.TRANSFER_STATUS_ERROR:
            buf = "sdget_status={},sdget_error_msg={},error_msg='{}',file_id={},status={},local_path={},url={}".format(
            self.sdget_status, self.sdget_error_msg, self.error_msg, self.file_id, self.status,
            self.get_full_local_path(), self.url)
        else:
            buf = "file_id={},status={},local_path={},url={}".format(self.file_id, self.status,
                                                                     self.get_full_local_path(), self.url)

        return buf


class Dataset(BaseType):
    def __init__(self, **kw):
        self.__dict__.update(kw)

    def get_full_local_path_without_version(self):
        return re.sub('/[^/]+$', '', self.get_full_local_path())

    def __str__(self):
        return "".join(['{}={}\n'.format(k, v) for (k, v) in self.__dict__.items()])


class SessionParam():
    def __init__(self, name, type_=str, default_value=None, search_api_facet=True, value=None, removable=True,
                 option=True):
        self.name = name
        self.type_ = type_
        self.default_value = default_value
        self.search_api_facet = search_api_facet
        self.value = value
        self.removable = removable  # not used for now
        self.option = option  # this flag means 'is Synda specific option ?'

    def value_to_string(self):
        if self.value is None:
            # we return '' if None whatever what type is

            return ''
        else:
            if self.type_ == bool:
                return 'true' if self.value else 'false'
            elif self.type_ == int:
                return str(self.value)
            elif self.type_ == str:
                return self.value

    def set_value_from_string(self, v):
        if self.type_ == bool:
            self.value = True if v == 'true' else False
        elif self.type_ == int:
            self.value = int(v)
        elif self.type_ == str:
            self.value = v

    def __str__(self):
        return "".join(['{}={}\n'.format(k, v) for (k, v) in self.__dict__.items()])


class Parameter():
    """Contain values for one parameter."""

    def __init__(self, values=None, name=None):
        self.values = values
        self.name = name

    def exists(self, value):
        """Check if parameter value exists."""
        if value in self.values:
            return True
        else:
            return False

    def __str__(self):
        return "{}=>{}".format(self.name, str(self.values))


class Item():
    """
    Note
        This class contains parameter value, but as each value can also contains sub-value (e.g. 'count'),
        it is named 'Item' for better clarity (instead of Value).
    """

    def __init__(self, name=None, count=None):
        self.name = name  # parameter value name (i.e. different from parameter name)
        self.count = count  # do NOT remove this attribute: it is used to count files/datasets for each parameter value

    def __str__(self):
        return ",".join(['{}={}'.format(k, str(v)) for (k, v) in self.__dict__.items()])


class Request(object):
    def __init__(self, url=None, pagination=True, limit=sdconst.SEARCH_API_CHUNKSIZE):
        self._url = url
        self.pagination = pagination
        if self.pagination:
            if sdtools.url_contains_limit_keyword(self._url):
                raise SDException("SDATYPES-008", "assert error (url={})".format(self._url))
        self.offset = 0
        self.limit = limit

    def get_limit_filter(self):
        if self.pagination:
            # pagination enabled

            return "&limit={}".format(self.limit)
        else:
            # pagination disabled
            # (in this mode, limit can be set to reduce the number of returned result)

            if sdtools.url_contains_limit_keyword(self._url):
                return ""  # return void here as already set in the url
            else:
                return "&limit={}".format(self.limit)

    def get_offset_filter(self):
        return "&offset={}".format(self.offset)

    def get_url(self):
        url = "{0}{1}{2}".format(self._url, self.get_limit_filter(), self.get_offset_filter())

        if sdconst.IDXHOSTMARK in url:
            raise SDException('SDATYPES-004', 'host must be set at this step (url={})'.format(url))

        # we limit buffer size as apache server doesnt support more than 4000 chars for HTTP GET buffer
        if len(url) > int(sdconfig.url_max_buffer_size):
            raise SDException("SDATYPES-003", "url is too long ({})".format(len(url)))
        return url

    @staticmethod
    def _serialize(self, param_name, values):
        """Serialize one parameter.

        Example
          input
            param_name="variable"
            values="tasmin,tasmax"
          output
            "&variable=tasmin&variable=tasmax"
        """
        l = []
        for v in values:
            l.append(param_name + "=" + v)

        if len(l) > 0:
            return "&" + "&".join(l)
        else:
            return ""

    def __str__(self):
        return ",".join(['{}={}'.format(k, str(v)) for (k, v) in self.__dict__.items()])


class CommonIO(object):
    """Abstract."""

    def __init__(self, *args, **kwargs):
        lowmem = kwargs.get('lowmem', sdconfig.lowmem)  # note that if store is not None, lowmem have no effect

        files = kwargs.get("files", None)
        store = kwargs.get('store', None)

        assert not (files is not None and store is not None)

        if files is not None:
            self.store = sdmts.get_new_store(lowmem)
            self.store.set_files(files)  # Files (key/value attribute based files list)
            self.size = compute_total_size(files)
        elif store is not None:
            # passing 'store' as argument is only used for internal operation (e.g. copy)

            self.store = store
            self.size = kwargs.get('size', None)

            assert self.size is not None  # size must be given if store is given
        else:
            self.store = sdmts.get_new_store(lowmem)
            self.size = 0

    def __del__(self):
        """Destructor

        Calls 'delete' when object is garbage collected.
        """

        self.delete()

    def count(self):
        return self.store.count()

    def set_files(self, files):
        self.store.set_files(files)
        self.size = compute_total_size(files)

    def add_files(self, files):
        assert isinstance(files, list)
        self.store.append_files(files)
        self.size += compute_total_size(files)

    def get_files(self):  # warning: load list in memory
        return self.store.get_files()

    def get_chunks(self, io_mode=sdconst.PROCESSING_FETCH_MODE_GENERATOR):
        assert not isinstance(self.store, list)
        return self.store.get_chunks(io_mode)

    def delete(self):
        self.store.delete()

    def get_one_file(self):
        return self.store.get_one_file()

    def connect(self):
        self.store.connect()

    def disconnect(self):
        self.store.disconnect()


def compute_total_size(files):
    if len(files) > 0:
        file_ = files[0]  # assume all items are of the same type

        # FIXME: remove this block
        if 'size' not in file_:
            return 0
        else:
            return sum(int(f['size']) for f in files)

        # FIXME: use this block instead
        # test with: synda search CMIP5 decadal1995 mon land
        """
        type_=file_.get('type')
        if type_=='Dataset':
            return 0
        elif type_=='File':
            return sum(int(f['size']) for f in files)
        else:
            raise SDException("SDATYPES-024","Incorrect type (type=%s)"%str(type_))
        """

    else:
        return 0


class ResponseIngester(object):
    """Abstract."""

    def slurp(self, response):
        assert isinstance(response, Response)
        self.store.append_files(
            response.get_files())  # get_files() here loads list in memory, but should work on lowmem machine as Response object never exceed SEARCH_API_CHUNKSIZE
        self.call_duration += response.call_duration
        self.size += response.size


class MetaResponse(CommonIO, ResponseIngester):
    """Abstract."""

    def __init__(self, *args, **kwargs):
        CommonIO.__init__(self, *args, **kwargs)
        self.call_duration = 0

    def to_metadata(self):
        metadata = Metadata(store=self.store.copy(), size=self.size)
        return metadata


class Metadata(CommonIO):
    """Concrete."""

    def slurp(self, metadata):
        assert isinstance(metadata, Metadata)
        self.store.merge(metadata.store)
        self.size += metadata.size

    def copy(self):
        cpy = Metadata(store=self.store.copy(), size=self.size)
        return cpy


class PaginatedResponse(MetaResponse):
    """Concrete."""

    pass


class MultiQueryResponse(MetaResponse):
    """Concrete."""

    pass


class Response(CommonIO):
    """Contains web service output after XML parsing.

    Note
        Concrete
    """

    def __init__(self, *args, **kwargs):
        CommonIO.__init__(self, *args, **kwargs)  # call base class initializer

        self.num_found = kwargs.get("num_found", 0)  # total match found in ESGF for the query
        self.call_duration = kwargs.get(
            "call_duration")  # ESGF index service call duration (if call has been paginated, then this member contains sum of all calls duration)
        self.parameter_values = kwargs.get("parameter_values",
                                           [])  # parameters list (come from the XML document footer)

        # check

        if self.num_found is None:
            raise SDException("SDATYPES-005", "assert error")

        if self.count() > sdconst.SEARCH_API_CHUNKSIZE:
            assert False

    def __str__(self):
        return "\n".join(['%s' % (f['id'],) for f in self.store.get_files()])  # warning load listin memory


_VERSION_FORMAT_SHORT = 'short'  # e.g. 'v1'
_VERSION_FORMAT_LONG = 'long'  # e.g. '20120101'
_VERSION_FORMAT_LONG_WITH_PREFIX = 'long_with_prefix'  # e.g. 'v20120101'


class DatasetVersion():
    """Dataset version object"""

    # FIXME we distinguish between versions like 20160618 or 20160619 and
    # versions like 1 or 2.
    # If a data set goes from 1 to 20160618 we see it as an error for now.
    # May change in the future (it may be handled as long as it doesn't go back to 3 for the next version. TBC)

    # FIXME If there is any overlap between those formats, the least selective
    # ones must come last.
    # For example, if /\d+/ came before /\d{8}/,
    # which_format() would identify 20160618
    # as matching /\d+/ instead of /\d{8}/.

    _dataset_version_regexp_strings = [
        # r'^v(\d{8})$',
        r'^v(\d+)$',
        # r'^(\d{8})$',
        r'^(\d+)$',
    ]

    _dataset_version_regexps = map(lambda s: re.compile(s, re.IGNORECASE), _dataset_version_regexp_strings);

    def __init__(self, version):
        self.version = version
        self._version_formats = None

    def get_version(self):
        return self.version

    def analyse(self):
        """Analyse a version string, identifying the format in which it is and
           extracting a version number (an integer) for comparing it to other
           versions. Returns the number of the regexp it matches and the
           version number or (None, None) if it matches none.
        """
        for n, re in enumerate(self._dataset_version_regexps):
            # print 'n = %d, re = "%s", self.version = "%s"' % (n, re, self.version)
            match = re.match(self.version)
            if match:
                vernum = long(match.group(0)) + 0
                vernum_str = '{}'.format(vernum)
                if vernum_str != match.group(0):  # Not supposed to happen
                    raise SDException("SDDATVER-006",
                                      'Unexpected error while extracting version number from version string "{}" with '
                                      'regexp "{}": capture "{}" converts to "{}"'
                                      .format(self.version, self._dataset_version_regexp_strings[n], match.group(0),
                                                vernum_str))
                return n, vernum

        return None, None


class DatasetVersions:
    """Manage dataset version.

    Note
        This class contains all different versions of the same dataset (contains a list of Dataset object, one for each version)
    """
    _dataset_versions = None  # contains Dataset objects

    def __init__(self):
        self._dataset_versions = []

    def add_dataset_version(self, d):
        self._dataset_versions.append(d)

    def get_datasets(self):
        return self._dataset_versions

    def count(self):
        return len(self._dataset_versions)

    def exists_version_with_latest_flag_set_to_true(self):
        for d in self._dataset_versions:
            if d.latest:
                return True

        return False

    def is_version_higher_than_latest(self, i__d):
        """ returns true if i__d version is higher than the version with latest flag set, else returns false """
        return self.compare(i__d, self.get_dataset_with_latest_flag_set())

    def get_dataset_with_latest_flag_set(self):
        for d in self._dataset_versions:
            if d.latest:
                return d

        raise SDException("SDDATVER-001", "fatal error")

    def is_most_recent_version_number(self, i__d):
        """Is i__d version the latest one.

        Note
            This method do not use the latest flag (computes from scratch)

        TODO
            Maybe rewrite this method to be based on get_latest_dataset() method (so to remove duplicate code)
        """

        # initialise with the first dataset's (may be any dataset)
        last_version = self._dataset_versions[0]

        for d in self._dataset_versions:
            if self.compare(d, last_version):
                last_version = d

        if last_version.version == i__d.version:
            return True
        else:
            return False

    def get_latest_dataset(self):
        """Return the latest dataset.

        Note
            This method do not use the latest flag (computes from scratch)
        """

        # initialise with the first dataset's (may be any dataset)
        latest_dataset = self._dataset_versions[0]

        for d in self._dataset_versions:
            if self.compare(d, latest_dataset):
                latest_dataset = d

        return latest_dataset

    def get_oldest_dataset(self):
        """Returns the oldest dataset."""

        # initialise with the first dataset's (may be any dataset)
        oldest_dataset = self._dataset_versions[0]

        for d in self._dataset_versions:
            if not self.compare(d, oldest_dataset):
                oldest_dataset = d

        return oldest_dataset

    def compare(self, d_a, d_b):
        """Returns true if d_a is more recent (higher in most case) than d_b, else false.

        Samples
            d_a.version => v20110901
            d_b.version => v1
        """
        if len(d_a.version) != len(d_b.version):

            if d_a.timestamp is not None and d_b.timestamp is not None:

                if d_a.timestamp > d_b.timestamp:
                    return True
                else:
                    return False

            else:
                # As some dataset don't have the timestamp set (e.g. obs4MIPs.PCMDI.CloudSat.mon.v1)
                # we need to fallback to the emergency solution below.

                # In some cases, dataset's timestamp cannot be set (can be
                # because the dataset version doesn't exist anymore in ESGF, or
                # because the timestamp doesn't exist for some dataset as well
                # as for dataset's file). For such cases, we use the old
                # comparaison method.
                #
                if len(d_a.version) == 9 and len(d_b.version) == 2:
                    return True
                elif len(d_a.version) == 2 and len(d_b.version) == 9:
                    return False
                else:
                    raise SDException("SDDATVER-002", "Incorrect version number ({},{})"
                                      .format(d_a.version, d_b.version))
        else:
            return d_a.version > d_b.version

    def is_short_version_format(self, version):
        if len(version) == 2:
            return True
        else:
            return False

    def is_long_version_format(self, version):
        if len(version) == 8:
            return True
        else:
            return False

    def is_long_version_with_prefix_format(self, version):
        if len(version) == 9:
            return True
        else:
            return False

    def get_dataset_versions_SORT_BY_VERSION(self):
        dataset_versions = sorted(self._dataset_versions, key=lambda dataset_version: dataset_version.version)
        return dataset_versions

    def get_sorted_versions(self):
        li = self.get_versions()
        return sorted(li)

    def get_versions(self):
        return [d.version for d in self._dataset_versions]
