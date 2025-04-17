import json
import hvac
import os

from pathlib import Path
from jinja2 import Template

import datetime
import hvac
import ipaddress
import json
import os

from cryptography import x509
from cryptography.x509 import NameConstraints, DNSName, IPAddress
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes

from oblivion.core import kubernetes


SECRETS_PATH = Path(".secrets/openbao.json")

POLICY_TEMPLATES = {
    "pki-intermediate-issue": """
path "pki-intermediate/issue/{{ pki_role_name }}" {
  capabilities = ["update"]
}
""",
    "sys": """
path "sys/mounts/{{ mount_path }}" {
  capabilities = ["create", "read", "update"]
}
""",
    "auth": """
path "auth/{{ auth_mount }}" {
  capabilities = ["create", "read", "update"]
}

path "auth/{{ auth_mount }}/config" {
  capabilities = ["create", "update"]
}
"""
}

def parse_role_name(name):
    if name.startswith("auth-"):
        parts = name.split("-", 2)
        return "auth", {"auth_mount": f"{parts[1]}-{parts[2]}"}
    elif name.startswith("sys-"):
        parts = name.split("-", 2)
        return "sys", {"mount_path": f"{parts[1]}-{parts[2]}"}
    elif name.startswith("pki-intermediate-issue-"):
        parts = name.split("-", 3)
        return "pki-intermediate-issue", {"pki_role_name": parts[3]}
    else:
        raise ValueError(f"Unsupported role naming convention: {name}")

def infer_policy(name, override=None):
    if override:
        return override
    role_type, ctx = parse_role_name(name)
    template = Template(POLICY_TEMPLATES[role_type])
    return template.render(**ctx)

def create_approle(name: str, vault_addr: str, vault_token: str, wrap_ttl: str = "100m", override_policy: str = None) -> dict:
    client = hvac.Client(url=vault_addr, token=vault_token, verify=False)
    if not client.is_authenticated():
        raise RuntimeError("Vault authentication failed")

    # Create the policy
    policy = infer_policy(name, override_policy)
    client.sys.create_or_update_policy(name=name, policy=policy)

    # Create the role
    client.write(f"auth/approle/role/{name}", token_policies=[name])

    # Fetch role_id
    role_id = client.read(f"auth/approle/role/{name}/role-id")["data"]["role_id"]

    # Create wrapped secret_id
    wrapped = client.write(
        f"auth/approle/role/{name}/secret-id",
        wrap_ttl=wrap_ttl,
        wrap=True
    )

    return {
        "role_name": name,
        "role_id": role_id,
        "wrapped_token": wrapped["wrap_info"]["token"],
        "vault_addr": vault_addr,
    }

def get_vault_token() -> dict:
    token = os.environ.get("VAULT_TOKEN")
    if token:
        return {"vault_token": token}

    if SECRETS_PATH.exists():
        secrets = json.loads(SECRETS_PATH.read_text())
        return {"vault_token": secrets["root_token"]}

def get_vault_address():
    return {"vault_addr": "https://10.8.0.3:8200"}

def mask_vault_token():
    return {"vault_token": "********"}

def mask_vault_unseal_keys():
    return {"vault_unseal_keys": "********"}



def get_unseal_keys():
    if not SECRETS_PATH.exists():
        raise RuntimeError(f"Missing {SECRETS_PATH}")

    secrets = json.loads(SECRETS_PATH.read_text())
    return {"vault_unseal_keys": secrets["keys"]}


OPENBAO_SECRETS_FILE = ".secrets/openbao.json"
PKI_PATH = "pki-intermediate"
PKI_ROLE_NAME = "rfc1918-wildcard-dns"
ROLE_NAME = f"pki-intermediate-{PKI_ROLE_NAME}"
COMMON_NAME = "OBLIVION INTERMEDIATE CA"
TTL = "43800h" # 5 years

ROOT_KEY_PATH = ".secrets/pki/root/oblivion-ca.key"
ROOT_CERT_PATH = ".secrets/pki/root/oblivion-ca.crt"

ALLOWED_DOMAINS = [
    "local", "lan", "wg", "mesh", "internal",
    "infra", "vault", "cluster"
]

RFC1918_IP_SANS = [
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16"
]

X509_CONSTRAINT_PERMITTED_SUBTREES = []

for name in ALLOWED_DOMAINS:
    X509_CONSTRAINT_PERMITTED_SUBTREES.append(DNSName(name))

for net in RFC1918_IP_SANS:
    X509_CONSTRAINT_PERMITTED_SUBTREES.append(IPAddress(ipaddress.IPv4Network(net)))


def enable_secrets_engine(vault_addr, vault_token, cluster_name):
    client = hvac.Client(
        url=vault_addr,
        token=vault_token,
        verify=False,
    )

    if not client.is_authenticated():
        raise Exception("OpenBao authentication failed.")

    secrets_mount = f"kubernetes-{cluster_name}"
    if f"{secrets_mount}/" not in client.sys.list_mounted_secrets_engines():
        client.sys.enable_secrets_engine(
            backend_type="kv",
            path=secrets_mount,
            options={"version": "2"},
        )

def create_role_vault_secrets_operator(vault_addr, vault_token, cluster_name):
    client = hvac.Client(
        url=vault_addr,
        token=vault_token,
        verify=False,
    )

    if not client.is_authenticated():
        raise Exception("OpenBao authentication failed.")

    service_account_name = "vault-secrets-operator-controller-manager"
    policy_name = f"kubernetes-{cluster_name}-{service_account_name}"
    policy = f'''
path "kubernetes-{cluster_name}/data/*" {{
  capabilities = ["read", "list"]
}}
'''

    client.sys.create_or_update_policy(name=policy_name, policy=policy)

    client.write(
        f"auth/kubernetes-{cluster_name}/role/{service_account_name}",
        bound_service_account_names="*",
        bound_service_account_namespaces="*",
        policies=policy_name,
        audience="vault",
        ttl="24h",
    )

def enable_auth_approle(vault_addr, vault_token):
    client = hvac.Client(
        url=vault_addr,
        token=vault_token,
        verify=False,
    )

    if not client.is_authenticated():
        raise Exception("OpenBao authentication failed.")

    if "approle/" not in client.sys.list_auth_methods():
        client.sys.enable_auth_method(method_type="approle")


def init(vault_addr):
    client = hvac.Client(
        url=vault_addr,
        verify=False,
    )

    if client.sys.is_initialized():
        return "doing nothing, already initialized."
    
    result = client.sys.initialize(1, 1)
    with open(OPENBAO_SECRETS_FILE, "w") as f:
        json.dump(result, f)

    client.token = result["root_token"]
    unseal_response = client.sys.submit_unseal_keys(result["keys"])
    print(f"unseal response: {unseal_response}")

    if not client.sys.is_sealed():
        return "successfully unsealed bao"

def delete_intermediate(vault_addr, vault_token):
    client = hvac.Client(
        url=vault_addr,
        token=vault_token,
        verify=False,
    )

    if not client.is_authenticated():
        return "OpenBao authentication failed."

    if f"{PKI_PATH}/" not in client.sys.list_mounted_secrets_engines():
        raise Exception(f"No intermediate mounted at {PKI_PATH} - nothing to clean.")

    try:
        client.delete(f"{PKI_PATH}/roles/{ROLE_NAME}")
    except Exception as e:
        print(f"Could not delete role: {e}")

    try:
        client.sys.disable_secrets_engine(path=PKI_PATH)
    except Exception as e:
        raise Exception(f"Could not disable secrets engine: {e}")


def bootstrap_intermediate(vault_addr, vault_token):
    with open(ROOT_KEY_PATH, "rb") as f:
        root_key = serialization.load_pem_private_key(f.read(), password=None)

    with open(ROOT_CERT_PATH, "rb") as f:
        root_cert = x509.load_pem_x509_certificate(f.read(), backend=default_backend())

    client = hvac.Client(
        url=vault_addr,
        token=vault_token,
        verify=False,
    )

    if not client.is_authenticated():
        raise Exception("OpenBao authentication failed.")

    if f"{PKI_PATH}/" in client.sys.list_mounted_secrets_engines():
        return "Already bootstrapped intermediate"

    client.sys.enable_secrets_engine(
        backend_type="pki",
        path=PKI_PATH,
        config={"max_lease_ttl": TTL},
    )

    # create and sign intermediate
    csr_resp = client.secrets.pki.generate_intermediate(
        type="internal",
        common_name=COMMON_NAME,
        mount_point=PKI_PATH,
    )
    csr_pem = csr_resp["data"]["csr"]
    csr = x509.load_pem_x509_csr(csr_pem.encode(), backend=default_backend())

    intermediate_cert = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(root_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(datetime.datetime.utcnow() - datetime.timedelta(minutes=5))
        .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
        .add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(csr.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(root_key.public_key()), critical=False)
        .add_extension(
            NameConstraints(
                permitted_subtrees=X509_CONSTRAINT_PERMITTED_SUBTREES,
                excluded_subtrees=None,
            ),
            critical=True,
        )
        .sign(root_key, hashes.SHA384(), backend=default_backend())
    )

    cert_pem = intermediate_cert.public_bytes(serialization.Encoding.PEM).decode()

    client.secrets.pki.set_signed_intermediate(
        certificate=cert_pem,
        mount_point=PKI_PATH,
    )

    client.secrets.pki.set_urls(
        mount_point=PKI_PATH,
        params=dict(
            issuing_certificates=f"{vault_addr}/v1/{PKI_PATH}/ca",
            crl_distribution_points=f"{vault_addr}/v1/{PKI_PATH}/crl",
        )
    )

    # we always want to update the rule in case there are changes
    client.secrets.pki.create_or_update_role(
        name=PKI_ROLE_NAME,
        mount_point=PKI_PATH,
        extra_params=dict(
            allowed_domains=ALLOWED_DOMAINS,
            allow_subdomains=True,
            allow_glob_domains=True,
            allow_ip_sans=True,
            enforce_hostnames=True,
            server_flag=True,
            client_flag=True,
            include_ca_chain=True,
            max_ttl="8760h",  # 1 year
        )
    )

def unseal(vault_addr, vault_unseal_keys):
    client = hvac.Client(
        url=vault_addr,
        verify=False,
    )

    unseal_response = client.sys.submit_unseal_keys(vault_unseal_keys)
    print(f"unseal response: {unseal_response}")

    if not client.sys.is_sealed():
        print("successfully unsealed bao")
        return

def update_kubernetes_backend(cluster_name, vault_addr, kube_host):
    auth_mount = f"kubernetes-{cluster_name}"
    sa_name = "token-reviewer"
    namespace = "oblivion"
    kubernetes.load_config()

    jwt, ca_crt, _ = kubernetes.extract_auth_details(sa_name, namespace)

    client = hvac.Client(
        url=vault_addr,
        verify=False,
    )
    # get vault_token for own service account
    data = client.auth.kubernetes.login(role=sa_name, jwt=jwt, mount_point=auth_mount)
    vault_token = data["auth"]["client_token"]

    client.token = vault_token


    # configure backend - make sure kubernetes can authenticate users
    client.write(
        f"auth/{auth_mount}/config",
        token_reviewer_jwt=jwt,
        kubernetes_host=kube_host,
        kubernetes_ca_cert=ca_crt,
    )

    print(f"updated backend: {auth_mount}")

def mount_kubernetes_backend(cluster_name, vault_addr, vault_token):
    # meant to be run outside of cluster
    client = hvac.Client(
        url=vault_addr,
        token=vault_token,
        verify=False,
    )

    # mount the backend idempotently
    auth_mount = f"kubernetes-{cluster_name}"
    auth_methods = client.sys.list_auth_methods()
    if f"{auth_mount}/" not in auth_methods:
        client.sys.enable_auth_method(
            method_type="kubernetes",
            path=auth_mount,
            description=f"Kubernetes auth for cluster '{cluster_name}'",
        )
    
    sa_name = "token-reviewer"
    namespace = "oblivion"
    kubernetes.load_config()
    jwt, ca_crt, kube_host = kubernetes.extract_auth_details(sa_name, namespace)

    # configure backend - make sure kubernetes can authenticate users
    client.write(
        f"auth/{auth_mount}/config",
        token_reviewer_jwt=jwt,
        kubernetes_host=kube_host,
        kubernetes_ca_cert=ca_crt,
    )

    policy_name = f"{auth_mount}"
    policy = f'''
path "auth/{auth_mount}/config" {{
  capabilities = ["read", "update"]
}}
'''
    client.sys.create_or_update_policy(name=policy_name, policy=policy)

    client.write(
        f"auth/{auth_mount}/role/{sa_name}",
        bound_service_account_names=sa_name,
        bound_service_account_namespaces=namespace,
        policies=policy_name,
        ttl="24h",
    )
    return {"cluster_name": cluster_name}

