import requests

PA_IP = "192.168.15.60"
API_KEY = "LUFRPT0xSW5SeVpTaVVNWE9ySmdISFhnS1ZxWVl2Um89UHh4anZLakxZclpKeW43Ly82anljS1R0QVBiZUlmRCtscFlpSlBqWFZPNHU0aWFpeHVEbUpvQnhxZ1BUdkxFUg=="

headers = {
    "X-PAN-KEY": API_KEY
}

url = f"https://{PA_IP}/restapi/v10.0/Objects/Addresses?location=vsys&vsys=vsys1"

response = requests.get(url, headers=headers, verify=False)

print("Status Code:", response.status_code)
print("Response:", response.text)