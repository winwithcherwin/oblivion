{ pkgs, config, ... }:
{
  dotenv.enable = true;
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
