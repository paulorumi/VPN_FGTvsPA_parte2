from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.services.fortigate_vpn import apply_fortigate_vpn
from backend.services.paloalto_vpn import apply_paloalto_vpn
from backend.services.connectivity_test import test_vpn_connectivity

app = FastAPI(title="VPN FGT vs PA Automation API")

# permitir acesso simples do frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # em produção, restringir
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/vpn/fortigate/apply")
def api_apply_fortigate_vpn():
    result = apply_fortigate_vpn()
    return result


@app.post("/vpn/paloalto/apply")
def api_apply_paloalto_vpn():
    result = apply_paloalto_vpn()
    return result


@app.post("/vpn/test-connectivity")
def api_test_connectivity(dst_host: str = "10.20.20.1"):
    return test_vpn_connectivity(dst_host)