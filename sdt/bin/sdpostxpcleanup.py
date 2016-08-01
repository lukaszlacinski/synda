#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

##################################
#  @program        synda
#  @description    climate models data transfer program
#  @copyright      Copyright “(c)2009 Centre National de la Recherche Scientifique CNRS. 
#                             All Rights Reserved”
#  @license        CeCILL (https://raw.githubusercontent.com/Prodiguer/synda/master/sdt/doc/LICENSE)
##################################

"""This module perform post xml parsing filtering.

Description
    - File rejection step 1 (file rejection step 2 is done by sdreducerow module)

Note
    sdpostxpcleanup means 'SynDa post Xml Parsing cleanup'

TODO
    - In the future, move/merge this module to/with sdreducerow module.
"""

from sdexception import SDException
import sdconfig
import sdlog

def run(files):
    (keep,reject)=filter(files)

    if len(reject)>0:
        sdlog.info("SDPOSXPC-001","%i anomalies found"%len(reject))

    return keep

def filter(files):
    keep=[]
    reject=[]

    if len(files)>0:

        # retrieve type
        file_=files[0]      # 'type' is the same for all files
        type_=file_['type'] # 'type' itself IS scalar

        if type_=='File':

            for f in files:

                variable=f.get('variable',[])
                assert isinstance(variable,list)

                if len(variable)==1:
                    keep.append(f)
                else:
                    reject.append(f)

                    if sdconfig.log_domain_inconsistency:
                        sdlog.warning("SDPOSXPC-002","WARNING: 'variable' attribute contains too much values ('%s')."%f['id'],stderr=False)

        elif type_=='Dataset':
            # currently, there is no reject rules for Dataset type, so we keep all of them

            for f in files:
                keep.append(f)

    return (keep,reject)
