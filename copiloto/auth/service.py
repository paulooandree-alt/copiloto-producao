from __future__ import annotations

import sqlite3
from datetime import UTC, datetime

from copiloto.auth.models import Usuario
from copiloto.auth.security import gerar_hash_senha, verificar_senha
from copiloto.core.config import PERFIS
from copiloto.core.database import conectar


def row_para_usuario(row: sqlite3.Row) -> Usuario:
    return Usuario(
        id=int(row["id"]),
        nome=row["nome"],
        email=row["email"],
        perfil=row["perfil"],
        ativo=bool(row["ativo"]),
    )


def autenticar_usuario(email: str, senha: str) -> tuple[bool, Usuario | None, str]:
    email_normalizado = email.strip().lower()
    if not email_normalizado or not senha:
        return False, None, "Informe e-mail e senha."

    with conectar() as conn:
        row = conn.execute(
            "SELECT * FROM usuarios WHERE lower(email) = ? AND ativo = 1",
            (email_normalizado,),
        ).fetchone()

    if not row or not verificar_senha(senha, row["senha_hash"]):
        return False, None, "E-mail ou senha inválidos."

    return True, row_para_usuario(row), "Login realizado com sucesso."


def cadastrar_usuario(nome: str, email: str, senha: str, perfil: str) -> tuple[bool, str]:
    nome = nome.strip()
    email = email.strip().lower()

    if not nome or not email or not senha or not perfil:
        return False, "Preencha todos os campos obrigatórios."
    if perfil not in PERFIS:
        return False, "Perfil inválido."
    if len(senha) < 6:
        return False, "A senha deve ter pelo menos 6 caracteres."

    agora = datetime.now(UTC).isoformat(timespec="seconds")
    try:
        with conectar() as conn:
            conn.execute(
                """
                INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo, criado_em, atualizado_em)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (nome, email, gerar_hash_senha(senha), perfil, agora, agora),
            )
    except sqlite3.IntegrityError:
        return False, "Já existe um usuário cadastrado com este e-mail."

    return True, "Usuário cadastrado com sucesso."


def alterar_senha_usuario(usuario_id: int, senha_atual: str, nova_senha: str, confirmar_senha: str) -> tuple[bool, str]:
    if not senha_atual or not nova_senha or not confirmar_senha:
        return False, "Preencha todos os campos de senha."
    if nova_senha != confirmar_senha:
        return False, "A confirmação da senha não confere."
    if len(nova_senha) < 8:
        return False, "A nova senha deve ter pelo menos 8 caracteres."
    if nova_senha == senha_atual:
        return False, "A nova senha deve ser diferente da senha atual."

    with conectar() as conn:
        row = conn.execute(
            "SELECT senha_hash FROM usuarios WHERE id = ? AND ativo = 1",
            (usuario_id,),
        ).fetchone()

        if not row:
            return False, "Usuário não encontrado ou inativo."
        if not verificar_senha(senha_atual, row["senha_hash"]):
            return False, "Senha atual incorreta."

        agora = datetime.now(UTC).isoformat(timespec="seconds")
        conn.execute(
            """
            UPDATE usuarios
            SET senha_hash = ?, atualizado_em = ?
            WHERE id = ?
            """,
            (gerar_hash_senha(nova_senha), agora, usuario_id),
        )

    return True, "Senha alterada com sucesso."


def listar_usuarios() -> list[Usuario]:
    with conectar() as conn:
        rows = conn.execute(
            """
            SELECT id, nome, email, perfil, ativo
            FROM usuarios
            ORDER BY nome
            """
        ).fetchall()
    return [row_para_usuario(row) for row in rows]
