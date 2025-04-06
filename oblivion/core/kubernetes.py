from kubernetes import client, config


def load_config():
    try:
        config.load_incluster_config()
    except config.config_exception.ConfigException:
        config.load_kube_config()

def generate_sa_token(sa_name, namespace, expiration_seconds=3600):
    core = client.CoreV1Api()
    token_request = client.AuthenticationV1TokenRequest(
        spec=client.V1TokenRequestSpec(
            audiences=["k3s"], # "kubectl get --raw /.well-known/openid-configuration | jq (spoiler, https://kubernetes.default.svc.cluster.local
            expiration_seconds=expiration_seconds,
        )
    )
    token = core.create_namespaced_service_account_token(
        name=sa_name,
        namespace=namespace,
        body=token_request,
    )
    return token.status.token

def extract_auth_details(sa_name, namespace):
    core = client.CoreV1Api()
    jwt = generate_sa_token(sa_name, namespace)
    ca_crt = core.read_namespaced_config_map("kube-root-ca.crt", "kube-system").data["ca.crt"]
    kube_host = client.Configuration.get_default_copy().host

    return jwt, ca_crt, kube_host

