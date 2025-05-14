{ pkgs, config, programs, ... }:
{
  env = {
    KUBECONFIG = "${builtins.getEnv "PWD"}/.secrets/k3s.yaml";
    TERM = "xterm-256color";
  };
  dotenv.enable = true;
  packages = [
    pkgs.k8sgpt
    pkgs.kyverno
    pkgs.stern
    pkgs.clusterctl
    pkgs.trivy
    pkgs.kubie
    pkgs.kustomize
    pkgs.direnv
    pkgs.dnsutils
    pkgs.yq
    pkgs.jq
    pkgs.fzf
    pkgs.bc
    pkgs.nmap
    pkgs.kubectl
    pkgs.kubecolor
    pkgs.kubectx
    pkgs.fluxcd
    pkgs.redis
    pkgs.vault
    pkgs.packer
    pkgs.ansible
    pkgs.k9s
    pkgs.tree
    pkgs.openssl
    pkgs.bat
    pkgs.docker
    pkgs.libgit2
    pkgs.zsh
    pkgs.kdash
  ];
  scripts.k.exec = ''
    kubectl "$@";
  '';
  scripts.ktx.exec = ''
    kubectx "$@";
  '';
  scripts.kns.exec = ''
    kubens "$@";
  '';
  scripts.get-ip.exec = ''
    kubectl describe droplet demo-droplet | grep -i ipv4address | head -n1 | cut -d: -f2 | xargs
  '';
  scripts.ob.exec = ''
    python -m oblivion "$@";
  '';
  languages.python = {
    enable = true;
    version = "3.12.3";

    venv.enable = true;
    venv.requirements = ./oblivion/requirements.txt;
  };

  languages.terraform = {
    enable = true;
    version = "1.11.2";
  };
}
