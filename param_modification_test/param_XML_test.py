# import xmltodict

# with open("PARAMS.xml",'w') as fd:
#     data = xmltodict.parse(fd.read())
#     data["MAIN"]["flowcontrol"]["l_execution_blocks"] = "1"
#     fd.write(xmltodict.unparse(data))
    
import xmltodict
from tkinter import *
import os,io

MAIN_FOLDER ="../IBP_2020_testrunSDT"
SCRIPT_FOLDER = MAIN_FOLDER + "/SCRIPTS"
INPUT_DATA_FOLDER = MAIN_FOLDER + "/INPUT"
OUTPUT_DATA_FOLDER = MAIN_FOLDER + "/OUTPUT"
PREPROCESSING_FOLDER = OUTPUT_DATA_FOLDER +"/002_preprocessing"
SPHERES_DT_FOLDER = OUTPUT_DATA_FOLDER +"/003_spheresDT"


def run_preprocessing():
    with open("PARAMS.xml","r") as prm:
        data = xmltodict.parse(prm.read())
        data["body"]["preprocessing"]["filter_parms"]["collect_stats"]["SEED_THR_DIVIDE_FACTOR"]["@value"] = str(seedThreshold.get())
        data["body"]["preprocessing"]["filter_parms"]["collect_stats"]["MEMBRANE_ACCEPTANCE_LEVEL"]["@value"] = str(acceptanceLevel.get())
        data["body"]["MAIN"]["flowcontrol"]["l_execution_blocks"]["@value"] = "1"
    with open("PARAMS.xml",'w') as prm:
    	prm.write(xmltodict.unparse(data,pretty = 'TRUE'))
    print("done")
#    os.system("python " + SCRIPT_FOLDER + "/SDT_MAIN.py " + SCRIPT_FOLDER + "/PARAMS.xml")


root = Tk()
preprocessingLabel = Label(root, text = "Preprocessing")
preprocessingLabel.grid(column=1, row=1)

preprocessingParameters = Frame();
seedThresholdL = Label(preprocessingParameters, text = "Seed Threshold")
seedThresholdL.grid(column=0, row=0)
seedThreshold = DoubleVar(value = 0.00080)
seedThresholdE = Entry(preprocessingParameters, textvariable = seedThreshold)
seedThresholdE.grid(column=1, row=0)



acceptanceLevelL = Label(preprocessingParameters, text = "Membrane Acceptance Level")
acceptanceLevelL.grid(column=0, row=1)
acceptanceLevel = DoubleVar(value = 20.00)
acceptanceLevelE = Entry(preprocessingParameters, textvariable =acceptanceLevel)
acceptanceLevelE.grid(column=1, row=1)


minimum3DsizeL = Label(preprocessingParameters, text = "Minimum 3D Size")
minimum3DsizeL.grid(column=0, row=2)
minimum3Dsize = DoubleVar(value = 39.00)
minimum3DsizeE = Entry(preprocessingParameters, textvariable =minimum3Dsize)
minimum3DsizeE.grid(column=1, row=2)

preprocessingParameters.grid(column=1, row=3)

runButton = Button(root, text = "run", command = lambda:run_preprocessing())
runButton.grid(column=1, row=4)

runButton = Button(root, text = "run", command = lambda:run_preprocessing())
runButton.grid(column=1, row=4)

root.title("SpheresDT-GUI")
root.mainloop()