import subprocess
import json
from datetime import datetime


def ping_host(host: str, count: int = 4) -> dict:
    # Em Windows, troque -c por -n se precisar
    cmd = ["ping", "-c", str(count), host]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return {
        "host": host,
        "count": count,
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "success": result.returncode == 0,
    }


def test_vpn_connectivity(dst_host: str = "10.20.20.1"):
    res = ping_host(dst_host)
    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "test_type": "vpn_connectivity_ping",
        "result": res,
    }
    return report