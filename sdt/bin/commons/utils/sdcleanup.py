#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

##################################
#  @program        synda
#  @description    climate models data transfer program
#  @copyright      Copyright (c)2009 Centre National de la Recherche Scientifique CNRS.
#                             All Rights Reserved
#  @license        CeCILL (https://raw.githubusercontent.com/Prodiguer/synda/master/sdt/doc/LICENSE)
##################################

"""
Contains directory cleanup routines.
"""

import os
from sdt.bin.commons.utils import sdconfig
from sdt.bin.commons.utils import sdlog
from sdt.bin.commons.utils import sdtools
from sdt.bin.commons.utils import sdutils
from sdt.bin.commons.utils.sdexception import SDException


def ignore(f):
    if f.endswith('.nc'):
        return False
    else:
        return True


def remove_empty_files(path):
    for p in sdtools.walk_backward_without_sibling(path):
        for name in os.listdir(p):
            f = '{}/{}'.format(p, name)
            # this is not to remove files at top of the tree, not related with synda
            # (e.g. every hidden file in HOME dir)
            if not ignore(f):
                if os.path.isfile(f):
                    if not os.path.islink(f):
                        if os.path.getsize(f) == 0:
                            try:
                                sdlog.info("SYNCLEAN-090", "Remove empty file ({})".format(f))
                                os.remove(f)
                            except Exception as e:
                                sdlog.warning("SYNCLEAN-040",
                                              "Error occurs during file deletion ({},{})".format(f, str(e)))


def full_cleanup():
    """Remove empty files and folders."""

    sdlog.info("SYNCLEAN-008", "Starting cleanup in {}.".format(sdconfig.data_folder))

    argv = [sdconfig.cleanup_tree_script, sdconfig.data_folder]

    (status, stdout, stderr) = sdutils.get_status_output(argv)
    if status != 0:
        sdtools.trace(sdconfig.stacktrace_log_file, os.path.basename(sdconfig.cleanup_tree_script), status, stdout,
                      stderr)
        raise SDException("SYNCLEAN-001", "Error occurs during tree cleanup")

    sdlog.info("SYNCLEAN-010", "Cleanup done.")


def part_cleanup(paths):
    """Remove empty files and folders."""

    sdlog.info("SYNCLEAN-018", "Cleanup begin")
    # maybe overkill (idea is that reverse order may allow the suppression of empty sibling,
    # but as all paths to be removed will go through a os.removedirs call it should work anyway)
    paths = sorted(paths, reverse=True)
    for p in paths:
        sdlog.info("SYNCLEAN-060", "Check for empty file and directory in {}".format(p))

        # remove empty files
        sdlog.debug("SYNCLEAN-120", "Remove empty files ({})".format(p))
        remove_empty_files(p)

        # remove empty directories starting from leaves
        sdlog.debug("SYNCLEAN-140", "Remove empty dirs ({})".format(p))
        try:
            os.removedirs(p)
        except OSError as e:
            pass  # Neutralize exception (needed as removedirs raise exception at first non empty dir).

    # as the previous command may also remove 'data' folder (when all data have been removed),
    # we re-create 'data' if missing
    if not os.path.isdir(sdconfig.data_folder):
        os.makedirs(sdconfig.data_folder)
    sdlog.info("SYNCLEAN-020", "Cleanup done.")
