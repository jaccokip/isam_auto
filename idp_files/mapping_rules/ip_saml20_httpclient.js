// SAML20 IP Mapping rule

importPackage(Packages.com.tivoli.am.fim.trustserver.sts);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.uuser);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.utilities);
importPackage(Packages.com.ibm.security.access.httpclient);


function jsToJavaArray(jsArray) {
	var javaArray = java.lang.reflect.Array.newInstance(java.lang.String, jsArray.length);
	for (var i = 0; i < jsArray.length; i++) {
		javaArray[i] = jsArray[i];
	}
	return javaArray;
}

IDMappingExtUtils.traceString("idp mapping rule called with stsuu: " + stsuu.toString());
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

// example of adding a new one - multi-valued in this case
var testAttr = new Attribute("testattr","urn:mytype", jsToJavaArray(["value1", "value2"]));
stsuu.addAttribute(testAttr);

// this part here calls an external SOAP web service to get another attribute

/**
 * httpPost(String url, Map headers, String body,String httpsTrustStore,
 * String basicAuthUsername,String basicAuthPassword, String
 * clientKeyStore,String clientKeyAlias);
 */
// example from http://www.webservicex.net/stockquote.asmx?op=GetQuote
var headers = new Headers();
var stockSymbol = "IBM";
var soapRequestBody = "<?xml version=\"1.0\" encoding=\"utf-8\"?><soap:Envelope xmlns:xsi=\"http://www.w3.org/2001/XMLSchema-instance\" xmlns:xsd=\"http://www.w3.org/2001/XMLSchema\" xmlns:soap=\"http://schemas.xmlsoap.org/soap/envelope/\"><soap:Body><GetQuote xmlns=\"http://www.webserviceX.NET/\"><symbol>"+stockSymbol+"</symbol></GetQuote></soap:Body></soap:Envelope>";

headers.addHeader("SOAPAction", "\"http://www.webserviceX.NET/GetQuote\"");
headers.addHeader("Content-Type", "text/xml; charset=UTF-8");
var endpoint = null;
var httpsTrustStore = null;
var clientKeyStore = null;
var clientKeyAlias = null;
var ssltest = true;
if (ssltest) {
  endpoint = "https://192.168.42.102:444/webservicex/stockquote.asmx";
  httpsTrustStore = "pdsrv";
  clientKeyStore = "testuser";
  clientKeyAlias = "testuser";
} else {
  endpoint = "http://www.webservicex.net/stockquote.asmx";
}

/* hr will be a com.ibm.security.access.httpclient.HttpResponse */
IDMappingExtUtils.traceString("endpoint: " + endpoint + " httpsTrustStore: " + httpsTrustStore + " clientKeyStore: " + clientKeyStore + " clientKeyAlias: " + clientKeyAlias);

var hr = HttpClient.httpPost(endpoint, headers, soapRequestBody, httpsTrustStore, null, null, clientKeyStore, clientKeyAlias);
if (hr != null) {
	IDMappingExtUtils.traceString("code: " + hr.getCode());
	IDMappingExtUtils.traceString("body: " + hr.getBody());
	headerKeys = hr.getHeaderKeys();
	if (headerKeys != null) {
		for ( var i = 0; i < headerKeys.length; i++) {
			var headerValues = hr.getHeaderValues(headerKeys[i]);
			for ( var j = 0; j < headerValues.length; j++) {
				IDMappingExtUtils.traceString("header: " + headerKeys[i] + "=" + headerValues[j]);
			}
		}
	}
	
	// let's put part of the body into an attribute
	// <?xml version="1.0" encoding="utf-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema"><soap:Body><GetQuoteResponse xmlns="http://www.webserviceX.NET/"><GetQuoteResult>&lt;StockQuotes&gt;&lt;Stock&gt;&lt;Symbol&gt;IBM&lt;/Symbol&gt;&lt;Last&gt;155.51&lt;/Last&gt;&lt;Date&gt;8/11/2015&lt;/Date&gt;&lt;Time&gt;4:03pm&lt;/Time&gt;&lt;Change&gt;-1.24&lt;/Change&gt;&lt;Open&gt;155.71&lt;/Open&gt;&lt;High&gt;155.99&lt;/High&gt;&lt;Low&gt;154.86&lt;/Low&gt;&lt;Volume&gt;3167111&lt;/Volume&gt;&lt;MktCap&gt;152.40B&lt;/MktCap&gt;&lt;PreviousClose&gt;156.75&lt;/PreviousClose&gt;&lt;PercentageChange&gt;-0.79%&lt;/PercentageChange&gt;&lt;AnnRange&gt;149.52 - 195.00&lt;/AnnRange&gt;&lt;Earns&gt;11.37&lt;/Earns&gt;&lt;P-E&gt;13.68&lt;/P-E&gt;&lt;Name&gt;International Business Machines&lt;/Name&gt;&lt;/Stock&gt;&lt;/StockQuotes&gt;</GetQuoteResult></GetQuoteResponse></soap:Body></soap:Envelope>
	var body = hr.getBody(); // this is java.lang.String
	var data = body.replaceFirst(".*<GetQuoteResult>", "").replaceFirst("</GetQuoteResult>.*", "").replaceAll("&gt;", ">").replaceAll("&lt;", "<");
	var quoteAttr = new Attribute("GetQuoteResult","urn:mytype", data);
	stsuu.addAttribute(quoteAttr);
}


