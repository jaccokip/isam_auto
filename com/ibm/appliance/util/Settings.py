'''
Created on Jul 25, 2015

@copyright: IBM
'''

class Settings(object):
    '''
    Features
    ''' 
    features = {
                
        "All" : False,
        
        # Basic Appliance Configuration
        "First_Steps" : False,
        "Admin_Password" : False,
        "Easuser_Password" : False,
        "DNS" : False, # not
        "NTP" : False,
        
        # Configure_Interfaces : False, # not in cook book
        "Runtime_Component" : False,
        "Product_Activation" : False,
        "Runtime_Interfaces" : False,
        "Hosts_File" : False,
        
        # Create Reverse Proxy instance
        "WebSEAL_Instance" : False,#
        "WebSEAL_Configfile" : False,# 
        "Signer_Certificates" : False,#
        "Junction" : False,#
        "ACL" : False,
        "Test_User" : False,#
        "Keystore" : False,
        "Upload_pages" :False,
        
        # Configure federation
        "Federation" : False,
        "Export_Metadata" : False,
        "POC_For_Federation" : False,
        
        #Import metadata
        "All_Metadata" : False,
        "IdP_Partner_Metadata" : False,
        "SP_Partner_Metadata" : False,
        
        #Modify partner settings
        "IdP_Partner_Sign_Settings" : False,
        "SP_Partner_Sign_Settings" : False,
        
        #Generic commands for Federation pieces
        "Macros" : False,
        "Runtime_Trace_String" : False,
        "Show_Pending_Changes" : False,
        "Deploy_Pending_Changes" : False,
        "Restart_LMI" : False,
        "Restart_Federation_Runtime" : False,
        "Enable_Demo_Application" : False, 
        "Upload_Mapping_Rules": False,
        
    
        
        #PoC
        "PoC_Use_PAC" : False,
        "PoC_Use_USERNAME" : False,
        "PoC_Use_EXTUSER" : False,
        
        #LTPA to STSUU
        "LTPA_to_STSUU" : False,
        
    }
