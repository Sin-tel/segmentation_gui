import cProfile
import os
import pstats
from pstats import SortKey

import sys
sys.path.append("SCRIPTS")

import SDT_MAIN

#SDTMAIN.main("SCRIPTS\PARAMS.xml")

#cProfile.run('SDT_MAIN.main("SCRIPTS\PARAMS.xml")', 'restats')


p = pstats.Stats('restats')
p.sort_stats(SortKey.TIME).print_stats(1000)
