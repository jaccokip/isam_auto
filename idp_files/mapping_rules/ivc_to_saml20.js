// mapping rule used for SAML junctions example - mapping ivc to saml20

importPackage(Packages.com.tivoli.am.fim.trustserver.sts);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.uuser);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.utilities);

IDMappingExtUtils.traceString("ivc_to_saml20 mapping rule called with stsuu: " + stsuu.toString());

// re-write Principal name with type as email nameid format
var principalName = stsuu.getPrincipalName();
stsuu.getPrincipalAttributeContainer().clear();
stsuu.addPrincipalAttribute(new Attribute("name", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress", principalName));

// keep just the attributes we want transmitted in SAML assertion
var keepAttrs = [ "emailAddress", "firstName", "lastName"];

var foundAttrs = [];
for (var i = 0; i < keepAttrs.length; i++) {
	var attr = stsuu.getAttributeContainer().getAttributeByName(keepAttrs[i]);
	if (attr != null) {
		foundAttrs.push(attr);
	}
}
	
// empty attrs, then add back what we want
stsuu.clearAttributeList();
for (var i = 0; i < foundAttrs.length; i++) {
	stsuu.addAttribute(foundAttrs[i]);
}
