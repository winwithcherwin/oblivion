import argparse
import json
import socket
import sys

from jinja2 import Environment, FileSystemLoader
from pyroute2 import IPDB

TEMPLATE_NAME = "openbao-agent.hcl.j2"
TEMPLATE_DIR = "/opt/oblivion/oblivion/engine/ansible/playbooks/openbao/templates"

def get_wireguard_ip(interface="wg0"):
    try:
        with IPDB() as ipdb:
            wg = ipdb.interfaces[interface]
            for ip_info in wg.ipaddr:
                if ip_info["prefixlen"] == 32:
                    return ip_info["address"]
    except Exception as e:
        raise RuntimeError(f"Could not retrieve IP for interface '{interface}'") from e

def infer_fields(data):

    if "fqdn" not in data:
        data["fqdn"] = socket.getfqdn()

    role = data.get("role_name", "")
    if "pki" in role and "issue" in role:
        if "wireguard_ip" not in data:
            data["wireguard_ip"] = get_wireguard_ip()
        role_name = data["role_name"]
        data.setdefault("certificate_destination_dir", f"/etc/ssl/{role_name}")
        data.setdefault("pki_path", "pki-intermediate")
        data.setdefault("pki_role_name", "-".join(role_name.split("-")[3:]))
        data.setdefault("crt_name", "tls.crt")
        data.setdefault("key_name", "tls.key")
    return data

def render_template(data):
    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        variable_start_string="[[",
        variable_end_string="]]",
        trim_blocks=True,
        lstrip_blocks=True,
        autoescape=False,
    )
    template = env.get_template(TEMPLATE_NAME)
    rendered = template.render(data)
    
    role = data.get("role_name")
    if "pki" in role and "issue" in role:
        rendered = (
            rendered
            .replace("[[ ROLE_NAME ]]", data["role_name"])
            .replace("[[ FQDN ]]", data["fqdn"])
            .replace("[[ WIREGUARD_IP ]]", data["wireguard_ip"])
            .replace("[[ PKI_PATH ]]", data["pki_path"])
            .replace("[[ PKI_ROLE_NAME ]]", data["pki_role_name"])
        )
    return rendered

def main():
    parser = argparse.ArgumentParser(description="Render OpenBao Agent HCL config")
    parser.add_argument("--input-file", help="Path to JSON file")
    parser.add_argument("--input-json", help="Inline JSON string")
    parser.add_argument("--output-path", help="Optional output file (defaults to stdout)")

    args = parser.parse_args()

    if args.input_file:
        with open(args.input_file) as f:
            raw_data = json.load(f)
    elif args.input_json:
        if args.input_json.strip() == "-":
            raw_data = json.load(sys.stdin)
        else:
            raw_data = json.loads(args.input_json)
    else:
        raise ValueError("You must provide --input-file, --input-json")

    if "role_name" not in raw_data:
        raise ValueError("role_name is required")

    if "vault_addr" not in raw_data:
        raise ValueError("vault_addr must be provided")

    data = infer_fields(raw_data)
    rendered = render_template(data)

    if args.output_path:
        with open(args.output_path, "w") as f:
            f.write(rendered)
    else:
        print(rendered)

if __name__ == "__main__":
    main()

