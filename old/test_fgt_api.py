#!/usr/bin/env python3
import requests
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

FGT_IP = "192.168.15.101"  # ajuste se o IP de gerência for outro
FGT_PORT = 443
API_TOKEN = "b8H59b5xrwrhmy0pprzxkHy0jgn8fq"

headers = {
    "Authorization": f"Bearer {API_TOKEN}"
}

url = f"https://{FGT_IP}:{FGT_PORT}/api/v2/cmdb/system/interface"


def main():
    try:
        resp = requests.get(url, headers=headers, verify=False, timeout=5)
        print("Status code:", resp.status_code)
        print("Primeiros 500 caracteres da resposta:")
        print(resp.text[:500])
    except requests.exceptions.RequestException as e:
        print("Erro ao conectar no Fortigate via API:")
        print(e)
        print("\nVerifique:")
        print("- Se consegue acessar https://{}:{}/ no navegador;".format(FGT_IP, FGT_PORT))
        print("- Se o usuário admin_api existe em 'config system api-user';")
        print("- Se o token está correto;")
        print("- Se a interface de gerência tem 'https' em allowaccess.")


if __name__ == "__main__":
    main()