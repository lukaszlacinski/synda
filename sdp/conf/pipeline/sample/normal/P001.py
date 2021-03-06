#!/usr/bin/env python
# -*- coding: ISO-8859-1 -*-

##################################
#  @program        synda
#  @description    climate models data transfer program
#  @copyright      Copyright “(c)2009 Centre National de la Recherche Scientifique CNRS. 
#                             All Rights Reserved”
#  @license        CeCILL (https://raw.githubusercontent.com/Prodiguer/synda/master/sdt/doc/LICENSE)
##################################

"""Contains P001 pipeline definition."""

import sppipelineutils
from sppostprocessingutils import PostProcessingPipeline,State,Transition

def get_pipeline():
    return ppp

# init.

name='P001'
ppp=PostProcessingPipeline(name)

t0=Transition(name='remove_duplicate',destination='S0200')
t1=Transition(name='time_axis_normalization',destination='S0300')
t2=Transition(name='remove_tmp_files',destination='S0400')

s0=State(name='S0100',transition=t0,initial=True)
s1=State(name='S0200',transition=t1)
s2=State(name='S0300',transition=t2)
s3=State(name='S0400',transition=None)

ppp.add(s0,s1,s2,s3)
