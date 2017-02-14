#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

##################################
# @program        synda
# @description    climate models data transfer program
# @copyright      Copyright “(c)2009 Centre National de la Recherche Scientifique CNRS. 
#                            All Rights Reserved”
# @license        CeCILL (https://raw.githubusercontent.com/Prodiguer/synda/master/sdt/doc/LICENSE)
##################################
 
"""This module contains delete functions."""

import sys
import os
import json
import sdapp
import sddao
import sdfiledao
import argparse
import sdconst
import sdlog
import sddeletequery
import sddb
import sdfilequery

def delete_transfers(limit=None,remove_all=True):
    """
    Returns
        how many files with TRANSFER_STATUS_DELETE status remain

    Note
        'limit' is used to delete only a subset of all files marked for
        deletion each time this func is called. If 'limit' is None,
        all files marked for deletion are removed.
    """
    transfer_list=sdfiledao.get_files(status=sdconst.TRANSFER_STATUS_DELETE,limit=limit)

    for tr in transfer_list:
        if remove_all:
            immediate_delete(tr)
        else:
            immediate_md_delete(tr)

    sddb.conn.commit() # final commit (we do all deletion in one transaction).

    return sdfilequery.transfer_status_count(status=sdconst.TRANSFER_STATUS_DELETE)

def deferred_delete(file_functional_id):
    f=sdfiledao.get_file(file_functional_id)

    f.status=sdconst.TRANSFER_STATUS_DELETE
    f.error_msg=None
    f.sdget_status=None
    f.sdget_error_msg=None

    sdfiledao.update_file(f,commit=False)

def immediate_delete(tr):
    """Delete file (metadata and data).

    Notes
        - This method remove files but not directories (directories are removed in "cleanup.sh" script)
    """
    sdlog.info("SDDELETE-055","Delete transfer (%s)"%tr.get_full_local_path())

    if os.path.isfile(tr.get_full_local_path()):
        try:
            os.remove(tr.get_full_local_path())
            # note: if data cannot be removed (i.e. exception is raised), we don't remove metadata
            sdfiledao.delete_file(tr,commit=False)

        except Exception,e:
            sdlog.error("SDDELETE-528","Error occurs during file suppression (%s,%s)"%(tr.get_full_local_path(),str(e)))
    else:
        if tr.status == sdconst.TRANSFER_STATUS_DONE:
            # this case is not normal as the file should exist on filesystem when status is done

            sdlog.error("SDDELETE-123","Can't delete file: file not found (%s)"%tr.get_full_local_path())
        else:
            # this case is for 'waiting' and 'error' status (in these cases, data do not exist, so we just remove metadata)

            sdfiledao.delete_file(tr,commit=False)

def immediate_md_delete(tr):
    """Delete file (metadata only) """
    sdlog.info("SDDELETE-080","Delete metadata (%s)"%tr.get_full_local_path())
    try:
        sdfiledao.delete_file(tr,commit=False)
    except Exception,e:
        sdlog.error("SDDELETE-128","Error occurs during file metadata suppression (%s,%s)"%(tr.get_full_local_path(),str(e)))

def reset():
    import sddeletedataset

    nbr=sddeletequery.purge_error_and_waiting_transfer()
    sddeletedataset.purge_orphan_datasets()

    sdlog.info("SDDELETE-931","%i transfer(s) removed"%nbr)
    return nbr

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    args = parser.parse_args()