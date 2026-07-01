from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from copiloto.auth.security import gerar_hash_senha, verificar_senha
from copiloto.auth.service import autenticar_usuario, cadastrar_usuario, listar_usuarios
from copiloto.core import config
from copiloto.core import database


class CopilotoSaasFoundationTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.original_data_dir = config.DATA_DIR
        self.original_db_path = config.DB_PATH
        self.original_database_data_dir = database.DATA_DIR
        self.original_database_db_path = database.DB_PATH

        temp_dir = Path(self.tmp.name)
        config.DATA_DIR = temp_dir / "data"
        config.DB_PATH = config.DATA_DIR / "teste_saas.db"
        database.DATA_DIR = config.DATA_DIR
        database.DB_PATH = config.DB_PATH

    def tearDown(self) -> None:
        config.DATA_DIR = self.original_data_dir
        config.DB_PATH = self.original_db_path
        database.DATA_DIR = self.original_database_data_dir
        database.DB_PATH = self.original_database_db_path
        self.tmp.cleanup()

    def test_inicializa_banco_com_admin_padrao(self) -> None:
        database.inicializar_banco()

        sucesso, usuario, mensagem = autenticar_usuario(
            config.ADMIN_EMAIL_PADRAO,
            config.ADMIN_SENHA_PADRAO,
        )

        self.assertTrue(sucesso, mensagem)
        self.assertIsNotNone(usuario)
        self.assertEqual(usuario.perfil, "Administrador")

    def test_hash_de_senha_nao_guarda_texto_puro(self) -> None:
        senha_hash = gerar_hash_senha("senha123")

        self.assertNotIn("senha123", senha_hash)
        self.assertTrue(verificar_senha("senha123", senha_hash))
        self.assertFalse(verificar_senha("errada", senha_hash))

    def test_cadastra_usuario_sem_duplicidade(self) -> None:
        database.inicializar_banco()

        sucesso, _ = cadastrar_usuario("Supervisor", "sup@empresa.com", "senha123", "Supervisor")
        repetido, mensagem = cadastrar_usuario("Supervisor", "sup@empresa.com", "senha123", "Supervisor")
        usuarios = listar_usuarios()

        self.assertTrue(sucesso)
        self.assertFalse(repetido)
        self.assertIn("existe", mensagem.lower())
        self.assertEqual(len([u for u in usuarios if u.email == "sup@empresa.com"]), 1)

    def test_rejeita_perfil_invalido(self) -> None:
        database.inicializar_banco()

        sucesso, mensagem = cadastrar_usuario("Teste", "teste@empresa.com", "senha123", "Diretor")

        self.assertFalse(sucesso)
        self.assertIn("perfil", mensagem.lower())


if __name__ == "__main__":
    unittest.main()
