from param_XML import Param_xml
import os,datetime,sys
from fileHandler import FileHandler
import shutil

def read_parms():

	l_execution_blocks = param_xml.get_value('l_execution_blocks', ['flowcontrol']) 
	ix_restart = param_xml.get_value('ix_restart', ['flowcontrol']) 
	l_execution_blocks = l_execution_blocks if (not ix_restart or ix_restart==0) else l_execution_blocks[ix_restart:]

	img_raw_file = param_xml.get_value('img_raw_file', ['paths'])
	img_exterior_outline = param_xml.get_value('img_exterior_outline', ['paths'])

	IMG_RAW_DIR = str(img_raw_file.parent)
	IMG_RAW_FILE= img_raw_file.name
	OUTPUT_FOLDER_ROOT = param_xml.get_value('OUTPUT_FOLDER_ROOT', ['paths'])
	ic_timestamp_subfolder = param_xml.get_value('ic_timestamp_subfolder', ['paths'])

	return l_execution_blocks, IMG_RAW_DIR,IMG_RAW_FILE,OUTPUT_FOLDER_ROOT,ic_timestamp_subfolder,img_exterior_outline

def initialize_filehandler():

	filehandler = FileHandler()
	filehandler.d_save_info['save_dir']= OUTPUT_FOLDER_ROOT
        #print("DEBUG1: filehandler {0},  OUTPUT_FOLDER_ROOT {1}, filehandler.get_save_location() {2}".format(filehandler.__repr__(), OUTPUT_FOLDER_ROOT,filehandler.get_save_location()))
        
	if ic_timestamp_subfolder:
		if IMG_RAW_FILE:
			filehandler.d_save_info['sub_dir_1']=str(datetime.datetime.now()).replace(":","_").replace(" ","_") + "_" + IMG_RAW_FILE[0:-4]
		else:
			filehandler.d_save_info['sub_dir_1']=str(datetime.datetime.now()).replace(":","_").replace(" ","_") 
			filehandler.set_save_info_root()
        #print("DEBUG2: filehandler {0},  OUTPUT_FOLDER_ROOT {1}, filehandler.get_save_location() {2}".format(filehandler.__repr__(), OUTPUT_FOLDER_ROOT,filehandler.get_save_location()))
		filehandler.d_load_info['load_dir']=IMG_RAW_DIR
		filehandler.take_snapshot()
		#print("DEBUG3: filehandler {0},  OUTPUT_FOLDER_ROOT {1}, filehandler.get_save_location() {2}".format(filehandler.__repr__(), OUTPUT_FOLDER_ROOT,filehandler.get_save_location()))
		print('SDT_MAIN.py:all info will be written to : ',filehandler.get_save_location())
        
	return filehandler

param_xml = Param_xml.get_param_xml(sys.argv,l_main_keys = ['body','MAIN'],verbose=True)
# file_param, param_xml,param_xml.l_main_keys = read_param_xml_file()
l_execution_blocks,IMG_RAW_DIR,IMG_RAW_FILE,OUTPUT_FOLDER_ROOT,ic_timestamp_subfolder,img_exterior_outline = read_parms()

print(l_execution_blocks)

Param_xml.store_value(l_execution_blocks,)

filehandler = initialize_filehandler()
os.makedirs(filehandler.get_save_location(),exist_ok=True)
shutil.copyfile(str(param_xml.file), os.path.join(filehandler.get_save_location(),param_xml.file.name)) #backup param file


