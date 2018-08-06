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


// add a test group
var group = new Group("testgroup", "urn:ibm:names:ITFIM:5.1:accessmanager", null);
// TODO - revisit whether g1,g2 are needed pending defect 66726
var g1 = new Attribute("registryid", "urn:ibm:names:ITFIM:5.1:accessmanager", "cn=testgroup,dc=iswga");
var g2 = new Attribute("uuid", "urn:ibm:names:ITFIM:5.1:accessmanager", "00000000-0000-0000-0000-000000000000");
group.setAttribute(g1);
group.setAttribute(g2);
stsuu.addGroup(group);

group = new Group("testgroup2", "urn:ibm:names:ITFIM:5.1:accessmanager", null);
// TODO - revisit whether g1,g2 are needed pending defect 66726
g1 = new Attribute("registryid", "urn:ibm:names:ITFIM:5.1:accessmanager", "cn=testgroup2,dc=iswga");
g2 = new Attribute("uuid", "urn:ibm:names:ITFIM:5.1:accessmanager", "00000000-0000-0000-0000-000000000000");
group.setAttribute(g1);
group.setAttribute(g2);
stsuu.addGroup(group);

IDMappingExtUtils.traceString("sp mapping rule ended with stsuu: " + stsuu.toString());
