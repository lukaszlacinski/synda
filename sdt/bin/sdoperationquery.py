#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

##################################
#  @program        synda
#  @description    climate models data transfer program
#  @copyright      Copyright “(c)2009 Centre National de la Recherche Scientifique CNRS. 
#                             All Rights Reserved”
#  @license        CeCILL (https://raw.githubusercontent.com/Prodiguer/synda/master/sdt/doc/LICENSE)
##################################

"""This module contains sql queries used by operational routines."""

import sdapp
import sddao
import sddatasetdao
import sdlargequery
from sdprogress import SDProgressDot

def populate_selection_transfer_junction():
    """
    populate "selection__transfer" association table

    WARNING: this method is only CMIP5 DRS compatible
    """
    sdlargequery.get_files_pagination__reset()

    transfer_without_selection=0
    transfer_without_dataset=0
    i=0
    transfers=sdlargequery.get_files_pagination() # loop over block (trick not to load 300000 CTransfer objects in memory..). Size is given by pagination_block_size
    while len(transfers)>0:
        for t in transfers:
            d=sddatasetdao.get_dataset(dataset_id=t.dataset_id)
            if d is not None:
                t.setDataset(d)
            else:
                insert_transfer_without_dataset(t)
                transfer_without_dataset+=1

                # we can't go on without dataset (contains() method needs it)
                continue

            # selection<=>transfer mapping and insertion in assoc table
            orphan=1 # this is to detect orphan transfer (i.e. don't belong to any selection)
            for us in get_Selections():

                # debug
                #print "%s<=>%s"%(t.getTransferID(),us.getSelectionID())

                if us.contains(t):

                    sddao.insert_selection_transfer_junction(t,us,_conn) # no commit inside
                    orphan=0

            if orphan==1:
                inserttransferwithoutselection(t)
                transfer_without_selection+=1


        _conn.commit() # commit block of insertSelectionTransferJunction

        # display progress
        #if i%100==0:
        SDProgressDot.print_char(".")

        i+=1



        transfers=sdlargequery.get_files_pagination()


    if transfer_without_selection>0:
        sdlog.log("SDOPERAQ-032","%d transfer(s) not matching any selection found"%transfer_without_selection)

    if transfer_without_dataset>0:
        sdlog.log("SDOPERAQ-033","%d missing dataset transfer(s) found"%transfer_without_dataset)
