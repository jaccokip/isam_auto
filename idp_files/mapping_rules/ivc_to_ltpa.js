// mapping rule used for LTPA junctions example - mapping ivc to ltpa

importPackage(Packages.com.tivoli.am.fim.trustserver.sts);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.uuser);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.utilities);

IDMappingExtUtils.traceString("ivc_to_ltpa mapping rule called with stsuu: " + stsuu.toString());

//re-write Principal name with type using LTPA namespace
var principalName = stsuu.getPrincipalName();
stsuu.getPrincipalAttributeContainer().clear();
stsuu.addPrincipalAttribute(new Attribute("name", "urn:ibm:names:ITFIM:ltpa", principalName));

// keep just the attributes we want included in LTPAv2 token
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

