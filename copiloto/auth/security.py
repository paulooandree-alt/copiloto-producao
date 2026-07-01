from __future__ import annotations

import hashlib
import hmac
import os


def gerar_hash_senha(senha: str) -> str:
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", senha.encode("utf-8"), salt, 120_000)
    return f"pbkdf2_sha256$120000${salt.hex()}${digest.hex()}"


def verificar_senha(senha: str, senha_hash: str) -> bool:
    try:
        algoritmo, iteracoes, salt_hex, digest_hex = senha_hash.split("$")
    except ValueError:
        return False

    if algoritmo != "pbkdf2_sha256":
        return False

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        senha.encode("utf-8"),
        bytes.fromhex(salt_hex),
        int(iteracoes),
    )
    return hmac.compare_digest(digest.hex(), digest_hex)
