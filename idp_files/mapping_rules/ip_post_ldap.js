importPackage(Packages.com.tivoli.am.fim.trustserver.sts);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.uuser);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.utilities);


//re-write Principal name with type as email nameid format
var principalName = stsuu.getPrincipalName();
stsuu.getPrincipalAttributeContainer().clear();
stsuu.addPrincipalAttribute(new Attribute("name", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress", principalName));

//
// filter out STSUU attributes that we don't want in the SAML assertion after the LDAP
// search has run. A good example of this is the BASE_DN attribute, plus other attributes
// that were in the ISAM Credential at the SAML IDP.
//

//
// The simplest way to do this is to decide which attributes we want to keep, and discard the rest.
//
var keepAttrs = [ "emailAddress", "firstName", "lastName", "phone", "displayName" ];

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
