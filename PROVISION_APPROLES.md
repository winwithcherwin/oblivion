## AppRole Naming Convention (OpenBao)

We use **strict naming conventions** to automatically infer OpenBao access policies from the AppRole name. This ensures:

- ✅ Least privilege access
- ✅ Audit-friendly roles
- ✅ No complex configuration required

### Structure
<capability>-<type>-<target>

### Naming Format
Examples:

| Role Name                                 | Grants Access To                          |
|-------------------------------------------|-------------------------------------------|
| `pki-intermediate-issue-rfc1918-wildcard-dns`          | Issue certs from `pki-intermediate/issue/rfc1918-wildcard-dns` |
| `sys-pki-intermediate`                    | Mount/configure engine `pki-intermediate` |
| `auth-kubernetes-development`             | Configure `auth/kubernetes-development`   |

### Convention Rules

* Prefixes map directly to OpenBao paths:
    * pki-* → secrets engine pki-*
    * auth-* → auth method auth/*
    * sys-* → sys/mounts/*

If the name doesn't match → fallback to custom mode (requires --policy)

All policies deny delete and * access

### Creating AppRole with Click (CLI)

```bash
oblivion bao create-approle pki-intermediate-issue-rfc1918-wildcard-dns --vault-addr https://10.8.0.2:8200
```

### Using the Callback with Ansible
```
oblivion ansible run openbao/agent \
  --queue do-1 \
  --extra-vars-callback "oblivion.core.bao:create_approle:name=pki-intermediate-issue-rfc1918-wildcard-dns,vault_addr=https://10.8.0.2:8200"
```
This:
1. Runs `create_approle` callback
1. Injects the result as --extra-vars into Ansible
1. Never sends `vault_token` to Ansible (secure chaining)

Addendum: Chaining `--extra-vars-callback`

You can **chain multiple callbacks** using `--extra-vars-callback` to prepare dynamic variables for Ansible without exposing secrets.

```bash
oblivion ansible run openbao/agent \
  --queue do-1 \
  --extra-vars-callback \
    "oblivion.core.bao:get_vault_token" \
    "oblivion.core.bao:create_approle:name=pki-intermediate-issue-rfc1918-wildcard-dns,vault_addr=https://10.8.0.2:8200"
```

This performs:
1.`get_vault_token` → returns { "vault_token": "..." }
1. Passes this into `create_approle(...)`
1. `create_approle` returns { "role_name": ..., "wrapped_token": ... }
1. Only the final result is sent to Ansible as --extra-vars

### Use Case Example
Want to bootstrap a OpenBao agent with a cert-issuing role?
```
oblivion ansible run openbao/agent \
  --queue do-1 \
  --extra-vars-callback \
    "oblivion.core.bao:get_vault_token" \
    "oblivion.core.bao:create_approle:name=pki-intermediate-issue-rfc1918-wildcard-dns,vault_addr=https://10.8.0.2:8200"
  --e "linux_user=openbao"
```

The openbao-agent is fully provisioned with:
1. A wrapped token
1. Minimal permissions (via inferred policy)
1. No need to store secrets on disk

