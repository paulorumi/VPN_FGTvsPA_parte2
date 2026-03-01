import yaml
import requests
import urllib3
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parents[2]
CONFIG_PATH = BASE_DIR / "config" / "vpn_params_example.yaml"


def load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


class PaloAltoAPI:
    def __init__(self, host: str, api_key: str):
        self.host = host
        self.api_key = api_key
        self.session = requests.Session()
        self.session.verify = False  # lab only

    def op_cmd(self, cmd: str):
        url = f"https://{self.host}/api/"
        params = {
            "type": "op",
            "cmd": cmd,
            "key": self.api_key,
        }
        resp = self.session.get(url, params=params, timeout=5)
        return resp.status_code, resp.text[:500]


def apply_paloalto_vpn():
    cfg = load_yaml(CONFIG_PATH)
    pa_cfg = cfg["paloalto"]

    api = PaloAltoAPI(
        host=pa_cfg["host"],
        api_key=pa_cfg["api_key"],
    )

    status, body = api.op_cmd("<show><system><info></info></system></show>")

    return {
        "paloalto_host": pa_cfg["host"],
        "show_system_info_status": status,
        "show_system_info_body": body,
        "note": "Automação conceitual. Próximo passo: criar objetos e túnel via XML/REST.",
    }