importPackage(Packages.com.tivoli.am.fim.trustserver.sts);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.uuser);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.utilities);

//re-write Principal name with type as email nameid format
var principalName = stsuu.getPrincipalName();
stsuu.getPrincipalAttributeContainer().clear();
stsuu.addPrincipalAttribute(new Attribute("name", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress", principalName));

// demo rule for mapping stsuu to stsuu
// just add an additional attribute
var testAttr = new Attribute("testattr_from_auxilary_chain","urn:mytype", "myvalue_from_auxilary_chain");
stsuu.addAttribute(testAttr);

// and clear out the RST attributes
stsuu.getRequestSecurityTokenAttributeContainer().clear();
