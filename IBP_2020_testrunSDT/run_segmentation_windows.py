# !/bin/bash
# declare -r SCRIPT_FOLDER="./SCRIPTS"
# python  "${SCRIPT_FOLDER}/SDT_MAIN.py" "${SCRIPT_FOLDER}/PARAMS.xml" 

# python script that does the same as bash script above
# for running in windows

import os

#import sys
#print(sys.version)

SCRIPT_FOLDER = ".\SCRIPTS"
#os.system("cd")
os.system("python " + SCRIPT_FOLDER + "\SDT_MAIN.py " + SCRIPT_FOLDER + "\PARAMS.xml")
#os.system("python " + SCRIPT_FOLDER + "\SDT_MAIN.py") #run with no args, should use default params