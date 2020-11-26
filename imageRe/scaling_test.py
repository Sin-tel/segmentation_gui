from tkinter import *
from tkinter import ttk
from tkinter.filedialog import askdirectory, askopenfilename, asksaveasfilename 
from PIL import ImageTk, Image, ImageEnhance
from matplotlib import cm
from shutil import copyfile
import skimage.io
import numpy as np
import xmltodict
import math
import os,io
from concurrent import futures
import time
import sys
import signal, psutil


inputFile = "E:/integrated_bioinformatics_project/IBP_images/RJ013_2020-09-02_E1_AiryProcess_t26_31.tif"

root = Tk()
inputArray = skimage.io.imread(inputFile)
timeDimension = inputArray.shape[0]
zDimension = inputArray.shape[1]
yDimension = inputArray.shape[2]
xDimension = inputArray.shape[3]
inputImage = Image.fromarray(inputArray[0,0,:,:])	