from __future__ import annotations

import tempfile
import unittest
from datetime import time
from pathlib import Path

import app


class CopilotoProducaoTest(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.base = Path(self.tmp.name)
        self.original_data_dir = app.DATA_DIR
        self.original_outputs_dir = app.OUTPUTS_DIR
        self.original_db_path = app.DB_PATH
        self.original_csv_path = app.CSV_LEGADO_PATH

        app.DATA_DIR = self.base / "data"
        app.OUTPUTS_DIR = self.base / "outputs"
        app.DB_PATH = app.DATA_DIR / "teste.db"
        app.CSV_LEGADO_PATH = app.DATA_DIR / "producao_diaria.csv"
        app.DATA_DIR.mkdir()
        app.limpar_cache()

    def tearDown(self) -> None:
        app.limpar_cache()
        app.DATA_DIR = self.original_data_dir
        app.OUTPUTS_DIR = self.original_outputs_dir
        app.DB_PATH = self.original_db_path
        app.CSV_LEGADO_PATH = self.original_csv_path
        self.tmp.cleanup()

    def test_migra_csv_legado_para_sqlite(self) -> None:
        app.CSV_LEGADO_PATH.write_text(
            "data,linha,turno,produto,producao_planejada,producao_realizada,horas_trabalhadas,observacoes\n"
            "2026-06-20,Linha 1,1o Turno,Produto A,100,95,8,Teste\n",
            encoding="utf-8",
        )

        app.preparar_ambiente()
        registros = app.carregar_producao()

        self.assertEqual(len(registros), 1)
        self.assertEqual(registros[0]["turno"], "1º Turno")
        self.assertEqual(registros[0]["producao_realizada"], 95)

    def test_evitar_producao_duplicada(self) -> None:
        app.preparar_ambiente()
        registro = {
            "data": "2026-06-20",
            "linha": "Linha 1",
            "turno": "1º Turno",
            "produto": "Produto A",
            "producao_planejada": 100,
            "producao_realizada": 98,
            "pecas_boas": 97,
            "pecas_reprovadas": 1,
            "horas_trabalhadas": 8,
            "tempo_planejado_horas": 8,
            "observacoes": "",
        }

        sucesso_1, _ = app.inserir_producao(registro)
        sucesso_2, mensagem = app.inserir_producao(registro)

        self.assertTrue(sucesso_1)
        self.assertFalse(sucesso_2)
        self.assertIn("duplicado", mensagem.lower())

    def test_calcula_oee(self) -> None:
        indicadores = app.calcular_indicadores_registro(
            {
                "producao_planejada": 100,
                "producao_realizada": 90,
                "pecas_boas": 85,
                "pecas_reprovadas": 5,
                "horas_trabalhadas": 7,
                "tempo_planejado_horas": 8,
            }
        )

        self.assertAlmostEqual(indicadores["disponibilidade"], 87.5)
        self.assertAlmostEqual(indicadores["performance"], 90.0)
        self.assertAlmostEqual(indicadores["qualidade"], 94.444444, places=4)
        self.assertAlmostEqual(indicadores["oee"], 74.375, places=3)

    def test_duracao_de_parada(self) -> None:
        self.assertEqual(app.minutos_entre(time(8, 0), time(9, 15)), 75)
        self.assertEqual(app.minutos_entre(time(9, 15), time(8, 0)), 0)

    def test_exportacoes_basicas(self) -> None:
        producao = [
            {
                "data": "2026-06-20",
                "linha": "Linha 1",
                "turno": "1º Turno",
                "produto": "Produto A",
                "producao_planejada": 100,
                "producao_realizada": 98,
                "pecas_boas": 97,
                "pecas_reprovadas": 1,
                "horas_trabalhadas": 8,
                "tempo_planejado_horas": 8,
                "observacoes": "Ok",
            }
        ]
        abas = {"Produção": (app.COLUNAS_PRODUCAO, producao, app.mapa_producao())}

        self.assertTrue(app.registros_para_csv(producao, app.COLUNAS_PRODUCAO, app.mapa_producao()).startswith(b"\xef\xbb\xbf"))
        self.assertTrue(app.gerar_xlsx(abas).startswith(b"PK"))
        self.assertTrue(app.gerar_pdf_texto("Teste", ["Linha 1"]).startswith(b"%PDF"))

    def test_limpa_dados_sem_remigrar_csv_legado(self) -> None:
        app.CSV_LEGADO_PATH.write_text(
            "data,linha,turno,produto,producao_planejada,producao_realizada,horas_trabalhadas,observacoes\n"
            "2026-06-20,Linha 1,1o Turno,Produto A,100,95,8,Teste\n",
            encoding="utf-8",
        )
        app.preparar_ambiente()
        self.assertEqual(len(app.carregar_producao()), 1)

        sucesso, mensagem = app.limpar_todos_os_dados()
        self.assertTrue(sucesso, mensagem)
        app.preparar_ambiente()

        self.assertEqual(app.contar_registros()["produção"], 0)
        self.assertEqual(len(app.carregar_producao()), 0)


if __name__ == "__main__":
    unittest.main()
