pipeline {
  step "oblivion.core.bao.get_vault_address",
  step "oblivion.core.bao.get_vault_token",
  step "oblivion.core.pki.init",
  step "oblivion.core.bao.init",
  step "oblivion.core.bao.bootstrap_intermediate",
  step "oblivion.core.bao.enable_auth_approle",
  step "oblivion.core.bao.create_approle" {
    name = "pki-intermediate-issue-rfc1919-wildcard-dns",
  },
  unset "vault_token",
  step "oblivion.core.ansible.stream_task" {
    playbook_path = "openbao/agent",
    queue = "do-3",
    linux_user = "openbao",
    certificate_destination = "/opt/openbao/tls"
  },
}

