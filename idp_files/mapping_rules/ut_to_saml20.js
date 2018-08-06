// mapping rule used for SAML junctions example - mapping ivc to saml20

importPackage(Packages.com.tivoli.am.fim.trustserver.sts);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.uuser);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.utilities);

//IDMappingExtUtils.traceString("ut_to_saml20 mapping rule called with stsuu: " + stsuu.toString());

// re-write Principal name with type as email nameid format
var principalName = stsuu.getPrincipalName();
var principalPassword = stsuu.getPrincipalAttributeContainer().getAttributeValueByName("Password");
stsuu.getPrincipalAttributeContainer().clear();
stsuu.addPrincipalAttribute(new Attribute("name", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress", principalName));

// add an attribute so we get an AttributeStatement in our resulting SAML assertion
// this demo shows a multi-valued attribute
var vals = java.lang.reflect.Array.newInstance(java.lang.String, 2);
vals[0] = "myvalue1";
vals[1] = "myvalue2";
stsuu.addAttribute(new Attribute("myattr", "urn:mytype", vals));
