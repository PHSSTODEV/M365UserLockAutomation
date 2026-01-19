import logging
import azure.functions as func
import os
import requests

def main(mytimer: func.TimerRequest):
    tenant_id = os.environ["TENANT_ID"]
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]
    group_id = os.environ["TARGET_GROUP_ID"]

    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    result = requests.post(token_url, data={
        "client_id": client_id,
        "scope": "https://graph.microsoft.com/.default",
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    }).json()

    token = result["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    users = requests.get(
        f"https://graph.microsoft.com/v1.0/groups/{group_id}/members",
        headers=headers
    ).json()

    for user in users.get("value", []):
        uid = user["id"]
        requests.patch(
            f"https://graph.microsoft.com/v1.0/users/{uid}",
            headers={**headers, "Content-Type": "application/json"},
            json={"accountEnabled": True}
        )
        logging.info(f"Usuário desbloqueado: {user['userPrincipalName']}")

    logging.info("Desbloqueio executado às 08h.")
