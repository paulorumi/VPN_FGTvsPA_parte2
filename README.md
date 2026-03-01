# Automação de VPN Site-to-Site – Fortigate x Palo Alto

Este projeto automatiza a criação de uma VPN IPsec **site-to-site** entre um **Fortigate** (Ponta A) e um **Palo Alto** (Ponta B), usando **Python** e chamadas de API REST/XML.

A aplicação possui:

- **Interface gráfica (Tkinter)** para preencher os parâmetros da VPN  
- Arquivo de configuração em **YAML** (`config/vpn_params_example.yaml`)  
- Dois scripts separados que aplicam a configuração em cada firewall:  
  - `scripts/configure_vpn_fortigate.py`  
  - `scripts/configure_vpn_paloalto.py`  

> 🔎 **Nota:** Esta automação foi desenvolvida com auxílio de uma IA da **OpenAI** (modelo GPT-5.1 Thinking), refinindo scripts, lógica de API e interface.

---

## 1. Requisitos

### 1.1. Ambiente

- Python **3.9+** (recomendado)
- Acesso de rede aos firewalls:
  - Fortigate (FortiOS 7.6.2) - HTTPS + API REST habilitada
  - Palo Alto (PanOS 10.0.0) - API XML/REST habilitada
- Credenciais / chaves:
  - **Fortigate**: token de API com permissão de escrita  
  - **Palo Alto**: **API Key** com permissão de configuração e commit  

### 1.2. Bibliotecas Python

Bibliotecas utilizadas:

- [requests](https://pypi.org/project/requests/)  
- [PyYAML](https://pypi.org/project/PyYAML/)  

As demais são da biblioteca padrão (não precisam ser instaladas separadamente):

- `tkinter` (interface gráfica)
- `subprocess`
- `pathlib`
- `sys`
- `urllib3`
- `json` / `typing` (se usados em versões futuras)

VPN_FGTvsPA/
├─ config/
│  └─ vpn_params_example.yaml      # Arquivo de configuração da VPN (editado pela GUI)
├─ scripts/
│  ├─ configure_vpn_fortigate.py   # Aplica configuração no Fortigate
│  └─ configure_vpn_paloalto.py    # Aplica configuração no Palo Alto
├─ main_gui.py                     # Arquivo principal da interface Tkinter (nome de exemplo)
├─ README.md                       # Este arquivo
└─ requirements.txt                # (opcional) Lista de dependências