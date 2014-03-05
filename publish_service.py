import os as OS
import sys as SYS
import getpass as GETPASS
import json as JSON
import tempfile as TEMPFILE
import time as TIME
import urllib as URLLIB
import urllib2 as URLLIB2
import zipfile as ZIPFILE
from xml.etree import ElementTree as ET
import xml.dom.minidom as DOM

import arcpy as ARCPY
import arcpy.management as DM
import arcpy.mapping as MAP
import requests as REQUESTS
import arcpy.server as SERVER
import arcpy.analysis as ANALYSIS

class AGOLHandler(object):
    """ArcGIS Online handler class."""
    def __init__(self, username, password, serviceName):
        self.username = username
        self.password = password
        self.serviceName = serviceName
        self.token, self.http = self.getToken(username, password)
        self.itemID = self.findItem("Feature Service")
        self.SDitemID = self.findItem("Service Definition")
        if self.SDitemID:
            self.exists = True
        else:
            self.exists = False

    def findItem(self, findType):
        """Find the itemID of whats being updated."""
        searchURL = self.http + "/search"
        query_dict = {'f': 'json',
                      'token': self.token,
                      'q': "title:\""+ self.serviceName + "\"AND owner:\"" + self.username + "\" AND type:\"" + findType + "\""}

        jsonResponse = send_AGOL_Reqeust(searchURL, query_dict)
        if jsonResponse['total'] == 0:
            return None
        else:
            print("found {} : {}").format(findType, jsonResponse['results'][0]["id"])
        return jsonResponse['results'][0]["id"]

    def findItemURL(self, findType):
        """Find the item url."""
        searchURL = self.http + "/search"
        query_dict = {'f': 'json',
                      'token': self.token,
                      'q': "title:\""+ self.serviceName + "\"AND owner:\"" + self.username + "\" AND type:\"" + findType + "\""}

        jsonResponse = send_AGOL_Reqeust(searchURL, query_dict)
        if jsonResponse['total'] == 0:
            return None
        else:
            print("found {} : {}").format(findType, jsonResponse['results'][0]["id"])
        return jsonResponse['results'][0]['url']


    def getToken(self, username, password, exp=60):
        """Generates a token."""
        referer = "http://www.arcgis.com/"
        query_dict = {'username': username,
                      'password': password,
                      'referer': referer}

        query_string = URLLIB.urlencode(query_dict)
        url = "https://www.arcgis.com/sharing/rest/generateToken"
        token = JSON.loads(URLLIB.urlopen(url + "?f=json", query_string).read())

        if "token" not in token:
            print(token['error'])
            SYS.exit()
        else:
            httpPrefix = "http://www.arcgis.com/sharing/rest"
            if token['ssl'] == True:
                httpPrefix = "https://www.arcgis.com/sharing/rest"
            return token['token'], httpPrefix

    def publish(self, itemID):
        """Publish the existing SD on AGOL."""
        publishURL = self.http+'/content/users/{}/publish'.format(self.username)

        fs_id = self.findItem('Feature Service')
        if fs_id:
            delete_existing(fs_id)

        query_dict = {'itemID': itemID,
                      'filetype': 'serviceDefinition',
                      'f': 'json',
                      'token': self.token}

        jsonResponse = send_AGOL_Reqeust(publishURL, query_dict)
        print("successfully updated...{}...").format(jsonResponse['services'])

    def delete_existing(self, item_id):
        """Delete existing feature service."""
        deleteURL = self.http + '/content/users/{}/items/{}/delete'.format(self.username, item_id)
        if not deleteURL == '':
            query_dict = {'f': 'json', 'token': self.token}
            jsonResponse = send_AGOL_Reqeust(deleteURL, query_dict)
            print("successfully deleted...{}...").format(jsonResponse['itemId'])

    def upload(self, fileName, tags, description):
        """Overwrite the SD on AGOL with the new SD.
        This method uses 3rd party module: requests.
        """

        if self.exists:
            updateURL = self.http+'/content/users/{}/items/{}/update'.format(self.username, self.SDitemID)
        else:
            updateURL = self.http+'/content/users/{}/addItem'.format(self.username)

        #sd_id = self.findItem('Service Definition')
        #if sd_id:
        #    delete_existing(sd_id)

        filesUp = {"file": open(fileName, 'rb')}

        url = updateURL + "?f=json&token="+self.token+ \
            "&filename="+fileName+ \
            "&type=Service Definition"\
            "&title="+self.serviceName+ \
            "&tags="+tags+\
            "&description="+description

        response = REQUESTS.post(url, files=filesUp);
        itemPartJSON = JSON.loads(response.text)

        if "success" in itemPartJSON:
            itemID = itemPartJSON['id']
            print("uploaded SD:   {}").format(itemID)
            return itemID
        else:
            print("\n.sd file not uploaded. Check the errors and try again.\n")
            print(itemPartJSON)
            SYS.exit()

def enrich(service, output_service, rest_token):

    service_name = """{{"serviceProperties":{{"name":"{}"}}}}""".format(output_service)
    job_data = {"inputLayer":  """{{"url":"{}"}}""".format(service),
                "analysisVariables": ["LandscapeFacts.NLCDAgPt","Soils.MeanSoilRa","employees.N02_TOTEMP"],
                "country":"US", "outputName": service_name, "f":"json"}

    # Uncomment below when using angp portal
##    analysis_url = "http://analysis1.arcgis.com/arcgis/rest/services/tasks/GPServer/EnrichLayer"

    # Comment analysis_url below when using angp portal
    analysis_url = "http://analysis.arcgis.com/arcgis/rest/services/tasks/GPServer/EnrichLayer"
    url = "{}/submitJob?token={}".format(analysis_url, rest_token)
    headers = {"Accept":"*/*",
               "Connection":"keep-alive",
               "Content-Type":"application/x-www-form-urlencoded",
               "Origin":"http://test-nossl.maps.arcgis.com",
               "Referer":"http://test-nossl.maps.arcgis.com/home/webmap/viewer.html?useExisting=1",
               "Host":"analysis.arcgis.com",
               "Accept-Language":"en-US,en;q=0.8"}

    # Uncomment headers below and comment out headers above when using angp portal
##    headers = {"Accept":"*/*",
##               "Connection":"keep-alive",
##               "Content-Type":"application/x-www-form-urlencoded",
##               "Origin":"http://angp.maps.arcgis.com",
##               "Referer":"http://angp.maps.arcgis.com/home/webmap/viewer.html?services=83426143304141a3b0984bf6ec0d323f",
##               "Host":"analysis1.arcgis.com",
##               "Accept-Language":"en-US,en;q=0.8"}
    request = URLLIB2.Request(url, URLLIB.urlencode(job_data), headers)
    response = URLLIB2.urlopen(request)
    json_data = JSON.load(response)
    response.close()
    return analysis_url, json_data


def check_job_status(analysis_url, json_data, rest_token):
    if "jobId" in json_data:
        job_id = json_data["jobId"]
        job_url = "{}/jobs/{}?token={}".format(analysis_url, job_id, rest_token)
        request = URLLIB2.Request("{}/jobs/{}?f=json&token={}".format(analysis_url, job_id, rest_token))
        response = URLLIB2.urlopen(request)
        json_data = JSON.load(response)
        while not json_data["jobStatus"] == "esriJobSucceeded":
            request = URLLIB2.Request("{}/jobs/{}?f=json&token={}".format(analysis_url, job_id, rest_token))
            response = URLLIB2.urlopen(request)
            json_data = JSON.load(response)
            print(json_data)
            if json_data["jobStatus"] == "esriJobFailed":
                failed = StandardError("job failed")
                response.close()
                raise failed
            elif json_data["jobStatus"] == "esriJobCancelled":
                cancelled = StandardError("job cancelled")
                response.close()
                raise cancelled
            elif json_data["jobStatus"] == "esriJobTimedOut":
                timed_out = StandardError("job timed out")
                response.close()
                raise timed_out
            TIME.sleep(10)


def delete_existing(item_id):
    """Delete existing feature service."""
    deleteURL = agol.http + '/content/users/{}/items/{}/delete'.format(agol.username, item_id)
    if not deleteURL == '':
        query_dict = {'f': 'json',
                      'token': agol.token}
        jsonResponse = send_AGOL_Reqeust(deleteURL, query_dict)
        print("successfully deleted...{}...").format(jsonResponse['itemId'])


def make_sd_draft(MXD, serviceName, tempDir):
    """Ceate a draft SD and modify the properties to overwrite an existing FS."""
    ARCPY.env.overwriteOutput = True
    # All paths are built by joining names to the tempPath
    SDdraft = OS.path.join(tempDir, "drought.sddraft")
    newSDdraft = OS.path.join(tempDir, "droughtupdated.sddraft")

    MAP.CreateMapSDDraft(MXD, SDdraft, serviceName, "MY_HOSTED_SERVICES")

    # Read the contents of the original SDDraft into an xml parser
    doc = ET.parse(SDdraft)

    root_elem = doc.getroot()
    if root_elem.tag != "SVCManifest":
        raise ValueError("Root tag is incorrect. Is {} a .sddraft file?".format(SDDraft))

    # Change service type from map service to feature service
    for config in doc.findall("./Configurations/SVCConfiguration/TypeName"):
        if config.text == "MapServer":
            config.text = "FeatureServer"

    #Turn off caching
    for prop in doc.findall("./Configurations/SVCConfiguration/Definition/" +
                                "ConfigurationProperties/PropertyArray/" +
                                "PropertySetProperty"):
        if prop.find("Key").text == 'isCached':
            prop.find("Value").text = "false"

    for prop in doc.findall("./Configurations/SVCConfiguration/Definition/Extensions/SVCExtension"):
        if prop.find("TypeName").text == 'KmlServer':
            prop.find("Enabled").text = "false"

    # Turn on feature access capabilities
    for prop in doc.findall("./Configurations/SVCConfiguration/Definition/Info/PropertyArray/PropertySetProperty"):
        if prop.find("Key").text == 'WebCapabilities':
            prop.find("Value").text = "Query,Create,Update,Delete,Uploads,Editing"

    # Add the namespaces which get stripped, back into the .SD
    root_elem.attrib["xmlns:typens"] = 'http://www.esri.com/schemas/ArcGIS/10.1'
    root_elem.attrib["xmlns:xs"] ='http://www.w3.org/2001/XMLSchema'

    # Write the new draft to disk
    with open(newSDdraft, 'w') as f:
        doc.write(f, 'utf-8')

    return newSDdraft

def upload(agol, fileName, tags, description):
    """Overwrite the SD on AGOL with the new SD.
    This method uses 3rd party module: requests.
    """
    updateURL = agol.http+'/content/users/{}/addItem'.format(agol.username)

    #sd_id = agol.findItem('Service Definition')
    #if sd_id:
    #    delete_existing(sd_id)

    filesUp = {"file": open(fileName, 'rb')}

    url = updateURL + "?f=json&token="+agol.token+ \
        "&filename="+fileName+ \
        "&type=Service Definition"\
        "&title="+agol.serviceName+ \
        "&tags="+tags+\
        "&description="+description

    response = REQUESTS.post(url, files=filesUp);
    itemPartJSON = JSON.loads(response.text)

    if "success" in itemPartJSON:
        itemID = itemPartJSON['id']
        print("uploaded SD:   {}").format(itemID)
        return itemID
    else:
        print("\n.sd file not uploaded. Check the errors and try again.\n")
        print(itemPartJSON)
        SYS.exit()

def send_AGOL_Reqeust(URL, query_dict):
    """Helper function which takes a URL
    and a dictionary and sends the request."""
    query_string = URLLIB.urlencode(query_dict)

    jsonResponse = URLLIB.urlopen(URL, URLLIB.urlencode(query_dict))
    jsonOuput = JSON.loads(jsonResponse.read())

    wordTest = ["success", "results", "services", "notSharedWith"]
    if any(word in jsonOuput for word in wordTest):
        return jsonOuput
    else:
        print("\nfailed:")
        print(jsonOuput)
        SYS.exit()

def publish(itemID):
    """Publish the existing SD on AGOL."""
    publishURL = agol.http+'/content/users/{}/publish'.format(agol.username)

    fs_id = agol.findItem('Feature Service')
    if fs_id:
        delete_existing(fs_id)

    query_dict = {'itemID': itemID,
              'filetype': 'serviceDefinition',
              'f': 'json',
              'token': agol.token}

    jsonResponse = send_AGOL_Reqeust(publishURL, query_dict)
    print("successfully updated...{}...").format(jsonResponse['services'])

    return jsonResponse['services'][0]['serviceItemId']

def update_sddraft(sddraft_file, soe, enabled):
    """Updates the sddraft file to
    disable or enable Server Object Extentions.
    """
    doc = DOM.parse(sddraft_file)

    # This is where the server object extension (SOE) names are defined.
    # Valid only for ArcGIS Server and not hosted services.
    typeNames = doc.getElementsByTagName('TypeName')
    for typeName in typeNames:
        # Get the SOE (TypeName) we want to enable/disable.
        if typeName.firstChild.data == soe:
            extension = typeName.parentNode
            for extElement in extension.childNodes:
                if extElement.tagName == 'Enabled':
                    extElement.firstChild.data = enabled

    # Update draft file to enable overwritting.
    newType = 'esriServiceDefinitionType_Replacement'
    newState = 'esriSDState_Published'
    myTagsType = doc.getElementsByTagName('Type')
    for myTagType in myTagsType:
        if myTagType.parentNode.tagName == 'SVCManifest':
            if myTagType.hasChildNodes():
                myTagType.firstChild.data = newType

    myTagsState = doc.getElementsByTagName('State')
    for myTagState in myTagsState:
        if myTagState.parentNode.tagName == 'SVCManifest':
            if myTagState.hasChildNodes():
                myTagState.firstChild.data = newState

    # Output to a new sddraft.
    outXml = sddraft_file
    f = open(outXml, 'w')
    doc.writexml(f)
    f.close()

def publish_service(agol, service_name, mxd_template, layer_file):
    """Publishe the service."""

    # Create an sddraft file from the mxd.
    sd_dir = TEMPFILE.mkdtemp()

    mxd_temp = MAP.MapDocument(mxd_template)
    mxd_temp.summary = service_name
    mxd_temp.tags = service_name
    layer = MAP.Layer(layer_file)
    MAP.AddLayer(mxd_temp.activeDataFrame, layer)
    mxd_temp.saveACopy(OS.path.join(sd_dir, '{}.mxd'.format(service_name)))
    mxd = MAP.MapDocument(OS.path.join(sd_dir, '{}.mxd'.format(service_name)))

    # Make the sd draft and enable feature server.
    sd_draft = make_sd_draft(mxd, service_name,  sd_dir)

    # Stage the sddraft file.
    SERVER.StageService(sd_draft, OS.path.join(sd_dir, "drought.sd"))

    # Upload (publish) map service.
    id = agol.upload(OS.path.join(sd_dir, "drought.sd"), "US Drought", "Current US Drought Conditions.")
    publish(id)

def drought_analysis(date_string):
    ARCPY.env.overwriteOutput = True
    working_dir = r"C:\Data\DevSummit14"
    zip_name = "USDM_" + date_string + "_M.zip"
    url = "http://droughtmonitor.unl.edu/data/shapefiles_m/" + zip_name
    mxd_path = OS.path.join(working_dir, "MapTemplate.mxd")
    lyr_template = OS.path.join(working_dir, "CurrentDroughtConditions.lyr")
    zip_name = OS.path.basename(url)

    drought_zip_file = URLLIB.URLopener()
    dzf = drought_zip_file.retrieve(url, OS.path.join(r"C:\Temp", zip_name))
    zf = ZIPFILE.ZipFile(dzf[0], "r")
    shp_name = [n for n in zf.namelist() if n.endswith('.shp')][0]
    zf.extractall(working_dir)

    fl = DM.MakeFeatureLayer(OS.path.join(working_dir, shp_name), OS.path.splitext(shp_name)[0])
    
    #### Add Winery Data ####
    beerWinePath = OS.path.join(working_dir, "BeerWine", 
                                "BeerWine.gdb", "BeerWine")
    intermediate_output = OS.path.join(working_dir, "BeerWine", 
                                "BeerWine.gdb", "BeerWineDrought")
    wine = DM.MakeFeatureLayer(beerWinePath, "BeerWine")
    wine_drought = DM.MakeFeatureLayer(intermediate_output, "BeerWineDrought")
    DM.SelectLayerByAttribute(wine[0], "NEW_SELECTION", "Type = 'Winery'")
    ANALYSIS.SpatialJoin(fl[0], wine[0], intermediate_output, "JOIN_ONE_TO_ONE", "KEEP_ALL")

    lf = DM.SaveToLayerFile(wine_drought[0], OS.path.join(working_dir, '{}.lyr'.format(fl[0])))
    DM.ApplySymbologyFromLayer(lf, lyr_template)

    pw = "PASSWORDHERE" #GETPASS.getpass("Enter AGOL password:")
    service_name = "Drought_and_Wine"

    agol = AGOLHandler("USERNAMEHERE", pw, service_name)
    
    publish_service(agol, service_name, mxd_path, lf[0])
    TIME.sleep(5)
    fs_url = agol.findItemURL('Feature Service')
    TIME.sleep(25)
    gp_url, jsondata = enrich(fs_url + '/0', '{}_Enriched'.format(service_name), agol.token)
    check_job_status(gp_url, jsondata, agol.token)

    DM.Delete(OS.path.join(working_dir, shp_name))
    DM.Delete(OS.path.join(working_dir, lf[0]))


if __name__ == '__main__':
    date_string = "20140225"
    ARCPY.env.overwriteOutput = True
    working_dir = r"C:\Data\DevSummit14"
    zip_name = "USDM_" + date_string + "_M.zip"
    url = "http://droughtmonitor.unl.edu/data/shapefiles_m/" + zip_name
    mxd_path = OS.path.join(working_dir, "MapTemplate.mxd")
    lyr_template = OS.path.join(working_dir, "CurrentDroughtConditions.lyr")
    zip_name = OS.path.basename(url)

    drought_zip_file = URLLIB.URLopener()
    dzf = drought_zip_file.retrieve(url, OS.path.join(r"C:\Temp", zip_name))
    zf = ZIPFILE.ZipFile(dzf[0], "r")
    shp_name = [n for n in zf.namelist() if n.endswith('.shp')][0]
    zf.extractall(working_dir)

    drought = OS.path.splitext(shp_name)[0]
    DM.MakeFeatureLayer(OS.path.join(working_dir, shp_name), drought)
    
    #### Add Winery Data ####
    beerWinePath = OS.path.join(working_dir, "BeerWine", 
                                "BeerWine.gdb", "BeerWine")
    intermediate_output = OS.path.join(working_dir, "BeerWine", 
                                "BeerWine.gdb", "BeerWineDrought")
    wine = "BeerWine"
    wine_drought = "Wine_Drought"
    DM.MakeFeatureLayer(beerWinePath, wine)
    DM.SelectLayerByAttribute(wine, "NEW_SELECTION", "Type = 'Winery'")
    ANALYSIS.SpatialJoin(drought, wine, intermediate_output, "JOIN_ONE_TO_ONE", "KEEP_ALL")
    try:
        DM.DeleteField(intermediate_output, "NAME")
    except:
        pass
    final_wine_drought = "Wine_Drought_Summary"
    DM.MakeFeatureLayer(intermediate_output, final_wine_drought)

    lf = DM.SaveToLayerFile(final_wine_drought, 
                            OS.path.join(working_dir, '{}.lyr'.format(final_wine_drought)))
    DM.ApplySymbologyFromLayer(lf, lyr_template)

    pw = "test" #GETPASS.getpass("Enter AGOL password:")
    service_name = "Drought_and_Wine"

    agol = AGOLHandler("analytics", pw, service_name)
    
    publish_service(agol, service_name, mxd_path, lf[0])
    TIME.sleep(5)
    fs_url = agol.findItemURL('Feature Service')
    TIME.sleep(35)
    gp_url, jsondata = enrich(fs_url + '/0', '{}_Enriched'.format(service_name), agol.token)
    check_job_status(gp_url, jsondata, agol.token)

    DM.Delete(OS.path.join(working_dir, shp_name))
    DM.Delete(OS.path.join(working_dir, lf[0]))
