'''
Created on Jul 25, 2015

@copyright: IBM
'''
import logging,sys,time,json,ConfigParser 
from com.ibm.appliance.manager.BaseManager import BaseManager
from com.ibm.appliance.util.Common import CommonProperties
from com.ibm.appliance.manager.WGAManager import WGAManager
from com.ibm.appliance.manager.FederationManager import FederationManager
from com.ibm.appliance.util.Settings import Settings

logging.basicConfig()
logger = logging.getLogger("SAMLSPConfig")
logger.setLevel(logging.INFO)

Config = ConfigParser.ConfigParser()
Config.read("automation.ini")
logger.debug("Read automation.ini.  Sections found: " + str(Config.sections()))

def usage():    
    logger.info("     Usage: SAMLSPConfig.py [options]")
    logger.info("         ")
    logger.info("         In order to run all sections:")
    logger.info("         -configure All")
    logger.info("         ")
    logger.info("         In order to run one section at a time use the following options:")
    
    logger.info("         ")
    logger.info("         -configure First_Steps")
    logger.info("         -configure Admin_Password ")
    logger.info("         -configure DNS ")
    
    logger.info("         ")
    logger.info("         -configure NTP ")
    logger.info("         -configure Product_Activation  ")
    logger.info("         -configure Runtime_Interfaces ")
    logger.info("         -configure Hosts_File ")
    logger.info("         -configure Runtime_Component ")
    
    logger.info("         ")
    logger.info("         -configure WebSEAL_Instance ")
    
    logger.info("         ")
    logger.info("         -configure Keystore ")
    logger.info("         -configure Federation ")
    logger.info("         -configure POC_For_Federation ")
    logger.info("         -configure Upload_Mapping_Rules")
    logger.info("         -configure Export_Metadata") 
    
    logger.info("         ")
    logger.info("         -configure Signer_Certificates ")
    logger.info("         -configure WebSEAL_Configfile ")
    logger.info("         -configure Junction ")
    logger.info("         -configure ACL ")
    logger.info("         -configure Test_User ")
    
    logger.info("         ")
    logger.info("         -action Restart_Federation_Runtime ")
    logger.info("         -action Runtime_Trace_String ") 
    logger.info("         -action Show_Pending_Changes ") 
    logger.info("         -action Deploy_Pending_Changes ") 
    logger.info("         -action Restart_LMI ") 
    logger.info("         -action Enable_Demo_Application ")
    
    logger.info("         ")
    logger.info("         -configure PoC_Use_PAC ")
    logger.info("         -configure PoC_Use_USERNAME ")
    logger.info("         -configure PoC_Use_EXTUSER ")

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
    #Will execute the specified command.  If the command failsthe program will exit.
    _args = sys.argv 
    if _args.__len__() < 2: 
        usage()
        sys.exit(1)      
    else:
        FunctionNeededtoRun =  _args[2]  
        if(Settings.features.has_key(FunctionNeededtoRun)): # The feagure name provided is available
            Settings.features[FunctionNeededtoRun] = True
        else:
            usage()
            sys.exit() 
            
    logger.debug("Begin SAML SP Configuration")
    
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
    properties[CommonProperties.PROP_SAML_JUNCT] = "/samljct"
    properties[CommonProperties.PROP_SAML_APPLIES_TO] = "http://appliesto/saml20"
    properties[CommonProperties.PROP_LTPA_JUNCT] = "/ltpajct"
    properties[CommonProperties.PROP_LTPA_APPLIES_TO] = "http://appliesto/ltpa"
    
    
    
    spFedName = properties[CommonProperties.PROP_SAML_FEDNAME]
    
    baseApplianceClient = BaseManager(properties)
    baseApplianceClient.doBaseConfig()
    
    wgaConfigIP = WGAManager(properties)
    wgaConfigIP.configureWga()
    
    spFedConfig = FederationManager(properties)
    spFedConfig.configureFedAndPartners()
    logger.debug("End SAML SP Configuration")
