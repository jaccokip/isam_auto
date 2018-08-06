'''
Created on Jul 25, 2015

@copyright: IBM
'''

from com.ibm.appliance.util.Common import CommonProperties 
from com.ibm.appliance.util.Settings import Settings
from com.ibm.appliance.util.HTTPRequest import ISAMRestClient
from com.ibm.appliance.util import HTTPRequest
import json,logging,time,os, uuid

logger = logging.getLogger("FederationManager")
logger.setLevel(logging.INFO)

class FederationManager(object):
    
    ISAM_RUNTIME_ENDPOINT = "/isam/runtime_components"
    ISAM_REVERSE_PROXY_ENDPOINT = "/wga/reverseproxy"
    ISAM_PDSRV_CERT_ENDPOINT = "/isam/ssl_certificates/pdsrv/signer_cert"
    ISAM_DEPLOY_CHANGES_ENDPOINT = "/isam/pending_changes/deploy"
    ISAM_GET_PENDING_CHANGES = "/isam/pending_changes"
    ISAM_RESTART_RUNTIME = "/mga/runtime_profile/local/v1"
    FIRMWARE_SETTINGS = "/firmware_settings"
    FIRST_STEPS = "/setup_complete"
    POC = "/iam/access/v8/poc"
    
    ISAM_MAPPING_RULES_ENDPOINT = "/iam/access/v8/mapping-rules"
    ISAM_ATTR_SOURCE_ENDPOINT = "/mga/attribute_sources"
    
    STS_BASE = "/iam/access/v8/sts"
    STS_MODULE_TYPES = STS_BASE + "/module-types"
    STS_MODULE_INSTANCES = STS_BASE + "/modules"
    STS_MODULE_CHAIN_TEMPLATES = STS_BASE + "/templates"
    STS_MODULE_CHAIN_MAPPINGS = STS_BASE + "/chains"
    
    def __init__(self, properties):
        
        self.BASEURL = properties[CommonProperties.PROP_BASEURL]  
        self.USERNAME = properties[CommonProperties.PROP_USERNAME]
        self.PASSWORD = properties[CommonProperties.PROP_PASSWORD]      
        self.WEB_HOST_NAME = properties[CommonProperties.PROP_WEB_HOST_NAME]
        self.WGA_HOST_NAME = properties[CommonProperties.PROP_WGA_HOST_NAME]
        self.APP_INTERFACE_IP = properties[CommonProperties.PROP_PRI_INTERFACE_IP]
        self.SAML_FED_NAME = properties[CommonProperties.PROP_SAML_FEDNAME]
        self.SAML_ROLE = properties[CommonProperties.PROP_SAML_FED_ROLE]
        self.RUNTIME_TRACE_STRING = properties[CommonProperties.PROP_RUNTIME_TRACE_STRING]
        self.EASUSER_OLD_PASSWORD = properties[CommonProperties.PROP_EASUSER_OLD_PASSWORD]
        self.EASUSER_PASSWORD = properties[CommonProperties.PROP_EASUSER_PASSWORD]
    
    def configureFedAndPartners(self):
        logger.debug("Triggering federation and partners configuration")
        deployChanges = False
        
        if Settings.features["All"] or Settings.features["Upload_Mapping_Rules"]:
            logger.debug("Upload mapping rules. They will be used by the Federation")
            self.uploadAllMappingRules()
            deployChanges = True
        
        if Settings.features["All"] or Settings.features["Federation"]:
            logger.debug("Configuring federation")
            self.restartLMI()
            
            if(self.SAML_ROLE == "idp"):
                self.configureIdPFederation()
                deployChanges = True
            if(self.SAML_ROLE == "sp"):
                self.configureSPFederation()
                deployChanges = True

        if Settings.features["All"]:        
            self.deployChanges()
        
        if Settings.features["All"] or Settings.features["POC_For_Federation"]:
            logger.debug("Configure Reverse Proxy for Federation")
            self.configureRProxy(self.SAML_FED_NAME)
            deployChanges = True
                    
        if Settings.features["All"] or Settings.features["Enable_Demo_Application"]: 
            self.setFedAdvancedConfigParams(keys=[{"key":"live.demos.enabled","value":"true"}])
            self.deployChanges()  
            self.setDemoAppSettings()
               
        if Settings.features["All"] or Settings.features["Export_Metadata"]:
            logger.debug("Exporting federation metadata")
            if(self.SAML_ROLE == "idp"):
                fedIdUrl = self.getIdpFedUrl(self.SAML_FED_NAME)
                self.exportMetadata(fedIdUrl)
            if(self.SAML_ROLE == "sp"):
                fedIdUrl = self.getIdpFedUrl(self.SAML_FED_NAME)
                self.exportMetadata(fedIdUrl)
            
            
        if Settings.features["Macros"]:
            logger.info("Setting Macros in the login page")
            if (self.getFirmwareVersion() >= CommonProperties.PROP_VERSION_9010):
                logger.debug("Using Version 9010 method")
                self.addMacroToPocProfile()
            else:
                logger.debug("Using pre-9010 method")
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.websealAuth.authenticationMacros","value":"%PARTNERID%"}])
                
            deployChanges = True
            logger.info("Successfully set Macros in the login page") 
            
        if  Settings.features["PoC_Use_PAC"]:
            logger.info("Set POC profile to use Access Manager Credential")
            if (self.getFirmwareVersion() >= CommonProperties.PROP_VERSION_9010):
                logger.debug("Using Version 9010 method")
                self.setPOCProfile("Access Manager Credential")
            else:
                logger.debug("Using pre-9010 method")
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.credResponseHeader","value":"am-eai-pac"}])
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.userResponseHeader","value":""}])
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.attributesResponseHeader","value":""}])
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.groupsResponseHeader","value":""}])
            
            deployChanges = True 
            logger.info("Successfully set POC profile to use Access Manager Credential")
        
        if  Settings.features["PoC_Use_USERNAME"]:
            logger.info("Set POC profile to use Access Manager Username and extended attributes")
            if (self.getFirmwareVersion() >= CommonProperties.PROP_VERSION_9010):
                logger.debug("Using Version 9010 method")
                self.setPOCProfile("Access Manager Username and extended attributes")
            else:
                logger.debug("Using pre-9010 method")
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.credResponseHeader","value":""}])
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.userResponseHeader","value":"am-eai-user-id"}])
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.attributesResponseHeader","value":"am-eai-xattrs"}])
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.groupsResponseHeader","value":""}])
            
            deployChanges = True 
            logger.info("Successfully set POC profile to use Access Manager Username and extended attributes")
            
        if  Settings.features["PoC_Use_EXTUSER"]:
            logger.info("Set POC profile to use Non-Access Manager Username, Access Manager groups and extended attributes")
            if (self.getFirmwareVersion() >= CommonProperties.PROP_VERSION_9010):
                logger.debug("Using Version 9010 method")
                self.setPOCProfile("Non-Access Manager Username, Access Manager groups and extended attributes")
            else:
                logger.debug("Using pre-9010 method")
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.credResponseHeader","value":""}])
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.userResponseHeader","value":"am-eai-ext-user-id"}])
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.attributesResponseHeader","value":"am-eai-xattrs"}])
                self.setFedAdvancedConfigParams(keys=[{"key":"poc.signIn.groupsResponseHeader","value":"am-eai-ext-user-groups"}])
            
            deployChanges = True
            logger.info("Successfully set POC profile to use Non-Access Manager Username, Access Manager groups and extended attributes")
                
        if Settings.features["Restart_Federation_Runtime"]:
            self.restartFederationRuntime()
            
        if Settings.features["All"] or Settings.features["Runtime_Trace_String"]:
            self.setRuntimeTraceString()
            deployChanges = True
            
        if Settings.features["Show_Pending_Changes"]:
            self.showPendingChanges()
        
        if Settings.features["Deploy_Pending_Changes"]:  
            self.deployChanges()
        
        if Settings.features["Restart_LMI"]:    
            self.restartLMI()
        
        if deployChanges:
                logger.debug("Deploying pending changes")
                self.deployChanges()  
        
        logger.debug("Federation and partners configuration completed")
    
    def configureSPFederation(self):
        logger.info("Configuring the SP Federation")
        
        referenceId = self.getMappingRuleRefernceID("sp_saml20.js")
        endpoint = "/iam/access/v8/federations/" 
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        fileLoc = 'sp_files/spfed.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj[u'configuration'][u'identityMapping'][u'properties'][u'identityMappingRuleReference'] = str(referenceId)
        data = json.dumps(jsonObj)
        f.close()
        
        logger.debug("POST to create SAML SP Federation")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create SAML SP federation. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the SP Federation")
            return contentHeader['location']
        else:
            logger.error("Unsuccessful POST to create SAML SP federation. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def disableHostnameValidation(self):
        logger.info("Disabling the Hostname Validation")
        
        #Disable the hostname validation
        self.setFedAdvancedConfigParams([{"key":"kess.hostnameValidationDisabled","value":"true"}])
        
        logger.info("Successfully disabled the Hostname Validation for IP and SP")
        
    def enableServerCertValidation(self):
        logger.info("Enabling Server Cert Validation by importing webseal's cert in partner's runtime keystore")
        
        #Load SP's WebSEAL(pdsrv) public cert to IP's runtime(rt_profile_keys) keystore
        self.loadSignerCertificate(keystore = "rt_profile_keys", label = "extCert", port = "443", server = "localhost")
                  
        #Modify IP Partner to enable serverCertValidation 
        '''Eg. 
            "soapSettings": {
              "serverCertValidation": {
                "enabled": true,
                "keystore": "rt_profile_keys",
                "label": ""
            }
        '''
        ipPartnerUrl = self.getFedPartnerUrl(fedName=IP_FED_NAME, partnerName=SP_COMPANY_NAME)
        ipPartnerJson = self.getPartnerJson(ipPartnerUrl)
#         modIpPartnerJson = self.modifyPartnerSoapSettings(ipPartnerJson)
# 
#         self.ipFedConfig.putFedPartner(ipPartnerUrl, modIpPartnerJson) 
#           
#         #Modify SP Partner to enable serverCertValidation 
#         spPartnerUrl = self.spFedConfig.getFedPartnerUrl(fedName=SP_FED_NAME, partnerName=IP_COMPANY_NAME)
#         spPartnerJson = self.spFedConfig.getPartnerJson(spPartnerUrl)
#         modSpPartnerJson = self.spFedConfig.modifyPartnerSoapSettings(spPartnerJson)
#         self.spFedConfig.putFedPartner(spPartnerUrl, modSpPartnerJson)
          
        logger.info("Successfully enabled the server certificate Validation for IP and SP")
    
    def loadSignerCertificate(self, keystore = "rt_profile_keys", label = "extCert", port = "443", server = "localhost"):
        logger.info("Loading Signer Certificate")

        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)

        endpoint = self.BASEURL + "/isam/ssl_certificates/%s/signer_cert" %keystore
        jsonObj = {"server": "%s" %server,"port": "%s" %port,"label": "%s" %label, "operation":"load"}
        data = json.dumps(jsonObj)

        logger.debug("POST to load signer certificate")
        statusCode, contentHeader, response = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 200:
            logger.debug("Successful POST to load signer certificate. Content returned : "+str(response)+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful POST to load signer certificate. Content returned : "+str(response)+" Status Code returned : "+str(statusCode))
            return None 
    
    def getMappingRuleRefernceID(self, fname):
        logger.info("Retrieving the mapping rule reference ID")
        
        endpoint = self.ISAM_MAPPING_RULES_ENDPOINT
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
   
        if statusCode == 200:
            logger.debug("Successful GET of Mapping Rules. Content returned : "+content+" Status Code returned : "+str(statusCode))
            mappingReferenceID = None
            content = json.loads(content)
            name = fname.split(".js")[0]
            
            for mappingRule in content:
                if(mappingRule[u'name'] == name): 
                    logger.debug("Retrieving the ID of the same mapping rule "+mappingRule[u'name'])
                    mappingReferenceID = mappingRule[u'id']
                    logger.debug("Mapping Rule refernce ID "+mappingReferenceID)
                    return mappingReferenceID
            if mappingReferenceID == None:
                logger.error("Mapping Rule " + name + "not found")
        
        else :
            logger.error("Unsuccessful GET of Mapping Rules. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
        
    def getAttrSourceReferenceID(self, name):
        logger.info("Retrieving the attribute source reference ID")
        
        endpoint = self.ISAM_ATTR_SOURCE_ENDPOINT
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
   
        if statusCode == 200:
            logger.debug("Successful GET of Mapping Rules. Content returned : "+content+" Status Code returned : "+str(statusCode))
            sourceReferenceID = None
            content = json.loads(content)
            
            for attrSource in content:
                if(attrSource[u'name'] == name): 
                    logger.debug("Retrieving the ID of the attribute source "+attrSource[u'name'])
                    sourceReferenceID = attrSource[u'id']
                    logger.debug("Mapping Rule refernce ID "+sourceReferenceID)
                    return sourceReferenceID
            if sourceReferenceID == None:
                logger.error("Attr Source " + name + "not found")
        else :
            logger.error("Unsuccessful GET of Mapping Rules. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
    def configureIdPFederation(self):
        logger.info("Configuring the IdP Federation")
        
        endpoint = "/iam/access/v8/federations/" 
        
        referenceId = self.getMappingRuleRefernceID("ip_saml20.js")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/ipfed.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj[u'configuration'][u'identityMapping'][u'properties'][u'identityMappingRuleReference'] = str(referenceId)
        data = json.dumps(jsonObj)
        f.close()
        
        logger.debug("POST to create SAML IdP Federation")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create SAML IdP federation. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the IdP Federation")
            return contentHeader['location']
        else:
            logger.error("Unsuccessful POST to create SAML IdP federation. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
        
    def configureSPFederationPartner(self, federationUrl):
        logger.info("Configuring the SP Federation's partner")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        endpoint = '/partners'
        
        fileLoc = 'sp_files/sppartner.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        data = json.dumps(jsonObj)
        f.close()
        
        logger.debug("POST to create SAML SP Federation's partner")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, federationUrl, endpoint, "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create SAML SP federation's partner. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the SP Federation's partner")
            return contentHeader['location']
        else:
            logger.error("Unsuccessful POST to create SAML SP federation's partner. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
    def configureIdPFederationPartner(self, federationUrl):
        logger.info("Configuring the IdP Federation's partner")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        endpoint = '/partners'
        
        fileLoc = 'idp_files/ippartner.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        data = json.dumps(jsonObj)
        f.close()
        
        logger.debug("POST to create SAML IdP Federation's partner")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, federationUrl, endpoint, "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create SAML IdP federation's partner. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the IdP Federation's partner")
            return contentHeader['location']
        else:
            logger.error("Unsuccessful POST to create SAML IdP federation's partner. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def setDemoAppSettings(self, runtimeJunction = "/isam", wgaHostName = None, instanceName='default'): 
        
        logger.info("Setting demo application settings")
        
        websealObjectName = "/WebSEAL/" + self.WGA_HOST_NAME + "-" + instanceName
        
        logger.debug("Configure ACLs, create temp-unauth and attach to "+websealObjectName+runtimeJunction+"/mobile-demo")
        
        endpoint = "/isam/pdadmin/"
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        jsonObj = {"admin_id":"sec_master","admin_pwd": "Passw0rd","commands":[]}
        data = json.loads(json.dumps(jsonObj))   
        data[u'commands'].append("acl create temp-unauth")
        data[u'commands'].append("acl modify temp-unauth set group iv-admin TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify temp-unauth set group webseal-servers Tgmdbsrxl")
        data[u'commands'].append("acl modify temp-unauth set user sec_master TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify temp-unauth set any-other Tr")
        data[u'commands'].append("acl modify temp-unauth set unauthenticated Tr")
        data[u'commands'].append("acl attach " + websealObjectName + runtimeJunction + "/mobile-demo temp-unauth")
        data[u'commands'].append("server replicate") 
        data = json.dumps(data)
                 
        logger.debug("POST to create and attach ACL")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        
        if statusCode == 200 and (str(content).find("Error") == -1):
            logger.debug("Successful POST to create and attach ACL. Content returned : "+content+" Status Code returned : "+str(statusCode))
            Runtime_Host = "localhost"
            Management_UI_HOST = self.WGA_HOST_NAME
            Management_UI_Password = self.PASSWORD
            Reverse_Proxy_Host = self.WEB_HOST_NAME
            
            endpoint =  "/isam/mobile-demo/setting/"  
            
            data = {"acHostAndPort":Runtime_Host+":443","lmiHostAndPort":Management_UI_HOST+":443","lmiAdminId":"admin","lmiAdminPwd":Management_UI_Password,"websealHostNameAndPort":Reverse_Proxy_Host+":443","acUuidCookieName":"ac.uuid"}
            
            HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD) 
            statusCode, contentHeader, content = ISAMRestClient.postEncodedData(HTTPRequest.ISAMRestClient, 'https://'+ self.WEB_HOST_NAME, endpoint, "application/json", data)
             
            if statusCode == 200:
                logger.debug("Successful PUT to configure demo application settings. Content returned : "+content+" Status Code returned : "+str(statusCode))
                logger.info("Successfully set demo application settings")
                
                logger.debug("deleting and detaching ACL")
                
                websealObjectName = "/WebSEAL/" + self.WGA_HOST_NAME + "-" + instanceName
                endpoint = "/isam/pdadmin/"
                 
                jsonObj = {"admin_id":"sec_master","admin_pwd": "Passw0rd","commands":[]}
                data = json.loads(json.dumps(jsonObj))
                data[u'commands'].append("acl attach " + websealObjectName + runtimeJunction + "/mobile-demo default-webseal")
                data[u'commands'].append("acl delete temp-unauth")
                data[u'commands'].append("server replicate") 
                data = json.dumps(data) 
                
                HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
                statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
                if statusCode == 200 and (str(content).find("Error") == -1):
                    logger.debug("Successful POST to delete and detach ACL. Content returned : "+content+" Status Code returned : "+str(statusCode))
                else:
                    logger.error("Unsuccessful POST to delete and detach an ACL. Content returned : "+content+" Status Code returned : "+str(statusCode))    
            else:
                logger.error("Unsuccessful PUT to configure demo application settings. Content returned : "+content+" Status Code returned : "+str(statusCode)) 
        else:
            logger.error("Unsuccessful POST to create and attach ACL. Content returned : "+content+" Status Code returned : "+str(statusCode)) 

    def createTestGroups(self): 
        
        logger.info("Creating testgroup and testgroup2")
        
        endpoint = "/isam/pdadmin/"
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        jsonObj = {"admin_id":"sec_master","admin_pwd": "Passw0rd","commands":[]}
        data = json.loads(json.dumps(jsonObj))   
        data[u'commands'].append("group create testgroup cn=testgroup,dc=iswga testgroup")
        data[u'commands'].append("group create testgroup2 cn=testgroup2,dc=iswga testgroup2")
        data = json.dumps(data)
                 
        logger.debug("POST to create groups")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        
        if statusCode == 200 and (str(content).find("Error") == -1):
            logger.debug("Successful POST to create groups. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Failed POST to create groups. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def configureRProxy(self, fedName, instanceName='default'):
        logger.info("Configuring Reverse Proxy for federation " + fedName)
        
        endpoint = self.ISAM_REVERSE_PROXY_ENDPOINT
        
        logger.debug("GET the WebSEAL details based on WebSEAL hostname")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        revProxiesJson = json.loads(content)
        
        noOfRevProx = len(revProxiesJson)
        webSealId = None
        logger.debug("Looking for WebSEAL Instance Name: " + instanceName)
        i = 0
        for i in range(noOfRevProx):
            if(revProxiesJson[i]['instance_name'] == instanceName):
                webSealId = revProxiesJson[i]['id']
        
        if(webSealId != None):
            logger.debug("Found WebSEAL ID: " + webSealId)
            fedId = self.getFedId(fedName)
            fedRuntime = {"hostname":"127.0.0.1","port":"443","username":"easuser","password":self.EASUSER_OLD_PASSWORD}
            jsonObj = {"runtime":fedRuntime,"federation_id":fedId,"reuse_certs":False,"reuse_acls":False}
            data = json.dumps(jsonObj)
            endpoint = "/wga/reverseproxy" + "/" + webSealId + "/fed_config"
            statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
            
            if statusCode == 400:
                errorMessage = json.loads(content)[u'message']
                if ("unauthorized" in errorMessage):
                    logger.debug("Trying new easuser password")
                    fedRuntime = {"hostname":"127.0.0.1","port":"443","username":"easuser","password":self.EASUSER_PASSWORD}
                    jsonObj = {"runtime":fedRuntime,"federation_id":fedId,"reuse_certs":False,"reuse_acls":False}
                    data = json.dumps(jsonObj)
                    endpoint = "/wga/reverseproxy" + "/" + webSealId + "/fed_config"
                    statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
            
            if statusCode == 204:
                logger.debug("Successful configuration of Reverse Proxy for federation. Status Code returned : "+str(statusCode))
                logger.info("Successfully configured Reverse Proxy for federation")    
            else:
                logger.error("Unsuccessful configuration of Reverse Proxy for federation. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful configuration of Reverse Proxy for federation.  Could not find instance: " + instanceName)
        
    def setFedAdvancedConfigParams(self,keys=[{"key":"live.demos.enabled","value":"true"}]):
        logger.debug("Modifying federation advanced configuration parameters")
        
        endpoint = "/iam/access/v8/override-configs"
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/jsonConverter", "", "")
   
        if statusCode == 200:
            logger.debug("Successful GET of federation advanced configuration parameters. Content returned : "+content+" Status Code returned : "+str(statusCode))
            
            content = json.loads(content)    
        
            for key in keys:
                keyName = key["key"]
                keyValue = key["value"] 
                for advancedConf in content:
                    if(advancedConf[u'key'] == keyName): 
                        logger.debug("Modifying key "+keyName+"'s value from "+advancedConf[u'value']+" to "+keyValue)
                        if(advancedConf[u'value'] == keyValue):
                            logger.debug("Value of key : "+keyName+" already set to value : "+keyValue)
                        else:
                            advancedConf[u'value'] = keyValue
                            configId = advancedConf[u'id']
                            data = json.dumps(advancedConf)
                            endpoint = endpoint + "/" + configId
                            statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
                            if statusCode == 204:
                                logger.debug("Successfully modified advanced configuration key: "+keyName+" into "+keyValue+". Content returned : "+content+" Status Code returned : "+str(statusCode))
                                logger.debug("Successfully modified federation advanced configuration parameters")
                            else:
                                logger.error("Unsuccessfully modified advanced configuration key: "+keyName+" into "+keyValue+". Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful GET of federation advanced configuration parameters. Content returned : "+content+" Status Code returned : "+str(statusCode))     
    
    def getPOCProfile(self, profileID):
        logger.debug("Getting the available POC profiles")
        
        endpoint = "/iam/access/v8/poc/profiles/"+str(profileID)
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/jsonConverter", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET on the current POC profile. Content returned : "+content)
            content = json.loads(content)
            for key in content:
                if content['id'] == str(profileID):
                    profileName = content['name']
                    return profileName       
        else :
            logger.error("Unsuccessful GET to the current POC profiles. Content returned : "+content+" Status Code returned : "+str(statusCode))
            
    def getPOCID(self, name):
        
        logger.debug("Getting the available POC profiles")
        
        endpoint = "/iam/access/v8/poc/profiles"
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/jsonConverter", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET on the current POC profile. Content returned : "+content)
            content = json.loads(content)
            profilelen = len(content)
            for i in range(profilelen):
                if content[i]['name'] == str(name):
                    profileID = content[i]['id']
                    return profileID       
        else :
            logger.error("Unsuccessful GET to the current POC profiles. Content returned : "+content+" Status Code returned : "+str(statusCode))
    def getCurrentPOCProfile(self):
        logger.debug("Getting the current POC profile")
        
        endpoint = "/iam/access/v8/poc"
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/jsonConverter", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET on the POC profiles. Content returned : "+content)
            profileID = json.loads(content)
            profileName = self.getPOCProfile(profileID['currentProfileId'])
            logger.info("The current POC profile name is : "+profileName)
                    
        else :
            logger.error("Unsuccessful GET to the available POC profiles. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def setPOCProfile(self, profileName):
        logger.debug("Getting the current POC profile")
        profileID = self.getPOCID(profileName)
        logger.debug("The current POC profile name is : "+profileID)
        
        logger.debug("Getting the current POC profile")
        
        endpoint = "/iam/access/v8/poc"
        
        jsonObj = {"currentProfileId":profileID} 
        data = json.dumps(jsonObj)
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        
        if statusCode == 204:
            logger.debug("Successfully PUT to set the POC profile.")
        else:
            logger.error("Unsuccessful PUT to set the POC profile.. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def setRuntimeTraceString(self):
        logger.info("Setting runtime trace string.")
         
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD) 
         
        endpoint = "/mga/runtime_tuning/trace_specification/v1"
         
        jsonObj = {"value":self.RUNTIME_TRACE_STRING} 
        data = json.dumps(jsonObj) 
 
        statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        
        if statusCode == 204:
            logger.debug("Successful PUT to set runtime trace string "+self.RUNTIME_TRACE_STRING+". Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully set runtime trace string.")
        else:
            logger.error("Unsuccessful PUT to set runtime trace string. Content returned : "+content+" Status Code returned : "+str(statusCode))
 
    def restartFederationRuntime(self):
        logger.info("Restarting federation runtime.")
         
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD) 
         
        endpoint = "/mga/runtime_profile/local/v1"
         
        jsonObj = {"operation":"restart"} 
        data = json.dumps(jsonObj) 
 
        statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        
        if statusCode == 200:
            logger.debug("Successful PUT to restart federation runtime. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully restarted federation runtime.")
        else:
            logger.error("Unsuccessful PUT to restart federation runtime. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def getIdpFedUrl(self,fedName):
        logger.debug("Find the URL for federation")
        
        endpoint = "/iam/access/v8/federations/" 
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful call to Federations end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            fedsJson = json.loads(content)
        
            noOfFeds = len(fedsJson)
            fedUrl = None
            i = 0
            for i in range(noOfFeds):
                if fedsJson[i]['name'] == fedName:
                    fedUrl = self.BASEURL + endpoint + fedsJson[i]['id']
            return fedUrl
        else:
            logger.error("Unsuccessful call to Federations end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def getFedId(self,fedName):
        logger.debug("Find the ID for federation")
        
        endpoint = "/iam/access/v8/federations/" 
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful call to Federations end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            fedsJson = json.loads(content)
        
            noOfFeds = len(fedsJson)
            fedId = None
            i = 0
            for i in range(noOfFeds):
                if fedsJson[i]['name'] == fedName:
                    fedId = fedsJson[i]['id']
            return fedId
        else:
            logger.error("Unsuccessful call to Federations end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def getFedPartnerUrl(self,fedName, partnerName):
        logger.debug("Find the URL for federation's partner")
        logger.debug("Lets get the federation name first. Use that to get partner")
        fedUrl = self.getIdpFedUrl(fedName)
        
        endpoint = fedUrl + "/partners" 
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, endpoint, "", "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful call to Federation Partners end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            fedPartnersJson = json.loads(content)
        
            noOfPartners = len(fedPartnersJson)
            partnerUrl = None
            i = 0
            for i in range(noOfPartners):
                if fedPartnersJson[i]['name'] == partnerName:
                    partnerUrl = fedUrl + "/partners/"+fedPartnersJson[i]['id']
            return partnerUrl
        else:
            logger.error("Unsuccessful call to Federation Partners end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def putFederation(self,fedURL, fedJsonStr):
        logger.debug("Use PUT to modify Federation JSON")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, fedURL, "", "*/*",jsonObj=fedJsonStr)
        
        if statusCode == 204:
            logger.info("Successfully modified the Federation using PUT")
            logger.debug("Successful PUT to Federation end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful PUT to Federation end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def putFedPartner(self,partnerUrl, partnerJsonStr):
        logger.debug("Use PUT to modify Partner JSON")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, partnerUrl, "", "*/*",jsonObj=partnerJsonStr)
        
        if statusCode == 204:
            logger.info("Successfully modified the partner using PUT")
            logger.debug("Successful PUT to Federation Partners end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful PUT to Federation Partners end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def getPartnerJson(self, partnerUrl):
        logger.debug("Get Partner JSON")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, partnerUrl, "", "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful call to Federation Partners end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful call to Federation Partners end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
    def getFederationJson(self, fedUrl):
        logger.debug("Get Partner JSON")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, fedUrl, "", "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful call to Federation Partners end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful call to Federation Partners end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def modifyIdPPartnerJson(self, jsonStr): 
        logger.info("Modifying IdP Partner JSON to enable signing and encryption")
        
        partnerJson = json.loads(jsonStr)      
        
        partnerJson["configuration"]["signatureSettings"]["signatureAlgorithm"] = "RSA-SHA512"
        partnerJson["configuration"]["signatureSettings"]["digestAlgorithm"] = "SHA512"
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateLogoutRequest"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateLogoutResponse"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateNameIDManagementRequest"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateNameIDManagementResponse"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateArtifactRequest"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateArtifactResponse"] = True
        partnerJson["configuration"]["signatureSettings"]["signingOptions"]["signAssertion"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateAuthnRequest"] = True
        partnerJson["configuration"]["signatureSettings"]["signingOptions"]["signAuthnResponse"] = True
        partnerJson["configuration"]["encryptionSettings"]["encryptionKeyTransportAlgorithm"] = "RSA-OAEP"
        partnerJson["configuration"]["encryptionSettings"]["blockEncryptionAlgorithm"] =  "AES-256"

        #Remove the partner's id and templateName before performing a PUT
        del partnerJson["id"]
        del partnerJson["templateName"]
        partnerJsonStr = json.dumps(partnerJson)

        return str(partnerJsonStr)
    
    
    def modifyIdPFederationJsonWSTrust(self, jsonStr): 
        logger.info("Modifying IdP Federation JSON to enable ExternalHttpCallout")
        
        fedJson = json.loads(jsonStr)      
        
        fedJson["configuration"]["identityMapping"]["activeDelegateId"] = "default-http-custom-map"
        fedJson["configuration"]["identityMapping"]["properties"]["uri"] = "https://localhost/TrustServer/SecurityTokenService"
        fedJson["configuration"]["identityMapping"]["properties"]["authType"] = "BASIC"
        fedJson["configuration"]["identityMapping"]["properties"]["basicAuthUsername"] = "easuser"
        fedJson["configuration"]["identityMapping"]["properties"]["basicAuthPassword"] = self.EASUSER_PASSWORD
        fedJson["configuration"]["identityMapping"]["properties"]["sslKeyStore"] = "pdsrv"
        fedJson["configuration"]["identityMapping"]["properties"]["issuerUri"] = "http://issuer/stsuu"
        fedJson["configuration"]["identityMapping"]["properties"]["appliesTo"] = "http://appliesto/stsuu"
        fedJson["configuration"]["identityMapping"]["properties"]["messageFormat"] = "WSTRUST"

        #Remove the partner's id and templateName before performing a PUT
        del fedJson["id"]
        del fedJson["templateName"]
        del fedJson["protocol"]
        fedJsonStr = json.dumps(fedJson)
        
        #Use str replace to add mapping rule. Change the code to use JSON libraries
        return str(fedJsonStr)
    
    def modifyIdPFederationJson(self, jsonStr, mappingRuleRefernce): 
        logger.info("Modifying IdP to change mapping rule")
        
        mappingRuleRefernce = self.getMappingRuleRefernceID(mappingRuleRefernce)
        fedJson = json.loads(jsonStr)      
        
        if fedJson["configuration"]["identityMapping"]["activeDelegateId"] == "default-http-custom-map":
            del fedJson["configuration"]["identityMapping"]["properties"]["uri"]
            del fedJson["configuration"]["identityMapping"]["properties"]["authType"]
            del fedJson["configuration"]["identityMapping"]["properties"]["basicAuthUsername"]
            del fedJson["configuration"]["identityMapping"]["properties"]["basicAuthPassword"]
            del fedJson["configuration"]["identityMapping"]["properties"]["sslKeyStore"]
            del fedJson["configuration"]["identityMapping"]["properties"]["issuerUri"]
            del fedJson["configuration"]["identityMapping"]["properties"]["appliesTo"]
            del fedJson["configuration"]["identityMapping"]["properties"]["messageFormat"]
            fedJson["configuration"]["identityMapping"]["activeDelegateId"] = "default-map"
            fedJson["configuration"]["identityMapping"]["properties"]["ruleType"] = "JAVASCRIPT"
            fedJson["configuration"]["identityMapping"]["properties"]["identityMappingRuleReference"] = mappingRuleRefernce
        elif fedJson["configuration"]["identityMapping"]["activeDelegateId"] == "default-map" :
            fedJson["configuration"]["identityMapping"]["activeDelegateId"] = "default-map"
            fedJson["configuration"]["identityMapping"]["properties"]["ruleType"] = "JAVASCRIPT"
            fedJson["configuration"]["identityMapping"]["properties"]["identityMappingRuleReference"] = mappingRuleRefernce


        #Remove the partner's id and templateName before performing a PUT
        del fedJson["id"]
        del fedJson["templateName"]
        del fedJson["protocol"]
        
        fedJsonStr = json.dumps(fedJson)
        
        #Use str replace to add mapping rule. Change the code to use JSON libraries
        return str(fedJsonStr)
    def modifyFederationJsonSoapSettings(self, jsonStr): 
        logger.info("Modifying IdP to change mapping rule")
        fedJson = json.loads(jsonStr)    
        fedJson["configuration"]["soapSettings"]["serverCertValidation"]["enabled"] = "True"
        fedJson["configuration"]["soapSettings"]["serverCertValidation"]["keystore"] = "rt_profiles_keys"
        fedJson["configuration"]["soapSettings"]["serverCertValidation"]["label"] = "extCert"
        fedJson["configuration"]["soapSettings"]["clientAuth"]["method"] = "ba"
        fedJson["configuration"]["soapSettings"]["clientAuth"]["properties"]["username"] = "test" 
        fedJson["configuration"]["soapSettings"]["clientAuth"]["properties"]["password"] = "admin"
        fedJsonStr = json.dumps(fedJson)
        
        #Use str replace to add mapping rule. Change the code to use JSON libraries
        return str(fedJsonStr)
        
    def modifySPFederationJson(self, jsonStr, mappingRuleRefernce): 
        logger.info("Modifying SP to change mapping rule")
        mappingRuleRefernce = self.getMappingRuleRefernceID(mappingRuleRefernce)
        fedJson = json.loads(jsonStr)      
        fedJson["configuration"]["identityMapping"]["activeDelegateId"] = "default-map"
        fedJson["configuration"]["identityMapping"]["properties"]["ruleType"] = "JAVASCRIPT"
        fedJson["configuration"]["identityMapping"]["properties"]["identityMappingRuleReference"] = mappingRuleRefernce


        #Remove the partner's id and templateName before performing a PUT
        del fedJson["id"]
        del fedJson["templateName"]
        del fedJson["protocol"]
        
        fedJsonStr = json.dumps(fedJson)
        
        #Use str replace to add mapping rule. Change the code to use JSON libraries
        return str(fedJsonStr)
                  
    def modifySPPartnerJson(self, jsonStr): 
        logger.info("Modifying SP Partner JSON to enable signing and encryption")
        
        partnerJson = json.loads(jsonStr)      
        
        partnerJson["configuration"]["signatureSettings"]["signatureAlgorithm"] = "RSA-SHA512"
        partnerJson["configuration"]["signatureSettings"]["digestAlgorithm"] = "SHA512"
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateLogoutRequest"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateLogoutResponse"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateNameIDManagementRequest"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateNameIDManagementResponse"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateArtifactRequest"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateArtifactResponse"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateAssertion"] = True
        partnerJson["configuration"]["signatureSettings"]["signingOptions"]["signAuthnRequest"] = True
        partnerJson["configuration"]["signatureSettings"]["validationOptions"]["validateAuthnResponse"] = True
        partnerJson["configuration"]["encryptionSettings"]["encryptionKeyTransportAlgorithm"] = "RSA-OAEP"
        partnerJson["configuration"]["encryptionSettings"]["blockEncryptionAlgorithm"] =  "AES-256"

        #Remove the partner's id and templateName before performing a PUT
        del partnerJson["id"]
        del partnerJson["templateName"]
        partnerJsonStr = json.dumps(partnerJson)

        return str(partnerJsonStr)

                  
    def exportMetadata(self, fedIdUrl, fileLocation=None):
        logger.info("Exporting Metadata")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        endpoint = "/metadata"
        
        if self.SAML_ROLE == "idp":
            fileLocation = 'tmp/ipmetadata.xml' #To export IdP metadata
        if self.SAML_ROLE == "sp":
            fileLocation = 'tmp/spmetadata.xml' #To export SP metadata
        
        statusCode, contentHeader, content = ISAMRestClient.getFile(HTTPRequest.ISAMRestClient, fedIdUrl, endpoint, "application/json", "", "application/json", "", "",fileLocation=fileLocation)
        if statusCode == 200:
            logger.debug("Successful export of metadata. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successful export of metadata")
        else:
            logger.error("Unsuccessful export of metadata. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def importMetadata(self, fedIdUrl, fileLocation=None):
        logger.info("Importing Metadata")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        endpoint = "/partners/metadata"
        
        if self.SAML_ROLE == "idp":
            fileLocation = 'tmp/spmetadata.xml' #To import SP metadata
        if self.SAML_ROLE == "sp":
            fileLocation = 'tmp/ipmetadata.xml' #To import IdP metadata
        
        multiple_files = {'metadata': ('metadata.xml', open(fileLocation, 'rb').read(),'application/octet-stream')}
        statusCode, contentHeader, content = ISAMRestClient.postMultiFile(HTTPRequest.ISAMRestClient, fedIdUrl, endpoint, "application/json",multiFileName=multiple_files)
        if statusCode == 201:
            logger.debug("Successful import of metadata. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successful import of metadata")
            return 0
        else:
            logger.error("Unsuccessful export of metadata. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def getAllMappingRules(self):
        logger.debug("Get Mapping Rules JSON")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        endpoint = self.BASEURL + self.ISAM_MAPPING_RULES_ENDPOINT
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, endpoint , "", "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful call to Mapping Rules end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful call to Mapping Rules end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
      
    def getSTSModuleTypes(self):
        logger.debug("Get Partner JSON")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        endpoint = self.BASEURL + self.STS_MODULE_TYPES
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, endpoint , "", "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful call to STS Module Types end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful call to STS Module Types end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
    def getSTSModuleInstances(self):
        logger.debug("Get Partner JSON")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        endpoint = self.BASEURL + self.STS_MODULE_INSTANCES
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, endpoint , "", "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful call to STS Module Instances end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful call to STS Module Instances end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
    def getSTSModuleChainTemplates(self):
        logger.debug("Get Partner JSON")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_TEMPLATES
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, endpoint , "", "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful call to STS Module Chain Templates end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful call to STS Module Chain Templates end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None       
    
    def getSTSModuleChains(self):
        logger.debug("Get Partner JSON")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_MAPPINGS
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, endpoint , "", "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful call to STS Module Chains end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful call to STS Module Chains end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None     
    
    def createMappingRule(self, name, category, filePath):
        logger.info("Create a mapping rule")
        
        endpoint = self.BASEURL + self.ISAM_MAPPING_RULES_ENDPOINT
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        fileObj = open(filePath, "r")
        fileData = fileObj.read()
        
        fileName = os.path.basename(filePath)
        
        jsonObj = {"fileName": fileName,"domain": "amapp-runtime","name": name,
        "category": category,"content": fileData}
        data = json.dumps(jsonObj)
        
        logger.debug("POST to create Mapping Rule")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create Mapping Rule. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully created the Mapping Rule")
            return str(contentHeader['location']).split(self.ISAM_MAPPING_RULES_ENDPOINT + "/")[1]
        else:
            logger.error("Unsuccessful POST to create Mapping Rule. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def updateMappingRule(self, mappingRuleId, filePath):
        logger.info("Update a mapping rule")
        
        endpoint = self.BASEURL + self.ISAM_MAPPING_RULES_ENDPOINT + "/" + mappingRuleId
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        fileObj = open(filePath, "r")
        fileData = fileObj.read()
        
        fileName = os.path.basename(filePath)
        
        jsonObj = {"content": fileData}
        data = json.dumps(jsonObj)
        
        logger.debug("POST to create Mapping Rule")
        statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 204:
            logger.debug("Successful POST to update Mapping Rule. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully updated the Mapping Rule")
        else:
            logger.error("Unsuccessful POST to update Mapping Rule. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def uploadAllMappingRules(self):
        logger.info("Upload all mapping rules")
        
        #GET all existing mapping rules. Read them into a list
        existingMappingRulesJson = json.loads(self.getAllMappingRules())
        existingMappingRulesJsonLen = len(existingMappingRulesJson)
        existingMappingRulesList = []
        existingMappingRulesNameIdMap = {}
        for i in range(existingMappingRulesJsonLen):
            existingMappingRulesList.append(existingMappingRulesJson[i]['name'])
            existingMappingRulesNameIdMap[existingMappingRulesJson[i]['name']] = existingMappingRulesJson[i]['id']
            
        #Get a list of mapping rules that need to be uploaded
        mappingRulesFilesDir = None
        if(self.SAML_ROLE == "idp"):
            mappingRulesFilesDir = "idp_files/mapping_rules"
        if(self.SAML_ROLE == "sp"):
            mappingRulesFilesDir = "sp_files/mapping_rules"
        
        mappingRulesFiles = os.listdir( mappingRulesFilesDir )
        for mappingRule in mappingRulesFiles:
            nameOfMappingRule = mappingRule.split(".js")[0]
            fileName = mappingRule
            categoryOfMappingRule = "SAML2_0"
            try:
                logger.debug("Update the existing Mapping Rule")
                mappingRuleId = existingMappingRulesNameIdMap[nameOfMappingRule]
                self.updateMappingRule(mappingRuleId, filePath=mappingRulesFilesDir+"/"+fileName)
            except:
                logger.debug("Create a Mapping Rule as it does not exist")
                self.createMappingRule(name=nameOfMappingRule, category=categoryOfMappingRule, filePath=mappingRulesFilesDir+"/"+fileName)
                
        
            
    def createSTSModuleChainTemplate(self, uuidChainItemIvc, uuidChainItemMap, uuidChainItemSaml):
        logger.info("Configuring the STS Module Chain Template")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_TEMPLATES
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschaintemplate.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainItems"][0]["prefix"] = str(uuidChainItemIvc)
        jsonObj["chainItems"][1]["prefix"] = str(uuidChainItemMap)
        jsonObj["chainItems"][2]["prefix"] = str(uuidChainItemSaml)
        data = json.dumps(jsonObj)
        f.close()
        
        logger.debug("POST to create STS Module Chain Template")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create STS Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the STS Module Chain Template")
            return str(contentHeader['location']).split(self.STS_MODULE_CHAIN_TEMPLATES + "/")[1]
        else:
            logger.error("Unsuccessful POST to create STS Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
    def createSTSModuleChainTemplateLTPAJunction(self, uuidChainItemIvc, uuidChainItemMap, uuidChainItemLtpa):
        logger.info("Configuring the IVCred to LTPA Module Chain Template")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_TEMPLATES
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschaintemplateivctoltpa.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainItems"][0]["prefix"] = str(uuidChainItemIvc)
        jsonObj["chainItems"][1]["prefix"] = str(uuidChainItemMap)
        jsonObj["chainItems"][2]["prefix"] = str(uuidChainItemLtpa)
        data = json.dumps(jsonObj)
        f.close()
        
        logger.debug("POST to create IVCred to LTPA Module Chain Template")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create IVCred to LTPA Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the IVCred to LTPA Module Chain Template")
            return str(contentHeader['location']).split(self.STS_MODULE_CHAIN_TEMPLATES + "/")[1]
        else:
            logger.error("Unsuccessful POST to create IVCred to LTPA Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
    def createSTSModuleChainTemplateLTPAtoSTSUU(self, uuidChainItemLtpa, uuidChainItemStsuu):
        logger.info("Configuring the LTPA to STSUU Module Chain Template")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_TEMPLATES
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschaintemplateLTPAtoSTSUU.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainItems"][0]["prefix"] = str(uuidChainItemLtpa)
        jsonObj["chainItems"][1]["prefix"] = str(uuidChainItemStsuu)
        data = json.dumps(jsonObj)
        f.close()
        
        logger.debug("POST to create LTPA to STSUU  Module Chain Template")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create LTPA to STSUU Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the LTPA to STSUU Module Chain Template")
            return str(contentHeader['location']).split(self.STS_MODULE_CHAIN_TEMPLATES + "/")[1]
        else:
            logger.error("Unsuccessful POST to create LTPA to STSUU Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
    def createSTSModuleChainTemplateSTSUU(self, uuidChainItemIvc, uuidChainItemMap, uuidChainItemSaml):
        logger.info("Configuring the STS Module Chain Template")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_TEMPLATES
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschaintemplate.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainItems"][0]["prefix"] = str(uuidChainItemIvc)
        jsonObj["chainItems"][0]["id"] = "default-stsuu"
        jsonObj["chainItems"][1]["prefix"] = str(uuidChainItemMap)
        jsonObj["chainItems"][1]["id"] = "default-map"
        jsonObj["chainItems"][2]["prefix"] = str(uuidChainItemSaml)
        jsonObj["chainItems"][2]["id"] = "default-stsuu"
        jsonObj["name"] ="STSUU to STSUU"
        jsonObj["description"] ="STSUU to STSUU"
        
        data = json.dumps(jsonObj)
        f.close()
        
        logger.debug("POST to create STS Module Chain Template")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create STS Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the STS Module Chain Template")
            return str(contentHeader['location']).split(self.STS_MODULE_CHAIN_TEMPLATES + "/")[1]
        else:
            logger.error("Unsuccessful POST to create STS Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def createSTSModuleChainTemplateUTtoSAML2(self, uuidChainItemUt, uuidChainItemMap, uuidChainItemSaml):
        logger.info("Configuring the Username to SAML20 Module Chain Template")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_TEMPLATES
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschaintemplateuttosaml2.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainItems"][0]["prefix"] = str(uuidChainItemUt)
        jsonObj["chainItems"][0]["id"] = "default-username"
        jsonObj["chainItems"][1]["prefix"] = str(uuidChainItemMap)
        jsonObj["chainItems"][1]["id"] = "default-map"
        jsonObj["chainItems"][2]["prefix"] = str(uuidChainItemSaml)
        jsonObj["chainItems"][2]["id"] = "default-saml2_0"
        jsonObj["name"] ="UsernameTokenToSAML20"
        jsonObj["description"] ="UsernameTokenToSAML20"
        
        data = json.dumps(jsonObj)
        f.close()
        
        logger.debug("POST to create Username to SAML20 Module Chain Template")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create Username to SAML20 Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the Username to SAML20 Module Chain Template")
            return str(contentHeader['location']).split(self.STS_MODULE_CHAIN_TEMPLATES + "/")[1]
        else:
            logger.error("Unsuccessful POST to create Username to SAML20 Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
       
    def createSTSModuleChainTemplateSAML2toSAML2(self, uuidChainItemSamlv, uuidChainItemMap, uuidChainItemSamli):
        logger.info("Configuring the SAML20 to SAML20 Module Chain Template")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_TEMPLATES
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschaintemplatesaml2tosaml2.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainItems"][0]["prefix"] = str(uuidChainItemSamlv)
        jsonObj["chainItems"][0]["id"] = "default-saml2_0"
        jsonObj["chainItems"][1]["prefix"] = str(uuidChainItemMap)
        jsonObj["chainItems"][1]["id"] = "default-map"
        jsonObj["chainItems"][2]["prefix"] = str(uuidChainItemSamli)
        jsonObj["chainItems"][2]["id"] = "default-saml2_0"
        jsonObj["name"] ="SAML20ToSAML20"
        jsonObj["description"] ="SAML20ToSAML20"

        data = json.dumps(jsonObj)
        f.close()
        
        logger.debug("POST to create SAML20 to SAML20 Module Chain Template")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create SAML20 to SAML20 Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the SAML20 to SAML20 Module Chain Template")
            return str(contentHeader['location']).split(self.STS_MODULE_CHAIN_TEMPLATES + "/")[1]
        else:
            logger.error("Unsuccessful POST to create SAML20 to SAML20 Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
        
        
        
    def createSTSModuleChainTemplateLDAP(self, uuidChainItemstsuuv, uuidChainItemMap1, uuidChainItemAttrMap, uuidChainItemMap2, uuidChainItemstsuui):
        logger.debug("Configuring the STS Module Chain Template")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_TEMPLATES
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stsldapattributetemplate.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainItems"][0]["prefix"] = str(uuidChainItemstsuuv)
        jsonObj["chainItems"][0]["id"] = "default-stsuu"
        jsonObj["chainItems"][1]["prefix"] = str(uuidChainItemMap1)
        jsonObj["chainItems"][1]["id"] = "default-map"
        jsonObj["chainItems"][2]["prefix"] = str(uuidChainItemAttrMap)
        jsonObj["chainItems"][2]["id"] = "default-attr_map"
        jsonObj["chainItems"][3]["prefix"] = str(uuidChainItemMap2)
        jsonObj["chainItems"][3]["id"] = "default-map"
        jsonObj["chainItems"][4]["prefix"] = str(uuidChainItemstsuui)
        jsonObj["chainItems"][4]["id"] = "default-stsuu"
        
        data = json.dumps(jsonObj)
        f.close()
        
        logger.debug("POST to create STS Module Chain Template")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create STS Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the STS Module Chain Template")
            return str(contentHeader['location']).split(self.STS_MODULE_CHAIN_TEMPLATES + "/")[1]
        else:
            logger.error("Unsuccessful POST to create STS Module Chain Template. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
    def createSTSModuleChain(self, uuidChainItemIvc, uuidChainItemMap, uuidChainItemSaml, chainTemplateId, mapJsRuleReference):
        logger.info("Configuring the STS Module Chain Mapping")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_MAPPINGS
        mapJsRuleReference = self.getMappingRuleRefernceID(mapJsRuleReference)
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschainmapping.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainId"] = chainTemplateId
        data = json.dumps(jsonObj)
        data = str(data).replace("ivc-uuid-str", str(uuidChainItemIvc))
        data = str(data).replace("map-uuid-str", str(uuidChainItemMap))
        data = str(data).replace("saml-uuid-str", str(uuidChainItemSaml))
        data = str(data).replace("mapJsRuleReference", mapJsRuleReference)
        
        logger.debug("POST to create STS Module Chain Mapping")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create STS Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the STS Module Chain Mapping")
            return contentHeader['location']
        else:
            logger.error("Unsuccessful POST to create STS Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def createSTSModuleChainLTPAJunction(self, uuidChainItemIvc, uuidChainItemMap, uuidChainItemLtpa, chainTemplateId, mapJsRuleReference):
        logger.info("Configuring the IVCred to LTPA Module Chain Mapping")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_MAPPINGS
        mapJsRuleReference = self.getMappingRuleRefernceID(mapJsRuleReference)
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschainmappingivctoltpa.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainId"] = chainTemplateId
        data = json.dumps(jsonObj)
        data = str(data).replace("ivc-uuid-str", str(uuidChainItemIvc))
        data = str(data).replace("map-uuid-str", str(uuidChainItemMap))
        data = str(data).replace("ltpa-uuid-str", str(uuidChainItemLtpa))
        data = str(data).replace("mapRuleReference", mapJsRuleReference)
        
        logger.debug("POST to create IVCred to LTPA Module Chain Mapping")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create IVCred to LTPA Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the IVCred to LTPA Module Chain Mapping")
            return contentHeader['location']
        else:
            logger.error("Unsuccessful POST to create IVCred to LTPA Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    
    def createSTSModuleChainLTPAtoSTSUU(self, uuidChainItemLtpa, uuidChainItemStsuu, chainTemplateId):
        logger.info("Configuring the LTPA to STSUU Module Chain Mapping")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_MAPPINGS
        #mapJsRuleReference = self.getMappingRuleRefernceID(mapJsRuleReference)
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschainmappingLTPAToSTSUU.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainId"] = chainTemplateId
        data = json.dumps(jsonObj)
        data = str(data).replace("id-prefix", str(uuidChainItemLtpa))
        
        logger.debug("POST to create STS Module Chain Mapping")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create LTPA to STSUU Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the LTPA to STSUU Module Chain Mapping ")
            return contentHeader['location']
        else:
            logger.error("Unsuccessful POST to create STS Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    
    def createSTSModuleChainSTSUU(self, uuidChainItemstsuu1, uuidChainItemMap, uuidChainItemstsuu2, chainTemplateId, mapJsRuleReference):
        logger.info("Configuring the STS Module Chain Mapping")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_MAPPINGS
        tmp1 = str(uuidChainItemMap) + ".map.rule.type"
        tmp3 = str(uuidChainItemMap) + ".map.rule.reference.ids"
        mapJsRuleReference = self.getMappingRuleRefernceID(mapJsRuleReference)
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschainmappingSTSUU.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainId"] = chainTemplateId
        jsonObj["properties"]["self"][0]["name"] = tmp1
        jsonObj["properties"]["self"][1]["name"] = tmp3
        
        data = json.dumps(jsonObj)
        data = str(data).replace("mapJsRuleReference", mapJsRuleReference)
        
        logger.debug("POST to create STS Module Chain Mapping")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create STS Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the STS Module Chain Mapping")
            return contentHeader['location']
        else:
            logger.error("Unsuccessful POST to create STS Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
    def createSTSModuleChainUTtoSAML2(self, uuidChainItemUt, uuidChainItemMap, uuidChainItemSaml, chainTemplateId, mapJsRuleReference):
        logger.info("Configuring the Username to SAML2 Module Chain Mapping")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_MAPPINGS
       
        mapJsRuleReference = self.getMappingRuleRefernceID(mapJsRuleReference)
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschainmappinguttosaml2.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainId"] = chainTemplateId        
        data = json.dumps(jsonObj)
        data = str(data).replace("ut-uuid-str", str(uuidChainItemUt))
        data = str(data).replace("map-uuid-str", str(uuidChainItemMap))
        data = str(data).replace("saml2-uuid-str", str(uuidChainItemSaml))
        data = str(data).replace("mapRuleReference", mapJsRuleReference)
        
        logger.debug("POST to create Username to SAML20 Module Chain Mapping")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create Username to SAML20 Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the Username to SAML20 Module Chain Mapping")
            return contentHeader['location']
        else:
            logger.error("Unsuccessful POST to create Username to SAML20 Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
        
    def createSTSModuleChainSAML2toSAML2(self, uuidChainItemSamlv, uuidChainItemMap, uuidChainItemSamli, chainTemplateId, mapJsRuleReference):
        logger.info("Configuring the SAML20 to SAML20 Module Chain Mapping")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_MAPPINGS
       
        mapJsRuleReference = self.getMappingRuleRefernceID(mapJsRuleReference)
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stschainmappingsaml2tosaml2.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainId"] = chainTemplateId        
        data = json.dumps(jsonObj)
        data = str(data).replace("saml2v-uuid-str", str(uuidChainItemSamlv))
        data = str(data).replace("map-uuid-str", str(uuidChainItemMap))
        data = str(data).replace("saml2i-uuid-str", str(uuidChainItemSamli))
        data = str(data).replace("mapRuleReference", mapJsRuleReference)
        logger.debug("POST to create SAML20 to SAML20 Module Chain Mapping")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create SAML20 to SAML20 Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the SAML20 to SAML20 Module Chain Mapping")
            return contentHeader['location']
        else:
            logger.error("Unsuccessful POST to create SAML20 to SAML20 Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
        
    def createSTSModuleChainLDAP(self, uuidChainItemstsuuv, uuidChainItemMap1, uuidChainItemAttrMap, uuidChainItemMap2, uuidChainItemstsuui, chainTemplateId, mapJsRuleReference1, mapJsRuleReference2,phoneSource,displaySource):
        
        logger.debug("Configuring the STS Module Chain Mapping")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_MAPPINGS
        mapJsRuleReference1 = self.getMappingRuleRefernceID(mapJsRuleReference1)
        mapJsRuleReference2 = self.getMappingRuleRefernceID(mapJsRuleReference2)
        phoneSourceID = self.getAttrSourceReferenceID(phoneSource)
        displaySourceID = self.getAttrSourceReferenceID(displaySource)
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        fileLoc = 'idp_files/stsldapattributemapping.json'
        f = open(fileLoc, 'r')
        jsonObj = json.loads(f.read()) 
        jsonObj["chainId"] = chainTemplateId
        data = json.dumps(jsonObj)
        data = str(data).replace("map1-uuid-str", str(uuidChainItemMap1))
        data = str(data).replace("map2-uuid-str", str(uuidChainItemMap2))
        data = str(data).replace("map3-attr", str(uuidChainItemAttrMap))
        data = str(data).replace("mapJsPRERuleReference", mapJsRuleReference1)
        data = str(data).replace("mapJsPOSTRuleReference", mapJsRuleReference2)
        data = str(data).replace("@phoneSource@", phoneSourceID)
        data = str(data).replace("@displaySource@", displaySourceID)
        
        logger.debug("POST to create STS Module Chain Mapping")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, endpoint, "",  "application/json", data)
        if statusCode == 201:
            logger.debug("Successful POST to create STS Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.debug("Successfully configured the STS Module Chain Mapping")
            return contentHeader['location']
        else:
            logger.error("Unsuccessful POST to create STS Module Chain Mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
        
    
    def deleteSTSModuleChain(self, listId):
        logger.debug("Delete the existing chain mapping")
        
        endpoint = self.BASEURL + self.STS_MODULE_CHAIN_MAPPINGS + "/" + listId
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.delete(HTTPRequest.ISAMRestClient, endpoint, "", "application/json", None) 
        if statusCode == 204:
            logger.debug("Successfully deleted chain mapping. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessfully deleted chain mapping. Content returned : "+content+" Status Code returned : "+str(statusCode)) 
    
    
    def getSTSMappingID(self, name):

        logger.debug("Find the ID of the STS Chain Mapping")

        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)

        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.STS_MODULE_CHAIN_MAPPINGS, "application/json", "", "application/json", "", "")

        if statusCode == 200:
            logger.debug("Successful call to STS Chain Mapping end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            stsChainJson = json.loads(content)

            noOfPartners = len(stsChainJson)
            chainID  = None
            i = 0
            for i in range(noOfPartners):
                if stsChainJson[i]['name'] == name:
                    chainID = stsChainJson[i]['id']

            return chainID
        else:
            logger.error("Unsuccessful call to STS Chain Mapping end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return None
    def changeEasuserPassword(self):
        logger.info("Configuring the easuser password")
        
        endpoint = "/mga/user_registry/users/easuser/v1"


        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        jsonObj = {"password":self.EASUSER_PASSWORD}
        data = json.dumps(jsonObj)
        logger.debug("PUT to change the password")
        statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        if statusCode == 204:
            logger.debug("Successfully  POST to change easuser password. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the easuser password")
        else:
            logger.error("Unsuccessful POST to change easuser password. Content returned : "+content+" Status Code returned : "+str(statusCode))

    def createServerConnection(self):

        logger.info("Configuring the server connection")
        endpoint = "/mga/server_connections/ldap/v1"
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password =self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        if statusCode == 200:
            logger.debug("Successful GET of ServerConnection. Content returned : "+content+" Status Code returned : "+str(statusCode))
            ldapID = None
            content = json.loads(content)    
            ldapName = "localldap"
            for ldap in content:
                if(ldap[u'name'] == ldapName): 
                    logger.debug("LDAP exists, deleting it and re creating it")
                    ldapID = ldap[u'uuid']
                    endpoint1 = "/mga/server_connections/ldap/" + ldapID +"/v1"
                    statusCode, contentHeader, content = ISAMRestClient.delete(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint1, "application/json", "", "")
                    if statusCode == 204:
                        logger.debug("LDAP deleted successfully"+content+":Status Code:"+str(statusCode))
                                     
                    else:
                        logger.debug("LDAP deletion failed"+content+":Status Code:"+str(statusCode))
                else:
                    logger.debug("LDAP with the same name does not exist")
        else:
            logger.error("Unsuccessful GET to server connection. Content returned : "+content+" Status Code returned : "+str(statusCode))
        jsonObj = {"connection":{"bindDN":"cn=root,secAuthority=default","bindPwd":"passw0rd","hostName":"localhost","ssl":"false","hostPort":389},"description":"Local LDAP server","name":"localldap","type":"ldap","connectionManager":{"connectTimeout":120}}
        data = json.dumps(jsonObj)
        logger.debug("POST to configure server connection")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        if statusCode == 201:
            logger.debug("Successfully POST to configure server connection. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured the server connection")
        else:
            logger.error("Unsuccessful POST to configure server connection. Content returned : "+content+" Status Code returned : "+str(statusCode))

    def createAttributeSources(self):

        logger.info("Configuring Attribute sources")
        endpoint = "/mga/attribute_sources"
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        jsonObj = {"name":"LDAPPhoneNumber","value":"homePhone","properties":[{"value":"localldap","key":"serverConnection"},{"value":"(objectclass=*)","key":"searchFilter"},{"value":"base","key":"scope"},{"value":"{BASE_DN}","key":"baseDN"},{"value":"homePhone,displayName","key":"selector"}],"type":"ldap"}
        data = json.dumps(jsonObj)
        logger.debug("POST to configure Attribute sources")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        if statusCode == 201:
            logger.debug("Successfully POST to configure Attribute sources for phone number. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful POST to configure Attribute sources for phone number. Content returned : "+content+" Status Code returned : "+str(statusCode))
        jsonObj = {"name":"LDAPDisplayName","value":"displayName","properties":[{"value":"localldap","key":"serverConnection"},{"value":"(objectclass=*)","key":"searchFilter"},{"value":"base","key":"scope"},{"value":"{BASE_DN}","key":"baseDN"},{"value":"homePhone,displayName","key":"selector"}],"type":"ldap"}
        data = json.dumps(jsonObj)
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        if statusCode == 201:
            logger.debug("Successfully POST to configure Attribute sources for display name. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured attribute sources")
        else:
            logger.error("Unsuccessful POST to configure Attribute sources for display name. Content returned : "+content+" Status Code returned : "+str(statusCode))

    def modifyAdvancedConfig(self, config="poc.websealAuth.authenticationMacros"):

        logger.info("Configuring Advanced Configuration to add Authentication Macros")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)

   
    
    def deployChanges(self):
        logger.debug("Deploy pending changes")
        
        content  = None
        content = json.loads(self.getCorePendingChanges())
        pendingChanges = content["changes"]
        
        if(len(pendingChanges) != 0):
            logger.debug("Pending changes to be deployed")
            self.deployPendingChangesBase()
        else:
            logger.debug("No pending changes to be deployed")
    
    def getCorePendingChanges(self):
        logger.debug("Deploy pending changes")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_GET_PENDING_CHANGES, "application/json", "", "application/json", "", "")
        if statusCode == 200:
            logger.debug("Successful GET of pending changes. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful GET of pending changes. Content returned : "+content+" Status Code returned : "+str(statusCode))

    def deployPendingChangesBase(self):
        logger.debug("Deploy pending changes in base")
        
        runtimeLastStart = -1
        runtimeLastStart = self.getRuntimeStartTime()
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_DEPLOY_CHANGES_ENDPOINT, "application/json", "", "application/json", "", "")
        if statusCode == 200:
            logger.debug("Successfully deployed pending changes. Content returned : "+content+" Status Code returned : "+str(statusCode))
            jsonContent = json.loads(content)
            result = jsonContent['result']
            status = jsonContent['status']
            message = jsonContent['message']
            if(result == 0):
                if(status == 0) :
                    logger.debug("Successful operation. No further action needed")
                if((status & 1) != 0):
                    logger.error("Deployment of core changes resulted in good result but failure status: "+str(status))
                if((status & 2) != 0):
                    logger.error("Appliance restart required - halting: "+str(status))                
                if((status & 4) != 0 or (status & 8) != 0):
                    logger.debug("LMI restart required for status: "+str(status))
                    self.restartLMI()
                if((status & 16) != 0):
                    logger.debug("Deployment of core changes indicates a server needs restarting: "+str(status))
                    self.restartReverseProxy()
                if((status & 32) != 0):
                    logger.debug("Runtime restart was performed for status: "+str(status))
                     #We better do this. Sometimes if you deploy again too soon
                     #after initiating a runtime restart, bad things can happen
                     #to the starting runtime
                    self.waitForRuntimeRestart(runtimeLastStart)
            else:
                logger.error("Deployment of core changes failed")    
        else:
            logger.error("Unsuccessfully deployed pending changes. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        
    def getRuntimeStartTime(self):
        logger.debug("Get Runtime Start Time")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_RESTART_RUNTIME, "application/json", "", "application/json", "", "")
        if statusCode == 200:
            logger.debug("Successful GET of last runtime start. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return json.loads(content)['last_start']
        else:
            logger.error("Unsuccessful GET of last runtime start. Content returned : "+content+" Status Code returned : "+str(statusCode))

    def waitForRuntimeRestart(self, lastStartTime):
        logger.debug("Wait for Runtime restart")
        
        if lastStartTime <= 0 :
            logger.error("Invalid lastStartTime when restarting runtime: " + str(lastStartTime))

        #Wait a brief period of time, then poll the runtime until it
        #returns a new number.
        # TODO - remove these sleeps when the runtime restart is synchronous to the deploy operation
        time.sleep(3)
        restartTime = self.getRuntimeStartTime()
        while(restartTime <= 0 or restartTime == lastStartTime):
            logger.debug("Waiting for runtime restart. lastStartTime=" + str(lastStartTime) + " restartTime=" + str(restartTime))
            time.sleep(3)
            restartTime = getRuntimeStartTime()
        #Extra sleep to be kiasu
        time.sleep(3)
    
    def restartLMI(self):
        logger.debug("Restart LMI")
        
        endpoint = "/restarts/commit_and_restart"
        
        lastStartTime = self.getLMIStartTime()
        if lastStartTime <= 0 :
            logger.error("Unable to get valid lastStartTime when restarting LMI: " + str(lastStartTime))
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        jsonObj = {"":""}
        data = json.dumps(jsonObj) 
        
        logger.debug("POST to restart LMI")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        if statusCode == 200:
            logger.debug("Successful LMI restart. Content returned : "+content+" Status Code returned : "+str(statusCode))
            restartResult = json.loads(content)["restart"]
            if restartResult == True :
                result = self.waitForLMIRestart(lastStartTime)
        else:
            logger.error("Unsuccessful LMI restart. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def waitForLMIRestart(self, lastStartTime):
        logger.debug("Wait for LMI Restart")
        
        result = False

        if lastStartTime <= 0 :
           logger.error("Invalid lastStartTime when restarting LMI: " + str(lastStartTime))

         # Wait a brief period of time, then poll the start_time until it
         # returns a new number. Because we may be setting NTP as part of the
         # restart, we can't just check for an increasing number

        time.sleep(4)
        restartTime = self.getLMIStartTime()
        while (restartTime <= 0 or restartTime == lastStartTime):
            logger.debug("Waiting for LMI restart. lastStartTime=" + str(lastStartTime) + " restartTime=" + str(restartTime))
            time.sleep(3)
            restartTime = self.getLMIStartTime()
        #give it a few more seconds to fully restart
        time.sleep(3)
        result = True

        return result
    
    def getLMIStartTime(self):
        logger.debug("Get LMI Start time")
        
        endpoint = "/lmi"
        try:
            HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
            
            statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
            if statusCode == 200:
                logger.debug("Successful call to LMI end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
                startTime = json.loads(content)[0]['start_time']
                return startTime
            else:
                logger.debug("Unsuccessful call to LMI end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
        except:
            logger.debug("Error during connection to lmi end point")
            return -1
    
    def restartReverseProxy(self):
        logger.debug("Restart all reverse proxy servers")
        
        endpoint = "/wga/reverseproxy"
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        logger.debug("GET all reverse proxy servers")
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/jsonConverter", "", "application/jsonConverter", "", "")
        
        if statusCode == 200:
            logger.debug("Successful retrieval of all reverse proxies. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful retrieval of all reverse proxies. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        revPrxJson = json.loads(content) 
        noOfinst = len(revPrxJson)
        logger.debug("Retrieve id of reverse proxy")
        
        i = 0
        for i in range(noOfinst):
            jsonObj = revPrxJson[i] 
            websealID = jsonObj['id'] 
            
            endpoint = "/wga/reverseproxy/" + websealID 
            
            jsonObj = {"instance_name":websealID,"restart":"true","started":"yes","id":websealID,"version":"","enabled":"yes","operation":"restart"}
            data = json.dumps(jsonObj)  
            
            logger.debug("PUT command to restart reverse proxy")
            statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
            
            if statusCode == 200:
                logger.debug("Successful restart of reverse proxy server. Content returned : "+content+" Status Code returned : "+str(statusCode))
            else:
                logger.error("Unsuccessful restart of reverse proxy server. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def checkPassword(self):
        logger.debug("Checking the username:password combination for the appliance")
        sessionTimeout = -1
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD) 
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.FIRST_STEPS, "application/json", "", "", "", "")
        if statusCode == 200 or statusCode ==302:
            logger.debug("Default username:password combination was right"+self.USERNAME+":"+self.PASSWORD)
            password = self.PASSWORD
        else:
            HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.OLD_PASSWORD) 
            statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.FIRST_STEPS, "application/json", "", "", "", "")
            if statusCode == 200 or statusCode ==302:
                logger.debug("Default username:password combination was right"+self.USERNAME+":"+self.OLD_PASSWORD)
                password = self.OLD_PASSWORD
            else:
                logger.debug("Unsuccessful to retrieve the correct username and password")
        return password
    
    def getFirmwareVersion(self):
        logger.debug("Get Firmware Information")
        password = self.checkPassword()
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = password)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.FIRMWARE_SETTINGS, "application/json", "", "application/json", "", "")
        if statusCode == 200:
            logger.debug("Successful GET of firmware information. Content returned : "+content+" Status Code returned : "+str(statusCode))
            content = json.loads(content)
            
            for firmware in content:
                if(firmware[u'active'] == True): 
                    logger.debug("Found active firmware in partition "+firmware[u'partition'])
                    firmwareVersion = firmware[u'firmware_version']
                    logger.debug("Firmware Version "+ firmwareVersion)
                    return firmwareVersion
            if firmwareVersion == None:
                logger.error("Failed to find active partition")
                
        elif statusCode == 404:
            logger.debug("Received 404 from runtime endpoint when querying firmware information.")
        else:
            logger.error("Unsuccessful GET of firmware information. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def addMacroToPocProfile(self):
        logger.debug("Add Macro to POC profile")
        password = self.checkPassword()
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = password)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.POC, "application/json", "", "application/json", "", "")
        if statusCode == 200:
            logger.debug("Successful GET of Current POC ID. Content returned : "+content+" Status Code returned : "+str(statusCode))
            content = json.loads(content)
            currentProfileId = content[u'currentProfileId']
            logger.debug("Current POC Profile ID is " + currentProfileId)
            statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.POC+"/profiles/"+currentProfileId, "application/json", "", "application/json", "", "")
            if statusCode == 200:
                logger.debug("Successful GET of POC Information. Content returned : "+content+" Status Code returned : "+str(statusCode))
                content = json.loads(content)
                poc_authenticateCallbacks = content[u'authenticateCallbacks']
                poc_localIdCallbacks = content[u'localIdCallbacks']
                poc_signInCallbacks = content[u'signInCallbacks']
                poc_signOutCallbacks = content[u'signOutCallbacks']
                poc_authnPolicyCallbacks = content[u'authnPolicyCallbacks']
                poc_description = content[u'description']
                poc_name = content[u'name']
                
                poc_name = "PartnerId Macro with " + poc_name
                poc_description = poc_description + "\n\n\nWith PARTNERID Macro."
                
                poc_parameters = poc_authenticateCallbacks[0][u'parameters']
                for parameter in poc_parameters:
                    if (parameter[u'name'] == "authentication.macros"):
                        parameter[u'value'] = "%PARTNERID%"
                        logger.debug("Set authentication macros parameter")
                logger.debug("Parameters:" + str(poc_parameters))
                poc_authenticateCallbacks[0][u'parameters'] = poc_parameters
                endpoint = self.POC+"/profiles"
                jsonObj = {"authenticateCallbacks":poc_authenticateCallbacks,"localIdCallbacks":poc_localIdCallbacks,"signInCallbacks":poc_signInCallbacks,"signOutCallbacks":poc_signOutCallbacks,"authnPolicyCallbacks":poc_authnPolicyCallbacks,"description":poc_description,"name":poc_name,"isReadOnly":False}
                data = json.dumps(jsonObj)
                logger.debug("POST to add new POC profile")
                statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
                if statusCode == 201:
                    logger.debug("Successfully POST to add new POC profile. Content returned : "+content+" Status Code returned : "+str(statusCode))
                    self.setPOCProfile(poc_name)
                else:
                    logger.error("Unsuccessful POST to add new POC profile. Content returned : "+content+" Status Code returned : "+str(statusCode))
            else:
                logger.error("Unsuccessful GET of POC information. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful GET of POC ID. Content returned : "+content+" Status Code returned : "+str(statusCode))
