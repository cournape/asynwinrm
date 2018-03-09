import subprocess
import io
import warnings

from cryptography import x509
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.exceptions import UnsupportedAlgorithm


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



class UnknownSignatureAlgorithmOID(Warning):
    pass


def set_kerb_pwd(username, password, realm, ad_server=None, generate_kerb_conf=False):
    if generate_kerb_conf:
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
                            stderr=subprocess.PIPE,
                            bufsize=-1)
    stream = io.TextIOWrapper(proc.stdin)
    stream.write(password)
    stream.close()
    std_err = proc.stderr.read()
    exit_code = proc.wait()
    if exit_code != 0:
        raise Exception(std_err.decode('utf-8'))


def get_certificate_hash(certificate_der):
    assert isinstance(certificate_der, bytes)
    # https://tools.ietf.org/html/rfc5929#section-4.1
    cert = x509.load_der_x509_certificate(certificate_der, default_backend())

    try:
        hash_algorithm = cert.signature_hash_algorithm
    except UnsupportedAlgorithm as ex:
        warnings.warn('Failed to get signature algorithm from certificate, '
                      'unable to pass channel bindings: %s' % str(ex), UnknownSignatureAlgorithmOID)
        return None

    # if the cert signature algorithm is either md5 or sha1 then use sha256
    # otherwise use the signature algorithm
    if hash_algorithm.name in ['md5', 'sha1']:
        digest = hashes.Hash(hashes.SHA256(), default_backend())
    else:
        digest = hashes.Hash(hash_algorithm, default_backend())

    digest.update(certificate_der)
    certificate_hash = digest.finalize()

    return certificate_hash