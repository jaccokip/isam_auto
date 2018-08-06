// mapping rule used for SAML 2.0 to SAML 2.0 STS example

importPackage(Packages.com.tivoli.am.fim.trustserver.sts);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.uuser);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.utilities);

//IDMappingExtUtils.traceString("saml20_to_saml20 mapping rule called with stsuu: " + stsuu.toString());

// re-write Principal name with type as email nameid format
var principalName = stsuu.getPrincipalName();
stsuu.getPrincipalAttributeContainer().clear();
stsuu.addPrincipalAttribute(new Attribute("name", "urn:oasis:names:tc:SAML:1.1:nameid-format:emailAddress", principalName));

// keep only these attributes from the AttributeList from the original SAML assertion
var keepAttrs = [ "emailAddress", "firstName", "lastName", "phone", "displayName" ];
var finalAttrs = [];
for (var i = 0; i < keepAttrs.length; i++) {
	var attr = stsuu.getAttributeContainer().getAttributeByName(keepAttrs[i]);
	if (attr != null) {
		finalAttrs.push(attr);
	}
}

// example of putting in an extra attribute
finalAttrs.push(new Attribute("testattr_from_saml20mapping","urn:mytype", "myvalue_from_saml20mapping"));

/*
 * Clear the attribute list, then add back in just what we want
 */
stsuu.clearAttributeList();
for (var i = 0; i < finalAttrs.length; i++) {
	stsuu.addAttribute(finalAttrs[i]);
}
