#!/usr/bin/env python3
import json
from pathlib import Path

import requests
import urllib3
import yaml

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Caminhos
SCRIPTS_DIR = Path(__file__).resolve().parent          # .../scripts
BASE_DIR = SCRIPTS_DIR.parent                          # .../VPN_FGTvsPA
CONFIG_PATH = BASE_DIR / "config" / "vpn_params_example.yaml"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f) or {}


class FortiAPI:
    def __init__(self, host: str, token: str, vdom: str = "root"):
        self.host = host
        self.token = token
        self.vdom = vdom
        self.base_url = f"https://{host}/api/v2"
        print(f"[FGT] Usando base_url: {self.base_url} (vdom={vdom})")

    # ----------- helper HTTP ----------- #

    def _request(self, method: str, path: str, params=None, data=None):
        url = f"{self.base_url}{path}"
        headers = {"Authorization": f"Bearer {self.token}"}
        params = params or {}
        if self.vdom:
            params.setdefault("vdom", self.vdom)

        resp = requests.request(
            method=method,
            url=url,
            headers=headers,
            params=params,
            json=data,
            verify=False,
            timeout=15,
        )
        return resp

    # ----------- Address objects ----------- #

    def address_get(self, name: str):
        return self._request("GET", f"/cmdb/firewall/address/{name}")

    def address_create(self, name: str, cidr: str):
        ip, mask = cidr.split("/")
        subnet = f"{ip} {self._cidr_to_netmask(int(mask))}"
        payload = {
            "name": name,
            "type": "ipmask",
            "subnet": subnet,
        }
        return self._request("POST", "/cmdb/firewall/address", data=payload)

    def address_update(self, name: str, cidr: str):
        ip, mask = cidr.split("/")
        subnet = f"{ip} {self._cidr_to_netmask(int(mask))}"
        payload = {
            "name": name,
            "type": "ipmask",
            "subnet": subnet,
        }
        return self._request("PUT", f"/cmdb/firewall/address/{name}", data=payload)

    def ensure_address(self, name: str, cidr: str):
        resp_get = self.address_get(name)
        if resp_get.status_code == 200:
            print(
                f"[FGT] Address {name} já existe, fazendo UPDATE (PUT) -> {cidr} "
                f"({self._cidr_to_netmask(int(cidr.split('/')[-1]))})"
            )
            resp = self.address_update(name, cidr)
        else:
            print(
                f"[FGT] Criando address {name} -> {cidr} "
                f"({self._cidr_to_netmask(int(cidr.split('/')[-1]))})"
            )
            resp = self.address_create(name, cidr)

        if resp.status_code != 200:
            print(f"[FGT] ERRO ao aplicar address {name}: status {resp.status_code}")
            print(resp.text)
        else:
            print(f"[FGT] Address {name} aplicado com sucesso (status {resp.status_code}).")

    # ----------- Phase1-interface ----------- #

    def phase1_get(self, name: str):
        return self._request("GET", f"/cmdb/vpn.ipsec/phase1-interface/{name}")

    def phase1_create_or_update(
        self,
        name: str,
        interface: str,
        remote_gw: str,
        proposal: str,
        dhgrp: int,
        psk: str,
    ):
        payload = {
            "name": name,
            "interface": interface,
            "peertype": "any",
            "net-device": "disable",
            "proposal": proposal,
            "dpd": "disable",
            "dhgrp": dhgrp,
            "remote-gw": remote_gw,
            "psksecret": psk,
        }

        exists = self.phase1_get(name).status_code == 200
        if exists:
            print(f"[FGT] Phase1-interface {name} já existe, atualizando (PUT).")
            resp = self._request("PUT", f"/cmdb/vpn.ipsec/phase1-interface/{name}", data=payload)
        else:
            print(f"[FGT] Criando Phase1-interface {name} (POST).")
            resp = self._request("POST", "/cmdb/vpn.ipsec/phase1-interface", data=payload)

        print(f"[FGT] Resposta Phase1: {resp.status_code} / {resp.text}")
        if resp.status_code == 200:
            print(f"[FGT] Phase1-interface '{name}' aplicada com sucesso.")
        else:
            print("[FGT] ATENÇÃO: erro ao aplicar Phase1-interface.")

    # ----------- Phase2-interface ----------- #

    def phase2_get(self, name: str):
        return self._request("GET", f"/cmdb/vpn.ipsec/phase2-interface/{name}")

    def phase2_create_or_update(
        self,
        name: str,
        phase1name: str,
        proposal: str,
        pfs: bool,
        src_name: str,
        dst_name: str,
    ):
        payload = {
            "name": name,
            "phase1name": phase1name,
            "proposal": proposal,
            "pfs": "enable" if pfs else "disable",
            "src-addr-type": "name",
            "dst-addr-type": "name",
            "src-name": src_name,
            "dst-name": dst_name,
        }

        exists = self.phase2_get(name).status_code == 200
        if exists:
            print(f"[FGT] Phase2-interface {name} já existe, atualizando (PUT).")
            resp = self._request("PUT", f"/cmdb/vpn.ipsec/phase2-interface/{name}", data=payload)
        else:
            print(f"[FGT] Criando Phase2-interface {name} (POST).")
            resp = self._request("POST", "/cmdb/vpn.ipsec/phase2-interface", data=payload)

        print(f"[FGT] Resposta Phase2 {name}: {resp.status_code} / {resp.text}")
        if resp.status_code == 200:
            print(f"[FGT] Phase2-interface '{name}' aplicada com sucesso.")
        else:
            print(f"[FGT] ATENÇÃO: erro ao aplicar Phase2-interface '{name}'.")

    # ----------- Static routes (tenta dstaddr, se falhar usa dst ip/mask) ----------- #

    def ensure_static_route(self, dstaddr_name: str, cidr: str, device: str):
        """
        1) Verifica se já existe rota com dstaddr=<dstaddr_name> e device=<device>.
        2) Se não existir, tenta criar com dstaddr.
        3) Se falhar (datasource error etc.), faz fallback criando rota com dst=<ip> <mask>.
        """
        # 1) Verificar rota existente por dstaddr
        params = {"filter": f"dstaddr=={dstaddr_name}"}
        resp_get = self._request("GET", "/cmdb/router/static", params=params)

        exists = False
        if resp_get.status_code == 200:
            try:
                body = resp_get.json()
                for r in body.get("results", []):
                    if r.get("dstaddr") == dstaddr_name and r.get("device") == device:
                        exists = True
                        break
            except Exception:
                pass

        if exists:
            print(
                f"[FGT] Rota para dstaddr '{dstaddr_name}' via {device} já existe, "
                f"não será recriada."
            )
            return

        # 2) Tentar criar com dstaddr
        print(f"[FGT] Tentando criar rota com dstaddr '{dstaddr_name}' via {device}...")
        payload_dstaddr = {
            "dstaddr": dstaddr_name,
            "device": device,
        }
        resp = self._request("POST", "/cmdb/router/static", data=payload_dstaddr)
        print(
            f"[FGT] Resposta rota (dstaddr={dstaddr_name}): "
            f"{resp.status_code} / {resp.text}"
        )

        if resp.status_code == 200:
            # deu certo, podemos sair
            return

        # 3) Fallback: criar por dst (ip/mask) usando o CIDR
        try:
            ip, mask = cidr.split("/")
            netmask = self._cidr_to_netmask(int(mask))
            dst_field = f"{ip} {netmask}"
        except Exception:
            print(
                f"[FGT] ERRO ao montar dst a partir de CIDR '{cidr}', "
                "rota não será criada."
            )
            return

        print(
            f"[FGT] Fallback: criando rota por dst '{dst_field}' via {device} "
            f"(sem usar dstaddr)."
        )
        payload_dst = {
            "dst": dst_field,
            "device": device,
        }
        resp2 = self._request("POST", "/cmdb/router/static", data=payload_dst)
        print(
            f"[FGT] Resposta rota (dst={dst_field}): "
            f"{resp2.status_code} / {resp2.text}"
        )

    # ----------- Firewall policies ----------- #

    def create_policy_if_absent(
        self,
        name: str,
        srcintf: str,
        dstintf: str,
        srcaddr: str,
        dstaddr: str,
    ):
        resp_get = self._request(
            "GET",
            "/cmdb/firewall/policy",
            params={"filter": f"name=={name}"},
        )
        exists = False
        if resp_get.status_code == 200:
            try:
                body = resp_get.json()
                if body.get("results"):
                    exists = True
            except json.JSONDecodeError:
                pass

        if exists:
            print(f"[FGT] Policy {name} já existe, não será recriada.")
            return

        payload = {
            "name": name,
            "srcintf": [{"name": srcintf}],
            "dstintf": [{"name": dstintf}],
            "srcaddr": [{"name": srcaddr}],
            "dstaddr": [{"name": dstaddr}],
            "action": "accept",
            "schedule": "always",
            "service": [{"name": "ALL"}],
            "logtraffic": "all",
        }
        resp = self._request("POST", "/cmdb/firewall/policy", data=payload)
        print(f"[FGT] Resposta policy {name}: {resp.status_code} / {resp.text}")

    # ----------- util ----------- #

    @staticmethod
    def _cidr_to_netmask(prefix: int) -> str:
        mask = (0xFFFFFFFF << (32 - prefix)) & 0xFFFFFFFF
        return ".".join(str((mask >> (8 * i)) & 0xFF) for i in range(4)[::-1])


def main():
    cfg = load_config()

    fgt_conf = cfg.get("fortigate", {})
    host = fgt_conf.get("host", "192.168.15.101")
    token = fgt_conf.get("api_token", "b8H59b5xrwrhmy0pprzxkHy0jgn8fq")
    vdom = fgt_conf.get("vdom", "root")

    vpn_conf = cfg.get("vpn", {})
    vpn_name = vpn_conf.get("name", "VPN-FGT-PA")
    psk = vpn_conf.get("psk", "admin123")

    # IP WAN do PA visto pelo Fortigate
    remote_gw = vpn_conf.get("remote_gw_fgt", "2.2.2.2")

    ike = vpn_conf.get("ike_phase1", {})
    ipsec = vpn_conf.get("ipsec_phase2", {})
    networks = vpn_conf.get("networks", {})
    pairs = vpn_conf.get("phase2_pairs") or []

    # Se não houver lista de pares, usa site_a/site_b como padrão
    if not pairs:
        site_a = networks.get("site_a", "10.10.10.0/24")
        site_b = networks.get("site_b", "10.20.20.0/24")
        pairs = [
            {
                "fgt_local": site_a,
                "fgt_remote": site_b,
                "pa_local": site_b,
                "pa_remote": site_a,
            }
        ]

    api = FortiAPI(host=host, token=token, vdom=vdom)

    # -------- Address objects para TODOS os pares -------- #
    for idx, pair in enumerate(pairs, start=1):
        fgt_local = pair.get("fgt_local")
        fgt_remote = pair.get("fgt_remote") or pair.get("pa_local")

        if idx == 1:
            local_name = "LAN_SITE_A"
            remote_name = "LAN_SITE_B"
        else:
            local_name = f"LAN_SITE_A_{idx}"
            remote_name = f"LAN_SITE_B_{idx}"

        api.ensure_address(local_name, fgt_local)
        api.ensure_address(remote_name, fgt_remote)

        # guarda os nomes para usar na Phase2 / policies / rotas
        pair["fgt_local_name"] = local_name
        pair["fgt_remote_name"] = remote_name

    # -------- Phase 1 -------- #
    ike_encryption = ike.get("encryption", "des")
    ike_integrity = ike.get("integrity", "sha1")
    ike_dh = ike.get("dh_group", 2)
    proposal_p1 = f"{ike_encryption}-{ike_integrity}"

    print("[FGT] Configurando Phase1-interface...")
    print(f"       - Nome: {vpn_name}")
    print("       - Interface WAN: port1")
    print(f"       - Remote GW: {remote_gw}")
    print(f"       - Proposta IKE: {proposal_p1}")
    print(f"       - DH Group: {ike_dh}")

    api.phase1_create_or_update(
        name=vpn_name,
        interface="port1",
        remote_gw=remote_gw,
        proposal=proposal_p1,
        dhgrp=ike_dh,
        psk=psk,
    )

    # -------- Phase 2 (uma por par) -------- #
    ipsec_enc = ipsec.get("encryption", "des")
    ipsec_int = ipsec.get("integrity", "sha1")
    ipsec_pfs = ipsec.get("pfs", False)
    proposal_p2 = f"{ipsec_enc}-{ipsec_int}"

    for idx, pair in enumerate(pairs, start=1):
        if idx == 1:
            p2_name = f"{vpn_name}_P2"
        else:
            p2_name = f"{vpn_name}_P2_{idx}"

        src_name = pair["fgt_local_name"]
        dst_name = pair["fgt_remote_name"]

        print("[FGT] Configurando Phase2-interface...")
        print(f"       - Nome: {p2_name}")
        print(f"       - Phase1name: {vpn_name}")
        print(f"       - Proposta IPSec: {proposal_p2}")
        print(f"       - PFS: {'enable' if ipsec_pfs else 'disable'}")
        print(f"       - src-name: {src_name}")
        print(f"       - dst-name: {dst_name}")

        api.phase2_create_or_update(
            name=p2_name,
            phase1name=vpn_name,
            proposal=proposal_p2,
            pfs=ipsec_pfs,
            src_name=src_name,
            dst_name=dst_name,
        )

    # -------- Rotas estáticas para cada rede remota -------- #
    print("[FGT] Garantindo rotas estáticas para todas as redes remotas...")
    used_remote_names = set()
    for pair in pairs:
        remote_name = pair["fgt_remote_name"]
        if remote_name in used_remote_names:
            continue
        used_remote_names.add(remote_name)

        cidr_remote = pair["fgt_remote"]
        print("[FGT] Criando/checando rota estática para LAN remota...")
        print(f"       - dstaddr: {remote_name} (cidr {cidr_remote})")
        print(f"       - Device: {vpn_name}")
        api.ensure_static_route(dstaddr_name=remote_name, cidr=cidr_remote, device=vpn_name)

    # -------- Policies para cada par (saída LAN -> VPN) -------- #
    print("[FGT] Garantindo policies LAN -> VPN para todos os pares...")
    for idx, pair in enumerate(pairs, start=1):
        if idx == 1:
            pol_name = "POL_VPN_SITEA_TO_SITEB"
            srcaddr = "LAN_SITE_A"
            dstaddr = "LAN_SITE_B"
        else:
            pol_name = f"POL_VPN_SITEA_TO_SITEB_{idx}"
            srcaddr = pair["fgt_local_name"]
            dstaddr = pair["fgt_remote_name"]

        api.create_policy_if_absent(
            name=pol_name,
            srcintf="port2",
            dstintf=vpn_name,
            srcaddr=srcaddr,
            dstaddr=dstaddr,
        )

    # -------- Policy VPN -> port3 (uma vez só) -------- #
    api.create_policy_if_absent(
        name="VPN-IN",
        srcintf=vpn_name,
        dstintf="port3",
        srcaddr="all",
        dstaddr="all",
    )

    print("\n[FGT] Automação Fortigate concluída.")


if __name__ == "__main__":
    main()