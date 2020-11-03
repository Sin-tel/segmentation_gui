# import xmltodict

# with open("PARAMS.xml",'w') as fd:
#     data = xmltodict.parse(fd.read())
#     data["MAIN"]["flowcontrol"]["l_execution_blocks"] = "1"
#     fd.write(xmltodict.unparse(data))
    
import xmltodict

with open("PARAMS.xml","r") as prm:
    data = xmltodict.parse(prm.read())
    print(data["body"]["spheresDT"]["parms"]["MIN_SPHERE_RADIUS"]["@value"])
