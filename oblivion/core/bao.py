import json
import hvac
import os

from pathlib import Path
from jinja2 import Template

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

    if not SECRETS_PATH.exists():
        raise RuntimeError(f"Missing {SECRETS_PATH}")

    secrets = json.loads(SECRETS_PATH.read_text())
    return {"vault_token": secrets["root_token"]}

def get_unseal_keys():
    if not SECRETS_PATH.exists():
        raise RuntimeError(f"Missing {SECRETS_PATH}")

    secrets = json.loads(SECRETS_PATH.read_text())
    return {"keys": secrets["keys"]}


