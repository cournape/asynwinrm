from enum import Enum
import io
import subprocess


class AuthEnum(Enum):

    Basic = 'basic'
    NTLM = 'ntlm'
    Kerberos = 'kerberos'
    Auto = 'auto'


KERB_TEMPLATE = """
[libdefaults]
    default_realm = {realm_upper}
    dns_lookup_realm = false
    dns_lookup_kdc = false
[realms]
    {realm_upper} = {{
        kdc = {ad_server}
        admin_server = {ad_server}
    }}
[domain_realm]
    .{realm_lower} = {realm_upper}
    {realm_lower} = {realm_upper}
[logging]
    kdc = FILE:/var/log/krb5kdc.log
    admin_server = FILE:/var/log/kadmin.log
    default = FILE:/var/log/krb5lib.log
"""
KERB_CONF = '/etc/krb5.conf'


def set_kerb_pwd(username, password, realm, ad_server=None):
    with open(KERB_CONF, 'w') as fl:
        fl.write(KERB_TEMPLATE.format(realm_lower=realm.lower(),
                                      realm_upper=realm.upper(),
                                      ad_server=ad_server if ad_server else realm.lower()))
    if '@' in username:
        username = username.split('@')[0]
    cmd = 'kinit {0}@{1}'.format(username, realm.upper())
    proc = subprocess.Popen(cmd,
                            shell=True,
                            stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE,
                            bufsize=-1)
    stream = io.TextIOWrapper(proc.stdin)
    stream.write(password)
    stream.close()
    proc.wait()