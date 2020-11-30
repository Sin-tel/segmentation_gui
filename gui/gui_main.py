from tkinter import *
from tkinter import ttk
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename 
from PIL import ImageTk, Image, ImageEnhance
from matplotlib import cm
from shutil import copyfile
import subprocess
import skimage.io
import platform
import numpy as np
import xmltodict
import math
import os,io
from concurrent import futures
import time
import sys
import signal, psutil
from contextlib import redirect_stdout

MAIN_FOLDER = os.path.abspath("../IBP_2020_testrunSDT")

SCRIPT_FOLDER = MAIN_FOLDER + "/SCRIPTS"
INPUT_DATA_FOLDER = MAIN_FOLDER + "/INPUT"
OUTPUT_DATA_FOLDER = MAIN_FOLDER + "/OUTPUT"
PREPROCESSING_FOLDER = OUTPUT_DATA_FOLDER +"/002_preprocessing"
SPHERES_DT_FOLDER = OUTPUT_DATA_FOLDER +"/003_spheresDT"
inputFile = INPUT_DATA_FOLDER+"/TL1_1_t1-5.tif"

sys.path.append(SCRIPT_FOLDER)
import SDT_MAIN

root = Tk()

thread_pool_executor = futures.ThreadPoolExecutor(max_workers=1)

w_max = 500;  # the max size of the image
h_max = 500; 

min_brightness = 0;

def scaling(pil_image): #the image need to scale
    w, h = pil_image.size #the original size 
    if w<= w_max and h<= h_max:
        return pil_image
    else:
        f1 = 1.0*w_max/w 
        f2 = 1.0*h_max/h
        factor = min([f1, f2])    
        width = int(w*factor)    
        height = int(h*factor)    
        return pil_image.resize((width, height), Image.BOX) #change to BILINEAR or BICUBIC for better quality 
    return pil_image    

def open_input():
    global inputFile
    getFile = askopenfilename(title = "Select inputfile",filetypes=[("TIF File","*.tif")])
    if getFile:
        inputFile = getFile
        global inputArray, preprocessArray, segmentationArray, zDimensionSlider, timeSlider
        inputArray, preprocessArray, segmentationArray, zDimensionSlider, timeSlider = update_gui_input(inputFile)  

def save_pre_output():
    fileName = asksaveasfilename(defaultextension='.tif',title="Save as", filetypes=[("TIF File", "*.tif")])
    if fileName:
        copyfile(PREPROCESSING_FOLDER+"/membranes.tif", fileName)


def save_segmentation_output():
    fileName = asksaveasfilename(defaultextension='.tif',title="Save as", filetypes=[("TIF File", "*.tif")])
    if fileName:
        copyfile(SPHERES_DT_FOLDER+"/RGBA_clusterview2.tif", fileName)
    

def update_gui_input(inputFile):
    inputArray = skimage.io.imread(inputFile)

    #add dummy dimension if single frame
    if len(inputArray.shape) == 3:
        inputArray = inputArray[np.newaxis, :]

    global min_brightness
    min_brightness = np.min(inputArray)

    timeDimension = inputArray.shape[0]
    zDimension = inputArray.shape[1]
    yDimension = inputArray.shape[2]
    xDimension = inputArray.shape[3]

    preprocessArray = np.zeros((timeDimension, zDimension, yDimension, xDimension))
    segmentationArray = np.zeros((timeDimension, zDimension, 2, yDimension, xDimension))

    timeSlider = Scale(slidersFrame, from_=0, to=timeDimension-1, length = 400,orient=HORIZONTAL, label="Time frame",
    command=time_frame)
    timeSlider.grid(column=0, row=0)
    zDimensionSlider = Scale(slidersFrame, from_=0, to=zDimension-1, length = 400,orient=HORIZONTAL, label="Z frame",
    command=z_frame)
    zDimensionSlider.grid(column=0, row=1)

    update_img(applyLut(Image.fromarray(inputArray[0,0,:,:]),1),inputImagePanel)
    update_img(Image.fromarray(preprocessArray[0,0,:,:]),preprocessingImagePanel)
    update_img(Image.fromarray(segmentationArray[0,0,0,:,:]), segmentationResultPanel)

    return inputArray, preprocessArray, segmentationArray, zDimensionSlider, timeSlider


def total_stacks_string():
    global inputArray
    timeDimension = inputArray.shape[0]
    stringRange = "1"
    for x in range(2, timeDimension + 1):
        stringRange = (stringRange + ";" + str(x))
    return stringRange

def set_label_text(button, text):
    button['text'] = text

def applyLut(im,b):
    imarray = np.array(im)
    imarray = np.uint8(cm.magma(np.uint16((imarray- min_brightness)*b))*255)
    return Image.fromarray(imarray)

def update_img(newim,imagePanel):
    new = ImageTk.PhotoImage(scaling(newim))
    imagePanel.configure(image=new)
    imagePanel.image = new
    
def brightness_cb(b):
    global brightness
    brightness = math.exp(float(b))
    newim = applyLut(Image.fromarray(inputArray[int(timeSlider.get()), int(zDimensionSlider.get()),:,:]), brightness)
    update_img(newim,inputImagePanel)

def time_frame(timepoint):
    inputImage = Image.fromarray(inputArray[int(timepoint), int(zDimensionSlider.get()),:,:])
    inputImage = applyLut(inputImage, brightness)
    preprocessingImage = Image.fromarray(preprocessArray[int(timepoint), int(zDimensionSlider.get()),:,:])
    segmentationImage = Image.fromarray(segmentationArray[int(timepoint), int(zDimensionSlider.get()),0,:,:])
    update_img(inputImage, inputImagePanel)    
    update_img(preprocessingImage, preprocessingImagePanel)
    update_img(segmentationImage, segmentationResultPanel)

def z_frame(depth):
    inputImage = Image.fromarray(inputArray[int(timeSlider.get()), int(depth),:,:])
    inputImage = applyLut(inputImage,brightness)
    preprocessingImage = Image.fromarray(preprocessArray[int(timeSlider.get()), int(depth),:,:])
    segmentationImage = Image.fromarray(segmentationArray[int(timeSlider.get()), int(depth),0,:,:])
    update_img(inputImage, inputImagePanel)    
    update_img(preprocessingImage, preprocessingImagePanel)
    update_img(segmentationImage, segmentationResultPanel)


# blocking code that is on a seperate thread
def run_preprocessing_blocking():
    root.after(0, set_label_text, runPreButton,'running...')

    # print("fake run...")
    # for number in range(5):
    #     #self.after(0, self.listbox_insert, number)
    #     print(number)
    #     time.sleep(1)
    tic = time.perf_counter()

    SDT_MAIN.main(SCRIPT_FOLDER + "/PARAMS.xml")

    toc = time.perf_counter()
    print(f"preprocessing took {toc - tic:0.4f} seconds")

    root.after(0, set_label_text, runPreButton,'run')

    global preprocessArray
    preprocessArray = skimage.io.imread(PREPROCESSING_FOLDER+"/membranes.tif") * 255
    preprocessingImage = Image.fromarray(preprocessArray[0,0,:,:])    
    update_img(preprocessingImage, preprocessingImagePanel)
    copyfile(SCRIPT_FOLDER+"/PARAMSCOPY.xml", SCRIPT_FOLDER+"/PARAMS.xml")
    os.remove(SCRIPT_FOLDER+"/PARAMSCOPY.xml")

def run_preprocessing():    
    global zMembraneDetectorBoolean

    copyfile(SCRIPT_FOLDER+"/PARAMS.xml", SCRIPT_FOLDER+"/PARAMSCOPY.xml")
    
    with open(SCRIPT_FOLDER+"/PARAMS.xml","r", encoding = 'utf-8') as prm:
        data = xmltodict.parse(prm.read())
        data["body"]["preprocessing"]["filter_parms"]["collect_stats"]["SEED_THR_DIVIDE_FACTOR"]["@value"] = str(seedThresholdE.get())
        data["body"]["preprocessing"]["filter_parms"]["collect_stats"]["MEMBRANE_ACCEPTANCE_LEVEL"]["@value"] = str(acceptanceLevelE.get())
        data["body"]["MAIN"]["flowcontrol"]["l_execution_blocks"]["@value"] = "1" 
        data["body"]["MAIN"]["paths"]["img_raw_file"]["@value"] = str(inputFile)  
        data["body"]["preprocessing"]["flowcontrol"]["l_stack_number"]["@value"] = str(total_stacks_string())
        if zMembraneDetectorC.get() == "OFF":
            data["body"]["preprocessing"]["flowcontrol"]["filter_order"]["@value"] = "0;25;4;37;99;39;38;28;27;99;18;31;98;34;98;35;99"
            data["body"]["preprocessing"]["flowcontrol"]["l_output_f_names"]["@value"] = "frangi;threshold;membranes;exterior_outline;exterior_mask"
            zMembraneDetectorBoolean = False
        elif zMembraneDetectorC.get() == "ON":
            data["body"]["preprocessing"]["flowcontrol"]["filter_order"]["@value"] = "0;25;4;37;99;39;38;28;27;99;18;31;98;34;98;35;99;43;98"
            data["body"]["preprocessing"]["flowcontrol"]["l_output_f_names"]["@value"] = "frangi;threshold;membranes;exterior_outline;exterior_mask;membranes_blend_z"
            zMembraneDetectorBoolean = True

    with open(SCRIPT_FOLDER+"/PARAMS.xml",'w') as prm:
        prm.write(xmltodict.unparse(data,pretty = 'TRUE'))

    
    thread_pool_executor.submit(run_preprocessing_blocking)

    
# blocking code that is on a seperate thread
def run_segmentation_blocking():
    root.after(0, set_label_text, runSegButton,'running...')

    # print("fake run...")
    # for number in range(5):
    #     print(number)
    #     time.sleep(1)
    tic = time.perf_counter()

    SDT_MAIN.main(SCRIPT_FOLDER + "/PARAMS.xml")

    toc = time.perf_counter()
    print(f"segmentation took {toc - tic:0.4f} seconds")

    

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
        data["body"]["MAIN"]["paths"]["img_raw_file"]["@value"] = str(inputFile)
        if zMembraneDetectorBoolean:
            data["body"]["spheresDT"]["paths"]["FILE_MEMBRANE"]["@value"] = "membranes_blend_z.tif"
        elif not zMembraneDetectorBoolean:
            data["body"]["spheresDT"]["paths"]["FILE_MEMBRANE"]["@value"] = "membranes.tif"

    with open(SCRIPT_FOLDER+"/PARAMS.xml",'w') as prm:
        prm.write(xmltodict.unparse(data,pretty = 'TRUE'))

    thread_pool_executor.submit(run_segmentation_blocking)

def open_external_editor():
    filepath = SCRIPT_FOLDER+"/PARAMS.xml"

    if platform.system() == 'Darwin':       # macOS
        subprocess.call(('open', filepath))
    elif platform.system() == 'Windows':    # Windows
        os.startfile(filepath)
    else:                                   # linux variants
        subprocess.call(('xdg-open', filepath))

def kill_child_processes(parent_pid, sig=signal.SIGTERM):
    try:
        parent = psutil.Process(parent_pid)
    except psutil.NoSuchProcess:
        return
    children = parent.children(recursive=True)
    for process in children:
        process.send_signal(sig)

def on_closing():
    thread_pool_executor.shutdown(wait=False)
    # force terminate all child processes
    kill_child_processes(os.getpid())
    root.destroy()

root.protocol("WM_DELETE_WINDOW", on_closing)

def redirector(inputStr):
    stdout_original(inputStr)
    textbox.configure(state='normal')
    textbox.insert("end", inputStr)
    textbox.see("end")
    textbox.configure(state='disabled')
    
stdout_original = sys.stdout.write
sys.stdout.write = redirector #whenever sys.stdout.write is called, redirector is called.
sys.stderr.write = redirector #for some reason joblib uses stderr so we will redirect it too


file = io.StringIO()


inputImagePanel = Label(root)
inputImagePanel.grid(column=0, row=1)

originalImageLabel = Label(root, text = "Input Image", width = 60)
originalImageLabel.grid(column=0, row=0)

openFileButton = Button(root, text = "Open File", command = open_input)
openFileButton.grid(column=0, row=2)

slidersFrame = Frame()
brightnessSlider = Scale(slidersFrame, from_=-4, to=1, resolution = 0.1, length = 400,orient=HORIZONTAL,
    label="Brightness", command=brightness_cb)
brightnessSlider.grid(column=0, row=2)
slidersFrame.grid(column=0, row=3)



#preprocessing part

preprocessingImagePanel = Label(root)
preprocessingImagePanel.grid(column=1, row=1)

preprocessingLabel = Label(root, text = "Preprocessing", width = 60)
preprocessingLabel.grid(column=1, row=0)

savePreButton = Button(root, text = "Save Preprocessing Output", command=save_pre_output)
savePreButton.grid(column=1, row=2)

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

zMembraneDetectorL = Label(preprocessingParameters, text="z-membrane detector")
zMembraneDetectorL.grid(column=0, row=2)
zMembraneDetectorC = ttk.Combobox(preprocessingParameters, values=["ON", "OFF"])
zMembraneDetectorC.grid(column=1, row=2)
zMembraneDetectorC.current(1)
zMembraneDetectorBoolean = False

preprocessingParameters.grid(column=1, row=3)

runPreButton = Button(root, text = "run", command = run_preprocessing)
runPreButton.grid(column=1, row=4)

#Segmentation result part

segmentationResultPanel = Label(root)
segmentationResultPanel.grid(column=2, row=1)

SegmentationLabel = Label(root, text = "Segmentation", width = 60)
SegmentationLabel.grid(column=2, row=0)

saveSegmentationButton = Button(root, text = "Save Segmentation Output", command=save_segmentation_output)
saveSegmentationButton.grid(column=2, row=2)

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

resolutionL = Label(SegmentationParameters, text="pixel width xyz (micron)")
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

SegmentationParameters.grid(column=2, row=3)

runSegButton = Button(root, text = "run", command = run_segmentation)
runSegButton.grid(column=2, row=4)

openExternalButton = Button(root, text = "edit parameters", command = open_external_editor)
openExternalButton.grid(column=0, row=4)

brightness = 1
inputArray, preprocessArray, segmentationArray, zDimensionSlider, timeSlider = update_gui_input(inputFile)

textbox=Text(root, height = 10, width = 120)
textbox.grid(column=0, row=5, columnspan = 3, padx = 12, pady = 12)
root.title("SpheresDT-GUI")
root.mainloop()