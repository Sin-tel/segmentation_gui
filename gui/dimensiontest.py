from tkinter import *
from tkinter.filedialog import askdirectory
from PIL import ImageTk, Image, ImageEnhance
from matplotlib import cm
import skimage
import numpy as np
import xmltodict
import math
import os,io

image = image.open("../IBP_2020_testrunSDT/OUTPUT/002_preprocessing/membranes_blend_z.tif", "")
image.show()



array = skimage.io.imread("../IBP_2020_testrunSDT/OUTPUT/002_preprocessing/membranes_blend_z.tif")
print(array.shape)
array = array * 255
img = Image.fromarray(array[3,5,:,:])
print(array[3,5,220,:])
img.show()