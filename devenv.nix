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
    pkgs.fluxcd
    pkgs.redis
    pkgs.vault
  ];
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
