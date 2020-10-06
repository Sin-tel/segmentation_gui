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
def run_cb():
    #need to spawn a new thread here because it will block the gui ..
    with redirect_stdout(file):
        #os.system("python " + SCRIPT_FOLDER + "\SDT_MAIN.py " + SCRIPT_FOLDER + "\PARAMS.xml")
        print("running......")

file = io.StringIO()

img = ImageTk.PhotoImage(convert(im_tif,brightness))
panel = Label(root, image = img)
panel.grid(column=0, row=0)

frameslider = Scale(root, from_=0, to=nframes-1, length = 400, command=frame_cb)
frameslider.grid(column=1, row=0)

brightnessslider = Scale(root, from_=-4, to=1, resolution = 0.1, length = 400, command=brightness_cb)
brightnessslider.grid(column=2, row=0)

outputtext = Text(root)
outputtext.grid(column=0, row=1)

runbutton = Button(root, text = "run", command = run_cb)
runbutton.grid(column=1, row=1)


root.mainloop()

