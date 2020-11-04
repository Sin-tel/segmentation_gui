# import xmltodict

# with open("PARAMS.xml",'r+') as fd:
#     data = xmltodict.parse(fd.read())
#     data["body"]["MAIN"]["flowcontrol"]["l_execution_blocks"]["@value"] = "1,2"
# with open("test.xml",'w') as fd:
#     fd.write(xmltodict.unparse(data,pretty = 'TRUE'))

import xmltodict

with open("PARAMS.xml",'r') as fd:
    data = xmltodict.parse(fd.read())
    data["body"]["MAIN"]["flowcontrol"]["l_execution_blocks"]["@value"] = "1"
with open("PARAMS.xml",'w') as fd:
    fd.write(xmltodict.unparse(data,pretty = 'TRUE'))