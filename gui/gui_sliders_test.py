# https://python-forum.io/Thread-Tkinter-How-to-deal-with-code-that-blocks-the-mainloop-freezing-the-gui


from tkinter import *
from PIL import ImageTk, Image, ImageEnhance
from matplotlib import cm
import os
import numpy as np
import math
import os

import io
from contextlib import redirect_stdout

SCRIPT_FOLDER = "..\IBP_2020_testrunSDT\SCRIPTS"

root = Tk()
im_tif = Image.open("TL1_1_t1-5.tif")
# im_tif = Image.open("frangi.tif")
nframes = im_tif.n_frames

brightness = 1


def convert(im,b):
    imarray = np.array(im)
    imarray = np.uint8(cm.magma(np.uint16(imarray*b))*255)
    return Image.fromarray(imarray)

def update_img(newim):
    new = ImageTk.PhotoImage(newim)
    panel.configure(image=new)
    panel.image = new

def frame_cb(frame):
    
    print(frame)
    im_tif.seek(int(frame))
    newim = convert(im_tif,brightness)
    update_img(newim)

    output = file.getvalue()

    print(output)
    outputtext.delete('1.0', END)
    outputtext.insert("1.0",output)
    

def brightness_cb(b):
    global brightness
    brightness = math.exp(float(b))
    newim = convert(im_tif, brightness)

    update_img(newim)
def run_preprocessing():
    #need to spawn a new thread here because it will block the gui ..
    with redirect_stdout(file):
        #os.system("python " + SCRIPT_FOLDER + "\SDT_MAIN.py " + SCRIPT_FOLDER + "\PARAMS.xml")
        print("running......")
def run_segmentation():
	print("running")

file = io.StringIO()

img = ImageTk.PhotoImage(convert(im_tif,brightness))
#<<<<<<< Updated upstream
panel = Label(root, image = img)
panel.grid(column=0, row=0)
#=======
originalImage = Label(root, image = img)
originalImage.grid(column=0, row=0)

originalImageLabel = Label(root, text = "Input Image")
originalImageLabel.grid(column=0, row=1)

frameSlider = Scale(root, from_=0, to=nframes-1, length = 400,orient=HORIZONTAL, command=frame_cb)
frameSlider.grid(column=0, row=2)

brightnessSlider = Scale(root, from_=-4, to=1, resolution = 0.1, length = 400,orient=HORIZONTAL, command=brightness_cb)
brightnessSlider.grid(column=0, row=3)



#preprocessing part

preprocessingLabel = Label(root, text = "Preprocessing")
preprocessingLabel.grid(column=1, row=1)

frameSlider = Scale(root, from_=0, to=nframes-1, length = 400,orient=HORIZONTAL, command=frame_cb)
frameSlider.grid(column=1, row=2)

preprocessingParameters = Frame();
seedThresholdL = Label(preprocessingParameters, text = "Seed Threshold")
seedThresholdL.grid(column=0, row=0)
seedThresholdE = Entry(preprocessingParameters)
seedThresholdE.grid(column=1, row=0)



acceptanceLevelL = Label(preprocessingParameters, text = "Membrane Acceptance Level")
acceptanceLevelL.grid(column=0, row=1)
acceptanceLevelE = Entry(preprocessingParameters)
acceptanceLevelE.grid(column=1, row=1)


seedThresholdL = Label(preprocessingParameters, text = "Seed Threshold")
seedThresholdL.grid(column=0, row=2)
seedThresholdE = Entry(preprocessingParameters)
seedThresholdE.grid(column=1, row=2)

preprocessingParameters.grid(column=1, row=3)

runButton = Button(root, text = "run", command = run_preprocessing)
runButton.grid(column=1, row=4)

#Segmentation result part

SegmentationLabel = Label(root, text = "Segmentation")
SegmentationLabel.grid(column=2, row=1)

frameSlider = Scale(root, from_=0, to=nframes-1, length = 400,orient=HORIZONTAL, command=frame_cb)
frameSlider.grid(column=2, row=2)

SegmentationParameters = Frame();
minCellRadiusL = Label(SegmentationParameters, text = "Minimum cell radius")
minCellRadiusL.grid(column=0, row=0)
minCellRadiusE = Entry(SegmentationParameters)
minCellRadiusE.grid(column=1, row=0)


minSphereRadiusL = Label(SegmentationParameters, text = "Minimum sphere radius")
minSphereRadiusL.grid(column=0, row=1)
minSphereRadiusE = Entry(SegmentationParameters)
minSphereRadiusE.grid(column=1, row=1)
#>>>>>>> Stashed changes

frameslider = Scale(root, from_=0, to=nframes-1, length = 400, command=frame_cb)
frameslider.grid(column=1, row=0)

brightnessslider = Scale(root, from_=-4, to=1, resolution = 0.1, length = 400, command=brightness_cb)
brightnessslider.grid(column=2, row=0)

outputtext = Text(root)
outputtext.grid(column=0, row=1)

#<<<<<<< Updated upstream
runbutton = Button(root, text = "run", command = run_preprocessing)
runbutton.grid(column=1, row=1)
#=======
runButton = Button(root, text = "run", command = run_segmentation)
runButton.grid(column=2, row=4)
#>>>>>>> Stashed changes


root.mainloop()

