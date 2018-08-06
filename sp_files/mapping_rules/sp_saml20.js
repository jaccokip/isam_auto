// SAML20 SP Mapping rule

importPackage(Packages.com.tivoli.am.fim.trustserver.sts);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.uuser);
importPackage(Packages.com.tivoli.am.fim.trustserver.sts.utilities);

IDMappingExtUtils.traceString("sp mapping rule called with stsuu: " + stsuu.toString());

// copy all the attributes from the idp, found in the AdditionalAttributeStatement, into this STSUU
for (var i = stsuu.getAttributeStatements(); i.hasNext(); ) {
	var attrStatement = i.next();
	var attrs = attrStatement.getAttributes();
	if (attrs != null && attrs.length > 0) {
		for (var j = 0; j < attrs.length; j++) {
			stsuu.addAttribute(attrs[j]);
		}
	}
}

var testAttr = new Attribute("testattr_sp","urn:mytype", "myvalue_sp");
stsuu.addAttribute(testAttr);
