import logging
import azure.functions as func
import os
import requests

def main(mytimer: func.TimerRequest):
    logging.info("Iniciando disable_users...")

    tenant_id = os.environ["TENANT_ID"]
    client_id = os.environ["CLIENT_ID"]
    client_secret = os.environ["CLIENT_SECRET"]
    group_id = os.environ["TARGET_GROUP_ID"]

    logging.info("Variáveis carregadas com sucesso.")

    # Obter token do Microsoft Graph
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    logging.info("Solicitando token...")

    token_response = requests.post(token_url, data={
        "client_id": client_id,
        "scope": "https://graph.microsoft.com/.default",
        "client_secret": client_secret,
        "grant_type": "client_credentials"
    })

    logging.info(f"Token status code: {token_response.status_code}")

    token = token_response.json().get("access_token")

    if not token:
        logging.error("Erro ao obter token. Resposta:")
        logging.error(token_response.text)
        return

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    logging.info("Token obtido com sucesso. Buscando membros do grupo...")

    group_url = f"https://graph.microsoft.com/v1.0/groups/{group_id}/members"
    users_response = requests.get(group_url, headers=headers)

    logging.info(f"Status da leitura do grupo: {users_response.status_code}")

    users = users_response.json().get("value", [])

    logging.info(f"{len(users)} usuários encontrados no grupo.")

    for user in users:
        uid = user["id"]
        upn = user.get("userPrincipalName", "desconhecido")

        logging.info(f"Bloqueando usuário: {upn}")

        patch_url = f"https://graph.microsoft.com/v1.0/users/{uid}"

        patch_response = requests.patch(
            patch_url,
            headers=headers,
            json={"accountEnabled": False}
        )

        logging.info(f"Resultado: {patch_response.status_code}")

    logging.info("Execução da função disable_users concluída.")
