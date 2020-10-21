import cProfile
import os
import pstats
from pstats import SortKey

import sys
sys.path.append("SCRIPTS")

import SDTMAIN

#SDTMAIN.main("SCRIPTS\PARAMS.xml")

cProfile.run('SDTMAIN.main("SCRIPTS\PARAMS.xml")', 'restats')


p = pstats.Stats('restats')
p.sort_stats(SortKey.TIME).print_stats(1000)
