import logging,sys,time, ConfigParser
from com.ibm.appliance.manager.BaseManager import BaseManager
from com.ibm.appliance.util.Common import CommonProperties
from com.ibm.appliance.util.Settings import Settings
from com.ibm.appliance.manager.WGAManager import WGAManager
from com.ibm.appliance.manager.FederationManager import FederationManager 

logging.basicConfig()
logger = logging.getLogger("UploadSPMappingRule")
logger.setLevel(logging.INFO)

Config = ConfigParser.ConfigParser()
Config.read("automation.ini")
logger.debug("Read automation.ini.  Sections found: " + str(Config.sections()))

def usage():    
    logger.info("     Usage: UploadSPMappingRule.py -configure dynamicGroupMapping")

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
       # Will execute the specified command.  If the command fails, the program will exit.
    
    _args = sys.argv 
    if _args.__len__() < 2: 
        usage()
        sys.exit(1)      
        logger.info("Provide the mapping rule name")
    else:
        MappingRule =  _args[2]  
        
    logger.info("Configuring Dynamic Group Mapping ")
    
    logger.debug("Getting configuration properties")   
    commonProps = ConfigSectionMap("common")
    spProps = ConfigSectionMap("sp")

    properties = {}
    properties[CommonProperties.PROP_PLATFORM_ACTIVATE_CODE] = str(commonProps[CommonProperties.PROP_PLATFORM_ACTIVATE_CODE]).strip()
    properties[CommonProperties.PROP_FEDERATION_ACTIVATE_CODE] = str(commonProps[CommonProperties.PROP_FEDERATION_ACTIVATE_CODE]).strip()
    properties[CommonProperties.PROP_DNS] = str(commonProps[CommonProperties.PROP_DNS]).strip()
    properties[CommonProperties.PROP_NTP_SERVER] = str(commonProps[CommonProperties.PROP_NTP_SERVER]).strip()
    properties[CommonProperties.PROP_HOSTS] = str(commonProps[CommonProperties.PROP_HOSTS]).strip()
    
    properties[CommonProperties.PROP_BASEURL] = str(spProps[CommonProperties.PROP_BASEURL]).strip()
    properties[CommonProperties.PROP_USERNAME] = str(spProps[CommonProperties.PROP_USERNAME]).strip()
    properties[CommonProperties.PROP_PASSWORD] = str(spProps[CommonProperties.PROP_PASSWORD]).strip()
    properties[CommonProperties.PROP_OLD_PASSWORD] = str(spProps[CommonProperties.PROP_OLD_PASSWORD]).strip()
    properties[CommonProperties.PROP_EASUSER_OLD_PASSWORD] = str(spProps[CommonProperties.PROP_EASUSER_OLD_PASSWORD]).strip()
    properties[CommonProperties.PROP_EASUSER_PASSWORD] = str(spProps[CommonProperties.PROP_EASUSER_PASSWORD]).strip()
    properties[CommonProperties.PROP_PRI_INTERFACE_IP] = str(spProps[CommonProperties.PROP_PRI_INTERFACE_IP]).strip()
    properties[CommonProperties.PROP_PRI_INTERFACE_MASK] = str(spProps[CommonProperties.PROP_PRI_INTERFACE_MASK]).strip()
    properties[CommonProperties.PROP_WEB_HOST_NAME] = str(spProps[CommonProperties.PROP_WEB_HOST_NAME]).strip()
    properties[CommonProperties.PROP_WGA_HOST_NAME] = str(spProps[CommonProperties.PROP_WGA_HOST_NAME]).strip()
    properties[CommonProperties.PROP_SAML_FEDNAME] = str(spProps[CommonProperties.PROP_SAML_FEDNAME]).strip()    

    properties[CommonProperties.PROP_SAML_FED_ROLE] = "sp" 
    properties[CommonProperties.PROP_RUNTIME_TRACE_STRING] = "com.tivoli.am.fim.*=ALL"
    
    #Find SP based on name  
    
    spFedConfig = FederationManager(properties)
    spFedUrl = spFedConfig.getIdpFedUrl(properties[CommonProperties.PROP_SAML_FEDNAME])
    fedJson = spFedConfig.getFederationJson(spFedUrl)
    
    if MappingRule == "dynamicGroupMapping":
        modfedJson = spFedConfig.modifySPFederationJson(fedJson, 'sp_saml20_dynamic_group.js')
        spFedConfig.putFederation(spFedUrl, modfedJson)
        spFedConfig.createTestGroups()
        spFedConfig.deployChanges()
        logger.info("Successfully configured Dynamic Group Mapping")
    else:
        modfedJson = spFedConfig.modifySPFederationJson(fedJson, MappingRule)
        spFedConfig.putFederation(spFedUrl, modfedJson)
        spFedConfig.deployChanges()
