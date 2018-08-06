import logging,sys,time, ConfigParser
from com.ibm.appliance.manager.BaseManager import BaseManager
from com.ibm.appliance.util.Common import CommonProperties
from com.ibm.appliance.util.Settings import Settings
from com.ibm.appliance.manager.WGAManager import WGAManager
from com.ibm.appliance.manager.FederationManager import FederationManager 

logging.basicConfig()
logger = logging.getLogger("UploadIPMappingRule")
logger.setLevel(logging.INFO)

Config = ConfigParser.ConfigParser()
Config.read("automation.ini")
logger.debug("Read automation.ini.  Sections found: " + str(Config.sections()))

def usage():    
    logger.info("     Usage: UploadIPMappingRule.py -configure HttpClientMappingRule")
    
    logger.info("     Usage: UploadIPMappingRule.py -configure ExternalHttpCallout")
    
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
        logger.info("Provide the mapping rule name")
    else:
        MappingRule =  _args[2]  
        
    logger.info("Configuring the "+MappingRule)
    
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
    
    #Find IdP based on name  
    ipFedConfig = FederationManager(properties)
    ipFedUrl = ipFedConfig.getIdpFedUrl(properties[CommonProperties.PROP_SAML_FEDNAME])
    fedJson = ipFedConfig.getFederationJson(ipFedUrl)
    
    if MappingRule == "HttpClientMappingRule" :
        modfedJson = ipFedConfig.modifyIdPFederationJson(fedJson, 'ip_saml20_httpclient_wstrust.js')
        ipFedConfig.putFederation(ipFedUrl, modfedJson)
        ipFedConfig.deployChanges()
        logger.info("Successfully configured the "+MappingRule)
    elif MappingRule == "ExternalHttpCallout" :
        modfedJson = ipFedConfig.modifyIdPFederationJsonWSTrust(fedJson)
        ipFedConfig.putFederation(ipFedUrl, modfedJson)
        ipFedConfig.deployChanges()
        logger.info("Successfully configured the "+MappingRule)
    else:
        modfedJson = ipFedConfig.modifyIdPFederationJson(fedJson, MappingRule)
        ipFedConfig.putFederation(ipFedUrl, modfedJson) 
        ipFedConfig.deployChanges()
