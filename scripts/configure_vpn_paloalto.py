#!/usr/bin/env python3
import sys
from pathlib import Path

import requests
import urllib3
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Caminhos
SCRIPTS_DIR = Path(__file__).resolve().parent        # .../scripts
BASE_DIR = SCRIPTS_DIR.parent                        # .../VPN_FGTvsPA
CONFIG_PATH = BASE_DIR / "config" / "vpn_params_example.yaml"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {}


class PaloAltoAPI:
    def __init__(self, host: str, api_key: str):
        self.host = host
        self.api_key = api_key
        self.base_url = f"https://{host}/api/"
        print(f"[PA] Usando base_url: {self.base_url}")

    def _request(self, params: dict):
        params = dict(params)
        params["key"] = self.api_key
        resp = requests.get(
            self.base_url,
            params=params,
            verify=False,
            timeout=20,
        )
        return resp

    # ---------- helpers de alto nível ---------- #

    def op_show_system_info(self):
        params = {
            "type": "op",
            "cmd": "<show><system><info></info></system></show>",
        }
        resp = self._request(params)
        print(f"[PA] show system info -> {resp.status_code}")
        if resp.text:
            print(resp.text[:250])
        return resp

    def set_config(self, xpath: str, element: str):
        params = {
            "type": "config",
            "action": "set",
            "xpath": xpath,
            "element": element,
        }
        resp = self._request(params)
        return resp

    def commit(self):
        params = {
            "type": "commit",
            "cmd": "<commit></commit>",
        }
        resp = self._request(params)
        return resp

    # ---------- Objetos de endereço ---------- #

    def set_address_object(self, vsys: str, name: str, cidr: str):
        xpath = (
            "/config/devices/entry[@name='localhost.localdomain']"
            f"/vsys/entry[@name='{vsys}']/address/entry[@name='{name}']"
        )
        element = f"<ip-netmask>{cidr}</ip-netmask>"
        resp = self.set_config(xpath, element)
        print(f"[PA] Resposta address {name}: {resp.status_code} / {resp.text}")
        return resp

    # ---------- Interface de túnel + zona + VR ---------- #

    def set_tunnel_interface(self, tunnel_if: str, vsys: str, zone_vpn: str, vr_name: str):
        # Apenas comentário na interface (IP já está configurado via GUI)
        xpath_if = (
            "/config/devices/entry[@name='localhost.localdomain']"
            f"/network/interface/tunnel/units/entry[@name='{tunnel_if}']"
        )
        element_if = "<comment>VPN-FGT-PA</comment>"
        resp_if = self.set_config(xpath_if, element_if)
        print(f"[PA] Resposta tunnel-if: {resp_if.status_code} / {resp_if.text}")

        # Importar a interface para o VSYS correto
        xpath_vsys_import = (
            "/config/devices/entry[@name='localhost.localdomain']"
            f"/vsys/entry[@name='{vsys}']/import/network/interface"
        )
        element_vsys_import = f"<member>{tunnel_if}</member>"
        resp_vsys_import = self.set_config(xpath_vsys_import, element_vsys_import)
        print(f"[PA] Resposta VR member: {resp_vsys_import.status_code} / {resp_vsys_import.text}")

        # Associar interface à zone "vpn" dentro do vsys1
        xpath_zone_layer3 = (
            "/config/devices/entry[@name='localhost.localdomain']"
            f"/vsys/entry[@name='{vsys}']"
            f"/zone/entry[@name='{zone_vpn}']/network/layer3"
        )
        element_zone_layer3 = f"<member>{tunnel_if}</member>"
        resp_zone_layer3 = self.set_config(xpath_zone_layer3, element_zone_layer3)
        print(f"[PA] Resposta zone member: {resp_zone_layer3.status_code} / {resp_zone_layer3.text}")

        # Adicionar tunnel.1 ao Virtual Router "default"
        xpath_vr = (
            "/config/devices/entry[@name='localhost.localdomain']"
            f"/network/virtual-router/entry[@name='{vr_name}']/interface"
        )
        element_vr = f"<member>{tunnel_if}</member>"
        resp_vr = self.set_config(xpath_vr, element_vr)
        print(f"[PA] Resposta VR interface: {resp_vr.status_code} / {resp_vr.text}")

    # ---------- IKE Gateway ---------- #

    def set_ike_gateway(
        self,
        name: str,
        external_if: str,
        peer_ip: str,
        psk: str,
    ):
        xpath = (
            "/config/devices/entry[@name='localhost.localdomain']"
            f"/network/ike/gateway/entry[@name='{name}']"
        )

        # NÃO mandamos <ip> local, só a interface (como no seu lab)
        element = f"""
        <authentication>
          <pre-shared-key>
            <key>{psk}</key>
          </pre-shared-key>
        </authentication>
        <protocol>
          <ikev1>
            <ike-crypto-profile>default</ike-crypto-profile>
          </ikev1>
        </protocol>
        <local-address>
          <interface>{external_if}</interface>
        </local-address>
        <peer-address>
          <ip>{peer_ip}</ip>
        </peer-address>
        """

        resp = self.set_config(xpath, element)
        print(f"[PA] Resposta IKE Gateway: {resp.status_code} / {resp.text}")
        return resp

    # ---------- IPSec Tunnel com múltiplos proxy-IDs ---------- #

    def set_ipsec_tunnel_with_proxies(
        self,
        tunnel_name: str,
        tunnel_if: str,
        ike_gateway_name: str,
        pairs: list,
    ):
        """
        pairs: lista de dicts com chaves 'pa_local' e 'pa_remote'
        Gera múltiplos <proxy-id><entry ...>...</entry></proxy-id>
        """
        proxy_entries = []
        for idx, pair in enumerate(pairs, start=1):
            local_cidr = pair["pa_local"]
            remote_cidr = pair["pa_remote"]

            if idx == 1:
                proxy_name = tunnel_name
            else:
                proxy_name = f"{tunnel_name}_{idx}"

            # IMPORTANTE: protocolo em formato <protocol><any/></protocol>
            proxy_xml = (
                f"<entry name='{proxy_name}'>"
                f"<protocol><any/></protocol>"
                f"<local>{local_cidr}</local>"
                f"<remote>{remote_cidr}</remote>"
                f"</entry>"
            )
            proxy_entries.append(proxy_xml)

        proxy_block = "<proxy-id>" + "".join(proxy_entries) + "</proxy-id>"

        auto_key = (
            "<auto-key>"
            "<ike-gateway>"
            f"<entry name='{ike_gateway_name}'/>"
            "</ike-gateway>"
            "<ipsec-crypto-profile>default</ipsec-crypto-profile>"
            f"{proxy_block}"
            "</auto-key>"
        )

        element = (
            f"<tunnel-interface>{tunnel_if}</tunnel-interface>"
            f"{auto_key}"
        )

        xpath = (
            "/config/devices/entry[@name='localhost.localdomain']"
            f"/network/tunnel/ipsec/entry[@name='{tunnel_name}']"
        )
        resp = self.set_config(xpath, element)
        print(f"[PA] Resposta IPSec Tunnel: {resp.status_code} / {resp.text}")
        return resp

    # ---------- Rotas estáticas ---------- #

    def set_static_route(self, vr_name: str, route_name: str, dst_cidr: str, tunnel_if: str):
        xpath = (
            "/config/devices/entry[@name='localhost.localdomain']"
            f"/network/virtual-router/entry[@name='{vr_name}']"
            f"/routing-table/ip/static-route/entry[@name='{route_name}']"
        )
        element = (
            f"<destination>{dst_cidr}</destination>"
            f"<interface>{tunnel_if}</interface>"
        )
        resp = self.set_config(xpath, element)
        print(f"[PA] Resposta Static Route {route_name}: {resp.status_code} / {resp.text}")
        return resp

    # ---------- Security Policy ---------- #

    def set_security_policy_pair(
        self,
        vsys: str,
        rule_name: str,
        from_zone: str,
        to_zone: str,
        src_addr: str,
        dst_addr: str,
    ):
        xpath = (
            "/config/devices/entry[@name='localhost.localdomain']"
            f"/vsys/entry[@name='{vsys}']"
            f"/rulebase/security/rules/entry[@name='{rule_name}']"
        )
        element = f"""
        <from><member>{from_zone}</member></from>
        <to><member>{to_zone}</member></to>
        <source><member>{src_addr}</member></source>
        <destination><member>{dst_addr}</member></destination>
        <source-user><member>any</member></source-user>
        <category><member>any</member></category>
        <application><member>any</member></application>
        <service><member>any</member></service>
        <action>allow</action>
        """

        resp = self.set_config(xpath, element)
        print(f"[PA] Resposta Security Policy {rule_name}: {resp.status_code} / {resp.text}")
        return resp


def main():
    cfg = load_config()

    pa_conf = cfg.get("paloalto", {})
    host = pa_conf.get("host", "192.168.15.60")
    api_key = pa_conf.get("api_key")
    vsys = pa_conf.get("vsys", "vsys1")
    external_if = pa_conf.get("external_if", "ethernet1/1")
    tunnel_if = pa_conf.get("tunnel_if", "tunnel.1")
    zone_lan = pa_conf.get("zone_lan", "vpn")   # lado LAN (siteB)
    zone_vpn = pa_conf.get("zone_vpn", "vpn")   # zona onde está o túnel
    vr_name = pa_conf.get("virtual_router", "default")

    vpn_conf = cfg.get("vpn", {})
    vpn_name = vpn_conf.get("name", "VPN-FGT-PA")
    psk = vpn_conf.get("psk", "admin123")

    # Do ponto de vista do PA, o peer é o Fortigate
    peer_ip = vpn_conf.get("remote_gw_pa", "1.1.1.1")

    networks = vpn_conf.get("networks", {})
    pairs = vpn_conf.get("phase2_pairs") or []

    # Se não tiver phase2_pairs no YAML, usa site_a/site_b padrão
    if not pairs:
        site_a = networks.get("site_a", "10.10.10.0/24")  # Fortigate
        site_b = networks.get("site_b", "10.20.20.0/24")  # Palo Alto
        pairs = [
            {
                "fgt_local": site_a,
                "fgt_remote": site_b,
                "pa_local": site_b,
                "pa_remote": site_a,
            }
        ]

    pa = PaloAltoAPI(host, api_key)

    # Teste simples da API
    print("[PA] Testando API com 'show system info'...")
    pa.op_show_system_info()

    # -------- Address objects (para todos os pares) -------- #
    for idx, pair in enumerate(pairs, start=1):
        pa_local = pair["pa_local"]
        pa_remote = pair["pa_remote"]

        if idx == 1:
            a_local_name = "LAN_SITE_B"      # siteB = lado Palo Alto
            a_remote_name = "LAN_SITE_A"     # siteA = lado Fortigate
        else:
            a_local_name = f"LAN_SITE_B_{idx}"
            a_remote_name = f"LAN_SITE_A_{idx}"

        pa.set_address_object(vsys, a_local_name, pa_local)
        pa.set_address_object(vsys, a_remote_name, pa_remote)

        pair["pa_local_name"] = a_local_name
        pair["pa_remote_name"] = a_remote_name

    # -------- Interface de túnel, zona e VR -------- #
    print(f"[PA] Configurando interface de túnel {tunnel_if} com IP 169.255.1.2/30")
    pa.set_tunnel_interface(tunnel_if=tunnel_if, vsys=vsys, zone_vpn=zone_vpn, vr_name=vr_name)

    # -------- IKE Gateway -------- #
    print("[PA] Configurando IKE Gateway (toFGT)...")
    pa.set_ike_gateway(
        name="toFGT",
        external_if=external_if,
        peer_ip=peer_ip,
        psk=psk,
    )

    # -------- IPSec Tunnel com múltiplos Proxy IDs -------- #
    print("[PA] Configurando IPSec Tunnel (toFGT)...")
    pa.set_ipsec_tunnel_with_proxies(
        tunnel_name="toFGT",
        tunnel_if=tunnel_if,
        ike_gateway_name="toFGT",
        pairs=pairs,
    )

    # -------- Rotas estáticas para TODAS as redes remotas (lado FGT) -------- #
    print("[PA] Criando/atualizando rotas estáticas para redes do Fortigate...")
    used_remotes = set()
    for idx, pair in enumerate(pairs, start=1):
        remote_cidr = pair["pa_remote"]
        if remote_cidr in used_remotes:
            continue
        used_remotes.add(remote_cidr)

        if idx == 1:
            route_name = "route-to-siteA"
        else:
            route_name = f"route-to-siteA_{idx}"

        pa.set_static_route(
            vr_name=vr_name,
            route_name=route_name,
            dst_cidr=remote_cidr,
            tunnel_if=tunnel_if,
        )

    # -------- Security Policies (uma por par) -------- #
    print("[PA] Criando/atualizando security policies LAN (siteB) -> LAN (siteA)...")
    for idx, pair in enumerate(pairs, start=1):
        if idx == 1:
            rule_name = "VPN_SITEB_TO_SITEA"
        else:
            rule_name = f"VPN_SITEB_TO_SITEA_{idx}"

        src_obj = pair["pa_local_name"]
        dst_obj = pair["pa_remote_name"]
        pa.set_security_policy_pair(
            vsys=vsys,
            rule_name=rule_name,
            from_zone=zone_lan,
            to_zone=zone_vpn,
            src_addr=src_obj,
            dst_addr=dst_obj,
        )

    # -------- Commit -------- #
    print("[PA] Executando commit...")
    resp_commit = pa.commit()
    print(f"[PA] Resposta commit: {resp_commit.status_code} / {resp_commit.text}")

    print("\n[PA] Automação Palo Alto concluída.")


if __name__ == "__main__":
    sys.exit(main())