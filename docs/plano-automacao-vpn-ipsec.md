```markdown
# Plano de Automação da Configuração de VPN IPSec entre Fortigate e Palo Alto

## 1. Objetivo

Planejar a automação da configuração de uma VPN IPSec entre um firewall Fortigate e um firewall Palo Alto, em ambiente de laboratório PNETLab, documentando:

- Parâmetros da VPN (WAN, LAN, túnel, propostas de Phase 1 e 2);
- Ferramentas e APIs a serem utilizadas;
- Passos lógicos da automação;
- Considerações de automação em ambiente heterogêneo;
- Estratégia de validação da configuração e alertas.

---

## 2. Definição de Parâmetros

### 2.1. Topologia WAN / “Internet”

- **Fortigate**
  - WAN: interface `port1`
  - IP: `1.1.1.1/30`
  - Gateway: `1.1.1.2` (router-internet e0/0)

- **Palo Alto**
  - WAN: interface `ethernet1/1`
  - IP: `2.2.2.2/30`
  - Gateway: `2.2.2.1` (router-internet e0/1)

- **Router-internet**
  - e0/0: `1.1.1.2/30`
  - e0/1: `2.2.2.1/30`

### 2.2. LANs de Exemplo

- LAN Fortigate (Site A): `10.10.10.0/24` (ex.: `port2 = 10.10.10.1/24`)
- LAN Palo Alto (Site B): `10.20.20.0/24` (ex.: `ethernet1/2 = 10.20.20.1/24`)

### 2.3. Rede de Túnel

- Rede de túnel: `169.255.1.0/30`
  - IP do túnel no Fortigate: `169.255.1.1/30`
  - IP do túnel no Palo Alto: `169.255.1.2/30`

### 2.4. Identificadores e Objetos

- Nome da VPN no Fortigate: `VPN-FGT-PA`
- Tunnel interface no Palo Alto: `tunnel.FGT-PA` (ex.: `tunnel.1`)
- Objetos de rede:
  - Fortigate:
    - `LAN_SITE_A = 10.10.10.0/24`
    - `LAN_SITE_B = 10.20.20.0/24`
  - Palo Alto:
    - `obj_LAN_SITE_A = 10.10.10.0/24`
    - `obj_LAN_SITE_B = 10.20.20.0/24`
- PSK: valor definido em variável segura (não versionado no Git).

### 2.5. Propostas de Phase 1 (IKE)

Parâmetros compatíveis entre FortiOS 7.0.5 e PAN-OS 10.0.0:

- Versão IKE: IKEv2
- Autenticação: Pre-shared key
- Criptografia: AES-256
- Integridade: SHA256
- Grupo DH: 14 (2048 bits)
- Lifetime: 28800 segundos
- NAT Traversal: habilitado.

### 2.6. Propostas de Phase 2 (IPSec)

- Protocolo: ESP
- Criptografia: AES-256
- Integridade: SHA256
- PFS: habilitado (DH14)
- Lifetime: 3600 segundos
- Seletores/Sub-redes:
  - Lado Fortigate: local = `10.10.10.0/24`, remota = `10.20.20.0/24`
  - Lado Palo Alto: local = `10.20.20.0/24`, remota = `10.10.10.0/24`

---

## 3. Identificação de Ferramentas/APIs

### 3.1. Linguagem e Bibliotecas

- Linguagem principal: **Python 3**
- Bibliotecas:
  - `requests` – chamadas HTTP/REST
  - `PyYAML` – leitura de arquivos YAML de parâmetros
  - (Opcional) `paramiko` / `netmiko` – acesso SSH/CLI, se desejado

### 3.2. Fortigate (FortiOS 7.0.5)

- API REST do FortiOS:
  - Base: `https://<FGT_IP>/api/v2/`
  - Autenticação: API token
- Endpoints relevantes (exemplos):
  - Objetos de endereço: `/cmdb/firewall/address`
  - Phase 1 interface: `/cmdb/vpn.ipsec/phase1-interface`
  - Phase 2 interface: `/cmdb/vpn.ipsec/phase2-interface`
  - Políticas de firewall: `/cmdb/firewall/policy`
  - Rotas estáticas: `/cmdb/router/static`

### 3.3. Palo Alto (PAN-OS 10.0.0)

- REST API oficial:
  - Base: `https://<PA_IP>/restapi/v10.0/`
  - Autenticação: header `X-PAN-KEY: <API_KEY>`
- Endpoints típicos:
  - Objetos de endereço: `/Objects/Addresses`
  - Tunnel interfaces: `/Network/TunnelInterfaces`
  - IKE Gateways: `/Network/IkeGateways`
  - IPSec Tunnels: `/Network/IPSecTunnels`
  - Security Policies: `/Policies/SecurityRules`
  - Commit: `/Commit`
  - Monitoramento de SA: `/Monitoring/VPN/IkeSa`, `/Monitoring/VPN/IpsecSa`

---
## 4. Passos de Automação

### 4.1. Fluxo Geral do Script

1. Carregar arquivos de parâmetros em `config/` (YAML).
2. Validar parâmetros (IPs, máscaras, redes).
3. Estabelecer conexão com Fortigate (API REST).
4. Estabelecer conexão com Palo Alto (API REST).
5. Criar/atualizar objetos de rede em ambos os firewalls.
6. Configurar IKE Phase 1 em ambos.
7. Configurar IPSec Phase 2 em ambos.
8. Criar/associar interfaces de túnel (IP 169.255.1.1/30 e 169.255.1.2/30).
9. Configurar rotas estáticas para as redes remotas.
10. Criar/ajustar políticas de firewall permitindo tráfego entre `10.10.10.0/24` e `10.20.20.0/24`.
11. Executar commit no Palo Alto e garantir persistência no Fortigate.
12. Validar estado da VPN (SAs IKE/IPSec) via API.
13. Executar testes de conectividade (ping) entre as LANs.
14. Registrar logs e gerar alertas em caso de falha.

### 4.2. Estratégia de Idempotência

- Consultar configuração atual via API antes de criar recursos;
- Somente criar objetos (endereços, túneis, políticas) se não existirem;
- Atualizar apenas recursos divergentes do estado desejado (descritos nos YAMLs);
- Não modificar recursos que já estão em conformidade.

---

## 5. Considerações Específicas

### 5.1. Diferenças de Modelo (Fortigate x Palo Alto)

- Fortigate:
  - CLI baseado em blocos `config/edit/set/next`.
  - Alterações via API são aplicadas diretamente.
- Palo Alto:
  - Modelo baseado em árvore de objetos e **commit** transacional.
  - Necessidade de criar dependências na ordem correta (interface → zone → VR → túnel → policy).

### 5.2. Segurança das Credenciais

- PSK e credenciais (usuário, token, API key) não devem ser versionados no Git.
- Devem ser obtidos via:
  - Variáveis de ambiente;
  - Arquivos de configuração protegidos;
  - Secret manager externo, se disponível.
- Comunicação com APIs sempre via HTTPS (permitindo `verify=False` apenas em lab).

### 5.3. Tratamento de Erros

- Verificar códigos HTTP das respostas das APIs.
- Tratar exceções de tempo de resposta, DNS, SSL e autenticação.
- Em caso de erro crítico:
  - Registrar log detalhado;
  - Retornar código de saída diferente de zero;
  - Evitar continuação da automação sem consistência.

### 5.4. Ambiente Heterogêneo

- Terminologias diferentes:
  - Fortigate: Phase1-interface, Phase2-interface, firewall policy.
  - Palo Alto: IKE Gateway, IPSec Tunnel, Proxy-ID, Security Policy.
- Necessidade de garantir que propostas IKE/IPSec sejam estritamente compatíveis em ambos os lados.
- Commit obrigatório no Palo Alto, opcional no Fortigate (mas recomendado backup).

---

## 6. Validação de Configuração e Alertas

### 6.1. Validação – Fortigate

Comandos (via CLI ou endpoints equivalentes):

- Estado do túnel:
  - `get vpn ipsec tunnel summary`
  - `diagnose vpn tunnel list name VPN-FGT-PA`
- Roteamento:
  - `get router info routing-table all | grep 10.20.20.0`

### 6.2. Validação – Palo Alto

Via CLI:

- `show vpn ike-sa`
- `show vpn ipsec-sa`
- `show routing route | match 10.10.10.0`

Via REST API:

- `GET /restapi/v10.0/Monitoring/VPN/IkeSa`
- `GET /restapi/v10.0/Monitoring/VPN/IpsecSa`

### 6.3. Testes Ativos de Conectividade

- Execução de ping entre as LANs:
  - Do lado Fortigate ou de um host em `10.10.10.0/24` para um host em `10.20.20.0/24`.
  - Do lado Palo Alto ou host em `10.20.20.0/24` para `10.10.10.0/24`.
- Script `test_vpn_connectivity.py`:
  - Recebe IP de destino;
  - Executa `ping`;
  - Gera relatório em JSON.

### 6.4. Alertas

Em caso de:

- Falha na criação de recursos;
- Túnel sem SA ativa;
- Falha no teste de ping;

o sistema deve:

- Registrar log com detalhes (timestamp, dispositivo, tipo de falha);
- (Opcional) Enviar alerta:
  - E-mail;
  - Webhook (Slack/Teams);
  - Integração com sistema de monitoramento (Zabbix, Prometheus, etc.).

---

## 7. Artefatos no Repositório

- `docs/plano-automacao-vpn-ipsec.md` – Este documento.
- `docs/topologia-pnetlab.md` – Topologia e endereçamento.
- `config/vpn_params_example.yaml` – Parâmetros da VPN (exemplo).
- `config/interfaces_example.yaml` – Interfaces físicas/lógicas (exemplo).
- `scripts/configure_vpn.py` – Script conceitual de automação da VPN.
- `scripts/test_vpn_connectivity.py` – Script de teste de conectividade via túnel.