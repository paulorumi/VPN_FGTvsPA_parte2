#!/usr/bin/env python3
import requests
import urllib3
import yaml
from pathlib import Path

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

BASE_DIR = Path(__file__).resolve().parents[1]
CONFIG_PATH = BASE_DIR / "config" / "vpn_params_example.yaml"


def load_yaml(path: Path) -> dict:
    with open(path, "r") as f:
        return yaml.safe_load(f)


def main():
    cfg = load_yaml(CONFIG_PATH)
    pa_cfg = cfg["paloalto"]

    host = pa_cfg["host"]
    api_key = pa_cfg["api_key"]

    url = f"https://{host}/api/"
    params = {
        "type": "op",
        "cmd": "<show><system><info></info></system></show>",
        "key": api_key,
    }

    resp = requests.get(url, params=params, verify=False, timeout=10)
    print("Status Code:", resp.status_code)
    print("Body (primeiros 500 chars):")
    print(resp.text[:500])


if __name__ == "__main__":
    main()