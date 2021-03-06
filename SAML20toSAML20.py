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
logger = logging.getLogger("SAML20toSAML20")
logger.setLevel(logging.INFO)

Config = ConfigParser.ConfigParser()
Config.read("automation.ini")
logger.debug("Read automation.ini.  Sections found: " + str(Config.sections()))

def usage():    
    logger.info("     Usage: SAML20toSAML20.py -configure All")

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
    _args = sys.argv 
    if _args.__len__() < 2: 
        usage()
        sys.exit(1)      
    else:
        FunctionNeededtoRun =  _args[2]  
    # Will execute the specified command.  If the command fails, the program will exit.
    logger.info("Configuring the SAML20 to SAML20 chain")
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
    properties[CommonProperties.PROP_RUNTIME_TRACE_STRING] = "com.tivoli.am.fim.*=ALL"
    properties[CommonProperties.PROP_SAML_JUNCT] = "/samljct"
    properties[CommonProperties.PROP_SAML_APPLIES_TO] = "http://appliesto/saml20"
    properties[CommonProperties.PROP_LTPA_JUNCT] = "/ltpajct"
    properties[CommonProperties.PROP_LTPA_APPLIES_TO] = "http://appliesto/ltpa"

    wgaClient = WGAManager(properties)
    wgaClient.doPDADMINCommandsSTS("isam.myidp.ibm.com", "default")
    
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
        stsModuleInstancesList.index("default-saml2_0")
        stsModuleInstancesList.index("default-map")
        stsModuleInstancesList.index("default-saml2_0")
    except ValueError:
        logger.error("The required module instances are missing")
        
    logger.debug("Module types "+str(stsModuleTypesList))
    
    logger.debug("Module instances "+str(stsModuleInstancesList))
        
    logger.debug("Chain Templates "+str(stsChainTemplatesList))
    
    logger.debug("Chain mappings "+str(stsChainMappingsList))
    
    chainTemplateName = "SAML20ToSAML20"
    chainTemplateId = None
    uuidChainItemstsuu1 = None
    uuidChainItemMap = None
    uuidChainItemstsuu2 = None
      
    for i in range(noOfChainTemplates):
        if (jsonStsChainTemplates[i]["name"] == chainTemplateName):
            chainItems = jsonStsChainTemplates[i]["chainItems"]
            if(len(chainItems) == 3 and chainItems[0]['id'] == 'default-saml2_0' and chainItems[0]['mode'] == 'validate' and 
               chainItems[1]['id'] == 'default-map' and chainItems[1]['mode'] == 'map' and
               chainItems[2]['id'] == 'default-saml2_0' and chainItems[2]['mode'] == 'issue'):
               chainTemplateId = jsonStsChainTemplates[i]["id"]
               uuidChainItemstsuu1 = chainItems[0]['prefix'] 
               uuidChainItemMap = chainItems[1]['prefix'] 
               uuidChainItemstsuu2 = chainItems[2]['prefix'] 
      
    if(chainTemplateId == None):
        logger.debug("Need to create a chain template")
        uuidChainItemstsuu1 = uuid.uuid4()
        uuidChainItemMap = uuid.uuid4()
        uuidChainItemstsuu2 = uuid.uuid4()
        chainTemplateId = ipFedConfig.createSTSModuleChainTemplateSAML2toSAML2(uuidChainItemstsuu1, uuidChainItemMap, uuidChainItemstsuu2)
         
    else:
        logger.debug("Chain template exists and the id is "+chainTemplateId)
      
    chainName = "SAML20ToSAML20Chain";
    chainIssuerAddress = "http://issuer/saml20";
    chainAppliesToAddress = "http://appliesto/saml20";
    chainRequestType = "http://schemas.xmlsoap.org/ws/2005/02/trust/Validate";
    chainListId = None
    for i in range(noOfChainMappings):
        if(jsonStsChainMappings[i]["name"] == chainName):
            chainListId = jsonStsChainMappings[i]["id"]
          
    if(chainListId == None):
        logger.debug("Need to create a chain mapping")
        ipFedConfig.createSTSModuleChainSAML2toSAML2(uuidChainItemstsuu1, uuidChainItemMap, uuidChainItemstsuu2, chainTemplateId, mapJsRuleReference='saml20_to_saml20.js')
    else:
        if(recreateChainMapping == True):
            logger.debug("Delete the existing chain")
            ipFedConfig.deleteSTSModuleChain(chainListId)
            ipFedConfig.createSTSModuleChainSAML2toSAML2(uuidChainItemstsuu1, uuidChainItemMap, uuidChainItemstsuu2, chainTemplateId, mapJsRuleReference='saml20_to_saml20.js')
        else:
            logger.debug("Chain mapping exists and the listId is "+chainListId)
    #Needs to changed
    ipFedConfig.deployChanges()
    #This won't be needed once the STS code if fixed. 
    logger.info("Successfully configured the SAML20 to SAML20 chain")
    
    