config = {
  bao = {
    server = "do-3",
    linux_user = "openbao",
    certificate_destination = "/opt/openbao/tls",
  },
  kubernetes = {
    cluster_name = "staging",
    host = "hetzner-4",
    kube_config_source = "/etc/rancher/k3s/k3s.yaml",
    kube_config_dest = "./.secrets/k3s.yaml",
    playbook = "k3s",
    oblivion = {
      overlay = "kubernetes/apps/oblivion/overlays/staging",
    }
  },
  pki = {
    ca_certificate_name = "oblivion-ca-certificate",
    ca_certificate_path = ".secrets/pki/root/oblivion-ca.crt",
    app_role_name = "pki-intermediate-issue-rfc1918-wildcard-dns",
    namespace = "kube-system",
  },
  flux = {
    method = "github",
    owner = "winwithcherwin",
    repository = "oblivion",
    path = "kubernetes/cluster/staging",
    branch = "main",
  },
}

pipeline {
  step "oblivion.core.terraform.output" {
    register = {
      name = "terraform_output",
    },
  },
  step "oblivion.core.bao.get_vault_address",
  step "oblivion.core.bao.get_vault_token",
  step "oblivion.core.pki.init",
  step "oblivion.core.ansible.stream_task" {
    args = {
      playbook_path = "openbao",
      queue = config.bao.server,
    },
  },
  step "oblivion.core.bao.init",
  step "oblivion.core.bao.bootstrap_intermediate",
  step "oblivion.core.bao.enable_auth_approle",
  step "oblivion.core.bao.create_approle" {
    args = {
      name = config.pki.app_role_name,
    },
    register = {
      name = "approle_info",
    },
  },
  step "oblivion.core.ansible.stream_task" {
    args = {
      playbook_path = "openbao/agent",
      queue = config.bao.server,
      linux_user = config.bao.linux_user,
      certificate_destination = config.bao.certificate_destination,
      extra_vars = var("approle_info"),
    },
  },
  step "oblivion.core.ansible.stream_task" {
    args = {
      playbook_path = "openbao/refresh-server",
      queue = config.bao.server,
    },
  },
  step "oblivion.core.bao.get_unseal_keys",
  step "oblivion.core.bao.unseal",
  step "oblivion.core.ansible.stream_task" {
    args = {
      playbook_path = config.kubernetes.playbook,
      queue = config.kubernetes.host,
    },
  },
  step "oblivion.core.kubernetes.copy_kube_config" {
    args = {
      host = function()
        return terraform_output.all_hosts.value[config.kubernetes.host]
      end,
      source = config.kubernetes.kube_config_source,
      dest = config.kubernetes.kube_config_dest,
    },
  },
  step "oblivion.core.kubernetes.publish_root_ca" {
    args = {
      name = config.pki.ca_certificate_name,
      source = config.pki.ca_certificate_path,
      destination = config.kubernetes.oblivion.overlay,
      namespace = config.pki.namespace,
    },
  },
  step "oblivion.core.git.add_commit_push" {
    enabled = false,
    args = {
      path = config.kubernetes.oblivion.overlay,
      commit_message = "Add CA certificate",
    },
  },
  step "oblivion.core.flux.bootstrap" {
    enabled = false,
    args = {
      method = config.flux.method,
      owner = config.flux.owner,
      repository = config.flux.repository,
      branch = config.flux.branch,
      path = config.flux.path,
    },
  },
  step "oblivion.core.kubernetes.kustomize_apply" {
    enabled = false,
    args = {
      path = config.flux.path,
    },
  },
  step "oblivion.core.bao.mount_kubernetes_backend" {
    args = {
      cluster_name = config.kubernetes.cluster_name,
    },
  },
  step "oblivion.core.bao.create_role_vault_secrets_operator",
  step "oblivion.core.bao.enable_secrets_engine",
}

