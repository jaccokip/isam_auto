// SAML20 IP Mapping rule

importPackage(Packages.com.tivoli.am.fim.trustserver.sts);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.uuser);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.utilities);
importPackage(Packages.com.ibm.security.access.httpclient);

var debug=false;

function jsToJavaArray(jsArray) {
	var javaArray = java.lang.reflect.Array.newInstance(java.lang.String, jsArray.length);
	for (var i = 0; i < jsArray.length; i++) {
		javaArray[i] = jsArray[i];
	}
	return javaArray;
}

function callSTS(endpoint, bauser, bapassword, issuerAddress, appliesToAddress, requestType, tokenType, baseToken) {
	
	var result = null;
	
	// tokenType is optional
	var tokenTypeElement = '';
	if (tokenType != null) {
		tokenTypeElement = '<wst:TokenType>' + tokenType + '</wst:TokenType>';
	}
	
	// build the WS-Trust 1.2 RST
	var soapRequestBody = '<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" xmlns:soapenc="http://schemas.xmlsoap.org/soap/encoding/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:wsa="http://schemas.xmlsoap.org/ws/2004/08/addressing" xmlns:wsp="http://schemas.xmlsoap.org/ws/2004/09/policy" xmlns:wst="http://schemas.xmlsoap.org/ws/2005/02/trust" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soapenv:Header/><soapenv:Body><wst:RequestSecurityToken><wst:RequestType>'
		+ requestType 
		+ '</wst:RequestType><wst:Issuer><wsa:Address>'
		+ issuerAddress
		+ '</wsa:Address></wst:Issuer><wsp:AppliesTo><wsa:EndpointReference><wsa:Address>'
		+ appliesToAddress
		+ '</wsa:Address></wsa:EndpointReference></wsp:AppliesTo>'
		+ tokenTypeElement
		+ '<wst:Base>'
		+ baseToken
	    + '</wst:Base></wst:RequestSecurityToken></soapenv:Body></soapenv:Envelope>';
	
	if (debug) {
		IDMappingExtUtils.traceString("Sending RST: " + soapRequestBody);
	}

	
	// connection properties
	var headers = new Headers();
	headers.addHeader("Content-Type", "text/xml");
	var httpsTrustStore = 'pdsrv';
	
	/**
	 * httpPost(String url, Map headers, String body,String httpsTrustStore,
	 * String basicAuthUsername,String basicAuthPassword, String
	 * clientKeyStore,String clientKeyAlias);
	 */
	var hr = HttpClient.httpPost(endpoint, headers, soapRequestBody, httpsTrustStore, bauser, bapassword, null, null);
	if (hr != null) {
		var code = hr.getCode(); // this is int
		var body = hr.getBody(); // this is java.lang.String

		if (debug) {
			IDMappingExtUtils.traceString("code: " + code);
			IDMappingExtUtils.traceString("body: " + body);
		}
		
		// sanity check the response code and body - this is "best-effort"
		if (code != 200) {
			IDMappingExtUtils.throwSTSException("Bad response code calling auxilary STS chain: " + code);
		}
		var simpleRSTRPattern = ".*<wst:RequestedSecurityToken>.*</wst:RequestedSecurityToken>.*";
		if (!body.matches(simpleRSTRPattern)) {
			IDMappingExtUtils.throwSTSException("Bad response body calling auxilary STS chain: " + body);
		}
		
		// retrieve the requested security token from the response body
		result = body.replaceFirst(".*<wst:RequestedSecurityToken>", "").replaceFirst("</wst:RequestedSecurityToken>.*", "").replaceAll("&gt;", ">").replaceAll("&lt;", "<");
	}

	return result;
}



if (debug) {
	IDMappingExtUtils.traceString("idp mapping rule called with stsuu: " + stsuu.toString());
}
var permittedAttrsFromCred = [ "emailAddress", "firstName", "lastName"];

var foundAttrs = {};
for (var i = 0; i < permittedAttrsFromCred.length; i++) {
	var vals = stsuu.getAttributeContainer().getAttributeValuesByName(permittedAttrsFromCred[i]);
	if (vals != null && vals.length > 0) {
		foundAttrs[permittedAttrsFromCred[i]] = vals;
	}
}

	
// empty attrs, then add back what we want
stsuu.clearAttributeList();
var keys = Object.keys(foundAttrs);
if (keys != null && keys.length > 0) {
	for (var i = 0; i < keys.length; i++) {
		stsuu.addAttribute(new Attribute(keys[i], "", foundAttrs[keys[i]]));
	}
}

// this part here calls an external trust chain in the STS which takes as input an STSUU and returns as output another STSUU
// The input token here could be our original stsuu if we wanted, however in this example we've chosen to send a new
// stsuu which just has the principal name from the original, and no other attributes.
// From the STSUU we get back from the external trust chain callout, we extract all attributes and add them to our mapping 
// rule's STSUU for this federation. 

var inputSTSUU = new STSUniversalUser();
inputSTSUU.setPrincipalName(stsuu.getPrincipalName());

var endpoint = "https://localhost/TrustServer/SecurityTokenService";
var bauser = "easuser";
var bapassword = "Passw0rd";
var issuerAddress = "http://issuer/stsuu";
var appliesToAddress = "http://appliesto/stsuu";
var requestType = "http://schemas.xmlsoap.org/ws/2005/02/trust/Validate";
var xmlHeader = '<?xml version="1.0" encoding="UTF-8"?>';
var tokenType = null;
var baseToken = inputSTSUU.toClearTextString();
// strip XML header from base token string since toClearTextString will include it
if (baseToken != null && baseToken.startsWith(xmlHeader)) {
	baseToken = baseToken.substring(xmlHeader.length);
}
var stsResult = callSTS(endpoint, bauser, bapassword, issuerAddress, appliesToAddress, requestType, tokenType, baseToken);
if (stsResult == null) {
	IDMappingExtUtils.throwSTSException("Error calling auxilary trust chain");
}

// build a new STSUU from what we got back from the STS
var outputSTSUU = new STSUniversalUser();
outputSTSUU.fromXML(stsResult);

// add all attributes in the attribute list from outputSTSUU to our stsuu
for (var i = outputSTSUU.getAttributes(); i.hasNext(); ) {
	var attr = i.next();
	stsuu.addAttribute(attr);
}
if (debug) {
	IDMappingExtUtils.traceString("idp mapping rule final stsuu: " + stsuu.toString());
}
