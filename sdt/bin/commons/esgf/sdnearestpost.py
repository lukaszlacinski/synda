#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

##################################
#  @program        synda
#  @description    climate models data transfer program
#  @copyright      Copyright (c)2009 Centre National de la Recherche Scientifique CNRS.
#                             All Rights Reserved
#  @license        CeCILL (https://raw.githubusercontent.com/Prodiguer/synda/master/sdt/doc/LICENSE)
##################################

"""This filter select the nearest replica using geolocation routines.

Notes
    - This filter do the same job as 'sdnearestpre' filter, except it operates
      in the 'file pipeline' instead of the 'query pipeline'.
    - This module is called 'sdnearestpost' as it operates post-call (i.e. after the search-API call).
    - This module can be used to process different metadata types (File and Dataset).
"""
from sdt.bin.commons.esgf import sdnearestutils
from sdt.bin.commons.pipeline import sdpostpipelineutils
from sdt.bin.commons.pipeline import sdpipelineprocessing

from sdt.bin.commons.utils import sdlog
from sdt.bin.commons.utils import sdconfig
from sdt.bin.commons.utils.sdexception import SDException
from sdt.bin.commons.facets import sdlmattrfilter

RTT_cache = {}
GEO_cache = {}


def run(metadata):
    if metadata.count() < 1:
        return metadata

    # retrieve global flag
    f = metadata.get_one_file()
    functional_id_keyname = sdpostpipelineutils.get_functional_identifier_name(f)
    # create light list with needed columns only, not to overload system memory.
    light_metadata = sdlmattrfilter.run(metadata, [functional_id_keyname, 'data_node'])
    score = build_score_table(light_metadata, functional_id_keyname)  # warning: load list in memory

    # filtering to keep nearest datanode
    for id in score:
        datanodes = score[id]
        dn = get_nearest_dn(datanodes)
        score[id] = dn  # replace list with scalar

    # at this point, 'score' table is in the form: [id]=dn

    # 'score' data structure transformation
    score = dict(((k, score[k]), False) for k in score)  # warning: two list in memory simultaneously !

    # at this point, 'score' table is in the form: [(id,dn)]=False

    # final filtering (come back to files list)
    po = sdpipelineprocessing.ProcessingObject(keep_nearest_file, functional_id_keyname, score)
    metadata = sdpipelineprocessing.run_pipeline(metadata, po)

    return metadata


def keep_nearest_file(files, functional_id_keyname, score):
    new_files = []

    for f in files:
        id_ = f[functional_id_keyname]
        dn = f['data_node']
        if (id_, dn) in score:  # add the nearest replicate
            # prevent adding duplicate (memo: duplicate != replicate). i.e.
            # some exact same file may be present multiple time in the list (see 'Type-A' in sdshrink for more info).
            if not score[(id_, dn)]:
                new_files.append(f)
                score[(id_, dn)] = True

    return new_files


def build_score_table(light_metadata, functional_id_keyname):
    score = {}

    for f in light_metadata.get_files():  # warning: load list in memory
        key = f[functional_id_keyname]
        dn = f['data_node']
        if key in score:
            if dn not in score[key]:  # prevent exact duplicate if any (i.e. duplicate NOT replicate)
                score[key].append(dn)
        else:
            score[key] = [dn]

    return score


def old_algo(files):
    """
    Note
        Use a lot of memory.

    Not used.
    """
    new_files = {}

    for f in files:
        id_ = sdpostpipelineutils.get_functional_identifier_value(f)
        if id_ in new_files:
            # there is a previous instance of this file (e.g. another replica)

            if compare_file(f, new_files[id_]):
                new_files[id_] = f  # replace as 'f' is the nearest
        else:
            new_files[id_] = f

    return new_files.values()


def get_nearest_dn(datanodes):
    nearest = datanodes[0]
    for d in datanodes:
        if compare_dn(d, nearest):
            nearest = d  # replace as d is the nearest of the two
    return nearest


def compare_file(f1, f2):
    return compare_dn(f1['data_node'], f2['data_node'])


def compare_dn(datanode_1, datanode_2):
    mode = sdconfig.config.get('behaviour', 'nearest_mode')

    if mode == 'geolocation':
        return get_distance(datanode_1) < get_distance(datanode_2)
    elif mode == 'rtt':
        return get_rtt(datanode_1) < get_rtt(datanode_2)
    else:
        raise SDException("SDNEARES-001", "Incorrect nearest mode (%s)" % mode)


def get_rtt(remote_host):
    if remote_host not in RTT_cache:
        sdlog.info("SDNEARES-012", "Compute RTT for '{}' host.".format(remote_host))
        RTT_cache[remote_host] = compute_rtt(remote_host)

    return RTT_cache[remote_host]


def get_distance(remote_host):
    if remote_host not in GEO_cache:
        GEO_cache[remote_host] = compute_distance(remote_host)

    return GEO_cache[remote_host]


def compute_distance(remote_host):
    """Returns distance between the client and the file (i.e. the file's datanode)."""
    client_place = sdnearestutils.get_client_place()  # our location
    datanode_place = sdnearestutils.get_datanode_place(remote_host)
    distance = sdnearestutils.compute_distance(client_place, datanode_place)
    return distance


def compute_rtt(remote_host, count=1):
    """
    Args
        count: how many ping used to compute the average Round Trip Time
    """
    rtt = 0.0
    try:
        (status, stdout, stderr) = sdutils.get_status_output('ping -q -c {} {}'.format(count, remote_host), shell=True)
        if status == 0:
            m = re.search('.*min/avg/max/mdev = ([0-9.]+)/([0-9.]+)/([0-9.]+)/([0-9.]+) ms.*', stdout,
                          re.MULTILINE | re.DOTALL)
            if m:
                rtt = float(m.group(2))
            else:
                raise SDException("SYNDARTT-001", "'ping' output parsing error ({})".format(stdout))
        else:
            raise SDException("SYNDARTT-002",
                              "'ping' command failed (remote_host={},status={})".format(remote_host, status))
    except SDException as e:
        if e.code == 'SYNDARTT-002':
            # when here, it means no response from host

            sdlog.info("SDNEARES-006", "No reply to ICMP request (ping) from '{}' host.".format(remote_host))

            # in this case, we return a high RTT to prevent using this host

            return 20000.0  # 20 seconds
        else:
            raise
    return rtt