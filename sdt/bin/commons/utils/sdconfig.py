#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

##################################
#  @program        synda
#  @description    climate models data transfer program
#  @copyright      Copyright (c)2009 Centre National de la Recherche Scientifique CNRS.
#                             All Rights Reserved�
#  @license        CeCILL (https://raw.githubusercontent.com/Prodiguer/synda/master/sdt/doc/LICENSE)
##################################

"""This module contains paths and configuration parameters."""

import os
import sys
import uuid
import argparse

from sdt.bin.sdconst import *
from sdt.bin.commons.utils.sdexception import SDException
from sdt.bin.commons.utils import sdcfbuilder
from sdt.bin.commons.utils import sdcfloader
from sdt.bin.commons.utils import sdconfigutils
from sdt.bin.commons.utils import sdtools
from sdt.bin.sdsetuputils import PostInstallCommand, EnvInit


def get_security_dir():
    if security_dir_mode == SECURITY_DIR_TMP:
        security_dir = "{}/.esg".format(tmp_folder)
    elif security_dir_mode == SECURITY_DIR_TMPUID:
        security_dir = "{}/{}/.esg".format(tmp_folder, str(os.getuid()))
    elif security_dir_mode == SECURITY_DIR_HOME:
        if 'HOME' not in os.environ:
            raise SDException('SDCONFIG-120', "HOME env. var. must be set when 'security_dir_mode' is set to {}".format(
                SECURITY_DIR_HOME))
        security_dir = "{}/.esg".format(os.environ['HOME'])
    elif security_dir_mode == SECURITY_DIR_MIXED:
        wia = sdtools.who_am_i()
        if wia == 'ihm':
            if 'HOME' not in os.environ:
                raise SDException('SDCONFIG-121',
                                  "HOME env. var. must be set when 'security_dir_mode' is set to {} "
                                  "in a IHM context".format(SECURITY_DIR_MIXED))
            security_dir = "{}/.esg".format(os.environ['HOME'])
        elif wia == 'daemon':
            security_dir = "{}/.esg".format(tmp_folder)
        else:
            assert False
    else:
        raise SDException('SDCONFIG-020', "Incorrect value for security_dir_mode ({})".format(security_dir_mode))

    return security_dir


def get_default_limit(command):
    return DEFAULT_LIMITS[default_limits_mode][command]


def get_path(name, default_value):
    path = config.get('core', name)
    if len(path) > 0:
        return path
    else:
        return default_value


def get_project_default_selection_file(project):
    path = "{}/default_{}.txt".format(default_folder, project)
    return path


def check_path(path):
    if not os.path.exists(path):
        raise SDException("SDCONFIG-014", "Path not found ({})".format(path))


def print_(name):
    if name is None:
        # print all configuration parameters

        sdtools.print_module_variables(globals())
    else:
        # print given configuration parameter

        if name in globals():
            print(globals()[name])
        else:
            print('No configuration entry found by the name {}'.format(name))


def is_openid_set():
    if openid == 'https://esgf-node.ipsl.fr/esgf-idp/openid/foo':
        return False
    else:
        return True


def is_event_enabled(event, project):
    if event == EVENT_FILE_COMPLETE:
        return False
    elif event == EVENT_VARIABLE_COMPLETE:
        if project == 'CMIP5':
            return False  # CMIP5 use special output12 event
        else:
            return True


# def module_init():
# Init module.
os.umask(0o002)

# set synda folders paths (aka install-folders)
# TODO this should become default behavior
if 'ST_HOME' not in os.environ:
    raise SDException('SDCONFIG-010', "'ST_HOME' is not set")

synda_home_folder = sdconfigutils.SourceInstallPaths(os.environ['ST_HOME'])

# set user folders
if not sdtools.is_file_read_access_OK(synda_home_folder.credential_file):
    # if we are here, it means we have NO access to the machine-wide credential file.
    # Running Environment initialization script and warning user.
    print('Synda has issues reaching your credential file, in ST_HOME.')
    print('Running synda checking environment tool...')
    pic = PostInstallCommand()
    environment_check = pic.run()
    if not environment_check:
        initenv = raw_input('Synda environment needs a few key files. \n'
                            'Would you like to init the stubs of these files? y/n: ').lower()
        while initenv == '' or initenv not in ['y', 'n']:
            initenv = raw_input('Synda environment needs a few key files. \n'
                                'Would you like to init the stubs of these files? y/n: ').lower()
        if initenv == 'y':
            ei = EnvInit()
            ei.run()
        else:
            sys.exit('Warning: Environment not set up for synda to operate properly. Exiting.')

# aliases
bin_folder = synda_home_folder.bin_folder
tmp_folder = synda_home_folder.tmp_folder
log_folder = synda_home_folder.log_folder
conf_folder = synda_home_folder.conf_folder
#
default_selection_folder = synda_home_folder.default_selection_folder
default_db_folder = synda_home_folder.default_db_folder
default_data_folder = synda_home_folder.default_data_folder
default_sandbox_folder = synda_home_folder.default_sandbox_folder
#
default_folder_default_path = synda_home_folder.default_folder_default_path
configuration_file = synda_home_folder.configuration_file
credential_file = synda_home_folder.credential_file

stacktrace_log_file = "/tmp/sdt_stacktrace_{}.log".format(str(uuid.uuid4()))

daemon_pid_file = "{}/daemon.pid".format(tmp_folder)
ihm_pid_file = "{}/ihm.pid".format(tmp_folder)

# check_path(bin_folder)

prevent_daemon_and_modification = False  # prevent modification while daemon is running
prevent_daemon_and_ihm = False  # prevent daemon/IHM concurrent accesses
prevent_ihm_and_ihm = False  # prevent IHM/IHM concurrent accesses

log_domain_inconsistency = True  # this is to prevent flooding log file with domain message during debugging session
# (i.e. set it to false when debugging).
print_domain_inconsistency = True  # If true, domain inconsistencies are printed on stderr

dataset_filter_mecanism_in_file_context = 'dataset_id'  # dataset_id | query

max_metadata_parallel_download_per_index = 3
sdtc_history_file = os.path.expanduser("~/.sdtc_history")

metadata_parallel_download = False
http_client = 'wget'  # wget | urllib

# note that variable below only set which low_level mecanism to use to find the nearest
# (i.e. it's not an on/off flag (the on/off flag is the 'nearest' selection file parameter))
nearest_schedule = 'post'  # pre | post

unknown_value_behaviour = 'error'  # error | warning

mono_host_retry = False
proxymt_progress_stat = False
poddlefix = True
lowmem = True
fix_encoding = False
twophasesearch = False  # Beware before enabling this: must be well tested/reviewed as it seems
# to currently introduce regression.
stop_download_if_error_occurs = False  # If true, stop download if error occurs during download,
# if false, the download continue. Note that in the case of a certificate renewal
# error, the daemon always stops not matter if this false is true or false.

config = sdcfloader.load(configuration_file, credential_file)

# alias
#
# Do not move me upward nor downward
# ('security_dir_mode' must be defined before any call to the get_security_dir() func, and config must be defined)
#
security_dir_mode = config.get('core', 'security_dir_mode')

# Set location of ESGF X.509 credential
esgf_x509_proxy = os.path.join(get_security_dir(), 'credentials.pem')
esgf_x509_cert_dir = os.path.join(get_security_dir(), 'certificates')

# aliases (indirection to ease configuration parameter access)
openid = config.get('esgf_credential', 'openid')
password = config.get('esgf_credential', 'password')
progress = config.getboolean('interface', 'progress')
download = config.getboolean('module', 'download')
metadata_server_type = config.get('core', 'metadata_server_type')
url_max_buffer_size = config.get('download', 'url_max_buffer_size')

default_folder = get_path('default_path', default_folder_default_path)
selection_folder = get_path('selection_path', default_selection_folder)
db_folder = get_path('db_path', default_db_folder)
data_folder = get_path('data_path', default_data_folder)
sandbox_folder = get_path('sandbox_path', default_sandbox_folder)

data_download_script_http = "{}/sdget.sh".format(bin_folder)
data_download_script_gridftp = "{}/sdgetg.sh".format(bin_folder)

cleanup_tree_script = "{}/sdcleanup_tree.sh".format(bin_folder)

default_selection_file = "{}/default.txt".format(default_folder)
db_file = "{}/sdt.db".format(db_folder)

files_dest_folder_for_get_subcommand = None

default_limits_mode = config.get('interface', 'default_listing_size')

# Set default type (File | Dataset | Variable)
sdtsaction_type_default = SA_TYPE_FILE if metadata_server_type == 'apache_default_listing' else SA_TYPE_DATASET

# Note
#     When set to xml, 'lxml' package is required (must be added both in install.sh and in requirements.txt)
searchapi_output_format = SEARCH_API_OUTPUT_FORMAT_JSON

# if set to True, automatically switch to the next url if error occurs (e.g. move from gridftp url to http url)
next_url_on_error = config.getboolean('download', 'http_fallback')

show_advanced_options = False

# when true, allow fast cycle for test (used for UAT)
fake_download = False

copy_ds_attrs = False

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--name', default=None,
                        help='Name of the parameter to be displayed (if not set, all parameters are displayed)')
    args = parser.parse_args()

    print_(args.name)