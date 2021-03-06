"""
Created on 8 Aug 2019
- composes a csv of spheres that can be used as the input for the meshing (skin surface meshing)
- option to shrink spheres to remove all overlap

@author: wimth
"""

import os
import re
import sys
from collections import namedtuple
from dataclasses import dataclass  # only in python 3.7...
from pathlib import Path

import numpy as np
import math
import pandas as pd
from helper_functions import get_3D_sphere_coordinates
from scipy.spatial import distance
from tifffile import TiffFile, imsave


def mpacts_input_generator(param_xml, filehandler):
	def read_parms(param_xml):
		d_parm= {}
		param_xml.l_main_keys = ['body', 'mpacts_input_generator']
		d_parm['input_file_csv'] = param_xml.get_value('input_file_csv', ['paths'])
		d_parm['input_file_frangi'] = param_xml.get_value('input_file_frangi', ['paths'])
		d_parm['input_file_threshold'] = param_xml.get_value('input_file_threshold', ['paths'])
		d_parm['output_folder'] = param_xml.get_value('output_folder', ['paths'])

		d_parm['nb_stack'] = param_xml.get_value('nb_stack', ['process_flow'])
		d_parm['nb_stack_timelapse'] = param_xml.get_value('nb_stack_timelapse', ['process_flow'])
		d_parm['shrink_spheres'] = param_xml.get_value('shrink_spheres', ['process_flow'])
		d_parm['overlap_tolerance'] = param_xml.get_value('overlap_tolerance', ['parms'])
		d_parm['file_spheres'] = param_xml.get_value('file_spheres', ['paths', 'output_folder'])
		d_parm['img_membranes_blend_z'] = param_xml.get_value('img_membranes_blend_z',['paths'])
		d_parm['img_exterior_outline'] = param_xml.get_value('img_exterior_outline',['paths'])

		param_xml.l_main_keys = ['body', 'RAM']
		if param_xml.get_value('RAW_IMG_DIM_TZYX'):
			_, d_parm['zmax'], d_parm['ymax'], d_parm['xmax'] = param_xml.get_value('RAW_IMG_DIM_TZYX')
		else:
			_, d_parm['zmax'], d_parm['ymax'], d_parm['xmax'] = filehandler.d_loaded_files['IMG_RAW'].shape

		param_xml.l_main_keys = ['body', 'spheresDT', 'parms']
		d_parm['zdim'],d_parm['ydim'],d_parm['xdim'] = param_xml.get_value('scaling_ZYX',l_path_keys=['body','RAM'],use_main_keys=False)

		param_xml.l_main_keys = ['body', 'MAIN', 'paths']
		d_parm['img_raw_file']= param_xml.get_value('img_raw_file')
		if param_xml.get_value('img_exterior_outline'): #main image (manual membrane), takes precedence
			d_parm['img_exterior_outline'] = param_xml.get_value('img_exterior_outline')



		param_xml.l_main_keys = ['body', 'preprocessing', 'flowcontrol']
		d_parm['l_stack_number_preprocess'] = param_xml.get_value('l_stack_number')


		return d_parm

	def get_spheres(s_spheres):
		# return should look like this ['1, [11, 243, 153], 53.0', '16, [14, 288, 164], 34.0']
		l_matches = p.findall(s_spheres)
		return l_matches

	def get_sphere_info(s_sphere):
		# return should look like ['1', '11', '243', '153', '53', '0']
		#print(s_sphere)
		l_matches = p2.findall(s_sphere)
		if len(l_matches) > 5:
			radius = float(l_matches[4]) + (float(l_matches[5]) / 100)
		else:
			radius = float(l_matches[4])
		return [float(i) for i in [l_matches[1], l_matches[2], l_matches[3], radius]]

	
	

	def shrink_spheres(idS, idS_overlap_max,verbose=False):
		overlap_sphere = Sphere.d_idS_sph[idS_overlap_max]

		sum_radii = overlap_sphere.radius + radius
		dist = calc_dist_spheres(Sphere.d_idS_sph[idS], overlap_sphere)
		length_overlap = sum_radii - dist
		radius_corr = length_overlap / 2
		if verbose:print('BEFORE SHRINKING : self radius=', radius, 'overlap radius=', overlap_sphere.radius,
			  "they overlap with =", length_overlap, "the distance between them=", dist)
		new_radius_self = radius - radius_corr
		new_radius_overlap = overlap_sphere.radius - radius_corr

		# update the overlapping sphere in all datastructures
		overlap_sphere.radius = new_radius_overlap
		Sphere.d_idS_sph[idS_overlap_max] = overlap_sphere
		l_pixels = get_3D_sphere_coordinates(a_coordZYX=[overlap_sphere.z, overlap_sphere.y, overlap_sphere.x],
											 radius=overlap_sphere.radius, limit_shape=(d_parm['zmax'], d_parm['ymax'], d_parm['xmax']),
											 xy_vs_z=xy_vs_z)
		Sphere.a_labelview[Sphere.a_labelview == Sphere.d_idS_label[idS_overlap_max]] = 0
		Sphere.a_labelview[l_pixels] = Sphere.d_idS_label[idS_overlap_max]

		if verbose:print('overlap_sphere', overlap_sphere)
		if verbose:print('number of pixels overlap sphere before = ', len(Sphere.a_sphereview[Sphere.a_sphereview == idS_overlap_max]))
		a_sphereview[a_sphereview == idS_overlap_max] = 0
		a_sphereview[l_pixels] = idS_overlap_max
		if verbose:print('number of pixels overlap sphere after = ', len(Sphere.a_sphereview[Sphere.a_sphereview == idS_overlap_max]))

		if verbose:print('AFTER SHRINKING : self radius=', new_radius_self, 'overlap radius=', overlap_sphere.radius)

		return new_radius_self, new_radius_overlap

	def write_csv_output():

		ls_columns = ["cell_label",  # this array determines the order of the columns (besides the names)
					  "x",
					  "y",
					  "z",
					  "radius",
					  "x_micron",
					  "y_micron",
					  "z_micron",
					  "radius_micron"]

		d_df = {}  # the dict that will be used to create the dataframe   

		# initialize the ls_columns
		l_cell_label = []
		l_x = []
		l_y = []
		l_z = []
		l_radius = []
		l_x_micron = []
		l_y_micron = []
		l_z_micron = []
		l_radius_micron = []

		if not d_parm['shrink_spheres']:
			for cell_label, l_nt_spheres in d_cellID_l_nt_spheres.items():
				for nt_sphere in l_nt_spheres:
					l_cell_label.append(cell_label)
					l_x.append(int(nt_sphere.x))
					l_y.append(int(nt_sphere.y))
					l_z.append(int(nt_sphere.z))
					l_radius.append(int(nt_sphere.radius))
					l_x_micron.append(int(nt_sphere.x) * d_parm['xdim'])
					l_y_micron.append(int(nt_sphere.y) * d_parm['ydim'])
					l_z_micron.append(int(nt_sphere.z) * d_parm['zdim'])
					l_radius_micron.append(int(nt_sphere.radius) * d_parm['xdim'])

		else:
			for idS_i, idMesh_i in sorted(Sphere.d_idS_mesh_key.items(), key=lambda kv: kv[1]):
				sphere = Sphere.d_idS_sph[idS_i]

				l_cell_label.append(idMesh_i)
				l_x.append(int(sphere.zyx[2]))
				l_y.append(int(sphere.zyx[1]))
				l_z.append(int(sphere.zyx[0]))
				l_radius.append(float(sphere.radius))
				l_x_micron.append(int(sphere.zyx[2]) * d_parm['xdim'])
				l_y_micron.append(int(sphere.zyx[1]) * d_parm['ydim'])
				l_z_micron.append(int(sphere.zyx[0]) * d_parm['zdim'])
				l_radius_micron.append(float(sphere.radius) * d_parm['xdim'])

		d_df[ls_columns[0]] = l_cell_label
		d_df[ls_columns[1]] = l_x
		d_df[ls_columns[2]] = l_y
		d_df[ls_columns[3]] = l_z
		d_df[ls_columns[4]] = l_radius
		d_df[ls_columns[5]] = l_x_micron
		d_df[ls_columns[6]] = l_y_micron
		d_df[ls_columns[7]] = l_z_micron
		d_df[ls_columns[8]] = l_radius_micron

		# output_path = os.path.join(filehandler.get_save_location(),'spheres_for_meshing.csv')
		d_parm['file_spheres'].parent.mkdir(parents=True, exist_ok=True)
		df_spheres = pd.DataFrame(d_df)
		df_spheres.sort_values(by=['cell_label', 'radius'],ascending=[True,False],inplace=True)
		df_spheres.to_csv(str(d_parm['file_spheres']), index=False)
		# filehandler.store_f_name('spheres_for_meshing',output_path)

		print('mpacts output written as', str(d_parm['file_spheres']))

	class Sphere:
		idS = 0
		d_idS_sph = {}
		d_idS_mesh_key = {}
		d_idS_label = {}

		d_parm = read_parms(param_xml)
		a_labelview = np.zeros((d_parm['zmax'], d_parm['ymax'], d_parm['xmax']), dtype='int')
		a_sphereview = np.zeros((d_parm['zmax'], d_parm['ymax'], d_parm['xmax']), dtype='int') #spheres will be sequentially added to these views

		def __init__(self, center_zyx, radius,mesh_key,label):
			Sphere.idS += 1
			self.zyx = center_zyx
			self.radius = radius
			self.mesh_key = mesh_key
			self.label = label
			self.idS = Sphere.idS
			self.l_pixels=None
			self.update_l_pixels()
			Sphere.d_idS_sph[self.idS] = self
			Sphere.d_idS_mesh_key[self.idS] = mesh_key
			Sphere.d_idS_label[self.idS] = label

		def update_l_pixels(self):
			if self.radius > 0:
				self.l_pixels = get_3D_sphere_coordinates(a_coordZYX=self.zyx, radius=self.radius,
					limit_shape=(d_parm['zmax'], d_parm['ymax'], d_parm['xmax']), xy_vs_z=xy_vs_z)


			return 


		def update_views(self,verbose=False):
			Sphere.a_sphereview[self.l_pixels] = 0 #only now the current sphere is added to the views
			Sphere.a_labelview[self.l_pixels]  = 0
			if verbose:print('__number of pixels overlap sphere ({1}) before = {0}'.format(len(self.l_pixels[0]),self.mesh_key))

			self.update_l_pixels()
			Sphere.a_sphereview[self.l_pixels] = self.idS #only now the current sphere is added to the views
			Sphere.a_labelview[self.l_pixels]  = self.label
			if verbose:print('__number of pixels overlap sphere ({1}) after = {0}'.format(len(self.l_pixels[0]),self.mesh_key))


			return

		def get_sphere_of_max_overlap(self,verbose=False):
			'''
			the sphere ID of the sphere that maximally overlaps with the current sphere is returned
			'''

			bincount = np.bincount(Sphere.a_sphereview[self.l_pixels].flatten())
			bincount[0] = 0  # not interested in overlap with zero region, so set zero count equal to zero
			sph_overlap_max = Sphere.d_idS_sph[np.argmax(bincount)]
			while sph_overlap_max.mesh_key==self.mesh_key:
				bincount[sph_overlap_max.idS] = 0
				sph_overlap_max = Sphere.d_idS_sph[np.argmax(bincount)]
			# if len(bincount) > self.idS:
			#     bincount[self.idS] = 0  # not interested in overlap with self

			if verbose:print("---> OVERLAPPING SPHERES DETECTED => nbpix overlap=", np.max(bincount))

			#sanity test
			if sph_overlap_max.mesh_key==self.mesh_key:
				print("WARNING : The two spheres belong to the same mesh {0} !  not good !".format(self.mesh_key))
			if not sph_overlap_max:
				print('no overlapping sphere from another label found, something is wrong')

			return sph_overlap_max


		def shrink_and_move_spheres(self, overlap_sphere,verbose=False):
			def shrink_radii():
				sum_radii = overlap_sphere.radius + self.radius
				dist = self.calc_dist_spheres(overlap_sphere)
				length_overlap = max(sum_radii - dist,0)
				radius_corr = length_overlap / 4 #shrinkage radii will account for half the overlap, the other accounted will be covered by translation

				if verbose:print("-->they overlap with =", length_overlap, "the distance between them=", dist, "")

				if length_overlap==0:
					length_overlap = 1
					radius_corr = 0.25 # we apply some shrinking to solve rounding errors that can cause looping

				self.radius           =  self.radius - radius_corr
				overlap_sphere.radius =  overlap_sphere.radius - radius_corr

				return length_overlap,dist


			def set_new_centers(length_overlap,dist,verbose=False):
				'''
				the centers are pushed in opposite directions.  it will land midway the current radius.  so the shrunken and translated sphere will be completely
				contained in the current sphere and pushed towards its own cluster.
				'''   
				scale_factor = length_overlap / (dist * 4 ) #dist = normalize vector; centers only need to shift with 1/4 ot the overlap (translation accounts for half of overlap, rest = shrinking)
				l_translation  = [(i-j)*scale_factor for i,j in zip(overlap_sphere.zyx,self.zyx)] # translation_distance = length_overlap / 4
				self.zyx           = [math.floor(i - j) for i,j in zip(self.zyx,l_translation)]
				overlap_sphere.zyx = [math.floor(i + j) for i,j in zip(overlap_sphere.zyx,l_translation)]

				#sanity checks (temp)
				new_dist = self.calc_dist_spheres(overlap_sphere)
				new_sum_radii = overlap_sphere.radius + self.radius
				new_radius_overlap = new_sum_radii - new_dist
				if verbose:print('test : the new distance between these cells is {0} instead of the old distance {1}.'.format(new_dist,dist))
				if verbose:print('test : the new length_overlap is now sum_radii{0} - new_dist{1} = {2}'.format(new_sum_radii, new_dist,new_radius_overlap))
				if new_radius_overlap < 1e-5:
					if verbose:print("test : OK no overlap left :-)")

				return 

			if verbose:print('_INITIAL : overlap_sphere:', overlap_sphere.repr())
			if verbose:print('_INITIAL : self:', self.repr())

			length_overlap, dist = shrink_radii()
			if (length_overlap>0 and dist>0):
				set_new_centers(length_overlap,dist)   #CORE
				if verbose:print('_UPDATED : overlap_sphere:', overlap_sphere.repr())
				if verbose:print('_UPDATED : self:', self.repr())
				overlap_sphere.update_views()


			return 

		def overlap_with_other_cell(self):
			'''
			the cluster label of the sphere that maximally overlaps with the current sphere is returned
			'''
			bincount = np.bincount(Sphere.a_labelview[self.l_pixels].flatten())
			bincount[0] = 0  # not interested in overlap with zero region, so set zero count equal to zero
			if len(bincount) > self.label:
				bincount[self.label] = 0  # not interested in overlap with own cell

			bincount[bincount <= d_parm['overlap_tolerance']] = 0  # 1 pixel overlap is ignored
			return True if np.argmax(bincount)>0 else False


		def calc_dist_spheres(self, sphere2):
			a = (self.zyx[0]* xy_vs_z, self.zyx[1], self.zyx[2])
			b = (sphere2.zyx[0]* xy_vs_z, sphere2.zyx[1], sphere2.zyx[2])
			dst = distance.euclidean(a, b)

			return dst

		def repr(self):
			return "zyx:{0},radius:{1},mesh_key:{2},idS:{3},nb_pixels:{4}".format(self.zyx,self.radius,self.mesh_key,self.idS,len(self.l_pixels[0]))


	# PART 1 : make a csv of spheres per cell used in meshing
	# -------------------------------------------------------
	# initialize
	d_parm = read_parms(param_xml)
	# filehandler.extend_save_info(extra_dir_1 = '008_mpacts_input',from_root=True,take_snapshot_after=True)

	LABEL_FILTERED = 9998
	LABEL_VALIDATION = 9999
	SKIP_LABEL = [LABEL_FILTERED, LABEL_VALIDATION]
	xy_vs_z = d_parm['zdim'] / d_parm['xdim']

	# READ IN EXCEL------------------------------------------
	df_ipt = pd.read_csv(str(d_parm['input_file_csv']), delimiter=',')
	df_ipt['validation_error'] = df_ipt['validation_error'].astype('str')

	# STEP 1 BUILD UP DATASTRUCTURES FROM EXCEL INPUT---------------------
	p = re.compile(r"(?:\()(.+?)(?:\))")
	p2 = re.compile(r"\d+")

	nb_stack_timelapse = d_parm['nb_stack_timelapse']
		
	if isinstance(d_parm['l_stack_number_preprocess'], str):
		d_parm['nb_stack'] = d_parm['nb_stack_timelapse']  #if not 'all' timesteps are processed, then only the first occurrence is processed
	else:
		d_parm['nb_stack'] = d_parm['nb_stack']

	if not d_parm['shrink_spheres']:

		d_cellID_l_nt_spheres = {}  # ix = mesh key
		nt_Sphere = namedtuple('nt_Sphere', ['z', 'y', 'x', 'radius'])

		for nb_time in d_parm['nb_stack']:
			for _, row_cluster in df_ipt[df_ipt.stack_nb == nb_time].iterrows():
				if row_cluster.cluster_label in SKIP_LABEL: continue
				mesh_key = "{0}_{1}_t{2}".format("{:02d}".format(row_cluster.cluster_label), row_cluster.color, row_cluster.stack_nb)
				print(mesh_key)
				if row_cluster.validation_error != 'nan': print(row_cluster.validation_error)  # ter info
				l_spheres = get_spheres(row_cluster['spheres(ctr,centre,radius)'])
				l_nt_spheres = []
				for sphere in l_spheres:
					z, y, x, radius = get_sphere_info(sphere)
					nt_sphere = nt_Sphere(z=z, y=y, x=x, radius=radius)
					l_nt_spheres.append(nt_sphere)

				if l_nt_spheres:
					l_nt_spheres_old = d_cellID_l_nt_spheres.get(mesh_key)
					l_nt_spheres_new = l_nt_spheres_old + l_nt_spheres if l_nt_spheres_old else l_nt_spheres
					d_cellID_l_nt_spheres[mesh_key] = l_nt_spheres_new

	else:
		dd = {}  #to avoid looping if the same combination keeps popping up
		for nb_time in d_parm['nb_stack']:  # for now, will only be 1 timepoint e.g. [4]
			for _, row_cluster in df_ipt[df_ipt.stack_nb == nb_time].iterrows():
				if row_cluster.cluster_label in SKIP_LABEL: 
					continue

				mesh_key = "{0}_{1}_t{2}".format("{:02d}".format(row_cluster.cluster_label), row_cluster.color, row_cluster.stack_nb)
				print('processing this cluster :',mesh_key,flush=True)
				if row_cluster.validation_error != 'nan': print(row_cluster.validation_error)  # ter info

				l_spheres = get_spheres(row_cluster['spheres(ctr,centre,radius)'])

				for sphere_i in l_spheres:
					z, y, x, radius = get_sphere_info(sphere_i)
					sph_curr = Sphere([int(z), int(y), int(x)], radius,mesh_key, int(row_cluster.cluster_label))

					while (sph_curr.overlap_with_other_cell()):

						sph_overlap_max = sph_curr.get_sphere_of_max_overlap()

						dd.setdefault(sph_curr.idS, []).append(sph_overlap_max.idS)

						sph_curr.shrink_and_move_spheres(sph_overlap_max,verbose=False)

						sph_curr.update_l_pixels()


					sph_curr.update_views(verbose=False)



	write_csv_output()

	# PART 2 : make the pixel input for mpacts-PiCS
	# ---------------------------------------------

	with TiffFile(str(d_parm['input_file_frangi'])) as tif:
		a_frangi = tif.asarray()
	with TiffFile(str(d_parm['input_file_threshold'])) as tif:
		a_threshold = tif.asarray()

	a_mpacts_pixel_selector = np.where(a_threshold[d_parm['nb_stack'][0] - 1, ...], a_frangi[d_parm['nb_stack'][0] - 1, ...], 0)

	#if a exterior outine is given, this will also be blended in with the image. every pixel will get the maximum frangi value of that slice
	if isinstance(d_parm['img_exterior_outline'], Path) and d_parm['img_exterior_outline'].is_file():
		with TiffFile(str(d_parm['img_exterior_outline'])) as tif:
			print('exterior_outline is blended into mpacts_pixel_selector :{0}'.format(d_parm['img_exterior_outline']))
			a_exterior_outline = tif.asarray()
			if len(a_exterior_outline.shape)==4:
					a_exterior_outline = a_exterior_outline[d_parm['nb_stack'][0] - 1, ...]
		a_copy = np.zeros_like(a_mpacts_pixel_selector)
		for ix_z,a_z in enumerate(a_mpacts_pixel_selector):
			a_copy[ix_z] = np.where(a_exterior_outline[ix_z]>0,np.max(a_z),a_z)
		a_mpacts_pixel_selector = a_copy

		imsave(str(d_parm['output_folder'] / "exterior_outline_stack.tif"), a_exterior_outline)

	#if z_membrane detection is used, this will also be blended in with the image. every pixel will get the maximum frangi value of that slice
	if isinstance(d_parm['img_membranes_blend_z'], Path) and d_parm['img_membranes_blend_z'].is_file():
		with TiffFile(str(d_parm['img_membranes_blend_z'])) as tif:
			a_membranes_blend_z = tif.asarray()[d_parm['nb_stack'][0] - 1, ...]

		a_copy = np.zeros_like(a_mpacts_pixel_selector)
		for ix_z,a_z in enumerate(a_mpacts_pixel_selector):
			a_copy[ix_z] = np.where(a_membranes_blend_z[ix_z]==3,np.max(a_z),a_z)  #the z membranes has value 3 by convention
		a_mpacts_pixel_selector = a_copy

	imsave(str(d_parm['output_folder'] / "mpacts_pixel_selector.tif"),a_mpacts_pixel_selector)


	# PART 3 : make the raw image slice that can be uploaded into paraview for comparison (y inverted)
	# -----------------------------------------------------------------------------------------------
	with TiffFile(str(d_parm['img_raw_file'])) as tif:
		a_raw = tif.asarray()
	if len(a_raw.shape)==4:
		a_raw = a_raw[nb_stack_timelapse[0] - 1, :]
	a_paraview = np.zeros_like(a_raw)
	if len(a_paraview.shape)==4:
		_, _, y_max, _ = a_paraview.shape
	else:   
		_, y_max, _ = a_paraview.shape
	for i_y in range(0, y_max):
		a_paraview[:, i_y, :] = a_raw[:, -1 * (i_y - y_max + 1), :]

	# the paraview image is bottomed to aid vizualization (lowest intensity pixel should be zero)
	a_paraview = a_paraview - np.min(a_paraview)

	imsave(str(d_parm['output_folder'] / "raw_img_inverted_y.tif"), a_paraview)
	imsave(str(d_parm['output_folder'] / "raw_img_selected_stack .tif"), a_raw)
		
	return
