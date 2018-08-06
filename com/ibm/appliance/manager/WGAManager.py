'''
Created on Jul 25, 2015

@copyright: IBM
'''

from com.ibm.appliance.util.Common import CommonProperties 
from com.ibm.appliance.util.Settings import Settings
from com.ibm.appliance.util.HTTPRequest import ISAMRestClient
from com.ibm.appliance.util import HTTPRequest
import json,logging,time,os,sys
from com.ibm.appliance.manager.BaseManager import BaseManager
from com.ibm.appliance.manager.ldapManager import ldapManager

logger = logging.getLogger("WGAManager")
logger.setLevel(logging.INFO)

class WGAManager(object):
    
    ISAM_RUNTIME_ENDPOINT = "/isam/runtime_components"
    ISAM_REVERSE_PROXY_ENDPOINT = "/wga/reverseproxy"
    ISAM_PDSRV_CERT_ENDPOINT = "/isam/ssl_certificates/pdsrv/signer_cert"
    ISAM_DEPLOY_CHANGES_ENDPOINT = "/isam/pending_changes/deploy"
    ISAM_GET_PENDING_CHANGES = "/isam/pending_changes"
    ISAM_RESTART_RUNTIME = "/mga/runtime_profile/local/v1"
    ISAM_SSL_CERTIFICATE = "/isam/ssl_certificates"
    ISAM_SAML_JCT_STS_TOKEN_TYPE_SAML20 = "http://docs.oasis-open.org/wss/oasis-wss-saml-token-profile-1.1#SAMLV2.0"
    ISAM_LTPA_JCT_STS_TOKEN_TYPE = "http://www.ibm.com/websphere/appserver/tokentype#LTPAv2"
    def __init__(self, properties):
        
        self.BASEURL = properties[CommonProperties.PROP_BASEURL]  
        self.USERNAME = properties[CommonProperties.PROP_USERNAME]
        self.PASSWORD = properties[CommonProperties.PROP_PASSWORD]      
        self.WEB_HOST_NAME = properties[CommonProperties.PROP_WEB_HOST_NAME]
        self.WGA_HOST_NAME = properties[CommonProperties.PROP_WGA_HOST_NAME]
        self.APP_INTERFACE_IP = properties[CommonProperties.PROP_PRI_INTERFACE_IP]
        self.SAML_FED_NAME = properties[CommonProperties.PROP_SAML_FEDNAME]
        self.SAML_FED_ROLE = properties[CommonProperties.PROP_SAML_FED_ROLE]
        self.ISAM_SAML_JCT = properties[CommonProperties.PROP_SAML_JUNCT] 
        self.ISAM_SAML_JCT_SAML_APPLIES_TO = properties[CommonProperties.PROP_SAML_APPLIES_TO]
        self.ISAM_LTPA_JCT = properties[CommonProperties.PROP_LTPA_JUNCT] 
        self.ISAM_LTPA_JCT_SAML_APPLIES_TO = properties[CommonProperties.PROP_LTPA_APPLIES_TO]
        self.EASUSER_OLD_PASSWORD = properties[CommonProperties.PROP_EASUSER_OLD_PASSWORD]
        self.EASUSER_PASSWORD = properties[CommonProperties.PROP_EASUSER_PASSWORD]
         
    
    def configureWgaAll(self):
        logger.debug("Triggering All WGA configuration")
        
        logger.debug("Configuring runtime component")
        self.configureRuntimeComponent()
                  
        logger.debug("Configuring WebSEAL instance")
        self.configureWebSEALInstance(self.APP_INTERFACE_IP, wgaHostName=self.WGA_HOST_NAME) 
        
        logger.debug("Adding Signer Certificates")        
        self.addSignerCertificates() 
         
        #Covered by POC Configuration with GA code
        #logger.debug("Creating ISAM junction")
        #self.createJunction()
               
        logger.debug("Configuring WebSEAL conf file")
        self.configureWebSEALConf(websealHostName=self.WEB_HOST_NAME)
        
        if(self.SAML_FED_ROLE == "idp"):
            logger.debug("Configuring WebSEAL conf file for IP")
            self.configureIdPWebSEALConf(websealHostName=self.WEB_HOST_NAME)
            
            logger.debug("Uploading the LTPA keys")
            self.uploadLTPAKeys("ltpasso.keys", "idp_files/LTPA/ltpasso.keys")
             
            #Covered by POC Configuration with GA code
            #logger.debug("Running pdadmin commands for IP")
            #self.doPDADMINCommandsSAMLIP(fedName=self.SAML_FED_NAME, wgaHostName=self.WGA_HOST_NAME)
            
            logger.debug("Uploading keystore for IP")
            self.uploadKeystore("myidpkeys.kdb", "idp_files/myidpkeys.kdb", "myidpkeys.sth", "idp_files/myidpkeys.sth")
            
            logger.debug("Uploading the modified pages")
            self.uploadPages(dirLocation="idp_files/pages")
        
        if(self.SAML_FED_ROLE == "sp"):
            logger.debug("Configuring WebSEAL conf file for SP")
            self.configureSPWebSEALConf(websealHostName=self.WEB_HOST_NAME)
            self.createTestUser("anonymous")
             
            #Covered by POC Configuration with GA Code
            #logger.debug("Running pdadmin commands for SP")
            #self.doPDADMINCommandsSAMLSP(fedName=self.SAML_FED_NAME, wgaHostName=self.WGA_HOST_NAME)
              
            logger.debug("Uploading keystore for SP")
            self.uploadKeystore("myspkeys.kdb", "sp_files/myspkeys.kdb", "myspkeys.sth", "sp_files/myspkeys.sth")
         
        logger.debug("Deploying pending changes")
        self.deployChanges()
              
        if(self.SAML_FED_ROLE == "idp"):       
            logger.debug("Creating a test user")
            self.createTestUser()
            
        if(self.SAML_FED_ROLE == "sp"):       
            #Need to fix ldap attribute issue
            logger.debug("Creating a test user")
            self.createTestUser()
              
        logger.debug("Restarting LMI")
        self.restartLMI()
         
        logger.debug("End of All WGA configuration")
     
    def configureWga(self):
        logger.debug("Triggering WGA configuration")
        
        if Settings.features["All"] :
            logger.debug("All WGA configuration is triggered")
            self.configureWgaAll()
        else:
            logger.debug("Subset of WGA configuration is triggered")
            deployChanges = False
            
            if Settings.features["Runtime_Component"]:
                deployChanges = True
                logger.debug("Configuring runtime component")
                self.configureRuntimeComponent()
            
            if Settings.features["WebSEAL_Instance"]:  
                deployChanges = True 
                logger.debug("Configuring WebSEAL instance")
                self.configureWebSEALInstance(self.APP_INTERFACE_IP, wgaHostName=self.WGA_HOST_NAME) 
                self.configureWebSEALConf(websealHostName=self.WEB_HOST_NAME)
            
            if Settings.features["Signer_Certificates"]:  
                deployChanges = True
                logger.debug("Adding Signer Certificates")        
                self.addSignerCertificates() 
            
            if Settings.features["Upload_pages"]:
                if(self.SAML_FED_ROLE == "idp"):
                    deployChanges = True
                    logger.debug("Uploading the modified pages")
                    logger.info("Configuring login HTML")
                    self.uploadPages(dirLocation="idp_files/pages")
                    logger.info("Successfully configured login HTML")
            
            if Settings.features["WebSEAL_Configfile"]:  
                if(self.SAML_FED_ROLE == "idp"):     
                    deployChanges = True
                    logger.debug("Configuring WebSEAL conf file for IP")
                    self.configureIdPWebSEALConf(websealHostName=self.WEB_HOST_NAME)
                if(self.SAML_FED_ROLE == "sp"):
                    deployChanges = True  
                    logger.debug("Configuring WebSEAL conf file for SP")
                    self.configureSPWebSEALConf(websealHostName=self.WEB_HOST_NAME)
                    self.createTestUser("anonymous")
                 
            if Settings.features["Junction"]:
                deployChanges = False
                logger.debug("Creating ISAM junction by default")
                self.createJunction()
            
            if Settings.features["ACL"]:
                if(self.SAML_FED_ROLE == "idp"):
                    deployChanges = True
                    logger.debug("Running pdadmin commands for IP")
                    self.doPDADMINCommandsSAMLIP(fedName=self.SAML_FED_NAME, wgaHostName=self.WGA_HOST_NAME)
                if(self.SAML_FED_ROLE == "sp"):
                    deployChanges = True
                    logger.debug("Running pdadmin commands for SP")
                    self.doPDADMINCommandsSAMLSP(fedName=self.SAML_FED_NAME, wgaHostName=self.WGA_HOST_NAME)
            
            if Settings.features["Keystore"]:
                if(self.SAML_FED_ROLE == "idp"):
                    deployChanges = True
                    logger.info("Configuring keystore for IdP")
                    self.uploadKeystore("myidpkeys.kdb", "idp_files/myidpkeys.kdb", "myidpkeys.sth", "idp_files/myidpkeys.sth")
                if(self.SAML_FED_ROLE == "sp"):
                    deployChanges = True
                    logger.info("Configuring keystore for SP")
                    self.uploadKeystore("myspkeys.kdb","sp_files/myspkeys.kdb", "myspkeys.sth", "sp_files/myspkeys.sth")
                   
            if Settings.features["Test_User"]:       
                logger.debug("Creating a test user")
                self.createTestUser()

            if deployChanges:
                logger.debug("Deploying pending changes")
                self.deployChanges()
              
            logger.debug("Subset of WGA configuration tasks completed")
    
    def uploadPages(self, dirLocation, instanceName='default'):
        logger.debug("Upload pages")
        
        listOfValidPages = ["acct_locked.html" ,"certfailure.html" ,"certlogin.html" ,"certstepuphttp.html" ,"help.html" ,"login.html" ,"login_success.html" ,"logout.html" ,
                                "nexttoken.html" ,"passwd.html" ,"passwd_exp.html" ,"passwd_rep.html" ,"passwd_warn.html" ,"redirect.html" ,"stepuplogin.html" ,
                                "switchuser.html" ,"temp_cache_response.html" ,"tokenlogin.html" ,"too_many_sessions.html"]
        
        
        listOfPagesInDir = []
        dirs = os.listdir( dirLocation )
        for page in dirs:
           try:
               listOfValidPages.index(page)
               listOfPagesInDir.append(page)
           except ValueError:
               logger.error("Pages directory does not have a page called %s" %(page))
                      
        endpoint = "/wga/reverseproxy"
        
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
        i = 0
        for i in range(noOfRevProx):
            if(revProxiesJson[i]['instance_name'] == instanceName):
                webSealId = revProxiesJson[i]['id']
        
        if(webSealId != None):
            for page in listOfPagesInDir:
                fileLoc = dirLocation + "/" + page
                fileObj = open(fileLoc, "r")
                fileData = fileObj.read()
                jsonObj = {"type":"File","contents":fileData}
                data = json.dumps(jsonObj)
                endpoint = "/wga/reverseproxy" + "/" + webSealId + "/management_root/management/C/" + page
                statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
                
                if statusCode == 200:
                    logger.debug("Successful modification of page. Content returned : "+content+" Status Code returned : "+str(statusCode))
                else:
                    logger.error("Unsuccessful modification of page. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def uploadLTPAKeys(self, targetFileName="ltpasso.keys", fileLocation="idp_files/LTPA/ltpasso.keys"):
        logger.debug("Upload LTPA keys") 
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        endpoint = "/wga/ltpa_key"
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        if statusCode == 200:
            logger.debug("Successful GET of LTPA Keys. Content returned : "+content+" Status Code returned : "+str(statusCode))
            content = json.loads(content) 
            keyName = "ltpasso.keys"
            for ltpa in content:
                if(ltpa[u'id'] == keyName): 
                    logger.debug("LTPAKey exists, deleting it and re creating it")
                    endpoint1 = "/wga/ltpa_key/" + keyName
                    statusCode, contentHeader, content = ISAMRestClient.delete(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint1, "application/json", "", "")
                    if statusCode == 200:
                        logger.debug("LTPAKey deleted successfully"+content+":Status Code:"+str(statusCode))
                                     
                    else:
                        logger.debug("LTPAKey deletion failed"+content+":Status Code:"+str(statusCode))
                else:
                    logger.debug("LTPAKey with the same name does not exist")
        else:
            logger.error("Unsuccessful GET to server connection. Content returned : "+content+" Status Code returned : "+str(statusCode))
        fileData = {"ltpa_keyfile": (str(targetFileName), open(fileLocation, 'rb').read(), 'application/octet-stream')}
        statusCode, contentHeader, content = ISAMRestClient.postFile(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json",file=fileData);
        if statusCode == 200:
            logger.debug("Successfully uploaded LTPA keys. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessfully uploaded LTPA keys. Content returned : "+content+" Status Code returned : "+str(statusCode)) 
    
    def deleteLTPAKeys(self, targetFileName):
        logger.debug("Delete LTPA keys.")
        endpoint = "/wga/ltpa_key" + "/" + targetFileName  
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)  
        statusCode, contentHeader, content = ISAMRestClient.delete(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", None) 
        if statusCode == 200:
            logger.debug("Successfully delete LTPA keys. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessfully delete LTPA keys. Content returned : "+content+" Status Code returned : "+str(statusCode)) 
            
    def getLTPAKeys(self, targetFileName):
        logger.debug("Get LTPA keys") 
        endpoint = "/wga/ltpa_key" + "/" + targetFileName 
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/jsonConverter", "", "application/jsonConverter", "", "")
        if statusCode == 200:
            logger.debug("Successfully get LTPA keys. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessfully get LTPA keys. Content returned : "+content+" Status Code returned : "+str(statusCode))  
            return None   
    
    def getKeystores(self):
        logger.debug("Get keystores") 
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_SSL_CERTIFICATE, "application/jsonConverter", "", "application/jsonConverter", "", "")
        if statusCode == 200:
            logger.debug("Successfully get keystores. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessfully get keystores. Content returned : "+content+" Status Code returned : "+str(statusCode)) 
    
    def uploadKeystore(self, kdbContentName, keystoreFilename, statshContentName, stashFilename):
        logger.debug("Configure keystore") 
        jsonObj = {"":""}
        data = json.dumps(jsonObj) 
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        keystoreFilename = keystoreFilename
        stashFilename = stashFilename 
        multiple_files = {'kdbs[]': (kdbContentName, open(keystoreFilename, 'rb').read(),'application/octet-stream'),'stashs[]': (statshContentName, open(stashFilename, 'rb').read(),'application/octet-stream')}
        statusCode, contentHeader, content = ISAMRestClient.postMultiFile(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_SSL_CERTIFICATE, "application/json",multiFileName=multiple_files) 
        if statusCode == 200:
            logger.debug("Successfully upload keystore. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully uploaded and configured keystore")
        else:
            logger.error("Unsuccessfully upload keystore. Content returned : "+content+" Status Code returned : "+str(statusCode)) 
    
    def deleteKeystore(self, keystoreName):
        logger.debug("Delete keystore.")
        endpoint = self.ISAM_SSL_CERTIFICATE + "/" + keystoreName  
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)  
        statusCode, contentHeader, content = ISAMRestClient.delete(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", None) 
        if statusCode == 200:
            logger.debug("Successfully delete keystore. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessfully delete keystore. Content returned : "+content+" Status Code returned : "+str(statusCode)) 
    
        
    def createTestUser(self, username='testuser', password='Passw0rd'):
        logger.info("Configuring user: " + username)
        ldapClient = ldapManager()
        endpoint = "/isam/pdadmin/"
        cnsn = "Test User"
        
        jsonObj = {"admin_id":"sec_master","admin_pwd": "Passw0rd","commands":[]}
        data = json.loads(json.dumps(jsonObj))
        data['commands'].append("user show "+username) 
        data = json.dumps(data) 
        
        createUserFlag = False
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data) 
        if statusCode == 500 and str(content).find("The entry was not found") > 0:
            createUserFlag = True

        if(createUserFlag == True):
            
            if (username == "anonymous"):
                cnsn = "anonymous anonymous"
            
            jsonObj = {"admin_id":"sec_master","admin_pwd": "Passw0rd","commands":[]}
            data = json.loads(json.dumps(jsonObj))
            data[u'commands'].append("user create "+username+" " + "cn="+username+",dc=iswga " + cnsn + " " +password)
            data[u'commands'].append("user modify "+username+" account-valid yes")        
            data = json.dumps(data)  
           
            logger.debug("POST to create a user")
            statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
            if statusCode == 200:
                logger.debug("Successful creation of a user. Content returned : "+content+" Status Code returned : "+str(statusCode))
                logger.info("Successfully configured user: " + username)
                if(self.SAML_FED_ROLE == "idp"):
                    logger.info("Configuring test user to add extra attributes")
                    ldapClient.ldap_configuration()
            else:
                logger.error("Unsuccessful creation of a user. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("User already exists")

        
    
    def doPDADMINCommandsSAMLIP(self, fedName, wgaHostName = 'localhost', instanceName='default'):
        logger.info("Configure ACLs for IdP")
        
        websealObjectName = "/WebSEAL/" + wgaHostName + "-" + instanceName
        
        endpoint = "/isam/pdadmin/"
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        jsonObj = {"admin_id":"sec_master","admin_pwd": self.PASSWORD,"commands":[]}
        data = json.loads(json.dumps(jsonObj)) 
        
        #saml20idp-unauth
        data[u'commands'].append("acl detach " + websealObjectName + "/favicon.ico")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20idp/saml20/login")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20idp/saml20/logininitial")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20idp/saml20/slo")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20idp/saml20/sloinitial")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/static")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20idp/saml20/mnids")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20idp/saml20/soap")
        
        
        
        

        data[u'commands'].append("acl delete saml20idp-unauth")

        data[u'commands'].append("acl create saml20idp-unauth")
        data[u'commands'].append("acl modify saml20idp-unauth set group iv-admin TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify saml20idp-unauth set group webseal-servers Tgmdbsrxl")
        data[u'commands'].append("acl modify saml20idp-unauth set user sec_master TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify saml20idp-unauth set any-other Tr")
        data[u'commands'].append("acl modify saml20idp-unauth set unauthenticated Tr")

        data[u'commands'].append("acl attach " + websealObjectName + "/favicon.ico saml20idp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20idp/saml20/login saml20idp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20idp/saml20/logininitial saml20idp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20idp/saml20/slo saml20idp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20idp/saml20/sloinitial saml20idp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/static saml20idp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20idp/saml20/mnids saml20idp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20idp/saml20/soap saml20idp-unauth")

        #saml20idp-anyauth
        data[u'commands'].append("acl detach " + websealObjectName + "/sam/spsi/auth")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20idp/saml20/auth")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/wssoi")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20idp/saml20/mnidsinitial")
    

        data[u'commands'].append("acl delete saml20idp-anyauth")

        data[u'commands'].append("acl create saml20idp-anyauth")
        data[u'commands'].append("acl modify saml20idp-anyauth set group iv-admin TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify saml20idp-anyauth set group webseal-servers Tgmdbsrxl")
        data[u'commands'].append("acl modify saml20idp-anyauth set user sec_master TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify saml20idp-anyauth set any-other Tr")
        data[u'commands'].append("acl modify saml20idp-anyauth set unauthenticated T")

        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20idp/saml20/auth saml20idp-anyauth")  
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/auth saml20idp-anyauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/wssoi saml20idp-anyauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20idp/saml20/mnidsinitial saml20idp-anyauth")
        
        data[u'commands'].append("object modify " + websealObjectName + "/isam set attribute HTTP-Tag-Value user_session_id=user_session_id")
        
        data[u'commands'].append("server replicate")      
        data = json.dumps(data)
                 
        logger.debug("POST to create and attach ACL")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        if statusCode == 200 and (str(content).find("Error") == -1 or str(content).count("Error: HPDAC0456E") == 13):
            logger.debug("Successful POST to create and attach ACL for SAML IdP. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured ACLs SAML IdP")
        else:
            logger.error("Unsuccessful POST to create and attach ACL for SAML IdP. Content returned : "+content+" Status Code returned : "+str(statusCode))

    
    def doPDADMINCommandsSAMLSP(self, fedName, wgaHostName = 'localhost', instanceName='default'):
        logger.info("Configure ACLs for SP")
        
        websealObjectName = "/WebSEAL/" + wgaHostName + "-" + instanceName
        
        endpoint = "/isam/pdadmin/"
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        jsonObj = {"admin_id":"sec_master","admin_pwd": self.PASSWORD,"commands":[]}
        data = json.loads(json.dumps(jsonObj)) 
        
        data[u'commands'].append("acl detach " + websealObjectName + "/favicon.ico")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20sp/saml20/login")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20sp/saml20/logininitial")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20sp/saml20/slo")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20sp/saml20/sloinitial")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20sp/saml20/soap")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20sp/saml20/mnids")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/static")
        
        data[u'commands'].append("acl delete saml20sp-unauth")

        data[u'commands'].append("acl create saml20sp-unauth")
        data[u'commands'].append("acl modify saml20sp-unauth set group iv-admin TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify saml20sp-unauth set group webseal-servers Tgmdbsrxl")
        data[u'commands'].append("acl modify saml20sp-unauth set user sec_master TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify saml20sp-unauth set any-other Tr")
        data[u'commands'].append("acl modify saml20sp-unauth set unauthenticated Tr")

        data[u'commands'].append("acl attach " + websealObjectName + "/favicon.ico saml20sp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20sp/saml20/login saml20sp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20sp/saml20/logininitial saml20sp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20sp/saml20/slo saml20sp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20sp/saml20/sloinitial saml20sp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/static saml20sp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20sp/saml20/soap saml20sp-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20sp/saml20/mnids saml20sp-unauth")
        
        #saml20sp-anyauth
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20sp/saml20/auth")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/auth")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/wssoi")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/sps/saml20sp/saml20/mnidsinitial")

        data[u'commands'].append("acl delete saml20sp-anyauth")

        data[u'commands'].append("acl create saml20sp-anyauth")
        data[u'commands'].append("acl modify saml20sp-anyauth set group iv-admin TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify saml20sp-anyauth set group webseal-servers Tgmdbsrxl")
        data[u'commands'].append("acl modify saml20sp-anyauth set user sec_master TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify saml20sp-anyauth set any-other Tr")
        data[u'commands'].append("acl modify saml20sp-anyauth set unauthenticated T")

        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20sp/saml20/auth saml20sp-anyauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/auth saml20sp-anyauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/wssoi saml20sp-anyauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/sps/saml20sp/saml20/mnidsinitial saml20sp-anyauth")
        
        data[u'commands'].append("object modify " + websealObjectName + "/isam set attribute HTTP-Tag-Value user_session_id=user_session_id")
        
        data[u'commands'].append("server replicate")
        
        data = json.dumps(data)
                 
        logger.debug("POST to create and attach ACL")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        if statusCode == 200 and (str(content).find("Error") == -1 or str(content).count("Error: HPDAC0456E") == 13):
            logger.debug("Successful POST to create and attach ACL for SAML SP. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured ACLs SAML SP")
        else:
            logger.error("Unsuccessful POST to create and attach ACL for SAML SP. Content returned : "+content+" Status Code returned : "+str(statusCode))

    def doPDADMINCommandsSTS(self, wgaHostName = 'localhost', instanceName='default'):
        logger.info("Configure WGA for STS Chains")

        websealObjectName = "/WebSEAL/" + wgaHostName + "-" + instanceName

        endpoint = "/isam/pdadmin/"

        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)

        jsonObj = {"admin_id":"sec_master","admin_pwd": self.PASSWORD,"commands":[]}
        data = json.loads(json.dumps(jsonObj))

        data[u'commands'].append("acl detach " + websealObjectName + "/isam/TrustServer/SecurityTokenService")
        data[u'commands'].append("acl detach " + websealObjectName + "/isam/TrustServerWST13/services/RequestSecurityToken")
        data[u'commands'].append("acl delete sts-unauth")
        data[u'commands'].append("acl create sts-unauth")
        data[u'commands'].append("acl modify sts-unauth set group iv-admin TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify sts-unauth set group webseal-servers Tgmdbsrxl")
        data[u'commands'].append("acl modify sts-unauth set user sec_master TcmdbsvaBRrxl")
        data[u'commands'].append("acl modify sts-unauth set any-other Tr")
        data[u'commands'].append("acl modify sts-unauth set unauthenticated Tr")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/TrustServerWST13/services/RequestSecurityToken sts-unauth")
        data[u'commands'].append("acl attach " + websealObjectName + "/isam/TrustServer/SecurityTokenService sts-unauth")
        data[u'commands'].append("server replicate")

        data = json.dumps(data)
        logger.debug("POST to create and attach ACL")
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        if statusCode == 200 and (str(content).find("Error") == -1 or str(content).count("Error: HPDAC0456E") == 3):
            logger.debug("Successful POST to create and attach ACL for STS Chain. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured ACLs for STS Chain.")
        else:
            logger.error("Unsuccessful POST to create and attach ACL for STS Chain.. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def createJunction(self, mgaHost='localhost', instanceName='default', junctionName='/isam'): 
        logger.info("Configuring junction")
        
        endpoint = "/wga/reverseproxy"
        
        logger.debug("GET the WebSEAL details based on WebSEAL hostname")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured junction")
        else:
            logger.error("Unsuccessful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        revProxiesJson = json.loads(content)
        
        noOfRevProx = len(revProxiesJson)
        webSealId = None
        i = 0
        for i in range(noOfRevProx):
            if(revProxiesJson[i]['instance_name'] == instanceName):
                webSealId = revProxiesJson[i]['id']
        
        if(webSealId != None):
        
            endpoint = "/wga/reverseproxy" + "/" + webSealId + "/junctions"
            
            jsonObj = {"server_hostname":mgaHost, "junction_point": str(junctionName), "junction_type": "ssl","remote_http_header":[], "client_ip_http":"yes", "stateful_junction":"yes", "basic_auth_mode":"ignore", "server_port":"443", "scripting_support":"yes", "request_encoding":"utf8_uri", "junction_cookie_javascript_block":"inhead", "force":"true"}
            data = json.loads(json.dumps(jsonObj)) 
            data[u'remote_http_header'].append("iv-user")
            data[u'remote_http_header'].append("iv-groups")
            data[u'remote_http_header'].append("iv-creds")  
            data = json.dumps(data) 
            
            logger.debug("POST to create junction")
            statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
            if statusCode == 200:
                logger.debug("Successful creation of junction. Content returned : "+content+" Status Code returned : "+str(statusCode))
            else:
                logger.error("Unsuccessful creation of junction. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def createSAMLJunction(self, mgaHost='localhost', instanceName='default', junctionName='/samljct'): 
        logger.info("Configuring junction")
        
        endpoint = "/wga/reverseproxy"
        
        logger.debug("GET the WebSEAL details based on WebSEAL hostname")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured junction")
        else:
            logger.error("Unsuccessful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        revProxiesJson = json.loads(content)
        
        noOfRevProx = len(revProxiesJson)
        webSealId = None
        i = 0
        for i in range(noOfRevProx):
            if(revProxiesJson[i]['instance_name'] == instanceName):
                webSealId = revProxiesJson[i]['id']
        
        if(webSealId != None):
        
            endpoint = "/wga/reverseproxy" + "/" + webSealId + "/junctions"
            
            jsonObj = {"server_hostname":mgaHost, "junction_point": str(junctionName), "junction_type": "ssl", 
                       "basic_auth_mode":"ignore", "tfim_sso":"yes","remote_http_header":[],
                       "server_port":"443", "force":"true"}
            data = json.loads(json.dumps(jsonObj)) 
            data[u'remote_http_header'].append("iv-user")
            data[u'remote_http_header'].append("iv-creds")  
            data = json.dumps(data) 
            
            logger.debug("POST to create SAML junction")
            statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
            if statusCode == 200:
                logger.debug("Successful creation of SAML junction. Content returned : "+content+" Status Code returned : "+str(statusCode))
            else:
                logger.error("Unsuccessful creation of SAML junction. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def createLTPAJunction(self, mgaHost='localhost', instanceName='default', junctionName='/ltpajct'): 
        logger.info("Configuring junction")
        
        endpoint = "/wga/reverseproxy"
        
        logger.debug("GET the WebSEAL details based on WebSEAL hostname")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured junction")
        else:
            logger.error("Unsuccessful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        revProxiesJson = json.loads(content)
        
        noOfRevProx = len(revProxiesJson)
        webSealId = None
        i = 0
        for i in range(noOfRevProx):
            if(revProxiesJson[i]['instance_name'] == instanceName):
                webSealId = revProxiesJson[i]['id']
        
        if(webSealId != None):
        
            endpoint = "/wga/reverseproxy" + "/" + webSealId + "/junctions"
            
            jsonObj = {"server_hostname":mgaHost, "junction_point": str(junctionName), "junction_type": "ssl", 
                       "basic_auth_mode":"ignore", "tfim_sso":"yes","remote_http_header":[],
                       "server_port":"443", "force":"true"}
            data = json.loads(json.dumps(jsonObj)) 
            data[u'remote_http_header'].append("iv-user")
            data[u'remote_http_header'].append("iv-creds")  
            data = json.dumps(data) 
            
            logger.debug("POST to create SAML junction")
            statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
            if statusCode == 200:
                logger.debug("Successful creation of SAML junction. Content returned : "+content+" Status Code returned : "+str(statusCode))
            else:
                logger.error("Unsuccessful creation of SAML junction. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    
    def configureWebSEALConfForSAMLJct(self, websealHostName, instanceName = 'default'):
        logger.info("Configuring WebSEAL.conf file for SAML Junction at IdP")
        
        endpoint = "/wga/reverseproxy"
        
        logger.debug("GET the WebSEAL details based on WebSEAL hostname")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured WebSEAL.conf file for SAML IdP")
        else:
            logger.error("Unsuccessful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        revProxiesJson = json.loads(content)
        
        noOfRevProx = len(revProxiesJson)
        webSealId = None
        i = 0
        for i in range(noOfRevProx):
            if(revProxiesJson[i]['instance_name'] == instanceName):
                webSealId = revProxiesJson[i]['id']
        
        if(webSealId != None):
            
            #TFIM cluster for local runtime
            clusterName = self.ISAM_SAML_JCT.split("/")[1]
            stanza = "tfim-cluster:" + clusterName
            self.pdconfSetEntry(webSealId, stanza, "server","9,https://localhost:443/TrustServerWST13/services/RequestSecurityToken")
            self.pdconfSetEntry(webSealId, stanza, "ssl-keyfile", "pdsrv.kdb")
            self.pdconfSetEntry(webSealId, stanza, "ssl-keyfile-stash", "pdsrv.sth")
            self.pdconfSetEntry(webSealId, stanza, "handle-pool-size", "10")
            self.pdconfSetEntry(webSealId, stanza, "handle-idle-timeout", "240")
            self.pdconfSetEntry(webSealId, stanza, "timeout", "240")
            self.pdconfSetEntry(webSealId, stanza, "basic-auth-user", "easuser")
            self.pdconfSetEntry(webSealId, stanza, "basic-auth-passwd", self.EASUSER_PASSWORD)

            #sso junction
            stanza = "tfimsso:" + self.ISAM_SAML_JCT
            self.pdconfSetEntry(webSealId, stanza, "token-type", self.ISAM_SAML_JCT_STS_TOKEN_TYPE_SAML20)
            self.pdconfSetEntry(webSealId, stanza, "applies-to", self.ISAM_SAML_JCT_SAML_APPLIES_TO)
            self.pdconfSetEntry(webSealId, stanza, "renewal-window", "15")
            self.pdconfSetEntry(webSealId, stanza, "preserve-xml-token", "false")
            self.pdconfSetEntry(webSealId, stanza, "always-send-tokens", "true")
            self.pdconfSetEntry(webSealId, stanza, "tfim-cluster-name", clusterName)

            #inefficient, but for demo shows new SAML assertions being sent on
            # every request and STS being called each request
            self.pdconfSetEntry(webSealId, stanza, "one-time-token", "true")
            self.pdconfSetEntry(webSealId, stanza, "token-collection-size", "1")

            #send via HTTP Header called SAMLAssertion for demo
            self.pdconfSetEntry(webSealId, stanza, "token-transmit-type", "header")
            self.pdconfSetEntry(webSealId, stanza, "token-transmit-name", "SAMLAssertion")
        else:
            logger.error("WebSEAL server not found. Cannot complelte configuration")
            
            
    def configureWebSEALConfForLTPAJct(self, websealHostName, instanceName = 'default'):
        logger.info("Configuring WebSEAL.conf file for LTPA Junction at IdP")
        
        endpoint = "/wga/reverseproxy"
        
        logger.debug("GET the WebSEAL details based on WebSEAL hostname")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured WebSEAL.conf file for LTPA junction at IdP")
        else:
            logger.error("Unsuccessful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        revProxiesJson = json.loads(content)
        
        noOfRevProx = len(revProxiesJson)
        webSealId = None
        i = 0
        for i in range(noOfRevProx):
            if(revProxiesJson[i]['instance_name'] == instanceName):
                webSealId = revProxiesJson[i]['id']
        
        if(webSealId != None):
            
            #TFIM cluster for local runtime
            clusterName = self.ISAM_LTPA_JCT.split("/")[1]
            stanza = "tfim-cluster:" + clusterName
            self.pdconfSetEntry(webSealId, stanza, "server","9,https://localhost:443/TrustServerWST13/services/RequestSecurityToken")
            self.pdconfSetEntry(webSealId, stanza, "ssl-keyfile", "pdsrv.kdb")
            self.pdconfSetEntry(webSealId, stanza, "ssl-keyfile-stash", "pdsrv.sth")
            self.pdconfSetEntry(webSealId, stanza, "handle-pool-size", "10")
            self.pdconfSetEntry(webSealId, stanza, "handle-idle-timeout", "240")
            self.pdconfSetEntry(webSealId, stanza, "timeout", "240")
            self.pdconfSetEntry(webSealId, stanza, "basic-auth-user", "easuser")
            self.pdconfSetEntry(webSealId, stanza, "basic-auth-passwd", self.EASUSER_PASSWORD)

            #sso junction
            stanza = "tfimsso:" + self.ISAM_LTPA_JCT
            self.pdconfSetEntry(webSealId, stanza, "token-type", self.ISAM_LTPA_JCT_STS_TOKEN_TYPE)
            self.pdconfSetEntry(webSealId, stanza, "applies-to", self.ISAM_LTPA_JCT_SAML_APPLIES_TO)
            self.pdconfSetEntry(webSealId, stanza, "renewal-window", "15")
            self.pdconfSetEntry(webSealId, stanza, "preserve-xml-token", "true")
            self.pdconfSetEntry(webSealId, stanza, "always-send-tokens", "true")
            self.pdconfSetEntry(webSealId, stanza, "tfim-cluster-name", clusterName)

            #inefficient, but for demo shows new SAML assertions being sent on
            # every request and STS being called each request
            self.pdconfSetEntry(webSealId, stanza, "one-time-token", "true")
            self.pdconfSetEntry(webSealId, stanza, "token-collection-size", "1")

            #send via HTTP Header called SAMLAssertion for demo
            self.pdconfSetEntry(webSealId, stanza, "token-transmit-type", "header")
            self.pdconfSetEntry(webSealId, stanza, "token-transmit-name", "LTPAToken")
        else:
            logger.error("WebSEAL server not found. Cannot complete configuration")
    
            
    def configureIdPWebSEALConf(self, websealHostName, instanceName = 'default'):
        logger.info("Configuring WebSEAL.conf file for SAML IdP")
        
        endpoint = "/wga/reverseproxy"
        
        logger.debug("GET the WebSEAL details based on WebSEAL hostname")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured WebSEAL.conf file for SAML IdP")
        else:
            logger.error("Unsuccessful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        revProxiesJson = json.loads(content)
        
        noOfRevProx = len(revProxiesJson)
        webSealId = None
        i = 0
        for i in range(noOfRevProx):
            if(revProxiesJson[i]['instance_name'] == instanceName):
                webSealId = revProxiesJson[i]['id']
        
        if(webSealId != None):
            # PUT actions to configure webSeal 
            self.pdconfAddEntry(webSealId, "TAM_CRED_ATTRS_SVC", "eperson", "azn_cred_registry_id")
            self.pdconfSetEntry(webSealId, "TAM_CRED_ATTRS_SVC:eperson", "emailAddress", "mail")
            self.pdconfSetEntry(webSealId, "TAM_CRED_ATTRS_SVC:eperson", "firstName", "cn")
            self.pdconfSetEntry(webSealId, "TAM_CRED_ATTRS_SVC:eperson", "lastName", "sn")
            
            # setup managed cookies list for /isam
            self.pdconfSetEntry(webSealId, "junction:/isam", "reset-cookies-list", "*ac.uuid,*JSESSIONID")
            
            #setup eai authentication - now performed by POC Configuration
            #self.pdconfSetEntry(webSealId, "eai", "eai-auth", "https")
            #self.pdconfSetEntry(webSealId, "eai", "eai-redir-url-priority", "yes")
            #self.pdconfSetEntry(webSealId, "eai", "retain-eai-session", "yes")
            
            #self.pdconfAddEntry(webSealId, "eai-trigger-urls", "trigger", "/isam/sps/saml20idp/saml20/login*")
            #self.pdconfAddEntry(webSealId, "eai-trigger-urls", "trigger", "/isam/sps/saml20idp/saml20/slo*")
            #self.pdconfAddEntry(webSealId, "eai-trigger-urls", "trigger", "/isam/sps/saml20idp/saml20/soap*")
            #self.pdconfAddEntry(webSealId, "eai-trigger-urls", "trigger", "/isam/sps/auth*")
        else:
            logger.error("WebSEAL server not found. Cannot complelte configuration")
            
    def configureSPWebSEALConf(self, websealHostName, instanceName = 'default'):
        logger.info("Configuring WebSEAL.conf file for SAML SP")
        
        endpoint = "/wga/reverseproxy"
        
        logger.debug("GET the WebSEAL details based on WebSEAL hostname")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured WebSEAL.conf file for SAML SP")
        else:
            logger.error("Unsuccessful GET WebSEAL / Reverse Proxy instances. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        revProxiesJson = json.loads(content)
        
        noOfRevProx = len(revProxiesJson)
        webSealId = None
        i = 0
        for i in range(noOfRevProx):
            if(revProxiesJson[i]['instance_name'] == instanceName):
                webSealId = revProxiesJson[i]['id']
        
        if(webSealId != None):
            # PUT actions to configure webSeal 
            self.pdconfDeleteEntry(webSealId, "authentication-levels", "level", None)
            self.pdconfAddEntry(webSealId, "authentication-levels", "level", "unauthenticated")
            self.pdconfAddEntry(webSealId, "authentication-levels", "level",
                    "ext-auth-interface")
            
            # setup managed cookies list for /isam
            self.pdconfSetEntry(webSealId, "junction:/isam", "reset-cookies-list", "*ac.uuid,*JSESSIONID")
            
            #setup eai authentication - Now covered by POC Configuration
            #self.pdconfSetEntry(webSealId, "eai", "eai-auth", "https")
            #self.pdconfSetEntry(webSealId, "eai", "eai-redir-url-priority", "yes")
            #self.pdconfSetEntry(webSealId, "eai", "retain-eai-session", "yes")
            
            #self.pdconfAddEntry(webSealId, "eai-trigger-urls", "trigger", "/isam/sps/saml20sp/saml20/login*")
            #self.pdconfAddEntry(webSealId, "eai-trigger-urls", "trigger", "/isam/sps/saml20sp/saml20/slo*")
            #self.pdconfAddEntry(webSealId, "eai-trigger-urls", "trigger", "/isam/sps/auth*")
            #self.pdconfAddEntry(webSealId, "eai-trigger-urls", "trigger", "/isam/sps/saml20sp/saml20/soap*")
        else:
            logger.error("WebSEAL server not found. Could not update the WebSEAL conf")
       
    def configureWebSEALConf(self, websealHostName, instanceName = 'default'):
        logger.debug("Configure WebSEAL.conf file")
        
        endpoint = "/wga/reverseproxy"
        
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
        i = 0
        for i in range(noOfRevProx):
            if(revProxiesJson[i]['instance_name'] == instanceName):
                webSealId = revProxiesJson[i]['id']
        
        if(webSealId != None):
            # PUT actions to configure webSeal 
            self.pdconfSetEntry(webSealId, "server", "web-host-name", websealHostName)
            self.pdconfSetEntry(webSealId, "server", "force-tag-value-prefix", "yes")
            self.pdconfSetEntry(webSealId, "server", "web-http-port", "443")
            self.pdconfSetEntry(webSealId, "server", "web-http-protocol", "https")
            self.pdconfSetEntry(webSealId, "server", "persistent-con-timeout", "30")
            self.pdconfSetEntry(webSealId, "server", "worker-threads", "600")
            self.pdconfSetEntry(webSealId, "ba", "ba-auth", "none")
            self.pdconfSetEntry(webSealId, "forms", "forms-auth", "https")
            # make sure webseal cookies are HttpOnly
            self.pdconfSetEntry(webSealId, "server", "use-http-only-cookies", "yes")
            # preserve HttpOnly attribute for cookies from junctioned servers
            self.pdconfSetEntry(webSealId, "junction", "pass-http-only-cookie-attr", "yes")
            # MOVED into federation-specific config
            #self.pdconfSetEntry(webSealId, "junction:/isam", "reset-cookies-list", "*ac.uuid,*JSESSIONID")
            # other stuff that might be useful
            self.pdconfSetEntry(webSealId, "step-up", "verify-step-up-user", "no")
            self.pdconfSetEntry(webSealId, "session", "user-session-ids", "yes")
            self.pdconfSetEntry(webSealId, "session", "inactive-timeout", "1800")
            self.pdconfSetEntry(webSealId, "session", "create-unauth-sessions", "yes")
            # set of secured ciphers that makes sense to set
            self.pdconfSetEntry(webSealId, "ssl-qop", "ssl-qop-mgmt", "yes")
            self.pdconfDeleteEntry(webSealId, "ssl-qop-mgmt-default", "default", None)
            self.pdconfSetEntry(webSealId, "ssl-qop-mgmt-default", "default", "DES-168") 
            self.pdconfAddEntry(webSealId, "ssl-qop-mgmt-default", "default", "RC2-128 #2")
            self.pdconfAddEntry(webSealId, "ssl-qop-mgmt-default", "default", "RC4-128 #3")
            self.pdconfAddEntry(webSealId, "ssl-qop-mgmt-default", "default", "AES-128 #4")
            self.pdconfAddEntry(webSealId, "ssl-qop-mgmt-default", "default", "AES-256 #5")
        else:
            logger.error("WebSEAL could not be found. Configuration failed")
            
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
    
    def checkLMIAvailable(self):
        logger.debug("Check if LMI is available")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
        
        endpoint = "/lmi"
        
        logger.debug("GET LMI")
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        
        if statusCode == 200:
            logger.debug("Successful LMI call. LMI is available. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return True
        else:
            logger.error("Unsuccessful LMI call. LMI is unavailable. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return False
    
    def pdconfDeleteEntry(self, websealID, stanza, entry, value):
        logger.debug("Delete entry in WebSEAL configuration")
         
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD) 
         
        endpoint = "/wga/reverseproxy" + "/" + websealID + "/configuration/stanza/" + stanza + "/entry_name/" + entry
         
        logger.debug("DELETE WebSEAL configuration")
         
        jsonObj = {"value":value} 
        data = json.dumps(jsonObj) 
 
        statusCode, contentHeader, content = ISAMRestClient.delete(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
         
        if statusCode == 200:
            logger.debug("Successful deletion of entry in WebSEAL configuration file. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful deletion of entry in WebSEAL configuration file. Content returned : "+content+" Status Code returned : "+str(statusCode))
     
    def pdconfAddEntry(self, websealID, stanza, webSealConfEntry, webSealConfValue):
        logger.debug("Adding entry in WebSEAL configuration")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD) 
        
        endpoint = "/wga/reverseproxy" + "/" + websealID + "/configuration/stanza/" + stanza + "/entry_name/" + webSealConfEntry
        
        logger.debug("POST to WebSEAL configuration")
        
        jsonObj = {"entries":[]} 
        data = json.loads(json.dumps(jsonObj)) 
        data[u'entries'].append(webSealConfEntry)
        data[u'entries'].append(webSealConfValue)
        data = json.dumps(data) 
        
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        
        if statusCode == 200:
            logger.debug("Successful adding of entry in WebSEAL configuration file. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful adding of entry in WebSEAL configuration file. Content returned : "+content+" Status Code returned : "+str(statusCode))
     
    def pdconfSetEntry(self, websealID, stanza, entry, value):
        logger.debug("Set entry in WebSEAL configuration")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD) 
        
        endpoint = "/wga/reverseproxy" + "/" + websealID + "/configuration/stanza/" + stanza + "/entry_name/" + entry
        
        logger.debug("PUT to WebSEAL configuration")
        
        jsonObj = {"value":value} 
        data = json.dumps(jsonObj) 
        
        statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
        
        if statusCode == 200:
            logger.debug("Successful setting of entry in WebSEAL configuration file. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful setting of entry in WebSEAL configuration file. Content returned : "+content+" Status Code returned : "+str(statusCode))
       
    def addSignerCertificates(self):
        logger.info("Configuring Signer Certificates") 
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD) 
        
        logger.debug("POST to add Signer Certificates")
        
        jsonObj = {"server":"127.0.0.1","port":"443","label":"Local Runtime","operation":"load"}
        data = json.dumps(jsonObj) 
        
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_PDSRV_CERT_ENDPOINT, "application/json", data)
        
        if statusCode == 200:
            logger.debug("Successful adding of Signer Certificates. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured Signer Certificates")
        else:
            logger.error("Unsuccessful adding of Signer Certificates. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def configureWebSEALInstance(self,reverseproxyIP, wgaHostName):
        logger.info("Configuring WebSEAL Instance") 
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD) 
        
        logger.debug("POST to create WebSEAL Instance")
        
        jsonObj = {"https_port":"443","nw_interface_yn":"yes","https_yn":"yes","domain":"Default","admin_id":"sec_master","host":"%s" %(wgaHostName),"inst_name":"default","ip_address":str(reverseproxyIP),"listening_port":"7234","ssl_yn":"no","http_yn":"no","admin_pwd":"Passw0rd"} 
        data = json.dumps(jsonObj) 
        
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_REVERSE_PROXY_ENDPOINT, "application/json", data)
        
        if statusCode == 200:
            logger.debug("Successful POST to create WebSEAL instance. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured WebSEAL Instance")
        elif statusCode == 400 and content == '''{"message":"The specified reverse proxy instance already exists. default"}''':
            logger.debug("WebSEAL instance already exists. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful POST to create WebSEAL instance. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
    def configureRuntimeComponent(self):
        logger.info("Configuring Runtime component") 
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD) 
        
        logger.debug("POST to create Runtime component")
        
        jsonObj = {"registry":"on","ssl_compliance":"fips","ps_mode":"local","admin_cert_lifetime":"1460","user_registry":"local","ldap_pwd":"passw0rd","admin_pwd":"Passw0rd"}
        data = json.dumps(jsonObj) 
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_RUNTIME_ENDPOINT, "application/json", data)
        
        if statusCode == 200:
            logger.debug("Successful POST to create Runtime component. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured Runtime component")
        elif statusCode == 500 and content == '''{"message":"Error: WGAWA0262E   The runtime environment has already been configured."}''':
            logger.debug("Runtime component already exists. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful POST to create Runtime component. Content returned : "+content+" Status Code returned : "+str(statusCode))
            
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

        time.sleep(3)
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