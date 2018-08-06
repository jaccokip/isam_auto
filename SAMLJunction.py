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
logger = logging.getLogger("SAML Junction")
logger.setLevel(logging.INFO)

Config = ConfigParser.ConfigParser()
Config.read("automation.ini")
logger.debug("Read automation.ini.  Sections found: " + str(Config.sections()))

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

def usage():    
    logger.info("     Usage: SAMLJunction.py [options]")
    logger.info("         ")
    logger.info("         In order to run all sections:")
    logger.info("         -configure All")
   
    
if __name__ == '__main__': 
    # Will execute the specified command.  If the command fails, the program will exit.
    _args = sys.argv 
    if _args.__len__() < 2: 
        usage()
        sys.exit(1)      
    else:
        FunctionNeededtoRun =  _args[2]
            
    logger.debug("Configuring SAML Junction")
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
    
    properties[CommonProperties.PROP_SAML_JUNCT] = "/samljct"
    properties[CommonProperties.PROP_SAML_APPLIES_TO] = "http://appliesto/saml20"
    
    properties[CommonProperties.PROP_LTPA_JUNCT] = "/ltpajct"
    properties[CommonProperties.PROP_LTPA_APPLIES_TO] = "http://appliesto/ltpa"

    ipFedConfig = FederationManager(properties)
    ipFedConfig.changeEasuserPassword()
    ipFedConfig.deployChanges()
    
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
        stsModuleInstancesList.index("default-saml2_0")
    except ValueError:
        logger.error("The required module instances are missing")
     
    chainTemplateName = "IVCredToSAML20JunctionExample"
    chainTemplateId = None
    uuidChainItemIvc = None
    uuidChainItemMap = None
    uuidChainItemSaml = None
     
    for i in range(noOfChainTemplates):
        if (jsonStsChainTemplates[i]["name"] == chainTemplateName):
            chainItems = jsonStsChainTemplates[i]["chainItems"]
            if(len(chainItems) == 3 and chainItems[0]['id'] == 'default-ivc' and chainItems[0]['mode'] == 'validate' and 
               chainItems[1]['id'] == 'default-map' and chainItems[1]['mode'] == 'map' and
               chainItems[2]['id'] == 'default-saml2_0' and chainItems[2]['mode'] == 'issue'):
                chainTemplateId = jsonStsChainTemplates[i]["id"]
                uuidChainItemIvc = chainItems[0]['prefix'] 
                uuidChainItemMap = chainItems[1]['prefix'] 
                uuidChainItemSaml = chainItems[2]['prefix'] 
     
    if(chainTemplateId == None):
        logger.debug("Need to create a chain template")
        uuidChainItemIvc = uuid.uuid4()
        uuidChainItemMap = uuid.uuid4()
        uuidChainItemSaml = uuid.uuid4()
        chainTemplateId = ipFedConfig.createSTSModuleChainTemplate(uuidChainItemIvc, uuidChainItemMap, uuidChainItemSaml)
         
    else:
        logger.debug("Chain template exists and the id is "+chainTemplateId)
     
    chainName = "IVCredToSAML20Chain"
    chainIssuerAddress = "amwebrte-sts-client"
    chainAppliesToAddress = "http://appliesto/saml20"
    chainRequestType = "http://docs.oasis-open.org/ws-sx/ws-trust/200512/Issue"
    chainListId = None
    for i in range(noOfChainMappings):
        if(jsonStsChainMappings[i]["name"] == chainName):
            chainListId = jsonStsChainMappings[i]["id"]
         
    if(chainListId == None):
        logger.debug("Need to create a chain mapping")
        ipFedConfig.createSTSModuleChain(uuidChainItemIvc, uuidChainItemMap, uuidChainItemSaml, chainTemplateId, mapJsRuleReference='saml20_ivc_to_saml20.js')
    else:
        if(recreateChainMapping == True):
            logger.debug("Delete the existing chain")
            ipFedConfig.deleteSTSModuleChain(chainListId)
            ipFedConfig.createSTSModuleChain(uuidChainItemIvc, uuidChainItemMap, uuidChainItemSaml, chainTemplateId, mapJsRuleReference='saml20_ivc_to_saml20.js')
        else:
            logger.debug("Chain mapping exists and the listId is "+chainListId)
    ipFedConfig.deployChanges()
        
    logger.debug("Creating the SAML junction")
    wgaConfigIP = WGAManager(properties)
    wgaConfigIP.configureWebSEALConfForSAMLJct(websealHostName=properties[CommonProperties.PROP_WEB_HOST_NAME])
    wgaConfigIP.deployChanges()
    wgaConfigIP.createSAMLJunction()
    
    logger.info("End SAML junction creation and configuration")
