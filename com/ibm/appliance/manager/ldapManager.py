import logging,sys,time,ldap
from ldap.cidict import cidict

logging.basicConfig()
logger = logging.getLogger("LDAP Manager")
logger.setLevel(logging.INFO)


ldap.set_option(ldap.OPT_X_TLS_REQUIRE_CERT, ldap.OPT_X_TLS_ALLOW)
class ldapManager(object):


    def ldap_configuration(self):
        l = ldap.initialize('ldaps://192.168.42.101:636')

        username = "cn=root,secAuthority=default"
        password  = "passw0rd"
        try:
            l.simple_bind_s(username, password)
            userInfo = l.search_s('dc=iswga',ldap.SCOPE_SUBTREE,'(cn=testuser*)')
            mod_attrs = [( ldap.MOD_ADD, 'mail', 'testuser@mailinator.com'), (ldap.MOD_ADD, 'homePhone', '555-12345'), (ldap.MOD_ADD, 'displayName', 'Test User') ]
            l.modify_s('cn=testuser,dc=iswga', mod_attrs)
            logger.info("Successfully added extra attributes to testuser ")
        except Exception:
            print Exception
            logger.error("Unsuccessful to add extra attributes to testuser")
            pass
