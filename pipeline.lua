pipeline {
  step "oblivion.core.bao.get_vault_token",
  step "oblivion.core.pki.init",
  step "oblivion.core.ansible.stream_task" {
    queue         = "do-3",
    playbook_path = "echo",
  },
  step "oblivion.core.bao.init",
}

