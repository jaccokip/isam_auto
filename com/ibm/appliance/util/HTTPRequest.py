'''
Created on Jul 25, 2015

@copyright: IBM
'''
from encodings.base64_codec import base64_encode
import requests, urllib
import requests.packages


class ISAMRestClient(object):
    
    def __init__(self, name='ISAMRestClient', username='admin', password='Passw0rd'):
        "Create a ISAMRestClient. It will use BA to authenticate by default. To disable it, call disableBasicAuth" 
        self.username = username
        self.password = password
        requests.packages.urllib3.disable_warnings() 
        
    def _getHeaders(self, acceptType="application/json",contentType="application/json",x_forwarded_host=None):
        headers = {"Accept": acceptType, "Content-type": contentType} 
        credential_encode, len = base64_encode("%s:%s" % (self.username, self.password)) 
        headers['Authorization'] = "Basic " + str(credential_encode).rstrip()  # sr().rstrip() is used in case there is no newline behind. 
        
        return headers        
    def put(self, baseurl, endpoint, accept_type="*/*", jsonObj="", x_forwarded_host=None):
        """Send a PUT request, returns statusCode, contentType, content"""
        
        ''' requests external library
        response = requests.post('https://10.1.16.90/net/dns',header,jsonObj)
        '''  
        #requests is a external library

        header = self._getHeaders("application/json","application/json",None)   
        url = baseurl + endpoint 
        headers = {"Content-type": str(header['Content-type']), "Accept":  str(header['Accept']), "Authorization": header['Authorization']}
        response  = requests.put(url=url, params=None, data=jsonObj, headers=headers, verify=False)   
        statusCode = response.status_code
        contentHeader = response.headers
        content = response._content
  
        response.close() 
          
        return statusCode, contentHeader, content
        
    def get(self, baseurl, endpoint, accept_type= '*/*', parameters=None,content_type='application/json',raw_mode=True, x_forwarded_host=None):
        """Issue a GET request. If parameters is not None, they will be added as query string parameter
        returns 3 values tuple statusCode, contentType, content
        """      
        header = self._getHeaders("application/json","application/json",None)   
        url = baseurl + endpoint 
        headers = {"Content-type": str(header['Content-type']), "Accept":  str(header['Accept']), "Authorization": header['Authorization']}
        response  = requests.get(url=url, params=None, headers=headers, verify=False) 
          
        statusCode = response.status_code
        contentHeader = response.headers
        content = response._content
  
        response.close() 
          
        return statusCode, contentHeader, content
    
    def getFile(self, baseurl, endpoint, accept_type= '*/*', parameters=None,content_type='application/json',raw_mode=True, x_forwarded_host=None, stream=True, fileLocation=None):
        """Issue a GET request. If parameters is not None, they will be added as query string parameter
        returns 3 values tuple statusCode, contentType, content
        """      
        header = self._getHeaders("application/json","application/json",None)   
        url = baseurl + endpoint 
        headers = {"Content-type": str(header['Content-type']), "Accept":  str(header['Accept']), "Authorization": header['Authorization']}
        response  = requests.get(url=url, params=None, headers=headers, verify=False, stream=True) 
        
        statusCode = response.status_code
        contentHeader = response.headers
        content = response.content
       
        with open(fileLocation, 'wb') as f:
            for chunk in response.iter_content(chunk_size=1024): 
                if chunk: # filter out keep-alive new chunks
                    f.write(chunk)
                    f.flush()
             
        response.close() 
          
        return statusCode, contentHeader, content    
    
    def post(self, baseurl, endpoint, accept_type="*/*", jsonObj="", x_forwarded_host=None):
        """Send a POST request, returns statusCode, contentType, content"""
 
        header = self._getHeaders("application/json","application/json",None)   
        url = baseurl + endpoint  
        headers = {"Content-type": str(header['Content-type']), "Accept":  str(header['Accept']), "Authorization": header['Authorization']}
        response  = requests.post(url=url, params=None, data=jsonObj, headers=headers, verify=False) 
           
        statusCode = response.status_code
        contentHeader = response.headers
        content = response._content
   
        response.close() 
           
        return statusCode, contentHeader, content
    
    def postEncodedData(self, baseurl, endpoint, accept_type="*/*", jsonObj="", x_forwarded_host=None):
        """Send a POST request, returns statusCode, contentType, content"""
 
        header = self._getHeaders(accept_type,"application/json",None)   
        url = baseurl + endpoint  
        headers = {"Content-type": "application/x-www-form-urlencoded", "Accept":  str(header['Accept']), "Authorization": header['Authorization']} 

        jsonObj = urllib.urlencode(jsonObj)
        response  = requests.post(url=url, params=None, data=jsonObj, headers=headers, verify=False) 
           
        statusCode = response.status_code
        contentHeader = response.headers
        content = response._content
   
        response.close() 
           
        return statusCode, contentHeader, content
    
    def postFile(self, baseurl, endpoint, accept_type="*/*", file={}, jsonObj=""):
        """POST a Multipart-Encoded File, returns statusCode, contentType, content""" 
        
        header = self._getHeaders("application/json","multipart/form-data",None)   
        url = baseurl + endpoint
        headers = {"Accept": str(header['Accept']),"Authorization": header['Authorization']}  
        # does not set the content type as  multipart/form-data into the header
        # Other wise a 422 error will get indicate that the boundaries error
        response  = requests.post(url = url, headers = headers, data = jsonObj, verify = False, files = file) 
           
        statusCode = response.status_code
        contentHeader = response.headers
        content = response._content
   
        response.close() 
           
        return statusCode, contentHeader, content
    
    def postMultiFile(self, baseurl, endpoint, accept_type="*/*", jsonObj="", multiFileName={}):
        """POST a multiple Multipart-Encoded Files, returns statusCode, contentType, content""" 
        
        header = self._getHeaders("application/json","multipart/form-data", None)   
        url = baseurl + endpoint
        headers = {"Accept": str(header['Accept']),"Authorization": header['Authorization']} 
        # does not set the content type as  multipart/form-data into the header
        # Other wise a 422 error will get indicate that the boundaries error
        response  = requests.post(url = url, headers = headers, data=jsonObj, verify = False, files = multiFileName)   
        
        statusCode = response.status_code
        contentHeader = response.headers
        content = response._content
    
        response.close() 
            
        return statusCode, contentHeader, content
        
    def delete(self, baseurl, endpoint, accept_type="*/*", jsonObj="", x_forwarded_host=None):
        """Send a DELETE request, returns statusCode, contentType, content"""

        #requests is a external library

        header = self._getHeaders("application/json","application/json",None)   
        url = baseurl + endpoint 
        headers = {"Content-type": str(header['Content-type']), "Accept":  str(header['Accept']), "Authorization": header['Authorization']}
        response  = requests.delete(url=url, params=None, headers=headers, verify=False) 

        statusCode = response.status_code
        contentHeader = response.headers
        content = response._content

        response.close() 

        return statusCode, contentHeader, content 
