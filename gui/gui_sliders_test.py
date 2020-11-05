# https://python-forum.io/Thread-Tkinter-How-to-deal-with-code-that-blocks-the-mainloop-freezing-the-gui


from tkinter import *
from tkinter.filedialog import askdirectory
from PIL import ImageTk, Image, ImageEnhance
from matplotlib import cm
import numpy as np
import xmltodict
import math
import os,io


from contextlib import redirect_stdout
#MAIN_FOLDER = askdirectory()
MAIN_FOLDER ="../IBP_2020_testrunSDT"
SCRIPT_FOLDER = MAIN_FOLDER + "/SCRIPTS"
INPUT_DATA_FOLDER = MAIN_FOLDER + "/INPUT"
OUTPUT_DATA_FOLDER = MAIN_FOLDER + "/OUTPUT"
PREPROCESSING_FOLDER = OUTPUT_DATA_FOLDER +"/002_preprocessing"
SPHERES_DT_FOLDER = OUTPUT_DATA_FOLDER +"/003_spheresDT"

root = Tk()



# for f_name in os.listdir(INPUT_DATA_FOLDER):
#     if fnmatch.fnmatch(f_name, '*.tif'):					#need more clear description of the file names
#         inputImageName = f_name
# print(INPUT_DATA_FOLDER+"/"+inputImageName+" loaded")
# im_tif = Image.open(INPUT_DATA_FOLDER+"/"+inputImageName)		
# nframes = im_tif.n_frames

inputImage = Image.open(INPUT_DATA_FOLDER+"/TL1_1_t1-5.tif")
preprocessingImage =Image.open(PREPROCESSING_FOLDER+"/membranes_blend_z.tif")
SegmentationImage =Image.open(SPHERES_DT_FOLDER+"/RGBA_clusterview2.tif")
#im_tif = Image.open("frangi.tif")
nframes = inputImage.n_frames

def convert(im,b):
    imarray = np.array(im)
    imarray = np.uint8(cm.magma(np.uint16(imarray*b))*255)
    return Image.fromarray(imarray)

def update_img(newim,imagePanel):
    new = ImageTk.PhotoImage(newim)
    imagePanel.configure(image=new)
    imagePanel.image = new

def frame_cb(im,frame):
    
    print(frame)
    im.seek(int(frame))
    newim = convert(im,brightness)
    return newim 
    
    
def brightness_cb(b):
    global brightness
    im = inputImage
    brightness = math.exp(float(b))
    newim = convert(im, brightness)
    update_img(newim,inputImagePanel)

def frame_input(frame):
    update_img(frame_cb(inputImage,frame),inputImagePanel)

def frame_pre(frame):
    update_img(frame_cb(preprocessingImage,frame),preprocessingImagePanel)

def frame_seg(frame):
    update_img(frame_cb(SegmentationImage,frame),segmentationResultPanel)


def run_preprocessing():
    with open("PARAMS.xml","r") as prm:
        data = xmltodict.parse(prm.read())
        data["body"]["preprocessing"]["filter_parms"]["collect_stats"]["SEED_THR_DIVIDE_FACTOR"]["@value"] = str(seedThreshold.get())
        data["body"]["preprocessing"]["filter_parms"]["collect_stats"]["MEMBRANE_ACCEPTANCE_LEVEL"]["@value"] = str(acceptanceLevel.get())
        data["body"]["MAIN"]["flowcontrol"]["l_execution_blocks"]["@value"] = "1"
    with open("PARAMS.xml",'w') as prm:
        prm.write(xmltodict.unparse(data,pretty = 'TRUE'))
    os.system("python " + SCRIPT_FOLDER + "/SDT_MAIN.py " + SCRIPT_FOLDER + "/PARAMS.xml")

def run_segmentation():
    with open("PARAMS.xml","r") as prm:
        data = xmltodict.parse(prm.read())
        data["body"]["spheresDT"]["parms"]["MIN_CELL_RADIUS"]["@value"] = str(minCellRadiu.get())
        data["body"]["spheresDT"]["parms"]["MIN_SPHERE_RADIUS"]["@value"] = str(minSphereRadius.get())
        data["body"]["spheresDT"]["parms"]["ANTI_CLUSTER_LEVEL"]["@value"] = str(fragmentationLevel.get())
        data["body"]["spheresDT"]["parms"]["MIN_SEED_RADIUS"]["@value"] = str(minSeedRadiu.get())
        data["body"]["MAIN"]["flowcontrol"]["l_execution_blocks"]["@value"] = "2"
    with open("PARAMS.xml",'w') as prm:
        prm.write(xmltodict.unparse(data,pretty = 'TRUE'))
    os.system("python " + SCRIPT_FOLDER + "/SDT_MAIN.py " + SCRIPT_FOLDER + "/PARAMS.xml")

file = io.StringIO()

brightness = 1
originalImage = ImageTk.PhotoImage(convert(inputImage,brightness))
inputImagePanel = Label(root, image = originalImage)
inputImagePanel.grid(column=0, row=0)

originalImageLabel = Label(root, text = "Input Image")
originalImageLabel.grid(column=0, row=1)

frameSlider = Scale(root, from_=0, to=nframes-1, length = 400,orient=HORIZONTAL, command=frame_input)
frameSlider.grid(column=0, row=2)

brightnessSlider = Scale(root, from_=-4, to=1, resolution = 0.1, length = 400,orient=HORIZONTAL, command=brightness_cb)
brightnessSlider.grid(column=0, row=3)



#preprocessing part

preprocessingImg = ImageTk.PhotoImage(preprocessingImage)
preprocessingImagePanel = Label(root, image = preprocessingImg)
preprocessingImagePanel.grid(column=1, row=0)

preprocessingLabel = Label(root, text = "Preprocessing")
preprocessingLabel.grid(column=1, row=1)

frameSlider = Scale(root, from_=0, to=nframes-1, length = 400,orient=HORIZONTAL, command=frame_pre)
frameSlider.grid(column=1, row=2)

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

#Segmentation result part

segmentationResult = ImageTk.PhotoImage(SegmentationImage)
segmentationResultPanel = Label(root, image = segmentationResult)
segmentationResultPanel.grid(column=2, row=0)

SegmentationLabel = Label(root, text = "Segmentation")
SegmentationLabel.grid(column=2, row=1)

frameSlider = Scale(root, from_=0, to=nframes-1, length = 400,orient=HORIZONTAL, command=frame_seg)
frameSlider.grid(column=2, row=2)

SegmentationParameters = Frame();

minCellRadiusL = Label(SegmentationParameters, text = "Minimum cell radius")
minCellRadiusL.grid(column=0, row=0)
minCellRadiu = DoubleVar(value = 0.00080)
minCellRadiusE = Entry(SegmentationParameters, textvariable = minCellRadiu)
minCellRadiusE.grid(column=1, row=0)


minSphereRadiusL = Label(SegmentationParameters, text = "Minimum sphere radius")
minSphereRadiusL.grid(column=0, row=1)
minSphereRadius = DoubleVar(value = 20.00)
minSphereRadiusE = Entry(SegmentationParameters,textvariable = minSphereRadius)
minSphereRadiusE.grid(column=1, row=1)


fragmentationLevelL = Label(SegmentationParameters, text = "Fragmentation Level")
fragmentationLevelL.grid(column=0, row=2)
fragmentationLevel = DoubleVar(value = 39.00)
fragmentationLevelE = Entry(SegmentationParameters,textvariable = fragmentationLevel)
fragmentationLevelE.grid(column=1, row=2)

minSeedRadiuL = Label(SegmentationParameters, text = "Minimum seed radiu")
minSeedRadiuL.grid(column=0, row=3)
minSeedRadiu = DoubleVar(value = 39.00)
minSeedRadiuE = Entry(SegmentationParameters,textvariable = minSeedRadiu)
minSeedRadiuE.grid(column=1, row=3)

SegmentationParameters.grid(column=2, row=3)

runButton = Button(root, text = "run", command = lambda: run_segmentation())
runButton.grid(column=2, row=4)


root.title("SpheresDT-GUI")
root.mainloop()

