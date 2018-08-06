'''
Created on Jul 25, 2015

@copyright: IBM
'''
import logging,sys,time,json, uuid, os, ConfigParser
from com.ibm.appliance.manager.BaseManager import BaseManager
from com.ibm.appliance.util.Common import CommonProperties
from com.ibm.appliance.util.Settings import Settings
from com.ibm.appliance.manager.WGAManager import WGAManager
from com.ibm.appliance.manager.FederationManager import FederationManager 

logging.basicConfig()
logger = logging.getLogger("UploadLTPAKeys")
logger.setLevel(logging.INFO)

Config = ConfigParser.ConfigParser()
Config.read("automation.ini")
logger.debug("Read automation.ini.  Sections found: " + str(Config.sections()))

def usage():    
    logger.info("     Usage: UploadLTPAKeys.py [options]")
    logger.info("         ")
    logger.info("         In order to run all sections:")
    logger.info("         filename filePath")
    logger.info("         ")
    logger.info("         In order to run one section at a time use the following options:")
    logger.info("         targetFileName filePath. Example: my_ltpakey.keys /home/user/temp/ltpasso.keys")

def ConfigSectionMap(section):
    logger.debug("Entering ConfigSectionMap for " + section)
    paraMap = {}
    options = Config.options(section)
    for option in options:
        try:
            paraMap[option] = Config.get(section, option)
            if paraMap[option] == -1:
                logger.debug("skip: %s" % option)
        except:
            logger.error("exception on %s!" % option)
            paraMap[option] = None
    logger.debug("Config for " + section + " is " + str(paraMap))
    return paraMap

if __name__ == '__main__': 
    # Will execute the specified command.  If the command fails, the program will exit.
    _args = sys.argv 
    if _args.__len__() < 2: 
        usage()
        sys.exit(1)      
            
    logger.debug("Begin Uploading LTPA keys")
    
    logger.debug("Getting configuration properties")   
    commonProps = ConfigSectionMap("common")
    idpProps = ConfigSectionMap("idp")

    properties = {}
    properties[CommonProperties.PROP_PLATFORM_ACTIVATE_CODE] = str(commonProps[CommonProperties.PROP_PLATFORM_ACTIVATE_CODE]).strip()
    properties[CommonProperties.PROP_FEDERATION_ACTIVATE_CODE] = str(commonProps[CommonProperties.PROP_FEDERATION_ACTIVATE_CODE]).strip()
    properties[CommonProperties.PROP_DNS] = str(commonProps[CommonProperties.PROP_DNS]).strip()
    properties[CommonProperties.PROP_NTP_SERVER] = str(commonProps[CommonProperties.PROP_NTP_SERVER]).strip()
    properties[CommonProperties.PROP_HOSTS] = str(commonProps[CommonProperties.PROP_HOSTS]).strip()
    
    properties[CommonProperties.PROP_BASEURL] = str(idpProps[CommonProperties.PROP_BASEURL]).strip()
    properties[CommonProperties.PROP_USERNAME] = str(idpProps[CommonProperties.PROP_USERNAME]).strip()
    properties[CommonProperties.PROP_PASSWORD] = str(idpProps[CommonProperties.PROP_PASSWORD]).strip()
    properties[CommonProperties.PROP_OLD_PASSWORD] = str(idpProps[CommonProperties.PROP_OLD_PASSWORD]).strip()
    properties[CommonProperties.PROP_EASUSER_OLD_PASSWORD] = str(idpProps[CommonProperties.PROP_EASUSER_OLD_PASSWORD]).strip()
    properties[CommonProperties.PROP_EASUSER_PASSWORD] = str(idpProps[CommonProperties.PROP_EASUSER_PASSWORD]).strip()
    properties[CommonProperties.PROP_PRI_INTERFACE_IP] = str(idpProps[CommonProperties.PROP_PRI_INTERFACE_IP]).strip()
    properties[CommonProperties.PROP_PRI_INTERFACE_MASK] = str(idpProps[CommonProperties.PROP_PRI_INTERFACE_MASK]).strip()
    properties[CommonProperties.PROP_WEB_HOST_NAME] = str(idpProps[CommonProperties.PROP_WEB_HOST_NAME]).strip()
    properties[CommonProperties.PROP_WGA_HOST_NAME] = str(idpProps[CommonProperties.PROP_WGA_HOST_NAME]).strip()
    properties[CommonProperties.PROP_SAML_FEDNAME] = str(idpProps[CommonProperties.PROP_SAML_FEDNAME]).strip()
    
    properties[CommonProperties.PROP_SAML_FED_ROLE] = "idp"
    properties[CommonProperties.PROP_RUNTIME_TRACE_STRING] = "com.tivoli.am.fim.*=ALL"
    properties[CommonProperties.PROP_SAML_JUNCT] = "/samljct"
    properties[CommonProperties.PROP_SAML_APPLIES_TO] = "http://appliesto/saml20"
    properties[CommonProperties.PROP_LTPA_JUNCT] = "/ltpajct"
    properties[CommonProperties.PROP_LTPA_APPLIES_TO] = "http://appliesto/ltpa"
    
    baseApplianceClient = BaseManager(properties)
    baseApplianceClient.doBaseConfig()
  
    wgaConfigIP = WGAManager(properties)
    
    targetFileName = _args[1]# Example: my_ltpa.keys
    fileLocation = _args[2];# Example: "/home/user/SAMLBetaAutomation/idp_files/LTPA/ltpasso.keys";
    
    #Try to delete before uploading
    existingKey = wgaConfigIP.getLTPAKeys(targetFileName)
    if existingKey != None:
        logger.info("Key exists. Deleting existing LTPA keys [target name=" + targetFileName + "]")
        wgaConfigIP.deleteLTPAKeys(str(targetFileName))
    #Now upload the key
    wgaConfigIP.uploadLTPAKeys(str(targetFileName), str(fileLocation))
    wgaConfigIP.deployChanges()
    logger.info("Finished uploading LTPA keys [target name=" + targetFileName + "]")