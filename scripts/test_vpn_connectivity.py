#!/usr/bin/env python3
import subprocess
import json
from datetime import datetime
import sys


def ping(host: str, count: int = 4) -> dict:
    cmd = ["ping", "-c", str(count), host]  # Em Windows, troque -c por -n
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    return {
        "host": host,
        "count": count,
        "return_code": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "success": result.returncode == 0,
    }


def main():
    dst_host = sys.argv[1] if len(sys.argv) > 1 else "10.20.20.1"

    res = ping(dst_host)

    report = {
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "test_type": "vpn_connectivity_ping",
        "result": res,
    }

    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()