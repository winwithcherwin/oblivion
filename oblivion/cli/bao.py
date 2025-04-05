import json
import click
import hvac

from oblivion.core import kubernetes


OPENBAO_SECRETS_FILE = ".secrets/openbao.json"

@click.group()
def cli():
    """OpenBao operations"""
    pass

@cli.command("bootstrap")
@click.argument("endpoint", type=str)
def bootstrap_command(endpoint):
    client = hvac.Client(
            url=endpoint,
            verify=False,
    )

    if client.sys.is_initialized():
        click.echo("doing nothing, already initialized.")
        return
    
    result = client.sys.initialize(1, 1)
    with open(OPENBAO_SECRETS_FILE, "w") as f:
        json.dump(result, f)

    client.token = result["root_token"]
    unseal_response = client.sys.submit_unseal_keys(result["keys"])
    click.echo(f"unseal response: {unseal_response}")

    if not client.sys.is_sealed():
        click.echo("successfully unsealed bao")
        return


@cli.group()
def integrate():
    """Integrate backends"""
    pass

@integrate.command("kubernetes")
@click.option("--endpoint", type=str, required=True, help="The address of OpenBao")
@click.option("--cluster-name", type=str, required=True, help="The name of the cluster")
def integrate_kubernetes(endpoint, cluster_name):
    with open(OPENBAO_SECRETS_FILE) as f:
        vault_info = json.load(f)

    vault_token = vault_info["root_token"]
    client_vault = hvac.Client(
        url=endpoint,
        token=vault_token,
        verify=False,
    )

    if not client_vault.is_authenticated():
        raise click.ClickException("OpenBao authentication failed.")

    auth_mount = f"kubernetes-{cluster_name}"
    auth_methods = client_vault.sys.list_auth_methods()
    if f"{auth_mount}/" not in auth_methods:
        client_vault.sys.enable_auth_method(
            method_type="kubernetes",
            path=auth_mount,
            description=f"Kubernetes auth for cluster '{cluster_name}'",
        )

    sa_name = "external-secrets"
    namespace = "external-secrets"
    kubernetes.load_config()
    jwt, ca_crt, kube_host = kubernetes.extract_auth_details(sa_name, namespace)

    client_vault.write(
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
    client_vault.sys.create_or_update_policy(name=policy_name, policy=policy)

    client_vault.write(
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

