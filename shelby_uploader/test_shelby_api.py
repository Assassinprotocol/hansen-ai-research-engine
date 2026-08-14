import os
from dotenv import load_dotenv
import requests

load_dotenv("/home/hansen/AI/hansen_engine/.env")
api_key = os.getenv("SHELBY_API_KEY")
print(f"API Key starts with: {api_key[:5] if api_key else 'None'}...")

url = "https://api.shelbynet.shelby.xyz/v1/accounts/0x85fdb9a176ab8ef1d9d9c1b60d60b3924f0800ac1de1cc2085fb0b8bb4988e6a/module/blob_metadata"
headers1 = {"Authorization": f"Bearer {api_key}"}
headers2 = {"x-api-key": api_key}
headers3 = {"api_key": api_key}

for name, h in [("Bearer", headers1), ("x-api-key", headers2), ("api_key", headers3)]:
    r = requests.get(url, headers=h)
    print(f"Testing {name}: {r.status_code} {r.text}")
