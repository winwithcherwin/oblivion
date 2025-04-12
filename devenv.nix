{ pkgs, config, ... }:
{
  dotenv.enable = true;
  packages = [
    pkgs.direnv
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
