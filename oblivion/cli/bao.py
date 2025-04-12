import datetime
import click
import hvac
import ipaddress
import json
import os

from cryptography import x509
from cryptography.x509 import NameConstraints, DNSName, IPAddress
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes

from oblivion.core import kubernetes
from oblivion.core.bao import create_approle, get_vault_token, get_unseal_keys
from oblivion.cli.callbacks import inject_extra_vars


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


@click.group()
def cli():
    """OpenBao operations"""
    pass

@cli.command("enable-secrets-engine")
@click.option("--vault-addr", envvar="VAULT_ADDR", required=True, help="Vault address")
@click.option("--cluster-name", required=True, help="Cluster name")
@inject_extra_vars([get_vault_token])
def enable_secrets_engine(vault_addr, vault_token, cluster_name):
    client = hvac.Client(
        url=vault_addr,
        token=vault_token,
        verify=False,
    )

    if not client.is_authenticated():
        raise click.ClickException("OpenBao authentication failed.")

    secrets_mount = f"kubernetes-{cluster_name}"
    if f"{secrets_mount}/" not in client.sys.list_mounted_secrets_engines():
        client.sys.enable_secrets_engine(
            backend_type="kv",
            path=secrets_mount,
            options={"version": "2"},
        )

@cli.command("create-role-vault-secrets-operator")
@click.option("--vault-addr", envvar="VAULT_ADDR", required=True, help="Vault address")
@click.option("--cluster-name", required=True, help="Cluster name")
@inject_extra_vars([get_vault_token])
def create_role_for_sa(vault_addr, vault_token, cluster_name):
    client = hvac.Client(
        url=vault_addr,
        token=vault_token,
        verify=False,
    )

    if not client.is_authenticated():
        raise click.ClickException("OpenBao authentication failed.")

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

@cli.command("enable-auth-approle")
@click.option("--vault-addr", envvar="VAULT_ADDR", required=True, help="Vault address")
@inject_extra_vars([get_vault_token])
def enable_auth_approle(vault_addr, vault_token):
    client = hvac.Client(
        url=vault_addr,
        token=vault_token,
        verify=False,
    )

    if not client.is_authenticated():
        raise click.ClickException("OpenBao authentication failed.")

    if "approle/" not in client.sys.list_auth_methods():
        client.sys.enable_auth_method(method_type="approle")

@cli.command("create-approle")
@click.argument("name")
@click.option("--vault-addr", envvar="VAULT_ADDR", required=True, help="Vault address")
@click.option("--wrap-ttl", default="5m", help="TTL for wrapped secret_id")
@click.option("--override-policy", help="Provide a custom policy to override defaults")
@inject_extra_vars([get_vault_token])
def do_create_approle(**kwargs):
    """Create a Vault AppRole"""
    result = create_approle(**kwargs)
    click.echo(json.dumps(result, indent=2))

@cli.command("init")
@click.argument("endpoint", type=str)
def init_command(endpoint):
    client = hvac.Client(
        url=endpoint,
        verify=False,
    )

    if client.sys.is_initialized():
        raise click.ClickException("doing nothing, already initialized.")
    
    result = client.sys.initialize(1, 1)
    with open(OPENBAO_SECRETS_FILE, "w") as f:
        json.dump(result, f)

    client.token = result["root_token"]
    unseal_response = client.sys.submit_unseal_keys(result["keys"])
    click.echo(f"unseal response: {unseal_response}")

    if not client.sys.is_sealed():
        click.echo("successfully unsealed bao")
        return

@cli.command("delete-intermediate")
@click.argument("endpoint", type=str)
@inject_extra_vars([get_vault_token])
def bootstrap_intermediate(endpoint, vault_token):
    client = hvac.Client(
        url=endpoint,
        token=vault_token,
        verify=False,
    )

    if not client.is_authenticated():
        raise click.ClickException("OpenBao authentication failed.")

    if f"{PKI_PATH}/" not in client.sys.list_mounted_secrets_engines():
        raise click.ClickException(f"No intermediate mounted at {PKI_PATH} - nothing to clean.")

    try:
        client.delete(f"{PKI_PATH}/roles/{ROLE_NAME}")
    except Exception as e:
        click.echo(f"Could not delete role: {e}")

    try:
        client.sys.disable_secrets_engine(path=PKI_PATH)
    except Exception as e:
        click.ClickException(f"Could not disable secrets engine: {e}")


@cli.command("bootstrap-intermediate")
@click.argument("endpoint", type=str)
@inject_extra_vars([get_vault_token])
def bootstrap_intermediate(endpoint, vault_token):
    with open(ROOT_KEY_PATH, "rb") as f:
        root_key = serialization.load_pem_private_key(f.read(), password=None)

    with open(ROOT_CERT_PATH, "rb") as f:
        root_cert = x509.load_pem_x509_certificate(f.read(), backend=default_backend())

    client = hvac.Client(
        url=endpoint,
        token=vault_token,
        verify=False,
    )

    if not client.is_authenticated():
        raise click.ClickException("OpenBao authentication failed.")

    if f"{PKI_PATH}/" not in client.sys.list_mounted_secrets_engines():
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
            issuing_certificates=f"{endpoint}/v1/{PKI_PATH}/ca",
            crl_distribution_points=f"{endpoint}/v1/{PKI_PATH}/crl",
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

@cli.command("unseal")
@click.argument("endpoint", type=str)
@inject_extra_vars([get_unseal_keys])
def unseal_command(endpoint, keys):
    client = hvac.Client(
        url=endpoint,
        verify=False,
    )

    unseal_response = client.sys.submit_unseal_keys(keys)
    click.echo(f"unseal response: {unseal_response}")

    if not client.sys.is_sealed():
        click.echo("successfully unsealed bao")
        return

@cli.command("update-kubernetes-backend")
@click.option("--vault-address", required=True, type=str)
@click.option("--cluster-name", required=True, type=str)
@click.option("--kube-host", required=True, type=str)
def do_update_kubernetes_backend(cluster_name, vault_address, kube_host):
    auth_mount = f"kubernetes-{cluster_name}"
    sa_name = "token-reviewer"
    namespace = "oblivion"
    kubernetes.load_config()

    jwt, ca_crt, _ = kubernetes.extract_auth_details(sa_name, namespace)

    client = hvac.Client(
        url=vault_address,
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

    click.echo(f"updated backend: {auth_mount}")

@cli.command("mount-kubernetes-backend")
@click.option("--vault-address", required=True, type=str)
@click.option("--cluster-name", required=True, type=str)
@inject_extra_vars([get_vault_token])
def do_mount_kubernetes_backend(cluster_name, vault_address, vault_token):
    # meant to be run outside of cluster
    client = hvac.Client(
        url=vault_address,
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

@cli.group()
def integrate():
    """Integrate backends"""
    pass

@integrate.command("kubernetes")
@click.option("--endpoint", type=str, required=True, help="The address of OpenBao")
@click.option("--cluster-name", type=str, required=True, help="The name of the cluster")
@inject_extra_vars([get_vault_token])
def integrate_kubernetes(endpoint, cluster_name, vault_token):
    client = hvac.Client(
        url=endpoint,
        token=vault_token,
        verify=False,
    )

    if not client.is_authenticated():
        raise click.ClickException("OpenBao authentication failed.")

    auth_mount = f"kubernetes-{cluster_name}"
    auth_methods = client.sys.list_auth_methods()
    if f"{auth_mount}/" not in auth_methods:
        client.sys.enable_auth_method(
            method_type="kubernetes",
            path=auth_mount,
            description=f"Kubernetes auth for cluster '{cluster_name}'",
        )

    sa_name = "external-secrets"
    namespace = "external-secrets"
    kubernetes.load_config()
    jwt, ca_crt, kube_host = kubernetes.extract_auth_details(sa_name, namespace)

    client.write(
        f"auth/{auth_mount}/config",
        token_reviewer_jwt=jwt,
        kubernetes_host=kube_host,
        kubernetes_ca_cert=ca_crt,
    )

    policy_name = f"external-secrets-{cluster_name}"
    policy = f'''
path "secret/data/*" {{
  capabilities = ["read"]
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

    result = {
        "vault_auth_path": f"auth/{auth_mount}/",
        "vault_policy": policy_name,
        "k8s_sa": sa_name,
        "namespace": namespace,
        "kube_host": kube_host,
        "jwt": jwt,
        "ca_crt": ca_crt,
    }

    click.echo("OpenBao Kubernetes auth backend configured successfully.")
    for k, v in result.items():
        click.echo(f"{k}: {v}")

