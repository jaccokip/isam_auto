'''
Created on Jul 25, 2015

@copyright: IBM
'''
import logging,sys,time,ConfigParser
from com.ibm.appliance.manager.BaseManager import BaseManager
from com.ibm.appliance.util.Common import CommonProperties
from com.ibm.appliance.util.Settings import Settings
from com.ibm.appliance.manager.WGAManager import WGAManager
from com.ibm.appliance.manager.FederationManager import FederationManager 

logging.basicConfig()
logger = logging.getLogger("ImportPartners")
logger.setLevel(logging.INFO)

Config = ConfigParser.ConfigParser()
Config.read("automation.ini")
logger.debug("Read automation.ini.  Sections found: " + str(Config.sections()))

def usage():    
    logger.info("     Usage: ImportPartners.py [options]")
    logger.info("         ")
    logger.info("         In order to run all sections:")
    logger.info("         -import All_Metadata")
    logger.info("         ")
    logger.info("         In order to run one section at a time use the following options:")
    logger.info("         -import IdP_Partner_Metadata ")
    logger.info("         -import SP_Partner_Metadata ")
    logger.info("         -modify IdP_Partner_Sign_Settings ")
    logger.info("         -modify SP_Partner_Sign_Settings ")

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
    else:
        FunctionNeededtoRun =  _args[2]  
        if(Settings.features.has_key(FunctionNeededtoRun)): # The feature name provided is available
            Settings.features[FunctionNeededtoRun] = True
        else:
            usage()
            sys.exit(1) 
            
    logger.debug("Begin SAML Metadata import")

    logger.debug("Getting configuration properties")   
    commonProps = ConfigSectionMap("common")
    idpProps = ConfigSectionMap("idp")
    spProps = ConfigSectionMap("sp")

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

    #Find IdP based on name  
    ipFedConfig = FederationManager(properties)
    ipFedName = properties[CommonProperties.PROP_SAML_FEDNAME]
    ipFedUrl = ipFedConfig.getIdpFedUrl(ipFedName)
    
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
    spFedName = properties[CommonProperties.PROP_SAML_FEDNAME]
    spFedUrl = spFedConfig.getIdpFedUrl(spFedName)
    
    if Settings.features["All_Metadata"]:
        #Import SP metadata into IdP
        importIPSuccess = ipFedConfig.importMetadata(fedIdUrl=ipFedUrl)
        ipFedConfig.deployChanges()
        #Import IdP metadta into SP
        importSPSuccess = spFedConfig.importMetadata(fedIdUrl=spFedUrl)
        spFedConfig.deployChanges()

        #Update IdP Partner to add Signature details
        if importIPSuccess == 0:  
            idpPartnerUrl = ipFedConfig.getFedPartnerUrl(fedName=ipFedName, partnerName='SP Company')
            partnerJson = ipFedConfig.getPartnerJson(idpPartnerUrl)
            modPartnerJson = ipFedConfig.modifyIdPPartnerJson(partnerJson)
            ipFedConfig.putFedPartner(idpPartnerUrl, modPartnerJson)
            ipFedConfig.deployChanges()
        if importSPSuccess == 0: 
            #Update SP Partner to add Signature details
            spPartnerUrl = spFedConfig.getFedPartnerUrl(fedName=spFedName, partnerName='IdP Company')
            spPartnerJson = spFedConfig.getPartnerJson(spPartnerUrl)
            modSpPartnerJson = spFedConfig.modifySPPartnerJson(spPartnerJson)
            spFedConfig.putFedPartner(spPartnerUrl, modSpPartnerJson)
            spFedConfig.deployChanges()
        
    if Settings.features["IdP_Partner_Sign_Settings"]:
        #Update IdP Partner to add Signature details
        idpPartnerUrl = ipFedConfig.getFedPartnerUrl(fedName=ipFedName, partnerName='SP Company')
        partnerJson = ipFedConfig.getPartnerJson(idpPartnerUrl)
        modPartnerJson = ipFedConfig.modifyIdPPartnerJson(partnerJson)
        ipFedConfig.putFedPartner(idpPartnerUrl, modPartnerJson)
        ipFedConfig.deployChanges()
        
    if Settings.features["SP_Partner_Sign_Settings"]:
        #Update SP Partner to add Signature details
        spPartnerUrl = spFedConfig.getFedPartnerUrl(fedName=spFedName, partnerName='IdP Company')
        spPartnerJson = spFedConfig.getPartnerJson(spPartnerUrl)
        modSpPartnerJson = spFedConfig.modifySPPartnerJson(spPartnerJson)
        spFedConfig.putFedPartner(spPartnerUrl, modSpPartnerJson)
        spFedConfig.deployChanges()
    
    if Settings.features["IdP_Partner_Metadata"]:
        #Import SP metadata into IdP
        ipFedConfig.importMetadata(fedIdUrl=ipFedUrl)
        ipFedConfig.deployChanges()
        
        #Update the signing and encryption setting to match the cookbook
        idpPartnerUrl = ipFedConfig.getFedPartnerUrl(fedName=ipFedName, partnerName='SP Company')
        partnerJson = ipFedConfig.getPartnerJson(idpPartnerUrl)
        modPartnerJson = ipFedConfig.modifyIdPPartnerJson(partnerJson)
        ipFedConfig.putFedPartner(idpPartnerUrl, modPartnerJson)
        ipFedConfig.deployChanges()
    
    if Settings.features["SP_Partner_Metadata"]:
        #Import IdP metadta into SP
        spFedConfig.importMetadata(fedIdUrl=spFedUrl)
        spFedConfig.deployChanges()
        
        #Update the signing and encryption setting to match the cookbook
        spPartnerUrl = spFedConfig.getFedPartnerUrl(fedName=spFedName, partnerName='IdP Company')
        spPartnerJson = spFedConfig.getPartnerJson(spPartnerUrl)
        modSpPartnerJson = spFedConfig.modifySPPartnerJson(spPartnerJson)
        spFedConfig.putFedPartner(spPartnerUrl, modSpPartnerJson)
        spFedConfig.deployChanges()
    
    logger.debug("End SAML Metadata import") 
    
    