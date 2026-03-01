import ipaddress
import yaml
import requests
import urllib3
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parents[2]
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

    def _cidr_to_subnet_string(self, cidr: str) -> str:
        net = ipaddress.ip_network(cidr, strict=False)
        return f"{net.network_address} {net.netmask}"

    def create_address_objects(self, vpn_cfg: dict) -> list:
        site_a = vpn_cfg["networks"]["site_a"]
        site_b = vpn_cfg["networks"]["site_b"]

        addr_url = self._url("/cmdb/firewall/address")
        params = {"vdom": self.vdom}

        objects = [
            {"name": "LAN_SITE_A", "cidr": site_a},
            {"name": "LAN_SITE_B", "cidr": site_b},
        ]

        results = []

        for obj in objects:
            subnet_str = self._cidr_to_subnet_string(obj["cidr"])
            payload = {
                "name": obj["name"],
                "type": "subnet",
                "subnet": subnet_str,
            }

            resp = self.session.post(addr_url, params=params, json=payload, timeout=5)
            entry = {
                "object": obj["name"],
                "cidr": obj["cidr"],
                "status_code": resp.status_code,
                "body": resp.text[:200],
            }
            results.append(entry)

        return results


def apply_fortigate_vpn():
    cfg = load_yaml(CONFIG_PATH)
    fgt_cfg = cfg["fortigate"]
    vpn_cfg = cfg["vpn"]

    api = FortigateAPI(
        host=fgt_cfg["host"],
        token=fgt_cfg["api_token"],
        vdom=fgt_cfg.get("vdom", "root"),
    )

    addr_results = api.create_address_objects(vpn_cfg)

    return {
        "fortigate_host": fgt_cfg["host"],
        "address_objects_result": addr_results,
    }