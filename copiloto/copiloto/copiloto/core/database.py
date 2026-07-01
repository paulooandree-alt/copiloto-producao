from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Iterator

from copiloto.auth.security import gerar_hash_senha
from copiloto.core.config import DATA_DIR, DB_PATH, obter_credenciais_admin_inicial


@contextmanager
def conectar(db_path: Path | None = None) -> Iterator[sqlite3.Connection]:
    caminho = db_path or DB_PATH
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(caminho)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def inicializar_banco() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    with conectar() as conn:
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS usuarios (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                senha_hash TEXT NOT NULL,
                perfil TEXT NOT NULL CHECK (perfil IN ('Administrador', 'Supervisor', 'Operador')),
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT NOT NULL,
                atualizado_em TEXT NOT NULL
            )
            """
        )
        criar_admin_padrao(conn)


def criar_admin_padrao(conn: sqlite3.Connection) -> None:
    admin_email, admin_senha = obter_credenciais_admin_inicial()
    existe = conn.execute("SELECT id FROM usuarios WHERE email = ?", (admin_email,)).fetchone()
    if existe:
        return

    agora = datetime.now(UTC).isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO usuarios (nome, email, senha_hash, perfil, ativo, criado_em, atualizado_em)
        VALUES (?, ?, ?, 'Administrador', 1, ?, ?)
        """,
        (
            "Administrador",
            admin_email,
            gerar_hash_senha(admin_senha),
            agora,
            agora,
        ),
    )
