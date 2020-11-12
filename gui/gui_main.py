from tkinter import *
from tkinter.filedialog import askdirectory
from PIL import ImageTk, Image, ImageEnhance
from matplotlib import cm
from shutil import copyfile
import skimage
import numpy as np
import xmltodict
import math
import os,io
from concurrent import futures
import time
import sys

from contextlib import redirect_stdout
#MAIN_FOLDER = askdirectory()
MAIN_FOLDER ="../IBP_2020_testrunSDT"
SCRIPT_FOLDER = MAIN_FOLDER + "/SCRIPTS"
INPUT_DATA_FOLDER = MAIN_FOLDER + "/INPUT"
OUTPUT_DATA_FOLDER = MAIN_FOLDER + "/OUTPUT"
PREPROCESSING_FOLDER = OUTPUT_DATA_FOLDER +"/002_preprocessing"
SPHERES_DT_FOLDER = OUTPUT_DATA_FOLDER +"/003_spheresDT"


sys.path.append(SCRIPT_FOLDER)
import SDT_MAIN

root = Tk()

thread_pool_executor = futures.ThreadPoolExecutor(max_workers=1)

# for f_name in os.listdir(INPUT_DATA_FOLDER):
#     if fnmatch.fnmatch(f_name, '*.tif'):                  #need more clear description of the file names
#         inputImageName = f_name
# print(INPUT_DATA_FOLDER+"/"+inputImageName+" loaded")
# im_tif = Image.open(INPUT_DATA_FOLDER+"/"+inputImageName)     
# nframes = im_tif.n_frames

inputArray = skimage.io.imread(INPUT_DATA_FOLDER+"/TL1_1_t1-5.tif")
timeDimension = inputArray.shape[0]
zDimension = inputArray.shape[1]
yDimension = inputArray.shape[2]
xDimension = inputArray.shape[3]
inputImage = Image.fromarray(inputArray[0,0,:,:])

preprocessArray = np.zeros((timeDimension, zDimension, yDimension, xDimension))
segmentationArray = np.zeros((timeDimension, zDimension, 2, yDimension, xDimension))
#im_tif = Image.open("frangi.tif")
#nframes = inputImage.n_frames

def set_label_text(button, text):
        button['text'] = text



def convert(im,b):
    imarray = np.array(im)
    imarray = np.uint8(cm.magma(np.uint16(imarray*b))*255)
    return Image.fromarray(imarray)

def update_img(newim,imagePanel):
    new = ImageTk.PhotoImage(newim)
    imagePanel.configure(image=new)
    imagePanel.image = new

#def frame_cb(im,frame):
#   
#    print(frame)
#    im.seek(int(frame))
#    newim = convert(im,brightness)
#    return newim 
    
    
def brightness_cb(b):
    global brightness
    brightness = math.exp(float(b))
    newim = convert(Image.fromarray(inputArray[int(timeSlider.get()), int(zDimensionSlider.get()),:,:]), brightness)
    update_img(newim,inputImagePanel)

def time_frame(timepoint):
    global inputImage
    inputImage = Image.fromarray(inputArray[int(timepoint), int(zDimensionSlider.get()),:,:])
    inputImage = convert(inputImage, brightness)
    preprocessingImage = Image.fromarray(preprocessArray[int(timepoint), int(zDimensionSlider.get()),:,:])
    segmentationImage = Image.fromarray(segmentationArray[int(timepoint), int(zDimensionSlider.get()),0,:,:])
    update_img(inputImage, inputImagePanel)    
    update_img(preprocessingImage, preprocessingImagePanel)
    update_img(segmentationImage, segmentationResultPanel)

def z_frame(depth):
    global inputImage
    inputImage = Image.fromarray(inputArray[int(timeSlider.get()), int(depth),:,:])
    inputImage = convert(inputImage,brightness)
    preprocessingImage = Image.fromarray(preprocessArray[int(timeSlider.get()), int(depth),:,:])
    segmentationImage = Image.fromarray(segmentationArray[int(timeSlider.get()), int(depth),0,:,:])
    update_img(inputImage, inputImagePanel)    
    update_img(preprocessingImage, preprocessingImagePanel)
    update_img(segmentationImage, segmentationResultPanel)

#def frame_input(frame):
#    update_img(frame_cb(inputImage,frame),inputImagePanel)

#def frame_pre(frame):
#    update_img(frame_cb(Image.fromarray((skimage.io.imread(PREPROCESSING_FOLDER+"/membranes_blend_z.tif")[:,:,0,0]), "1"),frame),preprocessingImagePanel)

#def frame_seg(frame):
#    update_img(frame_cb(SegmentationImage,frame),segmentationResultPanel)


# blocking code that is on a seperate thread
def run_preprocessing_blocking():
    root.after(0, set_label_text, runPreButton,'running...')

    # print("fake run...")
    # for number in range(5):
    #     #self.after(0, self.listbox_insert, number)
    #     print(number)
    #     time.sleep(1)
    SDT_MAIN.main(SCRIPT_FOLDER + "/PARAMS.xml")

    root.after(0, set_label_text, runPreButton,'run')

    global preprocessArray
    preprocessArray = skimage.io.imread(PREPROCESSING_FOLDER+"/membranes.tif") * 255
    preprocessingImage = Image.fromarray(preprocessArray[0,0,:,:])
    update_img(preprocessingImage, preprocessingImagePanel)
    copyfile(SCRIPT_FOLDER+"/PARAMSCOPY.xml", SCRIPT_FOLDER+"/PARAMS.xml")
    os.remove(SCRIPT_FOLDER+"/PARAMSCOPY.xml")

def run_preprocessing():
    copyfile(SCRIPT_FOLDER+"/PARAMS.xml", SCRIPT_FOLDER+"/PARAMSCOPY.xml")
    with open(SCRIPT_FOLDER+"/PARAMS.xml","r", encoding = 'utf-8') as prm:
        data = xmltodict.parse(prm.read())
        data["body"]["preprocessing"]["filter_parms"]["collect_stats"]["SEED_THR_DIVIDE_FACTOR"]["@value"] = str(seedThresholdE.get())
        data["body"]["preprocessing"]["filter_parms"]["collect_stats"]["MEMBRANE_ACCEPTANCE_LEVEL"]["@value"] = str(acceptanceLevelE.get())
        data["body"]["MAIN"]["flowcontrol"]["l_execution_blocks"]["@value"] = "1"        
    with open(SCRIPT_FOLDER+"/PARAMS.xml",'w', encoding = 'utf-8') as prm:
        prm.write(xmltodict.unparse(data,pretty = 'TRUE'))

    
    thread_pool_executor.submit(run_preprocessing_blocking)

    
# blocking code that is on a seperate thread
def run_segmentation_blocking():
    root.after(0, set_label_text, runSegButton,'running...')

    # print("fake run...")
    # for number in range(5):
    #     print(number)
    #     time.sleep(1)
    SDT_MAIN.main(SCRIPT_FOLDER + "/PARAMS.xml")

    root.after(0, set_label_text, runSegButton,'run')

    global segmentationArray
    segmentationArray = skimage.io.imread(SPHERES_DT_FOLDER+"/RGBA_clusterview2.tif")
    segmentationImage =Image.fromarray(segmentationArray[0,0,0,:,:])
    update_img(segmentationImage, segmentationResultPanel)
    copyfile(SCRIPT_FOLDER+"/PARAMSCOPY.xml",SCRIPT_FOLDER+"/PARAMS.xml")
    os.remove(SCRIPT_FOLDER+"/PARAMSCOPY.xml")

def run_segmentation():
    copyfile(SCRIPT_FOLDER+"/PARAMS.xml", SCRIPT_FOLDER+"/PARAMSCOPY.xml")
    with open(SCRIPT_FOLDER+"/PARAMS.xml","r", encoding = 'utf-8') as prm:
        data = xmltodict.parse(prm.read())
        data["body"]["spheresDT"]["parms"]["MIN_CELL_RADIUS"]["@value"] = str(minCellRadiusE.get())
        data["body"]["spheresDT"]["parms"]["MIN_SPHERE_RADIUS"]["@value"] = str(minSphereRadiusE.get())
        data["body"]["spheresDT"]["parms"]["ANTI_CLUSTER_LEVEL"]["@value"] = str(fragmentationLevelE.get())
        data["body"]["spheresDT"]["parms"]["MIN_SEED_RADIUS"]["@value"] = str(minSeedRadiusE.get())
        data["body"]["spheresDT"]["parms"]["dxyz"]["@value"] = (str(resolutionEx.get())+";"+str(resolutionEy.get())+";"
            +str())
        data["body"]["MAIN"]["flowcontrol"]["l_execution_blocks"]["@value"] = "2"
    with open(SCRIPT_FOLDER+"/PARAMS.xml",'w', encoding = 'utf-8') as prm:
        prm.write(xmltodict.unparse(data,pretty = 'TRUE'))

    thread_pool_executor.submit(run_segmentation_blocking)


    
 

file = io.StringIO()

brightness = 1
originalImage = ImageTk.PhotoImage(convert(inputImage,brightness))
inputImagePanel = Label(root, image = originalImage)
inputImagePanel.grid(column=0, row=0)

originalImageLabel = Label(root, text = "Input Image", width = 60)
originalImageLabel.grid(column=0, row=1)

slidersFrame = Frame()
timeSlider = Scale(slidersFrame, from_=0, to=timeDimension-1, length = 400,orient=HORIZONTAL, label="Time-resolution",
 command=time_frame)
timeSlider.grid(column=0, row=0)
zDimensionSlider = Scale(slidersFrame, from_=0, to=zDimension-1, length = 400,orient=HORIZONTAL, label="Z-resolution",
 command=z_frame)
zDimensionSlider.grid(column=0, row=1)
brightnessSlider = Scale(slidersFrame, from_=-4, to=1, resolution = 0.1, length = 400,orient=HORIZONTAL,
    label="Brightness", command=brightness_cb)
brightnessSlider.grid(column=0, row=2)
slidersFrame.grid(column=0, row=2)



#preprocessing part

preprocessingImage = Image.fromarray(preprocessArray[0,0,:,:])
preprocessingImageTK = ImageTk.PhotoImage(preprocessingImage)
preprocessingImagePanel = Label(root, image = preprocessingImageTK)
preprocessingImagePanel.grid(column=1, row=0)

preprocessingLabel = Label(root, text = "Preprocessing", width = 60)
preprocessingLabel.grid(column=1, row=1)

preprocessingParameters = Frame();
seedThresholdL = Label(preprocessingParameters, text = "Seed Threshold")
seedThresholdL.grid(column=0, row=0)
seedThreshold = DoubleVar(value = 1.0)
seedThresholdE = Entry(preprocessingParameters, textvariable = seedThreshold, width=10)
seedThresholdE.grid(column=1, row=0)



acceptanceLevelL = Label(preprocessingParameters, text = "Membrane Acceptance Level")
acceptanceLevelL.grid(column=0, row=1)
acceptanceLevel = DoubleVar(value = 5.5)
acceptanceLevelE = Entry(preprocessingParameters, textvariable =acceptanceLevel, width=10)
acceptanceLevelE.grid(column=1, row=1)

preprocessingParameters.grid(column=1, row=2)

runPreButton = Button(root, text = "run", command = run_preprocessing)
runPreButton.grid(column=1, row=3)

#Segmentation result part

segmentationImage =Image.fromarray(segmentationArray[0,0,0,:,:])
segmentationImageTK = ImageTk.PhotoImage(segmentationImage)
segmentationResultPanel = Label(root, image=segmentationImageTK)
segmentationResultPanel.grid(column=2, row=0)

SegmentationLabel = Label(root, text = "Segmentation", width = 60)
SegmentationLabel.grid(column=2, row=1)

SegmentationParameters = Frame();

minCellRadiusL = Label(SegmentationParameters, text = "Minimum cell radius")
minCellRadiusL.grid(column=0, row=0)
minCellRadiu = DoubleVar(value = 30)
minCellRadiusE = Entry(SegmentationParameters, textvariable = minCellRadiu, width=10)
minCellRadiusE.grid(column=1, row=0)


minSphereRadiusL = Label(SegmentationParameters, text = "Minimum sphere radius")
minSphereRadiusL.grid(column=0, row=1)
minSphereRadius = DoubleVar(value = 10)
minSphereRadiusE = Entry(SegmentationParameters,textvariable = minSphereRadius, width=10)
minSphereRadiusE.grid(column=1, row=1)


fragmentationLevelL = Label(SegmentationParameters, text = "Fragmentation Level")
fragmentationLevelL.grid(column=0, row=2)
fragmentationLevel = DoubleVar(value = 0.80)
fragmentationLevelE = Entry(SegmentationParameters,textvariable = fragmentationLevel, width=10)
fragmentationLevelE.grid(column=1, row=2)

minSeedRadiuL = Label(SegmentationParameters, text = "Minimum seed radius")
minSeedRadiuL.grid(column=0, row=3)
minSeedRadiu = DoubleVar(value = 14)
minSeedRadiusE = Entry(SegmentationParameters,textvariable = minSeedRadiu, width=10)
minSeedRadiusE.grid(column=1, row=3)

resolutionL = Label(SegmentationParameters, text="Resolution(xyz)")
resolutionL.grid(column=0, row=4)

resolutionFrame = Frame(SegmentationParameters)
resolutionx = DoubleVar(value = 0.1294751)
resolutiony = DoubleVar(value = 0.1294751)
resolutionz = DoubleVar(value = 1)
resolutionEx = Entry(resolutionFrame, textvariable=resolutionx, width=10)
resolutionEy = Entry(resolutionFrame, textvariable=resolutiony, width=10)
resolutionEz = Entry(resolutionFrame, textvariable=resolutionz, width=10)
resolutionEx.grid(column=1,row=0)
resolutionEy.grid(column=2,row=0)
resolutionEz.grid(column=3,row=0)
resolutionFrame.grid(column=1, row=4)

SegmentationParameters.grid(column=2, row=2)

runSegButton = Button(root, text = "run", command = run_segmentation)
runSegButton.grid(column=2, row=3)


root.title("SpheresDT-GUI")
root.mainloop()


