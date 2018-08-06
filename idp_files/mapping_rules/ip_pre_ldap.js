importPackage(Packages.com.tivoli.am.fim.trustserver.sts);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.uuser);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.utilities);

//
// we can inspect the stsuu and make and decisions we want here before populating STSUU
// that will be used as input to the LDAP Attribute mapping rule.
//

// for this demo, just set the BASE_DN to the DN we want to search for - if one isn't already set
var existingbaseDN = stsuu.getAttributeValueByName("BASE_DN");
if (existingbaseDN != null && existingbaseDN.length() > 0) {
	IDMappingExtUtils.traceString("The ip_pre_ldap.js found an existing BASE_DN: " + existingbaseDN);
} else {
	IDMappingExtUtils.traceString("The ip_pre_ldap.js mapping rule is setting the BASE_DN");
	var baseDNAttr = new Attribute("BASE_DN", null, "cn=testuser,dc=iswga");
	stsuu.addAttribute(baseDNAttr);
}
