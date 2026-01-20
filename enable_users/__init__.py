import logging
import azure.functions as func
import os
import requests

GRAPH_SCOPE = "https://graph.microsoft.com/.default"
GRAPH_BASE = "https://graph.microsoft.com/v1.0"

def get_env(name: str) -> str:
    val = os.environ.get(name)
    if not val:
        raise KeyError(f"Variável de ambiente ausente: {name}")
    return val

def get_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    token_url = f"https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
    resp = requests.post(
        token_url,
        data={
            "client_id": client_id,
            "scope": GRAPH_SCOPE,
            "client_secret": client_secret,
            "grant_type": "client_credentials",
        },
        timeout=30,
    )
    logging.info(f"[token] status={resp.status_code}")
    if resp.status_code != 200:
        logging.error(f"[token] body={resp.text}")
        raise RuntimeError("Falha ao obter token do Microsoft Graph")
    token = resp.json().get("access_token")
    if not token:
        logging.error(f"[token] body-sem-access_token={resp.text}")
        raise RuntimeError("Resposta de token sem access_token")
    return token

def iter_group_members(headers: dict, group_id: str):
    # Sem @odata.type no $select (não permitido pela API)
    url = f"{GRAPH_BASE}/groups/{group_id}/members?$select=id,userPrincipalName"
    while url:
        resp = requests.get(url, headers=headers, timeout=30)
        logging.info(f"[members] GET status={resp.status_code}")
        if resp.status_code != 200:
            logging.error(f"[members] body={resp.text}")
            raise RuntimeError("Falha ao listar membros do grupo")

        data = resp.json()
        for obj in data.get("value", []):
            # Filtrar somente usuários
            if obj.get("@odata.type") == "#microsoft.graph.user":
                yield obj

        url = data.get("@odata.nextLink")

def set_account_enabled(headers: dict, user_id: str, enabled: bool) -> int:
    url = f"{GRAPH_BASE}/users/{user_id}"
    resp = requests.patch(
        url,
        headers={**headers, "Content-Type": "application/json"},
        json={"accountEnabled": enabled},
        timeout=30,
    )
    if resp.status_code not in (200, 204):
        logging.error(f"[patch] user={user_id} status={resp.status_code} body={resp.text}")
    return resp.status_code

def main(mytimer: func.TimerRequest):
    try:
        logging.info("== Iniciando enable_users ==")

        tenant_id = get_env("TENANT_ID")
        client_id = get_env("CLIENT_ID")
        client_secret = get_env("CLIENT_SECRET")
        group_id = get_env("TARGET_GROUP_ID")
        logging.info("Variáveis de ambiente carregadas.")

        token = get_token(tenant_id, client_id, client_secret)
        headers = {"Authorization": f"Bearer {token}"}

        logging.info(f"Buscando membros do grupo {group_id}...")
        count = 0
        for user in iter_group_members(headers, group_id):
            uid = user["id"]
            upn = user.get("userPrincipalName", "desconhecido")
            status = set_account_enabled(headers, uid, enabled=True)
            logging.info(f"[enable] {upn} ({uid}) -> status={status}")
            count += 1

        logging.info(f"Concluído. {count} usuário(s) processado(s) para desbloqueio.")

    except Exception as e:
        logging.exception(f"ERRO na enable_users: {e}")
