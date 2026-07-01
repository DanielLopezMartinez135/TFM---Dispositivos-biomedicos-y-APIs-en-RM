import requests
import json
import os

ClientID = '7b1c00c28bb5135edce80036f66b15097443466034f3f116dff2cef3e1eb4b9f'
ClientSecret = '0e97b3561c734d1fe339aa1abdd593f1e8b30014c3a35842278dc2c56e3ad6b7'

import requests
import urllib.parse

CLIENT_ID = ClientID
CLIENT_SECRET = ClientSecret
CALLBACK_HOST = "localhost"
CALLBACK_PORT = 8765
CALLBACK_PATH = "/callback"
REDIRECT_URI = f"http://{CALLBACK_HOST}:{CALLBACK_PORT}{CALLBACK_PATH}"
AUTH_CODE = ""


auth_params = {
    "response_type": "code",
    "client_id": CLIENT_ID,
    "scope": "user.info,user.metrics",
    "redirect_uri": REDIRECT_URI,
    "state": "random_string"
}

auth_url = "https://account.withings.com/oauth2_user/authorize2?" + urllib.parse.urlencode(auth_params)

print(auth_url)

AUTH_CODE = input("auth_token: ")

token_url = "https://wbsapi.withings.net/v2/oauth2"

data = {
    "action": "requesttoken",
    "grant_type": "authorization_code",
    "client_id": CLIENT_ID,
    "client_secret": CLIENT_SECRET,
    "code": AUTH_CODE,
    "redirect_uri": REDIRECT_URI
}

response = requests.post(
    token_url,
    data=data,
    headers={"Accept": "application/json"},
    timeout=30
)

print("Status:", response.status_code)

try:
    tokens = response.json()
except Exception:
    raise RuntimeError(f"La respuesta no es JSON válido: {response.text}")

print("Tokens:", tokens)

if "body" not in tokens or "access_token" not in tokens["body"]:
    raise RuntimeError(f"No se obtuvo access_token. Respuesta: {tokens}")

access_token = tokens["body"]["access_token"]
refresh_token = tokens["body"]["refresh_token"]

api_url = "https://wbsapi.withings.net/measure"

headers = {
    "Authorization": f"Bearer {access_token}"
}

params = {
    "action": "getmeas",
    "meastype": [1,9,10,11]
}

response = requests.get(api_url, headers=headers, params=params, timeout=30)

print("Status:", response.status_code)
print("Response text:", response.text)

respuesta = response.json()

print(respuesta['body']['measuregrps'][1]['measures'])

# print(f"Peso: {respuesta['body']['measuregrps'][0]['measures'][0]['value'] * (10 ** respuesta['body']['measuregrps'][0]['measures'][0]['unit'])} Kg")

# for i in respuesta['body']['measuregrps']:
#     print(f"Medida: {i["measures"]}")