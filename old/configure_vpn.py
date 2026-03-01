#!/usr/bin/env python3
import yaml
import requests
import urllib3
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "vpn_params_example.yaml"
INTERFACES_PATH = BASE_DIR / "config" / "interfaces_example.yaml"


def load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


class FortigateAPI:
    def __init__(self, host: str, token: str, vdom: str = "root", port: int = 443):
        self.host = host
        self.port = port
        self.vdom = vdom
        self.base_url = f"https://{host}:{port}/api/v2"
        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {token}"})
        self.session.verify = False  # lab only

    def _url(self, path: str) -> str:
        return f"{self.base_url}{path}"

    def create_address_objects(self, vpn_cfg: dict):
        print("[FGT] (conceitual) Criando objetos de endereço LAN_SITE_A / LAN_SITE_B...")
        # aqui depois vamos pôr o POST real em /cmdb/firewall/address

    def configure_phase1(self, vpn_cfg: dict, ifaces: dict):
        print("[FGT] (conceitual) Configurando Phase1-interface...")

    def configure_phase2(self, vpn_cfg: dict):
        print("[FGT] (conceitual) Configurando Phase2-interface...")

    def configure_routes_and_policies(self, vpn_cfg: dict, ifaces: dict):
        print("[FGT] (conceitual) Configurando rotas e políticas...")


class PaloAltoAPI:
    def __init__(self, host: str, api_key: str):
        self.host = host
        self.base_url = f"https://{host}/restapi/v10.0"
        self.session = requests.Session()
        self.session.headers.update({
            "X-PAN-KEY": api_key,
            "Content-Type": "application/json"
        })
        self.session.verify = False  # lab only

    def create_address_objects(self, vpn_cfg: dict):
        print("[PA] (conceitual) Criando objetos de endereço...")

    def configure_tunnel_interface(self, vpn_cfg: dict, ifaces: dict):
        print("[PA] (conceitual) Configurando tunnel interface...")

    def configure_ike_gateway(self, vpn_cfg: dict, ifaces: dict):
        print("[PA] (conceitual) Configurando IKE Gateway...")

    def configure_ipsec_tunnel(self, vpn_cfg: dict, ifaces: dict):
        print("[PA] (conceitual) Configurando IPSec Tunnel...")

    def configure_routes_and_policies(self, vpn_cfg: dict, ifaces: dict):
        print("[PA] (conceitual) Configurando rotas e Security Policies...")

    def commit(self):
        print("[PA] (conceitual) Executando commit...")


def main():
    cfg = load_yaml(CONFIG_PATH)
    ifaces = load_yaml(INTERFACES_PATH)

    fgt_api = FortigateAPI(
        host=cfg["fortigate"]["host"],
        token=cfg["fortigate"]["api_token"],
        vdom=cfg["fortigate"].get("vdom", "root"),
    )

    pa_api = PaloAltoAPI(
        host=cfg["paloalto"]["host"],
        api_key=cfg["paloalto"]["api_key"]
    )

    vpn_cfg = cfg["vpn"]

    # Ordem lógica aproximada
    fgt_api.create_address_objects(vpn_cfg)
    pa_api.create_address_objects(vpn_cfg)

    fgt_api.configure_phase1(vpn_cfg, ifaces["fortigate"])
    pa_api.configure_tunnel_interface(vpn_cfg, ifaces["paloalto"])
    pa_api.configure_ike_gateway(vpn_cfg, ifaces["paloalto"])
    pa_api.configure_ipsec_tunnel(vpn_cfg, ifaces["paloalto"])

    fgt_api.configure_phase2(vpn_cfg)
    fgt_api.configure_routes_and_policies(vpn_cfg, ifaces["fortigate"])
    pa_api.configure_routes_and_policies(vpn_cfg, ifaces["paloalto"])

    pa_api.commit()

    print("Fluxo de automação (conceitual) executado.")


if __name__ == "__main__":
    main()