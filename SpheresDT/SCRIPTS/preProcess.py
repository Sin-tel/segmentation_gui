'''
Created on 28 Mar 2019
preprocessing pipeline 
@author: wimth

'''
from helper_functions import slice_tif, examine
from z_membrane_detector import detect_z_membrane
from tifffile import TiffFile,imsave

from skimage.filters import (threshold_otsu, laplace, median, frangi, threshold_li,
							 threshold_local, threshold_minimum, gaussian, threshold_triangle)
from skimage.morphology import (disk, remove_small_holes, remove_small_objects, binary_erosion,
								binary_dilation, binary_closing, binary_opening, reconstruction,
								medial_axis, skeletonize, skeletonize_3d,local_maxima,local_minima)
from skimage.segmentation import active_contour, watershed,chan_vese, morphological_chan_vese
from skimage.exposure import rescale_intensity
from skimage import img_as_int
from scipy.ndimage.morphology import distance_transform_edt
from skimage.feature import peak_local_max
from sklearn.preprocessing import MinMaxScaler
#from frangi3dmod.frangi import frangi as frangi3dmod  # my own version of frangi3d
from io import StringIO
from pathlib import Path
import traceback
import logging
import pandas as pd
import pprint

from math import ceil

import numpy as np
import matplotlib.pyplot as plt

from joblib import Parallel, delayed

USE_PARALLEL = True

def preprocess_image(param_xml, filehandler):
	def set_filter_parameters(param_xml):

		param_xml.l_main_keys = ['body', 'preprocessing', 'filter_parms']

		# datastructures
		d_number_filter = {0: 'ORIGINAL',  # loading in the file ,  O=grey
			 1: 'otsu',  # otsu threshold : I=grey, O=binary(threshold)
			 2: 'median',  # I=grey, O=grey
			 3: 'laplace',
			 4: 'frangi',
			 5: 'RmSmObj',  # remove small objects
			 6: 'RmSmHol',  # remove small holes
			 7: 'thrli',  # threshold li
			 8: 'thrloc',  # threshold local  (not suitable)
			 9: 'thrmin',  # threshold minimum
			 10: 'bineros',  # binary erosion
			 11: 'bindila',  # binary dilation
			 12: 'invert',  # invert a binary image
			 13: 'resint',  # rescale intensity
			 14: 'subtract',  # subtract image from another image
			 15: 'kuwahara',  # kuwahara filtering
			 16: 'gaussian',
			 17: 'binclos',  # binary closing
			 18: 'RmSmObj3D',
			 19: 'RmSmHol3D',
			 20: 'scale',
			 21: 'HPassOtsu',  # otsu filtering that sets everything below the threshold to zero
			 22: 'binopen',
			 23: 'tryallthr',
			 24: 'thrtriangle',
			 25: 'flip',
			 26: 'asint',
			 27: 'thrabs',
			 28: 'reconstruction',
			 29: 'cornerthr',
			 30: 'frangi3d',
			 31: 'skeletonize',
			 32: 'skeletonize3d',
			 33: 'medial_axis',
			 34: 'active_contour',
			 35: 'exterior_mask',
			 36: 'scale_constant',
			 37: 'scale_max',
			 38: 'collect_stats',
			 39: 'collect_Otsu',
			 40: 'frangi3dmod',
			 41: 'blend_manual_exterior', # keep at 41 (fix value)
			 42: 'chan_vese',  #ACWE = active contour without edges
			 43: 'blend_z_membrane',
			 44: 'morphological_chan_vese',
			 98: 'write_output_no_signal_filtered',
			 99: 'write_output'
											 }

		l_3D_filters = ['RmSmObj3D', 'RmSmHol3D', 'frangi3d', 'frangi3dmod', 'skeletonize3d', 'write_output',
			'write_output_no_signal_filtered', 'scale_constant', 'scale_max',
			'collect_stats','blend_z_membrane','morphological_chan_vese']  # ['RmSmHol']   #indicate which filters should work in 3D instead of 2D

		d_slice_selector = {'bindila': [0, 27],
			'binclos': [0, 27],
			'bineros': [0, 27],
			# only slices in the range([value,value]) will be filtered by the filter
			'RmSmObj': [5, 27],
			'binopen': [0, 27],
			}

		# the default dtype is considered to be uint16, other formats should be indicated below
		d_filter_outputdtype = {'scale': 'float',
			'otsu': 'bool',
			'thrtriangle': 'bool',
			'RmSmObj': 'bool',
			'subtract': 'bool',
			'RmSmHol': 'bool',
			'thrli': 'bool',
			'thrmin': 'bool',
			'invert': 'bool',
			'thrloc': 'bool',
			'binclos': 'bool',
			'bineros': 'bool',
			'bindila': 'bool',
			'binopen': 'bool',
			'RmSmObj3D': 'bool',
			'RmSmHol3D': 'bool',
			'thrabs': 'bool',
			'cornerthr': 'bool',
			'frangi': 'float'
			}

		d_filter_arg = {'median': {'selem': disk(1)},  # disk(5)

		'otsu': {'nbins': 256},

		# threshold_triangle(image, nbins=256)
		'thrtriangle': {'nbins': 10},

		'HPassOtsu': {'nbins': 20},

		'laplace': {'ksize': 3,
								'mask': None},

		'frangi': {  # 'sigmas':param_xml.get_value('sigmas',['frangi']),
				'scale_range': param_xml.get_value('scale_range', ['frangi']),
				'scale_step': param_xml.get_value('scale_step', ['frangi']),
				# 'alpha':param_xml.get_value('alpha',['frangi']),
				# 'beta':param_xml.get_value('beta',['frangi']),
				# 'gamma':param_xml.get_value('gamma',['frangi']),
				'beta1': param_xml.get_value('beta1', ['frangi']),
				'beta2': param_xml.get_value('beta2', ['frangi']),
				'black_ridges': param_xml.get_value('black_ridges', ['frangi'])},
		# black_ridges : for frangi3D only black_rigdes False seems to work (opposite to frangi2D !)

		# #skimage.filters.frangi(image, scale_range=(1, 10), scale_step=2, beta1=0.5, beta2=15, black_ridges=True) :
		# 'frangi':{'scale_range':param_xml.get_value('scale_range',['frangi']),  # 2-tuple of floats, optional -> The range of sigmas used. = related to width of the vessels 
		# 'scale_step':param_xml.get_value('scale_step',['frangi']),       #scale_step : float, optional -> Step size between sigmas.
		# 'beta1':param_xml.get_value('beta1',['frangi']),           #beta1 : float, optional -> Frangi correction constant that adjusts the filters sensitivity to deviation from a blob-like structure. a high value will create artefacts next to the membrane
		# #this is parameter 'beta' in the original Frangi paper  (code : filtered = np.exp(-rb / beta1) * (np.ones(np.shape(image)) - np.exp(-s2 / beta2))
		# #increasing 'beta' will make is more tolerant for blobs
		# 'beta2':param_xml.get_value('beta2',['frangi']),            #beta2 : float, optional -> Frangi correction constant that adjusts the filters sensitivity to areas of high variance/texture/structure
		# #this is parameter 'c' in the original frangi paper.  Increase if you feel the interior noise gets too high frangi output
		# 'black_ridges':param_xml.get_value('black_ridges',['frangi'])},  #black_ridges : boolean, optional -> When True (the default), the filter detects black ridges; when False, it detects white ridges.

		# this is the same frangi from scikitimage used for the 2D, but here setup for 3D.  beta1 is routed to beta, and beta2 is routed to gamma.  The alpha involves plate likestructures , so related to 3D
		# plate detection : 
		# ->alpha : keep low.  this will raise the importance of Ra which is the distinguishing factor for plate like structures
		# ->beta : keep extremely high.  this will completely neutralize the Rb effect (the factor will turn into 1 for all pixels)
		# ->gamma : keep extremely low to completely neutralize S effect, but better to set it low to avoid picking up noise
		'frangi3d': {'sigmas': param_xml.get_value('sigmas', ['frangi3d']),  # sigma range and stepsize
			 'alpha': param_xml.get_value('alpha', ['frangi3d']),
			 # alpha : treshold on Lambda2/Lambda3 determines.  Vessellike structures will have a large (lambda2/lambda3 ) with lambda being the largest eigenvalue.  Decreasing alpha will raise the importance of Ra (see formula). So lower to pick out platestructures
			 'beta': param_xml.get_value('beta', ['frangi3d']),
			 # beta : float, optional -> Frangi correction constant that adjusts the filters sensitivity to areas of high variance/texture/structure. alt = which determines the deviationfrom a blob like structure, default .5
			 'gamma': param_xml.get_value('gamma', ['frangi3d']),
			 # gives the threshold between eigenvalues of noise and vessel structure. A thumb rule is dividing the the greyvalues of the vessels by 4 till 6, default 500
			 'black_ridges': param_xml.get_value('black_ridges', ['frangi3d'])},
			# black_ridges : for frangi3D only black_rigdes False seems to work (opposite to frangi2D !)

		'frangi3dmod': {'scale_range': param_xml.get_value('scale_range', ['frangi3dmod']),
			'scale_step': param_xml.get_value('scale_step', ['frangi3dmod']),
			'alpha': param_xml.get_value('alpha', ['frangi3dmod']),
			# alpha : treshold on Lambda2/Lambda3 determines.  Vessellike structures will have a large (lambda2/lambda3 ) with lambda being the largest eigenvalue.  Decreasing alpha will raise the importance of Ra (see formula). So lower to pick out platestructures
			'beta': param_xml.get_value('beta', ['frangi3dmod']),
			# beta : float, optional -> Frangi correction constant that adjusts the filters sensitivity to areas of high variance/texture/structure. alt = which determines the deviationfrom a blob like structure, default .5
			'frangi_c': param_xml.get_value('frangi_c', ['frangi3dmod']),
			# gives the threshold between eigenvalues of noise and vessel structure. A thumb rule is dividing the the greyvalues of the vessels by 4 till 6, default 500
			'black_vessels': param_xml.get_value('black_vessels', ['frangi3dmod']),
			'spacing': param_xml.get_value('spacing', ['frangi3dmod']),
			'structure': param_xml.get_value('structure', ['frangi3dmod']),
			'fh': None  # filehandler for visual logging
			},

		# #frangi3d.frangi(nd_array, scale_range=(1, 10), scale_step=2, alpha=0.5, beta=0.5, frangi_c=500, black_vessels=True) :
		# #https://www.mathworks.com/matlabcentral/fileexchange/24409-hessian-based-frangi-vesselness-filter?focused=b7907f42-0ae3-e1dc-40e6-842a723973ab&tab=function
		# #uses the eigenvectors of the Hessian to compute the likeliness of an image region to vessels, according to the method described by Frangi
		# 'frangi3d':{'scale_range':(6,10),  # 2-tuple of floats, optional -> The range of sigmas used. = related to width of the vessels 
		# 'scale_step':1,        #scale_step : float, optional -> Step size between sigmas.
		# 'alpha':0.1,           #alpha : treshold on Lambda2/Lambda3 determines if its a line(vessel) or a plane like structure default .5;
		# 'beta':0.0001,            #beta : float, optional -> Frangi correction constant that adjusts the filters sensitivity to areas of high variance/texture/structure. alt = which determines the deviationfrom a blob like structure, default .5
		# 'frangi_c':50,    #gives the threshold between eigenvalues of noise and vessel structure. A thumb rule is dividing the the greyvalues of the vessels by 4 till 6, default 500
		# 'black_vessels':True},  #black_ridges : boolean, optional -> When True (the default), the filter detects black ridges; when False, it detects white ridges.

		# remove_small_objects(ar, min_size=64, connectivity=1, in_place=False)
		'RmSmObj': {'min_size': 50,
			# The smallest allowable connected component size (ea 1000 could be the size of a big polar body)
			'connectivity': 2},  # The connectivity defining the neighborhood of a pixel.

		# 3D ! remove_small_objects(ar, min_size=64, connectivity=1, in_place=False)
		'RmSmObj3D': {'min_size': param_xml.get_value('min_size', ['RmSmObj3D']),  # The smallest allowable connected component size
			'connectivity': param_xml.get_value('connectivity', ['RmSmObj3D'])},  # The connectivity defining the neighborhood of a pixel.

		# remove_small_holes(ar, area_threshold=64, connectivity=1, in_place=False, min_size=None)
		'RmSmHol': {'area_threshold': 3000,
			# The maximum area, in pixels, of a contiguous hole that will be filled. Replaces min_size.
			'connectivity': 2},
			# The connectivity defining the neighborhood of a pixel. (referring to the dimension of the structuring element 1 = a cross shaped structuring element (=4 pixels), 2 = 8- pixels, 3=26 pixels (i presume...)

		# 3D ! remove_small_holes(ar, area_threshold=64, connectivity=1, in_place=False, min_size=None)
		'RmSmHol3D': {'area_threshold': 50000,
			# The maximum area, in pixels, of a contiguous hole that will be filled. Replaces min_size.
			'connectivity': 2},  # The connectivity defining the neighborhood of a pixel.

		# threshold_local(image, block_size, method='gaussian', offset=0, mode='reflect', param=None)
		'thrloc': {'block_size': 5,
			 # Odd size of pixel neighborhood which is used to calculate the threshold value (e.g. 3, 5, 7, 21).
			 'method': 'median',
			 # {generic, gaussian, mean, median}, Method used to determine adaptive threshold for local neighbourhood in weighted mean image.
			 'offset': 0,
			 # Constant subtracted from weighted mean of neighborhood to calculate the local threshold value
			 'mode': 'reflect',
			 # {reflect, constant, nearest, mirror, wrap}, The mode parameter determines how the array borders are handled
			 'param': None
			 # Either specify sigma for gaussian method or function object for generic method. This functions takes the flat array of local neighbourhood as a single argument and returns the calculated threshold for the centre pixel.
			 },

		# threshold_minimum(image, nbins=256, max_iter=10000)
		'thrmin': {'nbins': 256,
							 'max_iter': 10000},

		# rescale_intensity(image, in_range="image", out_range="dtype")
		'resint': {'in_range': 'image',  # "image", "dtype", dtype-name or 2-tuple
			 'out_range': 'dtype'
			 },

		# subtract_img,ix_stack,ix_slice
		'subtract': {'subtract_img': None,  # attach the 4D image that you want to subtract here
			 'ix_stack': 0,
			 'ix_slice': 0
			 },

		# kuwahara filtering 5, 9, 13,17,25 ... = (4*k+1)
		'kuwahara': {'winsize': 17
								 },

		# gaussian(image, sigma=1, output=None, mode='nearest', cval=0, multichannel=None, preserve_range=False, truncate=4.0)
		'gaussian': {'sigma': 4,
			 'mode': 'nearest',
			 'preserve_range': True,
			 # Whether to keep the original range of values. Otherwise, the input image is converted according to the conventions of img_as_float.  KEEP = TRUE !
			 'truncate': 4.0  # Truncate the filter at this many standard deviations.
			 },

		# binary_erosion(image, selem=None, out=None)
		'bineros': {'selem': disk(4)
								},

		# binary_dilation(image, selem=None, out=None)
		'bindila': {'selem': disk(5)
								},

		# binary_closing(image, selem=None, out=None)
		'binclos': {'selem': disk(6)},

		# binary_opening(image, selem=None, out=None)
		'binopen': {'selem': disk(3)},

		# rescaling between a range (with sklearn scale) => works only on 2D, outputs a float
		'scale': {'feature_range': (0, 255)},

		# skimage.morphology.reconstruction(seed, mask, method='dilation', selem=None, offset=None)
		'reconstruction': {'method': 'dilation'},

		'cornerthr': {'rel_corner_dim': 0.1,
									'added_buffer': 0.1
									},

		# snake = active_contour(img,
		#       init, alpha=0.3, beta=0.00001, gamma=0.01,
		#      w_line=10000,w_edge=10000) => default values chosen specifically for skeletonize output
		# alpha=0.1;beta=0.0001;gamma=0.01;w-line=50000;w-edges=50000     
		# skimage.segmentation.active_contour(image, snake, alpha=0.01, beta=0.1, w_line=0, w_edge=1, gamma=0.01, bc='periodic', max_px_move=1.0, max_iterations=2500, convergence=0.1)
		'active_contour_deprecated': {'alpha': 0.1,
			 # Snake length shape parameter. Higher values makes snake contract faster
			 'beta': 1,
			 # Snake smoothness shape parameter. Higher values makes snake smoother.
			 'gamma': 0.001,  # Explicit time stepping parameter
			 'w_line': 500000,
			 # Controls attraction to brightness. Use negative values to attract toward dark regions
			 'w_edge': 500000
			 # Controls attraction to edges. Use negative values to repel snake from edges
			 },
		'active_contour': {'alpha': 0.1,
			 # Snake length shape parameter. Higher values makes snake contract faster
			 'beta': 0.01,
			 # Snake smoothness shape parameter. Higher values makes snake smoother.
			 'gamma': 0.01,  # Explicit time stepping parameter
			 'w_line': -600,
			 # Controls attraction to brightness. Use negative values to attract toward dark regions
			 'w_edge': 15000
			 # Controls attraction to edges. Use negative values to repel snake from edges
			 },
			# cv = chan_vese(image, mu=0.25, lambda1=1, lambda2=1, tol=1e-3, max_iter=200,dt=0.5, init_level_set="checkerboard", extended_output=True)
			'chan_vese':      {'mu': param_xml.get_value('mu', ['chan_vese']),
				 'lambda1': param_xml.get_value('lambda1', ['chan_vese']),
				 'lambda2': param_xml.get_value('lambda2', ['chan_vese']), # 
				 'tol': param_xml.get_value('tol', ['chan_vese']),
				 'max_iter': param_xml.get_value('max_iter', ['chan_vese']),
				 'init_level_set':param_xml.get_value('init_level_set', ['chan_vese']),
				 'extended_output':False
				 },

		 'morphological_chan_vese':      {'smoothing': param_xml.get_value('smoothing', ['morphological_chan_vese']),
			 'lambda1': param_xml.get_value('lambda1', ['morphological_chan_vese']),
			 'lambda2': param_xml.get_value('lambda2', ['morphological_chan_vese']), 
			 'iterations': param_xml.get_value('iterations', ['morphological_chan_vese']),
			 'init_level_set':param_xml.get_value('init_level_set', ['morphological_chan_vese'])
			 },
		 #detect_z_membrane(a_input,a_membrane_mask,l_spacing=[1,0.1083474,0.1083474],min_cell_radius = 5,path_output_folder=None,verbose=False)
		 'blend_z_membrane':      {'l_spacing': param_xml.get_value('scaling_ZYX', ['body','RAM'],use_main_keys=False),
			 'sigma_ddz_smoothing': param_xml.get_value('sigma_ddz_smoothing', ['blend_z_membrane']),
			 'min_dist_peak_membrane': param_xml.get_value('min_dist_peak_membrane', ['blend_z_membrane']),
			 'min_dist_between_peaks': param_xml.get_value('min_dist_between_peaks', ['blend_z_membrane']),
			 'peak_thresh_rel': param_xml.get_value('peak_thresh_rel', ['blend_z_membrane']),
			 'peak_thresh_rel_slice': param_xml.get_value('peak_thresh_rel_slice', ['blend_z_membrane']),
			 'SN_thresh': param_xml.get_value('SN_thresh', ['blend_z_membrane']),
			 'z_metric_mode': param_xml.get_value('z_metric_mode', ['blend_z_membrane']),
				'verbose':True
			 },
		 'peak_local_max':{'min_distance':1, 
			'threshold_abs':None, 
			'threshold_rel':0.4, 
			'exclude_border':True, 
			'indices':True, 
			'num_peaks' :10000,
			'footprint':None, 
			'labels':None, 
			'num_peaks_per_label':1
			}
		}

		a_no_signal_filter = np.array([0])

		for nb_filter in lnb_filter_order:
				if d_number_filter[nb_filter] == 'subtract':
						filehandler.d_load_info['load_dir'] = subtract_image_load_dir
						filehandler.d_load_info['f_name'] = subtract_image_f_name
						d_filter_arg['subtract']['subtract_img'] = filehandler.load_tif()

		return d_number_filter, l_3D_filters, d_slice_selector, d_filter_outputdtype, d_filter_arg, a_no_signal_filter

	def set_control_flow_parms_non_parameterized():

		COMPARE_2_SLICES_LvsR = False
		EXAMINE_PROCESSED_STACKS = True
		a_left_right_selector = [[2, 2, 21], [1, 4, 5], [1, 6, 7], [1, 11, 12], [1, 14, 15],
														 [1, 18, 19]]  # [[stack_number, slice_left, slice_right]]
		subtract_image_load_dir = r'C:\Users\wimth\Downloads\@tiffhandling\preprocessing\UseAsinput3'
		subtract_image_f_name = 'processed_4D'
		SAVE_TRESHOLD_PNG = False
		WRITE_EXTRA_TIF = False
		THRESH_EROSION = 0  # if the threshold is x% of MAX_PERC_PIX_TO_PICK_UP , erosion will kick in 
		MAKE_EXCEL_VESSELNESS_SCORE = True

		return COMPARE_2_SLICES_LvsR, EXAMINE_PROCESSED_STACKS, a_left_right_selector, subtract_image_load_dir, subtract_image_f_name, SAVE_TRESHOLD_PNG, WRITE_EXTRA_TIF, THRESH_EROSION, MAKE_EXCEL_VESSELNESS_SCORE

	def read_parms(param_xml):
		param_xml.l_main_keys = ['body', 'preprocessing']

		lnb_filter_order = param_xml.get_value('filter_order', ['flowcontrol'])
		l_stack_number = param_xml.get_value('l_stack_number', ['flowcontrol'])
		l_output_f_names = param_xml.get_value('l_output_f_names', ['flowcontrol'])

		return lnb_filter_order, l_stack_number, l_output_f_names
	
	def prep_active_contour():
		use_deprecated = param_xml.get_value('use_deprecated',['active_contour'])
		init_shape = param_xml.get_value('init_shape',['active_contour'])
				
		nb_points_snake = 400
		
		_,_,y, x = a_4D.shape
		s = np.linspace(0, 2 * np.pi, nb_points_snake)  # Return evenly spaced numbers over a specified interval.
		

		if init_shape=="wide_ellips":
				x_center = round(x / 2)
				y_center = round(y / 2)
				xy_max = max(x, y)
				x = x_center + xy_max * np.cos(s)  
				y = y_center + xy_max * np.sin(s)

				init = np.array([x, y]).T
				
		if init_shape=="fitted_ellips":
				x_center = round(x / 2)
				y_center = round(y / 2)
				xy_max = max(x, y)
				xy_min = min(x, y)
				if x>y:
						x = x_center + xy_max/2 * np.cos(s)
						y = y_center + xy_min/2 * np.sin(s)
				else:
						x = x_center + xy_min/2 * np.cos(s)
						y = y_center + xy_max/2 * np.sin(s)

				init = np.array([x, y]).T
				
		if init_shape=="box":
				delta = 5 # keep some distance from border (in pixels)
				y -= delta
				x -= delta
				sx = np.linspace(delta, x, 100)
				sx_rev = np.linspace(x, delta, 100)
				sy = np.linspace(delta, y, 100)
				sy_rev = np.linspace(y, delta, 100)
				s0 = np.linspace(delta, delta, 100)
				sxmax = np.linspace(x, x, 100)
				symax = np.linspace(y, y, 100)
				na_x = np.concatenate([s0,sx,sxmax,sx_rev])
				na_y = np.concatenate([sy,symax,sy_rev,s0])
				init = np.array([na_x, na_y]).T
				
		return init,use_deprecated

	def filter_threshold_otsu(img):
		thresh = threshold_otsu(img)
		binary = img >= thresh
		return binary

	def filter_threshold_triangle(img):
		thresh = threshold_triangle(img)
		binary = img >= thresh
		return binary

	def filter_threshold_HPassOtsu(img, ix_slice,a_otsu):
		thresh = threshold_otsu(img)
		img[img < thresh] = 0

		a_otsu[ix_slice] = thresh  # logged to excel

		return img

	def filter_collect_Otsu(img, ix_slice,a_otsu):
		thresh = threshold_otsu(img) #returns scalar = otsu-threshold value
		# img [img<thresh] =  0   #original data stays untouched
		thresh/=param_xml.get_value('SEED_THR_DIVIDE_FACTOR', ['collect_stats'])
		

		a_otsu[ix_slice] = thresh  # logged to excel

		return img

	def filter_median(img):
		# very important step for interior noise elimination, clusters noise, disk(2) is better than disk(1) for interior noise reduction.
		# for a harsh reduction choose disk(3), very clean but also more membrane loss
		# the harsher this step, the more binary dilation you need to clear the interior on the first slices
		# using disk(3) for the main filtering, and disk(1) for the low intensity image might be a good idea
		#     if img.dtype=='float64':  #  Images of type float must be between -1 and 1
		#         img = img.astype(np.int64)
		#         print('converted int64..',end='')
		return median(img, **d_filter_arg['median'])

	def filter_laplace(img):
		return laplace(img, **d_filter_arg['laplace'])

	def filter_frangi(img):
		# this frangi outputs the float, no scaling
		frangi_img = frangi(img, **d_filter_arg['frangi'])  # outputs a float
		# frangi_img_int = img_as_int(frangi_img)  # this scales the data between 0 and max int 16 bit (will give different scaling for each slice, so not good)
		
		# frangi creates artefacts (high signal) at every corner of the image (5x5 pixel area). these are always removed
		l  = 5
		frangi_img[:l,:l]=0
		frangi_img[-l:,:l]=0
		frangi_img[:l,-l:]=0
		frangi_img[-l:,-l:]=0
		# print("frangi corner artefacts removed (box {0}X{0})".format(l))

		return frangi_img

	def filter_scale_constant(img):
		#   scales an entire stack with a constant value
		frangi_img_int = np.rint(
				img * 10000)  # frangi is always between 0 and 1, so this will create values between 0 and 10000 (think of it like a probability with max 100,00%)
		return frangi_img_float

	def filter_scale_max(img):
		#   scales an entire stack so that the max gets value 10000 (will fit into int16)
		a_scaled_max = img * (10000 / np.max(img))
		return a_scaled_max

	def filter_frangi3d(img):
		frangi_img = frangi(img, **d_filter_arg['frangi3d'])

		return frangi_img

	#inactivated dependency (but works)
	# def filter_frangi3dmod(img):
	# 	print('arguments : d_filter_arg[frangi3dmod] \n', d_filter_arg['frangi3dmod'])
	# 	d_filter_arg['frangi3dmod']['fh'] = filehandler  # passing on filehandler triggers visual logging
	# 	frangi_img = frangi3dmod(img, **d_filter_arg['frangi3dmod'])
	# 	d_filter_arg['frangi3dmod']['fh'] = "removed"

	# 	return frangi_img

	def write_excel_vesselness_score(a_stack_processed,a_abs_thresh_slice, a_abs_thresh_slice_seed, a_otsu, nb_stack):
		d_df = {}  # the dict that will be used to create the dataframe   
		ls_columns = ["nb_stack",
						"ix_z",
						"_99th",
						"ideal_thr",
						"highest_noise",
						"abs_thresh_slice",
						"abs_thresh_slice_seed",
						"Otsu",
						"no_signal_filter"
						]

		# put filler in empty ls_columns
		a_abs_thresh_slice
		# intialize ls_columns
		l_nb_stack = []
		l_ix_z = []
		_99th = list(np.percentile(a_stack_processed, 99, axis=(1, 2)))
		ideal_thr = []
		highest_noise = []

		abs_thresh_slice = list(a_abs_thresh_slice)
		abs_thresh_slice_seed = list(a_abs_thresh_slice_seed)
		otsu = list(a_otsu)
		no_signal_filter = list(a_no_signal_filter)

		# append the data
		for ix_z, a_slice in enumerate(a_stack_processed):
				l_nb_stack.append(nb_stack)
				l_ix_z.append(ix_z)
				ideal_thr.append(0)
				highest_noise.append(0)

		d_df[ls_columns[0]] = l_nb_stack
		d_df[ls_columns[1]] = l_ix_z
		d_df[ls_columns[2]] = _99th
		d_df[ls_columns[3]] = ideal_thr
		d_df[ls_columns[4]] = highest_noise

		d_df[ls_columns[5]] = abs_thresh_slice
		d_df[ls_columns[6]] = abs_thresh_slice_seed
		d_df[ls_columns[7]] = otsu
		d_df[ls_columns[8]] = no_signal_filter

		# extra columns for histogrambins
		_, a_hist_bins = np.histogram(a_stack_processed, bins=100, range=(0, 10000))  # tuple(array of counts, array of binlimits).  shape of bins = 1 + shape counts
		a_hist_bins = a_hist_bins[1:]  # kick out 0

		a_hist_total = np.zeros((a_stack_processed.shape[0], a_hist_bins.shape[0]))
		for ix_slice, a_slice in enumerate(a_stack_processed):
				a_hist_counts, _ = np.histogram(a_slice, bins=100, range=(0, 10000))
				a_hist_total[ix_slice, ...] = a_hist_counts
		a_hist_total = np.transpose(a_hist_total)

		for ix_bin, bin in enumerate(a_hist_bins):
				ls_columns.append(str(bin) + '_bin')
				d_df[str(bin) + '_bin'] = a_hist_total[ix_bin]

		# save the data
		# filehandler.d_save_info['f_name'] = 'frangi_vesselness_scores'
		# filehandler.save_data(data=pd.DataFrame(d_df), csv_columns=ls_columns, file_ext='csv', verbose=True)
		#TODO uncomment
		#dflog_append =  {'frangi_vesselness_scores':pd.DataFrame(d_df,columns=ls_columns)}
		#append_dflog(dflog_append,nb_stack,axis=0)

		return pd.DataFrame(d_df)

	def filter_remove_small_objects(img):
		# needs int or bool input ! so precede with otsu for example
		# This will work even better in 3D
		return remove_small_objects(img, **d_filter_arg['RmSmObj'], in_place=True)

	def filter_remove_small_holes(img):
		# needs int or bool input ! so precede with otsu for example
		# This will work even better in 3D
		# this fills up circular holes, so it will not fill in membrane gaps ! so effect is limited, still beneficial for occasional holes in membrane
		# a good value for this is the minimum size of a cell
		return remove_small_holes(img, **d_filter_arg['RmSmHol'], in_place=True)

	def filter3D_remove_small_objects(img):
		# in 3D do not take connectivity = 3 , this will link too much between the z-stacks fixing some noise.  pick connectivity 1
		return remove_small_objects(img, **d_filter_arg['RmSmObj3D'], in_place=True)

	def filter3D_remove_small_holes(img):
		return remove_small_holes(img, **d_filter_arg['RmSmHol3D'], in_place=True)

	def filter_threshold_li(img):
		# bad result : otsu is better
		thresh = threshold_li(img)
		binary = img >= thresh
		return binary

	def filter_threshold_local(img):
		# needs int or bool input ! so precede with otsu for example
		# This will work even better in 3D
		# this fills up circular holes, so it will not fill in membrane gaps ! so effect is limited, still beneficial for occasional holes in membrane
		# a good value for this is the minimum size of a cell
		thresh = threshold_local(img, **d_filter_arg['thrloc'])
		binary = img >= thresh
		return binary

	def filter_threshold_minimum(img):
		# bad result : otsu is better
		thresh = threshold_minimum(img)
		binary = img >= thresh
		return binary

	def filter_binary_erosion(img):
		return binary_erosion(img, **d_filter_arg['bineros'])

	def filter_binary_dilation(img):
		# in as binary, out as binary
		# this is the opposite of what you want -> will enlarge dark spots = the membrane + noise.  dilation does the opposite
		return binary_dilation(img, **d_filter_arg['bindila'])

	def filter_inverse(img):
		# the membrane will have value 1, the background will be 0
		return np.invert(img)

	def filter_rescale_intensity(img):
		##print('max',np.max(img),'min',np.min(img))
		# it is best to use the default : so with the image defining the input range, the output range defined by the dtype
		# makes sense to do this a first step in the chain
		img_rescaled = rescale_intensity(img, **d_filter_arg['resint'])
		return img_rescaled

	def filter_subtract_image(img):
		# always use this at the end of the chain, on the already inverted binary image
		return subtract_image(img, **d_filter_arg['subtract'])

	def filter_kuwahara(img):
		# min size of window = 5 . picking 9 causes way too much blurring of the image
		return Kuwahara.Kuwahara(img.astype(np.int64), **d_filter_arg['kuwahara'])

	def filter_gaussian(img):
		return gaussian(img, **d_filter_arg['gaussian'])

	def filter_binary_closing(img):
		return binary_closing(img, **d_filter_arg['binclos'])

	def filter_binary_opening(img):
		return binary_opening(img, **d_filter_arg['binopen'])

	def filter_scaling(img):
		scaler = MinMaxScaler(**d_filter_arg['scale'])
		scaler = scaler.fit(img)
		return scaler.transform(img)

	def filter_flip(img):

		return (img * (-1)) + np.max(img)

	def filter_asint(img):
		return img_as_int(img)

	def filter_threshold_median_max_corners(img):
		y_max_ix, x_max_ix = [i - 1 for i in img.shape]
		y_delta, x_delta = [ceil(i * d_filter_arg['cornerthr']['rel_corner_dim']) for i in img.shape]
		a_upper_left = img[0:y_delta, 0:x_delta]
		a_upper_right = img[0:y_delta, x_max_ix - x_delta:x_max_ix]
		a_lower_left = img[y_max_ix - y_delta:y_max_ix, 0:x_delta]
		a_lower_right = img[y_max_ix - y_delta:y_max_ix, x_max_ix - x_delta:x_max_ix]
		threshold = np.median(
				[np.max(a_upper_left), np.max(a_lower_left), np.max(a_upper_right), np.max(a_lower_right)])
		threshold += threshold * d_filter_arg['cornerthr']['added_buffer']
		binary = img >= threshold

		return binary

	# functions
	def compare_good_bad_plot(a_good_bad, current_filter_ix, slice_left_nb, slice_right_nb):
		fig, (ax1, ax2) = plt.subplots(1, 2, sharey=True)
		fig.suptitle(compose_filters_desc(current_filter_ix), fontsize=9)
		s_title = 'sl{0}'.format(slice_left_nb);
		ax1.set_title(s_title)
		ax1.imshow(a_good_bad[0])

		output = StringIO()
		current_filter = d_number_filter.get(lnb_filter_order[current_filter_ix], 'no filter found')
		if current_filter in l_3D_filters:
				current_filter = current_filter + '3D'
				#print('3D MODE :', file=output)
		#print('sl' + str(slice_right_nb), file=output, end="")
		#pprint.pprint(d_filter_arg.get(current_filter, 'no parms'), stream=output)
		ax2.set_title(output.getvalue(), fontsize=4)
		ax2.imshow(a_good_bad[1])

		return fig

	def compose_filters_desc(current_filter_ix):
		filters_name = ''
		if current_filter_ix < 1: return

		for i in range(1, current_filter_ix + 1):
				filter_add = d_number_filter.get(lnb_filter_order[i], '_')
				if filter_add == 'write_output' or 'write_output_no_signal_filtered':
						continue
				else:
						filters_name += filter_add + '_'
		return filters_name

	def subtract_image(img, subtract_img, ix_stack, ix_slice):
		subtract_slice = slice_tif(subtract_img, ix_slice_time=[ix_stack, ix_stack + 1],
															 ix_slice_z=[ix_slice, ix_slice + 1], verbose=True)
		img[subtract_slice == 1] = 0
		return img

	def filter_skeletonize(img, ix_slice):
			skeleton = skeletonize(img)
			return skeleton

	def filter_skeletonize_3d(img):
			skeleton = skeletonize_3d(img)
			return skeleton

	def filter_medial_axis(img,ix_slice):  # very similar to skeletonize, but slightly more side branches, so use skeletonize instead
		skeleton = medial_axis(img, return_distance=False)
		return skeleton

	def collect_stats(a_stack,a_otsu):
		#   data needed for reconstruction and absolute thresholding

		a_abs_thresh_slice = np.zeros(a_stack.shape[0])
		a_abs_thresh_slice_seed = np.zeros(a_stack.shape[0])
		for ix_z, a_slice in enumerate(a_stack):
				a_nonzero = np.ravel(a_slice[a_slice > 0])
				if a_nonzero.size != 0:
						# a_abs_thresh_slice[ix_z]                        = np.percentile(a_nonzero,10)
						# a_abs_thresh_slice_seed[ix_z]                   = np.percentile(a_nonzero,99)
						a_abs_thresh_slice_seed[ix_z] = a_otsu[ix_z]  # use otsu as seed
						a_abs_thresh_slice[ix_z] = a_otsu[ix_z] / param_xml.get_value('MEMBRANE_ACCEPTANCE_LEVEL',['collect_stats'])
				else:
						print('temp =>slice contains all zeros.  Either signal is extremely low in this slice , or something went wrong with the scaling')
						a_abs_thresh_slice[ix_z] = 0
						a_abs_thresh_slice_seed[ix_z] = 0

		# no signal detection
		def slice_has_signal(z_i):
				if a_abs_thresh_slice_seed[z_i] > param_xml.get_value('NO_SIGNAL_THRESH', ['collect_stats']):
						#print('temp: ix_z{0} has {1} as a_abs_thresh_slice_seed[z_i] for threshold {2}'.format(z_i,a_abs_thresh_slice_seed[z_i],param_xml.get_value('NO_SIGNAL_THRESH', ['collect_stats'])))
						return True
				return False

		a_no_signal_filter = np.zeros(a_stack.shape[0], dtype='int')
		for z_i in range(a_stack.shape[0] - 1, - 1, -1):  # Bottom to top
				if slice_has_signal(z_i):
						break
				else:
						a_no_signal_filter[z_i] = 1

		for z_i in range(a_stack.shape[0]):  # top to bottom
				if slice_has_signal(z_i):
						break
				else:
						a_no_signal_filter[z_i] = 1

		# log data in excel and plots

		return a_abs_thresh_slice, a_abs_thresh_slice_seed, a_no_signal_filter

	def filter_reconstruction(img, ix_slice, a_abs_thresh_slice, a_abs_thresh_slice_seed):
		'''
		This is the downhill filter.  This reconstruction is variable ! it will only be done for thresholds that fall below the minimum
		it expects as input the frangi output
		'''
		thresh = a_abs_thresh_slice[ix_slice]
		thresh_seed = a_abs_thresh_slice_seed[ix_slice]

		seed = img.copy()
		seed[seed < thresh_seed] = 0
		img = reconstruction(seed=seed, mask=img, **d_filter_arg['reconstruction'])
		#             print('reconstruction applied to slice {0} for threshold {1} and thresh_seed {2}'.format(ix_slice + 1,thresh,thresh_seed))

		return img

	def filter_threshold_absolute(img, ix_slice,a_abs_thresh_slice):

		thresh = a_abs_thresh_slice[ix_slice]
		binary = img >= thresh

		return binary

	def save_threshold_graph(a_abs_thresh_slice):
		fig = plt.figure()  # start with a new figureobject
		ax = fig.add_subplot(111)  # add subplot to the figure (fills entire figure)
		a_abs_thresh_slice_pic = [min(i, 1000) for i in a_abs_thresh_slice]  # cap the extreme threshold for plotting purposes
		ax.plot(a_abs_thresh_slice_pic)  # put x and y on the subpot

		filehandler.extend_save_info(extra_dir_1='threshold_png')
		filehandler.d_save_info['f_name'] = 'variable_threshold_pixel_intensity'
		filehandler.save_data(fig, file_ext='png')
		filehandler.pop_save_info()

		return

	def filter_active_contour(img, ix_slice,img_original):
		'''
		img_new :the active contour (solely), 
		img     = active contour overlayed with the image
		img_original = the raw data

		'''

		if use_deprecated_active_contour:
			snake = active_contour(gaussian(img, 3), init_active_contour, **d_filter_arg['active_contour_deprecated'])
		else:
			snake = active_contour(gaussian(img_original, 10), init_active_contour, **d_filter_arg['active_contour'])

		img_new = np.zeros_like(img)
		img_new[tuple(np.transpose(np.floor(snake).astype('int'))[[1, 0], :])] = 1

		img[img == 1] = 2  # we give the membrane value 2, so the snake can have 1
		img[tuple(np.transpose(np.floor(snake).astype('int'))[[1, 0], :])] = 1  # snake will have 1, the membrane 2

		return img_new, img

	def filter_chan_vese(img, ix_slice):
		'''
		will give back the chan_vese_segmentation overlayed onto original image
		'''

		cv = chan_vese(img, **d_filter_arg['chan_vese'])  #nd array bool (only 2D possible)
		

		img[img == 1] = 2  # we give the membrane value 2, so the active contour can have 1
		img[cv] = 1  # snake will have 1, the membrane 2

		cv = np.where(cv,1,0)

		return cv, img

	def filter_morphological_chan_vese(img):
		'''
		will give back the morphological chan_vese_segmentation overlayed onto original image
		'''

		cv = morphological_chan_vese(img, **d_filter_arg['morphological_chan_vese'])  #nd array bool (only 2D possible)
		

		img[cv] = 1  # snake will have 1, the membrane 2

		return img

	def filter_blend_z_membrane(a_input,a_membrane_overlay,a_membrane,a_exterior_mask,ix_stack,nb_stack):
		"""
		a_input = the current image stack (raw)
		a_membrane_overlay= the threshold stack (=the otsu cutoff)
		a_membrane = the membrane stack (can include manual
		"""
		d_filter_arg['blend_z_membrane']['path_output_folder'] = Path(filehandler.get_root_save_location()) / '002_preprocessing' / 'z_membrane_intermediate_steps_{0}'.format(ix_stack)
		a_bool_peaks,dflog_append  = detect_z_membrane(a_input=a_input,
									a_membrane_mask=np.where(a_membrane_overlay,0,1),
									a_membrane=a_membrane,
									a_exterior_mask=a_exterior_mask,
									**d_filter_arg['blend_z_membrane'])
		a_membrane_blend_z = np.where(a_bool_peaks,3,a_membrane)  # z-membrane gets '3' as a value, just for ease of indentification
		#TODO uncomment
		#append_dflog(dflog_append,nb_stack)

		return a_membrane_blend_z

	def filter_blend_manual_exterior(img, ix_slice,img_exterior_outline):
		img[img == 1] = 2  # we give the membrane detection value 2
		img = np.where(img_exterior_outline>0,1,img) # exterior outline will have value 1, the membrane 2
		return img

	def filter_exterior_mask(img, ix_slice):
		'''
		will take extract the exterior mask using a distance transform (expects a binary image, like the skeletonized image as input)
		WATCH OUT : it expects 'img' to contain exterior-interior boundary indicated by the value '1' !(so other values are ignored)
		'''
		img_snake_points = np.ones_like(img)
		img_snake_points[img == 1] = 0  # selecting 1 as the signal = convention(snake can also be from manual input, cfr filter_blend_manual_exterior)
		img_DT = distance_transform_edt(img_snake_points)
		img_DT = -img_DT  # membrane should be mountain

		#new
		t_a_local_minima = local_minima(img_DT, selem=None, connectivity=None, indices=True, allow_borders=False)

		markers = np.zeros_like(img_DT, dtype='int')

		y_center, x_center = [round(i/2) for i in markers.shape]
		# markers[y_center, x_center] = 1  # label the center with 1
		if len(t_a_local_minima[0]) > 0:
			l_dist_center_minima = [abs(y-y_center) + abs(x-x_center) for y,x in zip(t_a_local_minima[0],t_a_local_minima[1])]    
			ix_centered_minimum = l_dist_center_minima.index(min(l_dist_center_minima))
			markers[t_a_local_minima[0][ix_centered_minimum], t_a_local_minima[1][ix_centered_minimum]] = 1  # label the local minimum closest to the center with 1

		markers[0, 0] = 2  # label the outside with 2

		img = watershed(img_DT, markers)
		img[img == 2] = 0  # set the exterior to zero (it's a mask), the interior will have 1

		return img

	def write_subtracted_image():
		filehandler.take_snapshot()
		filehandler.d_load_info = None
		filehandler.d_save_info['f_name'] = 'subtract_image'
		slice_tif(na_tif=d_filter_arg['subtract']['subtract_img'],
							ix_slice_z=None,
							ix_slice_time=[l_stack_number[0] - 1, l_stack_number[-1]],
							filehandler=filehandler,
							verbose=False)
		filehandler.reset_to_snapshot()

		return


	def write_dflog(dflog):

		if "z_metric" in dflog:
			l_extra_col = list(dflog['z_metric'].index)
			# l_extra_col = ['z_ix={0}'.format(i) for i in range (len(l_ixz_names))]
			l_extra_col[-3:]= [']ix_min','ix_max[','nb_peaks']
			dflog['z_metric'] = pd.concat([pd.DataFrame({'row':l_extra_col}),dflog['z_metric']],axis=1)

		f_name = Path(filehandler.get_save_location()) / "log_preprocess.xlsx"
		with pd.ExcelWriter(f_name) as writer:
			for tab_i, df_i in dflog.items():
				df_i.to_excel(writer, sheet_name=tab_i,index=True)
		print("excel dds output{0}".format(f_name))

		return

	def append_dflog(dflog_append,nb_stack,axis=1):
		
		for tab_i, df_i in dflog_append.items():
			if axis==1:
				df_i.rename(columns={df_i.columns[0]: nb_stack}, inplace = True)  #rename first column to the stack number
			if tab_i in dflog:
				dflog[tab_i] = pd.concat([dflog[tab_i],df_i],axis=axis) # axis=1= add as column, if indices do not match : use reset_index(drop=True)
			else:
				dflog[tab_i] = df_i
		return dflog

	def write_debug_log(output_log):

		[print('step', str(ix_stack), ':', d_number_filter.get(i, 'not found'), file=output_log) for ix_stack, i in
		 enumerate(lnb_filter_order)]

		print('\n slice selector : \n ---------------------', file=output_log)
		pprint.pprint(d_slice_selector, stream=output_log)
		print('\n Parameters used : \n ---------------------', file=output_log)
		pprint.pprint(d_filter_arg, stream=output_log)
		print('\n these filters were applied in 3D:  \n ---------------------', file=output_log)
		pprint.pprint(l_3D_filters, stream=output_log)
		print('\n file used as input :  \n ---------------------', file=output_log)
		pprint.pprint(filehandler.d_load_info, stream=output_log)
		filehandler.d_save_info['f_name'] = 'parameters_of_filters '
		print('\n MEMBRANE_ACCEPTANCE_LEVEL :  ',
					param_xml.get_value('MEMBRANE_ACCEPTANCE_LEVEL', ['collect_stats']), file=output_log)
		print('\n NO_SIGNAL_THRESH : ', param_xml.get_value('NO_SIGNAL_THRESH', ['collect_stats']), file=output_log)

		filehandler.d_save_info['f_name'] = 'debug_log'
		filehandler.save_data(output_log.getvalue(), file_ext='txt', verbose=False)

		return

	###################################################################################################################################################################
	# load parms
	lnb_filter_order, l_stack_number, l_output_f_names = read_parms(param_xml)

	# set control flow (non parametrized)
	d_number_filter, l_3D_filters, d_slice_selector, d_filter_outputdtype, d_filter_arg, a_no_signal_filter = set_filter_parameters(
			param_xml)
	COMPARE_2_SLICES_LvsR, EXAMINE_PROCESSED_STACKS, a_left_right_selector, subtract_image_load_dir, subtract_image_f_name, SAVE_TRESHOLD_PNG, WRITE_EXTRA_TIF, THRESH_EROSION, MAKE_EXCEL_VESSELNESS_SCORE = set_control_flow_parms_non_parameterized()

	# load the data + route save folder
	a_4D = filehandler.load_tif(storage_name='IMG_RAW_FILE')
	if len(a_4D.shape) == 3:
		a_4D = a_4D[np.newaxis, :]
		print(a_4D.shape, " a dummy dimension was added")
			
	filehandler.extend_save_info(extra_dir_1='002_preprocessing', from_root=True, take_snapshot_after=True)
	filehandler.d_save_info['nb_stack'] = str(a_left_right_selector[0][0])
	output_log = StringIO()

	#some preprocessing in advance
	if 41 in lnb_filter_order: #manually inputted file marking inside-outside border is needed
		with TiffFile(filehandler.get_f_name('img_exterior_outline')) as tif:
			a_exterior_outline = tif.asarray()
		if len(a_exterior_outline.shape) == 3:
			a_exterior_outline = a_exterior_outline[np.newaxis, :]
			print(a_exterior_outline.shape, " a dummy dimension was added to a_exterior_outline")
			
	if 34 in lnb_filter_order:
		init_active_contour,use_deprecated_active_contour = prep_active_contour()


	if l_stack_number == 'all':
			l_stack_number = range(1, a_4D.shape[0] + 1)
	z, y, x = a_4D.shape[-3:]
	t = len(l_stack_number)
	f = len(l_output_f_names)
	a_4D_processed = np.zeros((f, t, z, y, x),dtype=a_4D.dtype)  # the output of some filters are float, dtype int64 will cause 0.07 to be set to zero for example (coercing)
	dflog={}
	def stack_task(ix_stack, nb_stack):
		a_4D_processed_i = np.zeros((f, z, y, x),dtype=a_4D.dtype)
		#print('*processing stack number ', nb_stack, '>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
		ix_output_file = 0
		filehandler.d_save_info['nb_stack'] = nb_stack
		a_stack = slice_tif(a_4D, ix_slice_z=None, ix_slice_time=[nb_stack - 1, nb_stack], verbose=True)
		a_stack_processed = a_stack.copy()
		a_otsu = np.zeros(a_stack.shape[0])

		for ix_filter, filter_nb in enumerate(lnb_filter_order):  # FILTER LOOP
			s_current_filter = d_number_filter[filter_nb]
			#print('{2}**starting the {0} filter on stack {1}'.format(s_current_filter, nb_stack, '\n'), flush=True)

			slice_range = d_slice_selector.get(s_current_filter, [])

			# iterating and updating with different dtype causes coercing, so work with a temp stack
			a_stack_dtype = d_filter_outputdtype.get(s_current_filter, a_4D.dtype)
			a_stack_temp = np.zeros(a_stack_processed.shape, dtype=a_stack_dtype)

			

			if s_current_filter == 'blend_manual_exterior':
				a_stack_exterior_outline = slice_tif(a_exterior_outline, ix_slice_z=None, ix_slice_time=[nb_stack - 1, nb_stack], verbose=True)

			if s_current_filter in l_3D_filters:  # in 3D mode
				#print('***working in 3D~')
				if s_current_filter == 'RmSmObj3D':
					a_stack_temp = filter3D_remove_small_objects(a_stack_processed)
				elif s_current_filter == 'RmSmHol3D':
					a_stack_temp = filter3D_remove_small_holes(a_stack_processed)
				elif s_current_filter == 'frangi3d':
					a_stack_temp = filter_frangi3d(a_stack_processed)
				elif s_current_filter == 'frangi3dmod':
					#a_stack_temp = filter_frangi3dmod(a_stack_processed)
					continue #bypassed dependency
				elif s_current_filter == 'skeletonize3d':
					a_stack_temp = filter_skeletonize_3d(a_stack_processed)
				elif s_current_filter == 'write_output':
					# if s_prev_filter=='collect_Otsu':
					# a_4D_processed[ix_output_file,ix_stack,...] = a_stack_snapshot
					# else:
					a_4D_processed_i[ix_output_file, ...] = a_stack_processed
					ix_output_file += 1
					a_stack_temp = a_stack_processed
				elif s_current_filter == 'write_output_no_signal_filtered':
					a_4D_processed_i[ix_output_file, ...] = a_stack_processed
					if l_output_f_names[ix_output_file] == 'exterior_outline':
							a_4D_processed_i[ix_output_file,  ...][a_stack_processed!=1] = 0
					a_4D_processed_i[ix_output_file,  np.where(a_no_signal_filter == 1), ...] = 0
					
					ix_output_file += 1
					a_stack_temp = a_stack_processed
				elif s_current_filter == 'scale_constant':
					a_stack_temp = filter_scale_constant(a_stack_processed)
				elif s_current_filter == 'scale_max':
					a_stack_temp = filter_scale_max(a_stack_processed)

				elif s_current_filter == 'collect_stats':
					#TODO uncomment
					a_abs_thresh_slice, a_abs_thresh_slice_seed, a_no_signal_filter = collect_stats(a_stack_processed,a_otsu)
					#if MAKE_EXCEL_VESSELNESS_SCORE: df_frangi = write_excel_vesselness_score(a_stack_processed,a_abs_thresh_slice, a_abs_thresh_slice_seed, a_otsu, nb_stack)
					#if SAVE_TRESHOLD_PNG: save_threshold_graph(a_abs_thresh_slice)
					a_stack_temp = a_stack_processed
				elif s_current_filter == 'blend_z_membrane':
					a_stack_temp = filter_blend_z_membrane(a_input=a_stack,
						a_membrane_overlay=a_4D_processed_i[l_output_f_names.index('threshold'),...],
						a_membrane=a_4D_processed_i[l_output_f_names.index('membranes'),...],
						a_exterior_mask=a_4D_processed_i[l_output_f_names.index('exterior_mask'),...],
						ix_stack=ix_stack, nb_stack= nb_stack)
				elif s_current_filter == 'morphological_chan_vese':
					a_stack_temp = filter_morphological_chan_vese(a_stack_processed)
				if len(slice_range):
					a_stack_processed[slice_range[0]:slice_range[1]] = a_stack_temp[slice_range[0]:slice_range[1]]
				else:
					a_stack_processed = a_stack_temp
				s_prev_filter = s_current_filter


			else:
				def slice_task(ix_slice, a_slice):
					#print(a_slice.size,  flush=True)
					#print(isinstance(a_slice, np.memmap),  flush=True)

					if len(slice_range):
						if ix_slice not in range(slice_range[0], slice_range[1]):
							#print("_", end="");
							return a_slice	
					try:
						if s_current_filter == 'otsu':
							a_slice = filter_threshold_otsu(a_slice)
						elif s_current_filter == 'median':
							a_slice = filter_median(a_slice)
						elif s_current_filter == 'laplace':
							a_slice = filter_laplace(a_slice)
						elif s_current_filter == 'frangi':
							a_slice = filter_frangi(a_slice)
						elif s_current_filter == 'RmSmObj':
							a_slice = filter_remove_small_objects(a_slice)
						elif s_current_filter == 'RmSmHol':
							a_slice = filter_remove_small_holes(a_slice)
						elif s_current_filter == 'thrli':
							a_slice = filter_threshold_li(a_slice)
						elif s_current_filter == 'thrloc':
							a_slice = filter_threshold_local(a_slice)
						elif s_current_filter == 'thrmin':
							a_slice = filter_threshold_minimum(a_slice)
						elif s_current_filter == 'bineros':
							a_slice = filter_binary_erosion(a_slice)
						elif s_current_filter == 'bindila':
							a_slice = filter_binary_dilation(a_slice)
						elif s_current_filter == 'invert':
							a_slice = filter_inverse(a_slice)
						elif s_current_filter == 'resint':
							a_slice = filter_rescale_intensity(a_slice)
						elif s_current_filter == 'subtract':
							d_filter_arg['subtract']['ix_slice'] = ix_slice
							d_filter_arg['subtract']['ix_stack'] = nb_stack - 1
							a_slice = filter_subtract_image(a_slice)
						elif s_current_filter == 'kuwahara':
							a_slice = filter_kuwahara(a_slice)
						elif s_current_filter == 'gaussian':
							a_slice = filter_gaussian(a_slice)
						elif s_current_filter == 'binclos':
							a_slice = filter_binary_closing(a_slice)
						elif s_current_filter == 'binopen':
							a_slice = filter_binary_opening(a_slice)
						elif s_current_filter == 'scale':
							a_slice = filter_scaling(a_slice)
						elif s_current_filter == 'HPassOtsu':
							a_slice = filter_threshold_HPassOtsu(a_slice, ix_slice, a_otsu)
						elif s_current_filter == 'collect_Otsu':
							a_slice = filter_collect_Otsu(a_slice, ix_slice, a_otsu)
						elif s_current_filter == 'thrtriangle':
							a_slice = filter_threshold_triangle(a_slice)
						elif s_current_filter == 'flip':
							a_slice = filter_flip(a_slice)
						elif s_current_filter == 'asint':
							a_slice = filter_asint(a_slice)
						elif s_current_filter == 'thrabs':
							a_slice = filter_threshold_absolute(a_slice, ix_slice, a_abs_thresh_slice)
						elif s_current_filter == 'reconstruction':
							a_slice = filter_reconstruction(a_slice, ix_slice, a_abs_thresh_slice, a_abs_thresh_slice_seed)
						elif s_current_filter == 'cornerthr':
							a_slice = filter_threshold_median_max_corners(a_slice)
						elif s_current_filter == 'skeletonize':
							a_slice = filter_skeletonize(a_slice, ix_slice)
						elif s_current_filter == 'medial_axis':
							a_slice = filter_medial_axis(a_slice, ix_slice)
						elif s_current_filter == 'active_contour':
							a_active_contour_slice, a_slice = filter_active_contour(a_slice, ix_slice,a_stack[ix_slice])
						elif s_current_filter == 'chan_vese':
							_, a_slice = filter_chan_vese(a_slice, ix_slice)
						elif s_current_filter == 'blend_manual_exterior':
							a_slice = filter_blend_manual_exterior(a_slice, ix_slice, a_stack_exterior_outline[ix_slice])
						elif s_current_filter == 'exterior_mask':
							a_slice = filter_exterior_mask(a_slice, ix_slice)
					except Exception as e:
							logging.error(traceback.format_exc())

					# apply after 1 slice of 1 stack is processed with 1 filter

					#a_stack_temp[ix_slice] = slice_task(a_slice)  # dtype must match, otherwise implicit coercing
					#print('~', end='', flush=True)

					return a_slice


				#if s_current_filter == 'active_contour':
				#	a_stack_temp = Parallel(n_jobs=-1, verbose=10, max_nbytes=None, prefer="threads")(delayed(slice_task)(ix_slice,a_slice) for ix_slice, a_slice in enumerate(a_stack_processed))
				#else:
				#	for ix_slice, a_slice in enumerate(a_stack_processed):  # in 2D mode : SLICE LOOP
				#		a_stack_temp[ix_slice] = slice_task(ix_slice,a_slice)  # dtype must match, otherwise implicit coercing
				
				#a_stack_temp = [slice_task(ix_slice,a_slice) for ix_slice, a_slice in enumerate(a_stack_processed) ]

				for ix_slice, a_slice in enumerate(a_stack_processed):  # in 2D mode : SLICE LOOP
					a_stack_temp[ix_slice] = slice_task(ix_slice,a_slice)  # dtype must match, otherwise implicit coercing

				#force correct dtype
				a_stack_temp = np.array(a_stack_temp, dtype=a_stack_dtype)

				# apply after all slices of 1 stack is processed with 1 filter (2D)
				# if s_current_filter=='collect_Otsu':  #this filter leaves the data untouched ! used for data collection or a_temp used for visualisation 
				# a_stack_snapshot = a_stack_temp.copy()
				# else:
				a_stack_processed = a_stack_temp
				s_prev_filter = s_current_filter

			# apply after 1 stack is processed with 1 filter (2D or 3D)
			#print('output>>', a_stack_processed.dtype)

			#TODO uncomment
			#if EXAMINE_PROCESSED_STACKS:
				
				#s_name = 'the processed stack after filter {0} during step {1} of stack {2}'.format(s_current_filter,
				#						str(ix_filter),
				#						str(ix_stack))
				#examine(a_stack_processed, s_name, output=output_log)

			if COMPARE_2_SLICES_LvsR and s_current_filter not in ['write_output', 'write_output_no_signal_filtered',
																														'collect_stats']:
				filehandler.extend_save_info(extra_dir_1='compare_2slices', reset_to_snapshot=True)

				for good_bad_stack_nb, slice_left_nb, slice_right_nb in a_left_right_selector:
					if nb_stack == good_bad_stack_nb:
						a_good_bad = [a_stack_processed[slice_left_nb - 1], a_stack_processed[slice_right_nb - 1]]
						filehandler.d_save_info['f_name'] = 'step' + str(
								ix_filter) + '_' + s_current_filter + '_' + str(slice_left_nb) + 'VS' + str(slice_right_nb)
						fig = compare_good_bad_plot(a_good_bad, current_filter_ix=ix_filter,
																				slice_left_nb=slice_left_nb, slice_right_nb=slice_right_nb)
						filehandler.save_data(fig, file_ext='png', verbose=False)
				filehandler.reset_save_info()

			#TODO uncomment
			#if WRITE_EXTRA_TIF:  # if you want to write a tif of a certain stack,this is the place
			#	if s_current_filter == 'reconstruction' and nb_stack == 1:
			#		filehandler.d_save_info['nb_stack'] = nb_stack;
			#		filehandler.d_save_info['f_name'] = 'after_reconstruction'
			#		filehandler.save_data(a_stack_processed, file_ext='tif', verbose=True)

		# apply after 1 stack is fully processed with all filters
		#TODO uncomment
		#print(examine(a_stack_processed, output=output_log))
		# a_4D_processed[ix_stack,...] = a_stack_processed
		return a_4D_processed_i

	a_4D_processed_swap = np.zeros((t, f, z, y, x),dtype=a_4D.dtype)

	if USE_PARALLEL:
		print("USING PARALLEL")
		a_4D_processed_swap = Parallel(n_jobs=4, verbose=10)(delayed(stack_task)(ix_stack, nb_stack) for ix_stack, nb_stack in enumerate(l_stack_number))
		a_4D_processed_swap = np.array(a_4D_processed_swap, dtype=a_4D.dtype)
	else:
		print("NOT USING PARALLEL")
		for ix_stack, nb_stack in enumerate(l_stack_number):  # STACK LOOP
			a_4D_processed_swap[ix_stack, ...] = stack_task(ix_stack, nb_stack)

	a_4D_processed = np.swapaxes(a_4D_processed_swap, 0,1)


	# apply after all stacks are fully processed
	filehandler.d_save_info['nb_stack'] = ''
	for ix_file in range(0, f):
		filehandler.d_save_info['f_name'] = l_output_f_names[ix_file]
		filehandler.save_data(a_4D_processed[ix_file, ...], file_ext='tif', verbose=True)

			# log and summary to file and screen
	write_debug_log(output_log)
	#TODO uncomment
	#write_dflog(dflog)

	for nb_filter in lnb_filter_order:
		if d_number_filter[nb_filter] == 'subtract':
				write_subtracted_image()

	print('All preprocess data written to : ');
	print(filehandler.get_save_location())

	return