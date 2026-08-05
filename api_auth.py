"""
Autenticação da API JSON (usada pelo conector MCP) — separada do login por
sessão do site. Token JWT assinado com CR_API_SECRET (env var própria,
diferente da SECRET_KEY do Flask), validade ~30 dias — a mesma janela do
access token do conector, para não expirar no meio de uma sessão de uso.
"""
import os
import time

import jwt

_SECRET = os.environ.get("CR_API_SECRET", "")
_TTL = 30 * 24 * 3600


def emitir_token(usuario):
    agora = int(time.time())
    payload = {
        "uid": usuario["id"],
        "nome": usuario["nome"],
        "papel": usuario["papel"],
        "iat": agora,
        "exp": agora + _TTL,
    }
    return jwt.encode(payload, _SECRET, algorithm="HS256")


def verificar_token(token):
    if not _SECRET or not token:
        return None
    try:
        return jwt.decode(token, _SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
