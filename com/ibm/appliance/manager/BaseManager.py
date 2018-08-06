'''
Created on Jul 25, 2015

@copyright: IBM
'''
from com.ibm.appliance.util import HTTPRequest
from com.ibm.appliance.util.Common import CommonProperties 
from com.ibm.appliance.util.Settings import Settings
from com.ibm.appliance.util.HTTPRequest import ISAMRestClient   
import sys, time, json, uuid, logging

logger = logging.getLogger("BaseManager")
logger.setLevel(logging.INFO)

class BaseManager(object):
       
    ISAM_NTP_ENDPOINT = "/core/time_cfg"
    ISAM_CAPABILITIES_ENDPOINT = "/isam/capabilities/v1"
    ISAM_DEPLOY_CHANGES_ENDPOINT = "/isam/pending_changes/deploy"
    ISAM_GET_PENDING_CHANGES = "/isam/pending_changes"
    CORE_GET_PENDING_CHANGES = "/core/pending_changes"
    ISAM_INTERFACES_ENDPOINT = "/net/ifaces/"
    ISAM_DNS_ENDPOINT = "/net/dns"
    ISAM_HOSTS_ENDPOINT = "/isam/host_records.json"
    ISAM_RESTART_RUNTIME = "/isam/runtime_profile/local/v1"
    CORE_RESTART_RUNTIME = "/lmi"
    FIRMWARE_SETTINGS = "/firmware_settings"
    FIRST_STEPS = "/setup_complete"
    SERVICE_AGREEMENTS_ACCEPTED = "/setup_service_agreements/accepted"
    FIPS_CFG = "/fips_cfg"
    FIPS_CFG_REBOOT = "/fips_cfg/restart"
    
    def __init__(self,properties):

        self.BASEURL = properties[CommonProperties.PROP_BASEURL]  
        self.USERNAME = properties[CommonProperties.PROP_USERNAME]
        self.PASSWORD = properties[CommonProperties.PROP_PASSWORD]
        self.OLD_PASSWORD = properties[CommonProperties.PROP_OLD_PASSWORD]  
        self.DNS_STR = properties[CommonProperties.PROP_DNS]
        self.HOSTS = properties[CommonProperties.PROP_HOSTS]
        self.PLAT_ACTCODE = properties[CommonProperties.PROP_PLATFORM_ACTIVATE_CODE]
        self.FED_ACTCODE = properties[CommonProperties.PROP_FEDERATION_ACTIVATE_CODE]
        self.PRI_INTERFACE_IP = properties[CommonProperties.PROP_PRI_INTERFACE_IP]
        self.PRI_INTERFACE_MASK = properties[CommonProperties.PROP_PRI_INTERFACE_MASK]
        self.NTP_SERVER = properties[CommonProperties.PROP_NTP_SERVER]
        self.EASUSER_OLD_PASSWORD = properties[CommonProperties.PROP_EASUSER_OLD_PASSWORD]
        self.EASUSER_PASSWORD = properties[CommonProperties.PROP_EASUSER_PASSWORD]
        
    def doBaseConfig(self):       
        logger.debug("Triggering basic configuration REST APIs")
        
        deployChanges = False
        if Settings.features["All"]:
            logger.debug("All Basic configuration is triggered")
            self.doBaseConfigAll()
            self.deployChanges()

        else:
            logger.debug("Subset of Basic configuration is triggered")
            if Settings.features["First_Steps"]:
                logger.debug("Perform initial configuration")
                self.firstSteps()
                self.configureDNS() 
                #deployChanges = False
                deployChanges = True
            
            if Settings.features["Admin_Password"]:
                logger.debug("Change admin password")
                self.changeAdminPassword(self.OLD_PASSWORD)
                deployChanges = True
            
            if Settings.features["Easuser_Password"]:
                logger.debug("Change easuser password")
                self.changeAdminPassword(self.EASUSER_OLD_PASSWORD)
                deployChanges = True
            
            if Settings.features["DNS"]:
                logger.debug("Configuring DNS")
                self.configureDNS() 
                deployChanges = True
                
            if Settings.features["NTP"]:   
                logger.debug("Configuring NTP server") 
                self.configureNTP(self.NTP_SERVER)
                deployChanges = True
            
            if Settings.features["Product_Activation"]:    
                logger.debug("Activating licenses / Offerings")
                self.activateAllOfferings()
                deployChanges = True
            
            if Settings.features["Runtime_Interfaces"]: 
                logger.debug("Configuring Interfaces") 
                self.configureInterface(self.PRI_INTERFACE_IP, self.PRI_INTERFACE_MASK)
                deployChanges = True
                     
            if Settings.features["Hosts_File"]: 
                logger.debug("Configuring Hosts file")
                self.changeHostFile(self.HOSTS)
                deployChanges = True

            if deployChanges:
                logger.debug("Deploying pending changes")
                self.deployChanges()
                
            logger.debug("Subset of Basic configuration completed")
          
        logger.debug("End of basic appliance configuration ")
    
    def doBaseConfigAll(self):
        logger.debug("Performing the first steps")
        self.OLD_PASSWORD = self.firstSteps()
         
        logger.debug("Change admin password")
        self.changeAdminPassword(self.OLD_PASSWORD)
    
        logger.debug("Configuring DNS")
        self.configureDNS() 
     
        logger.debug("Configuring Hosts file")
        self.changeHostFile(self.HOSTS)
    
        logger.debug("Configuring Interfaces") 
        self.configureInterface(self.PRI_INTERFACE_IP, self.PRI_INTERFACE_MASK)
    
        logger.debug("Activating licenses / Offerings")
        self.activateAllOfferings()
    
        logger.debug("Configuring NTP server") 
        self.configureNTP(self.NTP_SERVER)
          

    
    def firstSteps(self):
        logger.info("Configuring the first steps for the appliance")
        logger.debug("Checking the username:password combination for the appliance")
        password = self.checkPassword()
        logger.debug("password is " + password)
        if self.isLicenseAccepted(self.USERNAME,password) == False:
            logger.debug("SLA Not accepted, accepting license")
            self.acceptLicense(self.USERNAME,password) 
        else:
            logger.debug("SLA has been accepted, checking if the appliance is configured")       
        
        isConfigured = self.isFirstStepsConfigured(self.USERNAME,password)
        if isConfigured:
            logger.debug("SLA has been accepted, appliance has been configured")
        else:
            logger.debug("SLA has been accepted, appliance has not been configured")     
            self.configureFirstSteps(self.USERNAME,password)
        logger.info("Successfully configured the first steps for the appliance")
        return password
    
    def configureFirstSteps(self, username, password):
        logger.info("Configuring the appliance")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = username, password = password) 
        statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, self.FIRST_STEPS, "application/json", None)
        if statusCode == 200 :
            logger.debug("SLA has been accepted, appliance has been configured")
        else:
            logger.debug("Unsuccessful PUT to configure the appliance"+content)
            
            
    def isFirstStepsConfigured(self, username,password):
        result = False
        logger.info("Checking if the appliance is configured")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = username, password = password) 
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.FIRST_STEPS, "application/json", "", "application/json", "", "")
        if statusCode == 200 :
            configurationComplete = json.loads(content)   
            logger.debug("Is Configuration Complete:"+str(configurationComplete['configured']))    
            result = configurationComplete['configured']
        else:
            logger.debug("Unsuccessful GET while accessing the endpoint"+content)
        return result
                
    def checkPassword(self):
        #password = "admin"
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
        
    def isLicenseAccepted(self, username, password):
        result = False
        logger.info("Checking if the SLA has been accepted")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = username, password = password) 
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.SERVICE_AGREEMENTS_ACCEPTED, "application/json", "", "application/json", "", "")
        licenseAccepted = json.loads(content)
        if statusCode == 200:
            logger.debug("Is License Accepted:"+str(licenseAccepted['accepted']))
            result=licenseAccepted['accepted']
        else:
            logger.debug("Unsuccessful GET while accessing the endpoint"+content)
        return result
            
    
    def acceptLicense(self, username,password):
        logger.info("Accepting the SLA")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = username, password = password) 
        jsonData = {"accepted":"true"}
        jsonFinal = json.dumps(jsonData)
        statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, self.SERVICE_AGREEMENTS_ACCEPTED, "application/json", json.dumps(jsonData))
        if statusCode == 200:                   
            logger.debug("Successfully accepted SLA")
        else:
            logger.debug("Unsuccessful in accepting License"+content)
                
    def changeAdminPassword(self, oldPassword):
        logger.info("Configuring the administrator password")
        endpoint = "/core/admin_cfg"
        
        logger.debug("GET to verify that old password is working")
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = oldPassword) 
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
        # sessionTimeout will be -1 if the old password is incorrect
        sessionTimeout = -1
        if statusCode == 200:
            sessionTimeout = json.loads(content)[u'sessionTimeout']  
            if(sessionTimeout > 0):
                HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = oldPassword) 
                jsonObj = {"sessionTimeout":str(sessionTimeout),"oldPassword":oldPassword,"newPassword":self.PASSWORD,"confirmPassword":self.PASSWORD} 
                data = json.dumps(jsonObj)
                logger.debug("PUT to change the password")
                statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
                if statusCode == 200:
                    logger.debug("Successfully  POST to change password. Content returned : "+content+" Status Code returned : "+str(statusCode))
                    logger.info("Successfully configured the administrator password")
                else:
                    logger.error("Unsuccessful POST to change password. Content returned : "+content+" Status Code returned : "+str(statusCode))
            else:
                logger.error("A session timeout was not returned. Old password is incorrect or contact administrator")
        else: 
            logger.debug("Check if the new password is set")
            HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.PASSWORD)
            logger.debug("GET to verify that new password is already set and is working")
            statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
            if statusCode == 200:
                logger.debug("Successful GET. The password is set correctly. Content returned : "+content+" Status Code returned : "+str(statusCode))
            else:     
                logger.debug("Unsuccessful GET. The password is set incorrectly. Content returned : "+content+" Status Code returned : "+str(statusCode))

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
                    logger.debug("Firmware Version "+firmwareVesion)
                    return firmwareVersion
            if firmwareVersion == None:
                logger.error("Failed to find active partition")
                
        elif statusCode == 404:
            logger.debug("Received 404 from runtime endpoint when querying firmware information.")
        else:
            logger.error("Unsuccessful GET of firmware information. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def changeEasuserPassword(self):
        logger.info("Configuring the easuser password")
        
        endpoint = "/mga/user_registry/users/easuser/v1"


        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword())
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
       
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password =self.checkPassword())
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
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword())
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
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword())


    def changeHostFile(self,hostsName):
        logger.info("Configuring HOSTS file entries")
        endpoint = "/mga/attribute_sources"
         
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword()) 

        hostsName = json.loads(json.dumps(hostsName))
        hostsName = str(hostsName).split(",")
        for index in range(0, hostsName.__len__()):
            hostname = str(hostsName[index]).split(":")
            hostIP = hostname[0]
            hostName = hostname[1]  
            jsonObj = {"hostnames":[{"name":hostName}],"addr":hostIP}
            data = json.dumps(jsonObj)
            
            logger.debug("POST to create entries in HOSTS file")
            statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_HOSTS_ENDPOINT, "application/json", data)
            if statusCode == 200:
                logger.debug("Successful POST to configure HOSTS file. Content returned : "+content+" Status Code returned : "+str(statusCode))
                logger.info("Successfully configured HOSTS file entries")
            else:
                logger.error("Unuccessful POST to configure HOSTS file. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
    def configureNTP(self,ntp_server):    
        
        logger.info("Configuring NTP server")
         
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword()) 
        
        jsonObj = {"dateTime":"0000-00-00 00:00:00","ntpServers":str(ntp_server),"timeZone":"Australia/Brisbane","enableNtp":True}
        data = json.dumps(jsonObj)
          
        statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_NTP_ENDPOINT, "application/json", data)
         
        if statusCode == 200:
            logger.debug("Successful PUT to configure NTP setting. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured NTP server")
        else:
            logger.error("Unuccessful PUT to configure NTP setting. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
    
    def activateAllOfferings(self):
        
        logger.info("Configuring product activation")
        
        if len(self.PLAT_ACTCODE) != 39:
            logger.error("Platform Activation code not set correctly in automation.ini")
        if len(self.FED_ACTCODE) != 39:
            logger.error("Federation Activation code not set correctly in automation.ini")

        if (len(self.PLAT_ACTCODE) != 39 or len(self.FED_ACTCODE) != 39):
                sys.exit(1)
        
        logger.debug("GET current offerings / licenses ")
         
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword()) 
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_CAPABILITIES_ENDPOINT, "application/json", "", "application/jsonConverter", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET current offerings / licenses. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful GET current offerings / licenses. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        logger.debug("POST to current offerings / licenses such that Platform is enabled")
        jsonObj = {"code":self.PLAT_ACTCODE}
        data = json.dumps(jsonObj) 
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_CAPABILITIES_ENDPOINT, "application/json", data)
        if statusCode == 200:
            logger.info("Successfully activated platform")
            logger.debug("Successful POST current offerings / licenses. Platform enabled. Content returned : "+content+" Status Code returned : "+str(statusCode))
        elif statusCode == 400 and content == str('''{"message":"The capability specified in the request is already activated."}'''):
            logger.debug("Platform is already enabled. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unuccessful POST current offerings / licenses. Platform not enabled. Content returned : "+content+" Status Code returned : "+str(statusCode))
           
        logger.debug("POST to current offerings / licenses such that Federation is enabled")
        jsonObj = {"code":self.FED_ACTCODE}
        data = json.dumps(jsonObj) 
        statusCode, contentHeader, content = ISAMRestClient.post(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_CAPABILITIES_ENDPOINT, "application/json", data)
        if statusCode == 200:
            logger.info("Successfully activated federation")
            logger.debug("Successful POST current offerings / licenses. Federation enabled. Content returned : "+content+" Status Code returned : "+str(statusCode))
        elif statusCode == 400 and content == str('''{"message":"The capability specified in the request is already activated."}'''):
            logger.debug("Federation is already enabled. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unuccessful POST current offerings / licenses. Federation not enabled. Content returned : "+content+" Status Code returned : "+str(statusCode))
            
    def deployChanges(self):
        logger.debug("Deploy pending changes")
        
        content  = None
        content = json.loads(self.getCorePendingChanges())
        pendingChangesCore = content["changes"]
        contentISAM = json.loads(self.getISAMPendingChanges())
        pendingChangesISAM = contentISAM["changes"]
            
        if(len(pendingChangesCore) != 0):
            logger.debug("Pending changes to be deployed")
            self.deployPendingChangesBase()
        elif(len(pendingChangesISAM) != 0):
            logger.debug("Pending changes to be deployed")
            self.deployPendingChangesISAM()
        else:
            logger.debug("No pending changes to be deployed")
    
    def getCorePendingChanges(self):
        logger.debug("Deploy pending changes")
        
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword())
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.CORE_GET_PENDING_CHANGES, "application/json", "", "application/json", "", "")
        if statusCode == 200:
            logger.debug("Successful GET of pending changes. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful GET of pending changes. Content returned : "+content+" Status Code returned : "+str(statusCode))

    def getISAMPendingChanges(self):
        logger.debug("Deploy pending changes")
        
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword())
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_GET_PENDING_CHANGES, "application/json", "", "application/json", "", "")
        if statusCode == 200:
            logger.debug("Successful GET of pending changes. Content returned : "+content+" Status Code returned : "+str(statusCode))
            return content
        else:
            logger.error("Unsuccessful GET of pending changes. Content returned : "+content+" Status Code returned : "+str(statusCode))

    def deployPendingChangesBase(self):
        logger.debug("Deploy pending changes in base")
        
        runtimeLastStart = -1
        runtimeLastStart = self.getLMIStartTime()
        
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword())
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
                if((status & 32) != 0):
                    logger.debug("Runtime restart was performed for status: "+str(status))
                     #We better do this. Sometimes if you deploy again too soon
                     #after initiating a runtime restart, bad things can happen
                     #to the starting runtime
                    self.waitForLMIRestart(runtimeLastStart)
            else:
                logger.error("Deployment of core changes failed")    
        else:
            logger.error("Unsuccessfully deployed pending changes. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
    
    def deployPendingChangesISAM(self):
        logger.debug("Deploy pending changes in base")
        
        runtimeLastStart = -1
        runtimeLastStart = self.getRuntimeStartTime()
        
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword())
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
        
        password = self.checkPassword()
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = password)
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_RESTART_RUNTIME, "application/json", "", "application/json", "", "")
        if statusCode == 200:
            logger.debug("Successful GET of last runtime start. Content returned : "+content+" Status Code returned : "+str(statusCode))
#             return json.loads(content)['last_start']
            return json.loads(content)[0]['start_time']
        elif statusCode == 404:
            logger.debug("Received 404 from runtime endpoint when querying start time.")
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
            restartTime = self.getRuntimeStartTime()
        #Extra sleep to be kiasu
        time.sleep(3)
    
    def restartLMI(self):
        logger.debug("Restart LMI")
        
        endpoint = "/restarts/commit_and_restart"
        
        lastStartTime = self.getLMIStartTime()
        if lastStartTime <= 0 :
            logger.error("Unable to get valid lastStartTime when restarting LMI: " + str(lastStartTime))
        
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword())
        
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
            
            
            HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword())
            
            statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", "", "application/json", "", "")
            if statusCode == 200:
                logger.debug("Successful call to LMI end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
                startTime = json.loads(content)[0]['start_time']
                return startTime
            elif statusCode == 404:
                logger.debug("Received 404 from LMI end point.")
            else:
                logger.error("Unsuccessful call to LMI end point. Content returned : "+content+" Status Code returned : "+str(statusCode))
        except:
            logger.debug("Error during connection to lmi end point")
            return -1
    
    def configureInterface(self, ipv4Address, netmask):
        
        logger.info("Configuring Runtime Interfaces")
        logger.debug("GET current Interface setting")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword())
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_INTERFACES_ENDPOINT, "application/jsonConverter", "", "application/jsonConverter", "", "")
        
        if statusCode == 200:
            logger.debug("Successful GET current Interface setting. Content returned : "+content+" Status Code returned : "+str(statusCode))
        else:
            logger.error("Unsuccessful GET current Interface setting. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        jsonObj = json.loads(content)   
        interface_1_1_json = jsonObj['interfaces'][0]
        interface_1_1_ipv4_addresses_json =interface_1_1_json['ipv4']['addresses']
        
        flagInterfaceSet = False
        
        noOfAddrs = len(interface_1_1_ipv4_addresses_json)
        i = 0
        for i in range(noOfAddrs):
            if interface_1_1_ipv4_addresses_json[i]['address'] == str(ipv4Address) and interface_1_1_ipv4_addresses_json[i]['allowManagement'] == False:
                logger.debug("Interface is already configured . Content returned : "+str(interface_1_1_ipv4_addresses_json[i]))
                flagInterfaceSet = True
         
        if flagInterfaceSet == False:       
            logger.debug("Configuring interface")

            uuidStr = uuid.uuid4()
            #The payload during a PUT that creates the interface
            addressPayload = {
                "maskOrPrefix": "255.255.255.0",
                "address": "10.1.16.90",
                "allowManagement": False,
                "uuid": "e7187407-43bd-4147-97db-ee537d738877",
                "objType": "ipv4Address",
                "enabled": True
            } 
            #Modify the payload
            addressPayload['maskOrPrefix'] = netmask
            addressPayload['address'] = ipv4Address
            addressPayload['uuid'] = str(uuidStr)
            
            jsonObj = json.loads(content)    
            # The code assumes only 1.1 is enabled and used
            interface1_payload = jsonObj[u'interfaces'][0]
            interface1_1_uuid = interface1_payload[u'uuid']
            interface1_payload[u'ipv4'][u'addresses'].append(addressPayload)
            data = json.dumps(interface1_payload)
            
            endpoint = self.ISAM_INTERFACES_ENDPOINT + str(interface1_1_uuid)
            statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, endpoint, "application/json", data)
            if statusCode == 200:
                logger.debug("Successful PUT of Interface. Content returned : "+content+" Status Code returned : "+str(statusCode))
                logger.info("Successfully configured Runtime Interfaces")
            else:
                logger.error("Unsuccessful PUT of Interface. Content returned : "+content+" Status Code returned : "+str(statusCode))
    
    def configureDNS(self): 
        logger.debug("Configuring DNS")
        
        logger.debug("GET current DNS setting")
        
        HTTPRequest.ISAMRestClient = ISAMRestClient("",username = self.USERNAME, password = self.checkPassword())
        statusCode, contentHeader, content = ISAMRestClient.get(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_DNS_ENDPOINT, "application/json", "", "application/json", "", "")
                 
        if statusCode == 200:
            logger.debug("Successful GET current DNS. Content returned : "+content+" Status Code returned : "+str(statusCode))
            logger.info("Successfully configured DNS Setting")
        else:
            logger.debug("Unsuccessful GET current DNS. Content returned : "+content+" Status Code returned : "+str(statusCode))
        
        jsonObj = json.loads(content)    
        
        if jsonObj['auto'] == "True":
            logger.warn("DNS setting exists in the appliance. Exiting the DNS configuration")
        else:
            jsonObj['auto'] = False 
            jsonObj['primaryServer'] = self.DNS_STR 
            data = json.dumps(jsonObj)
            statusCode, contentHeader, content = ISAMRestClient.put(HTTPRequest.ISAMRestClient, self.BASEURL, self.ISAM_DNS_ENDPOINT, "application/json",data) 

            if statusCode == 200:
                logger.debug("Successful PUT of DNS. Content returned : "+content+" Status Code returned : "+str(statusCode))
            else:
                logger.error("Unsuccessful PUT of DNS. Content returned : "+content+" Status Code returned : "+str(statusCode))
                exit
