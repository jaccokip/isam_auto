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
logger = logging.getLogger("LTPA Junction")
logger.setLevel(logging.INFO)

Config = ConfigParser.ConfigParser()
Config.read("automation.ini")
logger.debug("Read automation.ini.  Sections found: " + str(Config.sections()))

def usage():    
    logger.info("     Usage: LTPAJunction.py [options]")
    logger.info("         ")
    logger.info("         In order to run all sections:")
    logger.info("         -configure All")
    logger.info("         ")

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
            
    logger.info("Configuring LTPA Junction")
    recreateChainMapping = True

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
    properties[CommonProperties.PROP_RUNTIME_TRACE_STRING] = "com.am.fim.*=ALL"
    
    properties[CommonProperties.PROP_LTPA_JUNCT] = "/ltpajct"
    properties[CommonProperties.PROP_LTPA_APPLIES_TO] = "http://appliesto/ltpa"

    properties[CommonProperties.PROP_SAML_JUNCT] = "/samljct"
    properties[CommonProperties.PROP_SAML_APPLIES_TO] = "http://appliesto/saml20"

    ipFedConfig = FederationManager(properties)
     
    logger.debug("GET module types")
    stsModuleTypes = ipFedConfig.getSTSModuleTypes()
    jsonStsModuleTypes = json.loads(stsModuleTypes)
    noOfStsModuleTypes = len(jsonStsModuleTypes)
    stsModuleTypesList = []
    for i in range(noOfStsModuleTypes):
        stsModuleTypesList.append(jsonStsModuleTypes[i]["id"])
      
    logger.debug("GET module instances")    
    stsModuleInstances = ipFedConfig.getSTSModuleInstances()
    jsonStsModuleInstances = json.loads(stsModuleInstances)
    noOfStsModuleInstances = len(jsonStsModuleInstances)
    stsModuleInstancesList = []
    for i in range(noOfStsModuleInstances):
        stsModuleInstancesList.append(jsonStsModuleInstances[i]["id"])
         
    logger.debug("GET chain templates")
    stsChainTemplates = ipFedConfig.getSTSModuleChainTemplates()
    jsonStsChainTemplates = json.loads(stsChainTemplates)
    noOfChainTemplates = len(jsonStsChainTemplates)
    stsChainTemplatesList = []
    for i in range(noOfChainTemplates):
        stsChainTemplatesList.append(jsonStsChainTemplates[i]["id"])
         
    logger.debug("GET chain mappings")
    stsChainMappings = ipFedConfig.getSTSModuleChains()
    jsonStsChainMappings = json.loads(stsChainMappings)
    noOfChainMappings = len(jsonStsChainMappings)
    stsChainMappingsList = []
    for i in range(noOfChainMappings):
        stsChainMappingsList.append(jsonStsChainMappings[i]["id"])
     
    #Check if the default chains used for this module exist
    try:
        stsModuleInstancesList.index("default-ivc")
        stsModuleInstancesList.index("default-map")
        stsModuleInstancesList.index("default-ltpa")
    except ValueError:
        logger.error("The required module instances are missing")
     
    chainTemplateName = "IVCredToLTPAJunctionExample"
    chainTemplateId = None
    uuidChainItemIvc = None
    uuidChainItemMap = None
    uuidChainItemltpa = None
     
    for i in range(noOfChainTemplates):
        if (jsonStsChainTemplates[i]["name"] == chainTemplateName):
            chainItems = jsonStsChainTemplates[i]["chainItems"]
            if(len(chainItems) == 3 and chainItems[0]['id'] == 'default-ivc' and chainItems[0]['mode'] == 'validate' and 
               chainItems[1]['id'] == 'default-map' and chainItems[1]['mode'] == 'map' and
               chainItems[2]['id'] == 'default-ltpa' and chainItems[2]['mode'] == 'issue'):
                chainTemplateId = jsonStsChainTemplates[i]["id"]
                uuidChainItemIvc = chainItems[0]['prefix'] 
                uuidChainItemMap = chainItems[1]['prefix'] 
                uuidChainItemltpa = chainItems[2]['prefix'] 
     
    if(chainTemplateId == None):
        logger.debug("Need to create a chain template")
        uuidChainItemIvc = uuid.uuid4()
        uuidChainItemMap = uuid.uuid4()
        uuidChainItemltpa = uuid.uuid4()
        chainTemplateId = ipFedConfig.createSTSModuleChainTemplateLTPAJunction(uuidChainItemIvc, uuidChainItemMap, uuidChainItemltpa)
         
    else:
        logger.debug("Chain template exists and the id is "+chainTemplateId)
     
    chainName = "IVCredToLTPAChain"
    chainIssuerAddress = "amwebrte-sts-client"
    chainAppliesToAddress = "http://appliesto/saml20"
    chainRequestType = "http://docs.oasis-open.org/ws-sx/ws-trust/200512/Issue"
    chainListId = None
    for i in range(noOfChainMappings):
        if(jsonStsChainMappings[i]["name"] == chainName):
            chainListId = jsonStsChainMappings[i]["id"]
         
    if(chainListId == None):
        logger.debug("Need to create a chain mapping")
        ipFedConfig.createSTSModuleChainLTPAJunction(uuidChainItemIvc, uuidChainItemMap, uuidChainItemltpa, chainTemplateId, mapJsRuleReference='ivc_to_ltpa.js')
    else:
        if(recreateChainMapping == True):
            logger.debug("Delete the existing chain")
            ipFedConfig.deleteSTSModuleChain(chainListId)
            ipFedConfig.createSTSModuleChainLTPAJunction(uuidChainItemIvc, uuidChainItemMap, uuidChainItemltpa, chainTemplateId, mapJsRuleReference='ivc_to_ltpa.js')
        else:
            logger.debug("Chain mapping exists and the listId is "+chainListId)
    ipFedConfig.deployChanges()        
    logger.debug("Creating the LTPA junction")
    wgaConfigIP = WGAManager(properties)
    wgaConfigIP.uploadLTPAKeys("ltpasso.keys", "idp_files/LTPA/ltpasso.keys")
    wgaConfigIP.configureWebSEALConfForLTPAJct(websealHostName=properties[CommonProperties.PROP_WEB_HOST_NAME])
    wgaConfigIP.deployChanges()
    wgaConfigIP.createLTPAJunction()
    
    logger.info("End LTPA junction creation and configuration")
