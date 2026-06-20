from __future__ import annotations

import csv
import io
import sqlite3
import zipfile
from collections import defaultdict
from contextlib import contextmanager
from datetime import date, datetime, time
from html import escape
from pathlib import Path
from xml.sax.saxutils import escape as xml_escape

import plotly.graph_objects as go
import streamlit as st


APP_TITLE = "Copiloto de Produção"
DATA_DIR = Path("data")
OUTPUTS_DIR = Path("outputs")
DB_PATH = DATA_DIR / "copiloto_producao.db"
CSV_LEGADO_PATH = DATA_DIR / "producao_diaria.csv"

TURNOS = ["1º Turno", "2º Turno", "3º Turno", "Geral"]
TIPOS_PARADA = [
    "Manutenção",
    "Falta de Matéria-Prima",
    "Troca de Produto",
    "Limpeza",
    "Falha Operacional",
    "Outros",
]
STATUS_OCORRENCIA = ["Aberto", "Em andamento", "Resolvido"]

COLUNAS_PRODUCAO = [
    "data",
    "linha",
    "turno",
    "produto",
    "produção_planejada",
    "produção_realizada",
    "peças_boas",
    "peças_reprovadas",
    "horas_trabalhadas",
    "tempo_planejado_horas",
    "observações",
]
COLUNAS_PARADAS = [
    "data",
    "turno",
    "linha",
    "tipo_parada",
    "hora_inicial",
    "hora_final",
    "duração_minutos",
    "observação",
]
COLUNAS_OCORRENCIAS = [
    "data",
    "turno",
    "responsável",
    "ocorrência",
    "status",
]


def preparar_ambiente() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    OUTPUTS_DIR.mkdir(exist_ok=True)
    inicializar_banco()
    migrar_csv_legado()


@contextmanager
def conectar():
    conn = sqlite3.connect(DB_PATH)
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
    DATA_DIR.mkdir(exist_ok=True)
    with conectar() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS producao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                linha TEXT NOT NULL,
                turno TEXT NOT NULL,
                produto TEXT NOT NULL,
                producao_planejada REAL NOT NULL,
                producao_realizada REAL NOT NULL,
                pecas_boas REAL NOT NULL,
                pecas_reprovadas REAL NOT NULL,
                horas_trabalhadas REAL NOT NULL,
                tempo_planejado_horas REAL NOT NULL,
                observacoes TEXT,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(data, linha, turno, produto)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS paradas (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                turno TEXT NOT NULL,
                linha TEXT NOT NULL,
                tipo_parada TEXT NOT NULL,
                hora_inicial TEXT NOT NULL,
                hora_final TEXT NOT NULL,
                duracao_minutos REAL NOT NULL,
                observacao TEXT,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(data, turno, linha, tipo_parada, hora_inicial, hora_final)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ocorrencias (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                data TEXT NOT NULL,
                turno TEXT NOT NULL,
                responsavel TEXT NOT NULL,
                ocorrencia TEXT NOT NULL,
                status TEXT NOT NULL,
                criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(data, turno, responsavel, ocorrencia)
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_config (
                chave TEXT PRIMARY KEY,
                valor TEXT NOT NULL
            )
            """
        )


def normalizar_turno(valor: str) -> str:
    mapa = {
        "1o Turno": "1º Turno",
        "2o Turno": "2º Turno",
        "3o Turno": "3º Turno",
    }
    return mapa.get(valor, valor or "Geral")


def numero(valor: str | int | float | None) -> float:
    if valor in (None, ""):
        return 0.0
    try:
        return float(str(valor).replace(",", "."))
    except ValueError:
        return 0.0


def migrar_csv_legado() -> None:
    if obter_config("csv_legado_migrado") == "1":
        return

    if not CSV_LEGADO_PATH.exists():
        return

    with conectar() as conn:
        with CSV_LEGADO_PATH.open("r", newline="", encoding="utf-8") as arquivo:
            reader = csv.DictReader(arquivo)
            for row in reader:
                realizada = numero(row.get("producao_realizada"))
                horas = numero(row.get("horas_trabalhadas"))
                if not row.get("data") or not row.get("linha") or not row.get("produto"):
                    continue
                conn.execute(
                    """
                    INSERT OR IGNORE INTO producao (
                        data, linha, turno, produto, producao_planejada,
                        producao_realizada, pecas_boas, pecas_reprovadas,
                        horas_trabalhadas, tempo_planejado_horas, observacoes
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        row.get("data"),
                        row.get("linha", "").strip(),
                        normalizar_turno(row.get("turno", "").strip()),
                        row.get("produto", "").strip(),
                        numero(row.get("producao_planejada")),
                        realizada,
                        realizada,
                        0.0,
                        horas,
                        horas,
                        row.get("observacoes", "").strip(),
                    ),
                )
        conn.execute(
            """
            INSERT INTO app_config (chave, valor)
            VALUES ('csv_legado_migrado', '1')
            ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
            """
        )


def obter_config(chave: str) -> str | None:
    with conectar() as conn:
        row = conn.execute(
            "SELECT valor FROM app_config WHERE chave = ?",
            (chave,),
        ).fetchone()
    return row["valor"] if row else None


def definir_config(chave: str, valor: str) -> None:
    with conectar() as conn:
        conn.execute(
            """
            INSERT INTO app_config (chave, valor)
            VALUES (?, ?)
            ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
            """,
            (chave, valor),
        )


def linhas_para_dicts(rows: list[sqlite3.Row]) -> list[dict]:
    return [dict(row) for row in rows]


@st.cache_data(show_spinner=False)
def carregar_producao() -> list[dict]:
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM producao ORDER BY data DESC, linha, turno"
        ).fetchall()
    registros = linhas_para_dicts(rows)
    for item in registros:
        item.update(calcular_indicadores_registro(item))
    return registros


@st.cache_data(show_spinner=False)
def carregar_paradas() -> list[dict]:
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM paradas ORDER BY data DESC, linha, hora_inicial"
        ).fetchall()
    return linhas_para_dicts(rows)


@st.cache_data(show_spinner=False)
def carregar_ocorrencias() -> list[dict]:
    with conectar() as conn:
        rows = conn.execute(
            "SELECT * FROM ocorrencias ORDER BY data DESC, turno, status"
        ).fetchall()
    return linhas_para_dicts(rows)


def limpar_cache() -> None:
    carregar_producao.clear()
    carregar_paradas.clear()
    carregar_ocorrencias.clear()


def inserir_producao(registro: dict) -> tuple[bool, str]:
    try:
        with conectar() as conn:
            conn.execute(
                """
                INSERT INTO producao (
                    data, linha, turno, produto, producao_planejada,
                    producao_realizada, pecas_boas, pecas_reprovadas,
                    horas_trabalhadas, tempo_planejado_horas, observacoes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    registro["data"],
                    registro["linha"],
                    registro["turno"],
                    registro["produto"],
                    registro["producao_planejada"],
                    registro["producao_realizada"],
                    registro["pecas_boas"],
                    registro["pecas_reprovadas"],
                    registro["horas_trabalhadas"],
                    registro["tempo_planejado_horas"],
                    registro["observacoes"],
                ),
            )
        limpar_cache()
        return True, "Produção registrada com sucesso."
    except sqlite3.IntegrityError:
        return False, "Registro duplicado: já existe produção para esta data, linha, turno e produto."
    except sqlite3.Error as erro:
        return False, f"Erro ao salvar a produção: {erro}"


def inserir_parada(registro: dict) -> tuple[bool, str]:
    try:
        with conectar() as conn:
            conn.execute(
                """
                INSERT INTO paradas (
                    data, turno, linha, tipo_parada, hora_inicial, hora_final,
                    duracao_minutos, observacao
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    registro["data"],
                    registro["turno"],
                    registro["linha"],
                    registro["tipo_parada"],
                    registro["hora_inicial"],
                    registro["hora_final"],
                    registro["duracao_minutos"],
                    registro["observacao"],
                ),
            )
        limpar_cache()
        return True, "Parada registrada com sucesso."
    except sqlite3.IntegrityError:
        return False, "Registro duplicado: esta parada já foi lançada."
    except sqlite3.Error as erro:
        return False, f"Erro ao salvar a parada: {erro}"


def inserir_ocorrencia(registro: dict) -> tuple[bool, str]:
    try:
        with conectar() as conn:
            conn.execute(
                """
                INSERT INTO ocorrencias (
                    data, turno, responsavel, ocorrencia, status
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    registro["data"],
                    registro["turno"],
                    registro["responsavel"],
                    registro["ocorrencia"],
                    registro["status"],
                ),
            )
        limpar_cache()
        return True, "Ocorrência registrada com sucesso."
    except sqlite3.IntegrityError:
        return False, "Registro duplicado: esta ocorrência já existe."
    except sqlite3.Error as erro:
        return False, f"Erro ao salvar a ocorrência: {erro}"


def contar_registros() -> dict[str, int]:
    with conectar() as conn:
        return {
            "produção": conn.execute("SELECT COUNT(*) FROM producao").fetchone()[0],
            "paradas": conn.execute("SELECT COUNT(*) FROM paradas").fetchone()[0],
            "ocorrências": conn.execute("SELECT COUNT(*) FROM ocorrencias").fetchone()[0],
        }


def limpar_todos_os_dados() -> tuple[bool, str]:
    try:
        with conectar() as conn:
            conn.execute("DELETE FROM ocorrencias")
            conn.execute("DELETE FROM paradas")
            conn.execute("DELETE FROM producao")
            conn.execute("DELETE FROM sqlite_sequence WHERE name IN ('producao', 'paradas', 'ocorrencias')")
            conn.execute(
                """
                INSERT INTO app_config (chave, valor)
                VALUES ('csv_legado_migrado', '1')
                ON CONFLICT(chave) DO UPDATE SET valor = excluded.valor
                """
            )
        limpar_cache()
        return True, "Todos os dados foram limpos com sucesso."
    except sqlite3.Error as erro:
        return False, f"Erro ao limpar os dados: {erro}"


def data_iso_para_date(valor: str) -> date | None:
    try:
        return datetime.strptime(valor, "%Y-%m-%d").date()
    except ValueError:
        return None


def minutos_entre(hora_inicial: time, hora_final: time) -> float:
    inicio = datetime.combine(date.today(), hora_inicial)
    fim = datetime.combine(date.today(), hora_final)
    if fim <= inicio:
        return 0.0
    return (fim - inicio).total_seconds() / 60


def calcular_indicadores_registro(item: dict) -> dict:
    planejada = numero(item.get("producao_planejada"))
    realizada = numero(item.get("producao_realizada"))
    boas = numero(item.get("pecas_boas"))
    reprovadas = numero(item.get("pecas_reprovadas"))
    horas = numero(item.get("horas_trabalhadas"))
    tempo_planejado = numero(item.get("tempo_planejado_horas"))
    total_qualidade = boas + reprovadas

    disponibilidade = horas / tempo_planejado * 100 if tempo_planejado > 0 else 0
    performance = realizada / planejada * 100 if planejada > 0 else 0
    qualidade = boas / total_qualidade * 100 if total_qualidade > 0 else 0
    oee = disponibilidade * performance * qualidade / 10000
    produtividade = realizada / horas if horas > 0 else 0

    return {
        "eficiencia": performance,
        "produtividade": produtividade,
        "disponibilidade": disponibilidade,
        "performance": performance,
        "qualidade": qualidade,
        "oee": oee,
    }


def calcular_resumo(registros: list[dict]) -> dict:
    planejada = sum(numero(item.get("producao_planejada")) for item in registros)
    realizada = sum(numero(item.get("producao_realizada")) for item in registros)
    boas = sum(numero(item.get("pecas_boas")) for item in registros)
    reprovadas = sum(numero(item.get("pecas_reprovadas")) for item in registros)
    horas = sum(numero(item.get("horas_trabalhadas")) for item in registros)
    tempo_planejado = sum(numero(item.get("tempo_planejado_horas")) for item in registros)
    total_qualidade = boas + reprovadas

    disponibilidade = horas / tempo_planejado * 100 if tempo_planejado > 0 else 0
    performance = realizada / planejada * 100 if planejada > 0 else 0
    qualidade = boas / total_qualidade * 100 if total_qualidade > 0 else 0
    oee = disponibilidade * performance * qualidade / 10000

    return {
        "produção_planejada": planejada,
        "produção_realizada": realizada,
        "eficiência_média": performance,
        "horas_trabalhadas": horas,
        "produtividade": realizada / horas if horas > 0 else 0,
        "disponibilidade": disponibilidade,
        "performance": performance,
        "qualidade": qualidade,
        "oee": oee,
    }


def cor_indicador(valor: float) -> str:
    if valor >= 95:
        return "#1f8f4d"
    if valor >= 90:
        return "#b7791f"
    return "#c53030"


def status_indicador(valor: float) -> str:
    if valor >= 95:
        return "Acima da meta"
    if valor >= 90:
        return "Atenção"
    return "Crítico"


def formatar_numero(valor: float) -> str:
    return f"{valor:,.0f}".replace(",", ".")


def formatar_decimal(valor: float) -> str:
    return f"{valor:.1f}".replace(".", ",")


def formatar_percentual(valor: float) -> str:
    return f"{formatar_decimal(valor)}%"


def renderizar_css() -> None:
    st.markdown(
        """
        <style>
        .block-container { padding-top: 1.4rem; padding-bottom: 2rem; }
        div[data-testid="stMetric"] {
            border: 1px solid #d8dee8;
            border-radius: 8px;
            padding: 14px 16px;
            background: #ffffff;
            min-height: 112px;
        }
        .kpi-card {
            border: 1px solid #d8dee8;
            border-left-width: 6px;
            border-radius: 8px;
            padding: 14px 16px;
            background: #ffffff;
            min-height: 124px;
        }
        .kpi-label { color: #475569; font-size: 0.88rem; margin-bottom: 8px; }
        .kpi-value { color: #0f172a; font-size: 1.55rem; font-weight: 700; }
        .kpi-status { color: #475569; font-size: 0.82rem; margin-top: 8px; }
        .section-note { color: #64748b; font-size: 0.92rem; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def kpi_card(titulo: str, valor: str, referencia: float | None = None) -> None:
    cor = cor_indicador(referencia) if referencia is not None else "#2563eb"
    status = status_indicador(referencia) if referencia is not None else "Indicador operacional"
    st.markdown(
        f"""
        <div class="kpi-card" style="border-left-color:{cor}">
            <div class="kpi-label">{escape(titulo)}</div>
            <div class="kpi-value">{escape(valor)}</div>
            <div class="kpi-status">{escape(status)}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_cabecalho() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    renderizar_css()
    st.title(APP_TITLE)
    st.caption("Gestão diária da produção, eficiência, paradas, ocorrências e OEE.")


def filtrar_producao(registros: list[dict]) -> list[dict]:
    if not registros:
        return registros

    st.sidebar.header("Filtros")
    datas_validas = [
        data_iso_para_date(item["data"]) for item in registros if data_iso_para_date(item["data"])
    ]
    data_min = min(datas_validas) if datas_validas else date.today()
    data_max = max(datas_validas) if datas_validas else date.today()
    periodo = st.sidebar.date_input(
        "Período",
        value=(data_min, data_max),
        min_value=data_min,
        max_value=data_max,
    )

    linhas = sorted({item["linha"] for item in registros if item["linha"]})
    turnos = sorted({item["turno"] for item in registros if item["turno"]})
    produtos = sorted({item["produto"] for item in registros if item["produto"]})

    linhas_sel = st.sidebar.multiselect("Linhas", linhas, default=linhas)
    turnos_sel = st.sidebar.multiselect("Turnos", turnos, default=turnos)
    produtos_sel = st.sidebar.multiselect("Produtos", produtos, default=produtos)

    filtrados = []
    for item in registros:
        data_item = data_iso_para_date(item["data"])
        if len(periodo) == 2 and data_item:
            inicio, fim = periodo
            if data_item < inicio or data_item > fim:
                continue
        if linhas_sel and item["linha"] not in linhas_sel:
            continue
        if turnos_sel and item["turno"] not in turnos_sel:
            continue
        if produtos_sel and item["produto"] not in produtos_sel:
            continue
        filtrados.append(item)
    return filtrados


def validar_texto(valor: str, campo: str) -> str | None:
    if not valor or not valor.strip():
        return f"O campo {campo} é obrigatório."
    return None


def renderizar_formulario_producao() -> None:
    st.subheader("Lançamento de Produção")
    st.markdown('<p class="section-note">Registre a produção consolidada por data, linha, turno e produto.</p>', unsafe_allow_html=True)

    with st.form("form_producao", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            data_registro = st.date_input("Data", value=date.today())
            linha = st.text_input("Linha de produção", placeholder="Ex.: Linha 1")
            horas_trabalhadas = st.number_input(
                "Horas trabalhadas", min_value=0.0, max_value=24.0, step=0.5, value=8.0
            )
        with col2:
            turno = st.selectbox("Turno", TURNOS)
            produto = st.text_input("Produto", placeholder="Ex.: Produto A")
            tempo_planejado = st.number_input(
                "Tempo planejado (h)", min_value=0.0, max_value=24.0, step=0.5, value=8.0
            )
        with col3:
            producao_planejada = st.number_input("Produção planejada", min_value=0.0, step=1.0)
            producao_realizada = st.number_input("Produção realizada", min_value=0.0, step=1.0)
            pecas_reprovadas = st.number_input("Peças reprovadas", min_value=0.0, step=1.0)

        pecas_boas = st.number_input(
            "Peças boas",
            min_value=0.0,
            step=1.0,
            value=max(0.0, producao_realizada - pecas_reprovadas),
        )
        observacoes = st.text_area("Observações", placeholder="Informe desvios, restrições ou comentários relevantes.")
        enviado = st.form_submit_button("Salvar produção", type="primary")

    if not enviado:
        return

    erros = [
        validar_texto(linha, "Linha de produção"),
        validar_texto(produto, "Produto"),
    ]
    if producao_planejada <= 0:
        erros.append("A produção planejada deve ser maior que zero.")
    if producao_realizada < 0 or horas_trabalhadas <= 0 or tempo_planejado <= 0:
        erros.append("Horas e produção devem ter valores válidos.")
    if pecas_boas + pecas_reprovadas == 0:
        erros.append("Informe peças boas ou peças reprovadas para calcular a qualidade.")
    erros = [erro for erro in erros if erro]

    if erros:
        for erro in erros:
            st.error(erro)
        return

    sucesso, mensagem = inserir_producao(
        {
            "data": data_registro.isoformat(),
            "linha": linha.strip(),
            "turno": turno,
            "produto": produto.strip(),
            "producao_planejada": producao_planejada,
            "producao_realizada": producao_realizada,
            "pecas_boas": pecas_boas,
            "pecas_reprovadas": pecas_reprovadas,
            "horas_trabalhadas": horas_trabalhadas,
            "tempo_planejado_horas": tempo_planejado,
            "observacoes": observacoes.strip(),
        }
    )
    (st.success if sucesso else st.error)(mensagem)
    if sucesso:
        st.rerun()


def renderizar_dashboard(registros: list[dict]) -> None:
    st.subheader("Dashboard Executivo")
    if not registros:
        st.info("Ainda não há dados de produção para exibir.")
        return

    resumo = calcular_resumo(registros)
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        kpi_card("Produção Planejada", formatar_numero(resumo["produção_planejada"]))
    with col2:
        kpi_card("Produção Realizada", formatar_numero(resumo["produção_realizada"]), resumo["eficiência_média"])
    with col3:
        kpi_card("Eficiência Média", formatar_percentual(resumo["eficiência_média"]), resumo["eficiência_média"])
    with col4:
        kpi_card("Horas Trabalhadas", f'{formatar_decimal(resumo["horas_trabalhadas"])} h')
    with col5:
        kpi_card("Produtividade", f'{formatar_decimal(resumo["produtividade"])} un/h')

    renderizar_graficos_producao(registros)


def agrupar_soma(registros: list[dict], chave: str) -> list[dict]:
    grupos = defaultdict(lambda: {"planejada": 0.0, "realizada": 0.0, "horas": 0.0})
    for item in registros:
        nome = item.get(chave) or "Sem informação"
        grupos[nome]["planejada"] += numero(item.get("producao_planejada"))
        grupos[nome]["realizada"] += numero(item.get("producao_realizada"))
        grupos[nome]["horas"] += numero(item.get("horas_trabalhadas"))

    saida = []
    for nome, totais in grupos.items():
        eficiencia = totais["realizada"] / totais["planejada"] * 100 if totais["planejada"] else 0
        saida.append(
            {
                chave: nome,
                "produção_planejada": totais["planejada"],
                "produção_realizada": totais["realizada"],
                "horas_trabalhadas": totais["horas"],
                "eficiência": eficiencia,
            }
        )
    return saida


def renderizar_graficos_producao(registros: list[dict]) -> None:
    st.subheader("Gráficos de Desempenho")
    por_dia = sorted(agrupar_soma(registros, "data"), key=lambda item: item["data"])
    por_linha = sorted(
        agrupar_soma(registros, "linha"),
        key=lambda item: item["produção_realizada"],
        reverse=True,
    )

    col1, col2 = st.columns(2)
    with col1:
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=[i["data"] for i in por_dia], y=[i["produção_planejada"] for i in por_dia], mode="lines+markers", name="Planejada"))
        fig.add_trace(go.Scatter(x=[i["data"] for i in por_dia], y=[i["produção_realizada"] for i in por_dia], mode="lines+markers", name="Realizada"))
        fig.update_layout(title="Produção Planejada x Realizada", xaxis_title="Data", yaxis_title="Quantidade")
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        cores = [cor_indicador(item["eficiência"]) for item in por_linha]
        fig = go.Figure(go.Bar(x=[i["linha"] for i in por_linha], y=[i["eficiência"] for i in por_linha], marker_color=cores, text=[formatar_percentual(i["eficiência"]) for i in por_linha], textposition="outside"))
        fig.update_layout(title="Eficiência por Linha", xaxis_title="Linha", yaxis_title="Eficiência (%)", yaxis_range=[0, max(110, max([i["eficiência"] for i in por_linha], default=0) * 1.15)])
        st.plotly_chart(fig, use_container_width=True)

    col3, col4 = st.columns(2)
    with col3:
        fig = go.Figure()
        fig.add_trace(go.Bar(x=[i["linha"] for i in por_linha], y=[i["produção_planejada"] for i in por_linha], name="Planejada"))
        fig.add_trace(go.Bar(x=[i["linha"] for i in por_linha], y=[i["produção_realizada"] for i in por_linha], name="Realizada"))
        fig.update_layout(title="Produção por Linha", xaxis_title="Linha", yaxis_title="Quantidade", barmode="group")
        st.plotly_chart(fig, use_container_width=True)

    with col4:
        fig = go.Figure(go.Scatter(x=[i["horas_trabalhadas"] for i in registros], y=[i["producao_realizada"] for i in registros], mode="markers", text=[f'{i["data"]} | {i["linha"]} | {i["produto"]} | {formatar_percentual(i["eficiencia"])}' for i in registros], hoverinfo="text+x+y"))
        fig.update_layout(title="Produção por Horas Trabalhadas", xaxis_title="Horas trabalhadas", yaxis_title="Produção realizada")
        st.plotly_chart(fig, use_container_width=True)


def renderizar_paradas(paradas: list[dict]) -> None:
    st.subheader("Gestão de Paradas")
    with st.form("form_parada", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            data_parada = st.date_input("Data", value=date.today(), key="data_parada")
            turno = st.selectbox("Turno", TURNOS, key="turno_parada")
            linha = st.text_input("Linha", placeholder="Ex.: Linha 1", key="linha_parada")
        with col2:
            tipo = st.selectbox("Tipo de parada", TIPOS_PARADA)
            hora_inicial = st.time_input("Hora inicial", value=time(8, 0))
            hora_final = st.time_input("Hora final", value=time(8, 30))
        with col3:
            duracao = minutos_entre(hora_inicial, hora_final)
            st.metric("Duração automática", f"{formatar_decimal(duracao)} min")
            observacao = st.text_area("Observação")
        enviado = st.form_submit_button("Salvar parada", type="primary")

    if enviado:
        erros = [validar_texto(linha, "Linha")]
        if duracao <= 0:
            erros.append("A hora final deve ser maior que a hora inicial.")
        erros = [erro for erro in erros if erro]
        if erros:
            for erro in erros:
                st.error(erro)
        else:
            sucesso, mensagem = inserir_parada(
                {
                    "data": data_parada.isoformat(),
                    "turno": turno,
                    "linha": linha.strip(),
                    "tipo_parada": tipo,
                    "hora_inicial": hora_inicial.strftime("%H:%M"),
                    "hora_final": hora_final.strftime("%H:%M"),
                    "duracao_minutos": duracao,
                    "observacao": observacao.strip(),
                }
            )
            (st.success if sucesso else st.error)(mensagem)
            if sucesso:
                st.rerun()

    renderizar_tabela("Histórico de Paradas", paradas, COLUNAS_PARADAS)
    if paradas:
        por_tipo = defaultdict(float)
        for item in paradas:
            por_tipo[item["tipo_parada"]] += numero(item["duracao_minutos"])
        fig = go.Figure(go.Bar(x=list(por_tipo.keys()), y=list(por_tipo.values()), marker_color="#2563eb"))
        fig.update_layout(title="Tempo de Parada por Tipo", xaxis_title="Tipo de parada", yaxis_title="Minutos")
        st.plotly_chart(fig, use_container_width=True)


def renderizar_ocorrencias(ocorrencias: list[dict]) -> None:
    st.subheader("Ocorrências de Turno")
    with st.form("form_ocorrencia", clear_on_submit=True):
        col1, col2, col3 = st.columns(3)
        with col1:
            data_ocorrencia = st.date_input("Data", value=date.today(), key="data_ocorrencia")
            turno = st.selectbox("Turno", TURNOS, key="turno_ocorrencia")
        with col2:
            responsavel = st.text_input("Responsável")
            status = st.selectbox("Status", STATUS_OCORRENCIA)
        with col3:
            ocorrencia = st.text_area("Ocorrência")
        enviado = st.form_submit_button("Salvar ocorrência", type="primary")

    if enviado:
        erros = [
            validar_texto(responsavel, "Responsável"),
            validar_texto(ocorrencia, "Ocorrência"),
        ]
        erros = [erro for erro in erros if erro]
        if erros:
            for erro in erros:
                st.error(erro)
        else:
            sucesso, mensagem = inserir_ocorrencia(
                {
                    "data": data_ocorrencia.isoformat(),
                    "turno": turno,
                    "responsavel": responsavel.strip(),
                    "ocorrencia": ocorrencia.strip(),
                    "status": status,
                }
            )
            (st.success if sucesso else st.error)(mensagem)
            if sucesso:
                st.rerun()

    renderizar_tabela("Histórico de Ocorrências", ocorrencias, COLUNAS_OCORRENCIAS)


def renderizar_oee(registros: list[dict]) -> None:
    st.subheader("OEE")
    if not registros:
        st.info("Registre produção para calcular Disponibilidade, Performance, Qualidade e OEE.")
        return

    resumo = calcular_resumo(registros)
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        kpi_card("Disponibilidade", formatar_percentual(resumo["disponibilidade"]), resumo["disponibilidade"])
    with col2:
        kpi_card("Performance", formatar_percentual(resumo["performance"]), resumo["performance"])
    with col3:
        kpi_card("Qualidade", formatar_percentual(resumo["qualidade"]), resumo["qualidade"])
    with col4:
        kpi_card("OEE Final", formatar_percentual(resumo["oee"]), resumo["oee"])

    por_linha = sorted(
        agrupar_oee_por_linha(registros),
        key=lambda item: item["oee"],
        reverse=True,
    )
    fig = go.Figure()
    fig.add_trace(go.Bar(x=[i["linha"] for i in por_linha], y=[i["disponibilidade"] for i in por_linha], name="Disponibilidade"))
    fig.add_trace(go.Bar(x=[i["linha"] for i in por_linha], y=[i["performance"] for i in por_linha], name="Performance"))
    fig.add_trace(go.Bar(x=[i["linha"] for i in por_linha], y=[i["qualidade"] for i in por_linha], name="Qualidade"))
    fig.add_trace(go.Scatter(x=[i["linha"] for i in por_linha], y=[i["oee"] for i in por_linha], mode="lines+markers", name="OEE Final"))
    fig.update_layout(title="OEE por Linha", xaxis_title="Linha", yaxis_title="Percentual (%)", barmode="group")
    st.plotly_chart(fig, use_container_width=True)


def agrupar_oee_por_linha(registros: list[dict]) -> list[dict]:
    grupos = defaultdict(list)
    for item in registros:
        grupos[item["linha"]].append(item)
    saida = []
    for linha, itens in grupos.items():
        resumo = calcular_resumo(itens)
        saida.append({"linha": linha, **resumo})
    return saida


def renderizar_tabela(titulo: str, registros: list[dict], colunas: list[str]) -> None:
    st.subheader(titulo)
    if not registros:
        st.info("Nenhum registro encontrado.")
        return
    html = ["<table style='width:100%; border-collapse:collapse;'>"]
    html.append("<thead><tr>")
    for coluna in colunas:
        html.append(f"<th style='border-bottom:1px solid #cbd5e1; text-align:left; padding:8px;'>{escape(coluna.replace('_', ' ').title())}</th>")
    html.append("</tr></thead><tbody>")
    for item in registros:
        html.append("<tr>")
        for coluna in colunas:
            chave = coluna.replace("produção", "producao").replace("duração", "duracao").replace("observação", "observacao").replace("observações", "observacoes").replace("peças", "pecas")
            valor = item.get(chave, item.get(coluna, ""))
            if isinstance(valor, float):
                valor = formatar_decimal(valor)
            html.append(f"<td style='border-bottom:1px solid #e2e8f0; padding:8px;'>{escape(str(valor))}</td>")
        html.append("</tr>")
    html.append("</tbody></table>")
    st.markdown("".join(html), unsafe_allow_html=True)


def registros_para_csv(registros: list[dict], colunas: list[str], mapa: dict[str, str] | None = None) -> bytes:
    mapa = mapa or {}
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(colunas)
    for item in registros:
        writer.writerow([item.get(mapa.get(coluna, coluna), "") for coluna in colunas])
    return buffer.getvalue().encode("utf-8-sig")


def gerar_xlsx(abas: dict[str, tuple[list[str], list[dict], dict[str, str]]]) -> bytes:
    shared_strings: list[str] = []
    shared_index: dict[str, int] = {}

    def shared(value: str) -> int:
        if value not in shared_index:
            shared_index[value] = len(shared_strings)
            shared_strings.append(value)
        return shared_index[value]

    def col_ref(index: int) -> str:
        resultado = ""
        index += 1
        while index:
            index, resto = divmod(index - 1, 26)
            resultado = chr(65 + resto) + resultado
        return resultado

    sheets_xml = []
    workbook_sheets = []
    rels = []
    for sheet_id, (nome, (colunas, registros, mapa)) in enumerate(abas.items(), start=1):
        rows = []
        linhas = [colunas]
        for item in registros:
            linhas.append([item.get(mapa.get(coluna, coluna), "") for coluna in colunas])
        for row_index, linha in enumerate(linhas, start=1):
            cells = []
            for col_index, valor in enumerate(linha):
                ref = f"{col_ref(col_index)}{row_index}"
                if isinstance(valor, (int, float)):
                    cells.append(f'<c r="{ref}"><v>{valor}</v></c>')
                else:
                    cells.append(f'<c r="{ref}" t="s"><v>{shared(str(valor))}</v></c>')
            rows.append(f'<row r="{row_index}">{"".join(cells)}</row>')
        sheets_xml.append((f"xl/worksheets/sheet{sheet_id}.xml", f'<?xml version="1.0" encoding="UTF-8"?><worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>{"".join(rows)}</sheetData></worksheet>'))
        workbook_sheets.append(f'<sheet name="{xml_escape(nome[:31])}" sheetId="{sheet_id}" r:id="rId{sheet_id}"/>')
        rels.append(f'<Relationship Id="rId{sheet_id}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet{sheet_id}.xml"/>')

    shared_xml = "".join(f'<si><t>{xml_escape(texto)}</t></si>' for texto in shared_strings)
    workbook_xml = f'<?xml version="1.0" encoding="UTF-8"?><workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets>{"".join(workbook_sheets)}</sheets></workbook>'
    rels_xml = f'<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">{"".join(rels)}<Relationship Id="rIdSharedStrings" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/></Relationships>'

    content_types = ['<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>', '<Default Extension="xml" ContentType="application/xml"/>', '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>', '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>']
    for sheet_id in range(1, len(abas) + 1):
        content_types.append(f'<Override PartName="/xl/worksheets/sheet{sheet_id}.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>')

    arquivo = io.BytesIO()
    with zipfile.ZipFile(arquivo, "w", zipfile.ZIP_DEFLATED) as pacote:
        pacote.writestr("[Content_Types].xml", f'<?xml version="1.0" encoding="UTF-8"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">{"".join(content_types)}</Types>')
        pacote.writestr("_rels/.rels", '<?xml version="1.0" encoding="UTF-8"?><Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/></Relationships>')
        pacote.writestr("xl/workbook.xml", workbook_xml)
        pacote.writestr("xl/_rels/workbook.xml.rels", rels_xml)
        pacote.writestr("xl/sharedStrings.xml", f'<?xml version="1.0" encoding="UTF-8"?><sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="{len(shared_strings)}" uniqueCount="{len(shared_strings)}">{shared_xml}</sst>')
        for caminho, conteudo in sheets_xml:
            pacote.writestr(caminho, conteudo)
    return arquivo.getvalue()


def gerar_pdf_texto(titulo: str, linhas: list[str]) -> bytes:
    conteudo = ["BT", "/F1 12 Tf", "50 790 Td", f"({pdf_escape(titulo)}) Tj"]
    y_step = 18
    for linha in linhas[:38]:
        conteudo.append(f"0 -{y_step} Td")
        conteudo.append(f"({pdf_escape(linha[:100])}) Tj")
    conteudo.append("ET")
    stream = "\n".join(conteudo).encode("latin-1", errors="replace")
    objetos = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    buffer = io.BytesIO()
    buffer.write(b"%PDF-1.4\n")
    offsets = [0]
    for idx, obj in enumerate(objetos, start=1):
        offsets.append(buffer.tell())
        buffer.write(f"{idx} 0 obj\n".encode("ascii"))
        buffer.write(obj)
        buffer.write(b"\nendobj\n")
    xref = buffer.tell()
    buffer.write(f"xref\n0 {len(objetos) + 1}\n".encode("ascii"))
    buffer.write(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        buffer.write(f"{offset:010d} 00000 n \n".encode("ascii"))
    buffer.write(f"trailer << /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode("ascii"))
    return buffer.getvalue()


def pdf_escape(texto: str) -> str:
    return texto.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")


def renderizar_relatorios(producao: list[dict], paradas: list[dict], ocorrencias: list[dict]) -> None:
    st.subheader("Relatórios")
    abas = {
        "Produção": (COLUNAS_PRODUCAO, producao, mapa_producao()),
        "Paradas": (COLUNAS_PARADAS, paradas, mapa_paradas()),
        "Ocorrências": (COLUNAS_OCORRENCIAS, ocorrencias, mapa_ocorrencias()),
    }
    col1, col2, col3 = st.columns(3)
    with col1:
        st.download_button("Exportar Produção em CSV", registros_para_csv(producao, COLUNAS_PRODUCAO, mapa_producao()), "producao.csv", "text/csv")
        st.download_button("Exportar Paradas em CSV", registros_para_csv(paradas, COLUNAS_PARADAS, mapa_paradas()), "paradas.csv", "text/csv")
        st.download_button("Exportar Ocorrências em CSV", registros_para_csv(ocorrencias, COLUNAS_OCORRENCIAS, mapa_ocorrencias()), "ocorrencias.csv", "text/csv")
    with col2:
        st.download_button("Exportar Excel (.xlsx)", gerar_xlsx(abas), "copiloto_producao.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    with col3:
        resumo = calcular_resumo(producao) if producao else {}
        linhas = [
            f"Produção planejada: {formatar_numero(resumo.get('produção_planejada', 0))}",
            f"Produção realizada: {formatar_numero(resumo.get('produção_realizada', 0))}",
            f"Eficiência média: {formatar_percentual(resumo.get('eficiência_média', 0))}",
            f"Horas trabalhadas: {formatar_decimal(resumo.get('horas_trabalhadas', 0))}",
            f"Produtividade: {formatar_decimal(resumo.get('produtividade', 0))} un/h",
            f"Disponibilidade: {formatar_percentual(resumo.get('disponibilidade', 0))}",
            f"Performance: {formatar_percentual(resumo.get('performance', 0))}",
            f"Qualidade: {formatar_percentual(resumo.get('qualidade', 0))}",
            f"OEE final: {formatar_percentual(resumo.get('oee', 0))}",
        ]
        st.download_button("Exportar PDF", gerar_pdf_texto("Relatório Executivo - Copiloto de Produção", linhas), "relatorio_executivo.pdf", "application/pdf")

    st.caption(f"Banco SQLite em uso: {DB_PATH}")


def mapa_producao() -> dict[str, str]:
    return {
        "produção_planejada": "producao_planejada",
        "produção_realizada": "producao_realizada",
        "peças_boas": "pecas_boas",
        "peças_reprovadas": "pecas_reprovadas",
        "observações": "observacoes",
    }


def mapa_paradas() -> dict[str, str]:
    return {"duração_minutos": "duracao_minutos", "observação": "observacao"}


def mapa_ocorrencias() -> dict[str, str]:
    return {"responsável": "responsavel", "ocorrência": "ocorrencia"}


def renderizar_ia_planejamento(producao: list[dict], paradas: list[dict]) -> None:
    st.subheader("Inteligência Artificial - Planejamento")
    st.markdown(
        """
        Estrutura preparada para uma camada futura de IA operacional:
        - detecção de queda de eficiência por linha, produto e turno;
        - identificação de tendências de perda de produção;
        - correlação entre paradas, ocorrências e OEE;
        - recomendações automáticas para priorização de ações.
        """
    )

    alertas = gerar_alertas_operacionais(producao, paradas)
    if alertas:
        st.warning("Sinais operacionais detectados para análise futura de IA:")
        for alerta in alertas:
            st.write(f"- {alerta}")
    else:
        st.success("Nenhum sinal crítico detectado nos dados atuais.")


def renderizar_administracao() -> None:
    st.subheader("Administração")
    st.markdown(
        """
        Use esta área quando quiser preparar o aplicativo para outra pessoa testar ou começar uma nova base.
        Antes de limpar, baixe um backup do banco atual.
        """
    )

    contadores = contar_registros()
    col1, col2, col3 = st.columns(3)
    col1.metric("Registros de produção", contadores["produção"])
    col2.metric("Registros de paradas", contadores["paradas"])
    col3.metric("Ocorrências", contadores["ocorrências"])

    if DB_PATH.exists():
        st.download_button(
            "Baixar backup SQLite",
            data=DB_PATH.read_bytes(),
            file_name="backup_copiloto_producao.db",
            mime="application/octet-stream",
        )

    st.divider()
    st.warning(
        "A limpeza remove produção, paradas e ocorrências. Esta ação não pode ser desfeita pelo aplicativo."
    )
    confirmar = st.checkbox("Entendo que a limpeza apagará os dados registrados.")
    frase = st.text_input("Digite LIMPAR DADOS para confirmar")

    if st.button("Limpar todos os dados", type="primary"):
        if not confirmar or frase.strip() != "LIMPAR DADOS":
            st.error("Confirme a ação e digite exatamente LIMPAR DADOS.")
            return
        sucesso, mensagem = limpar_todos_os_dados()
        (st.success if sucesso else st.error)(mensagem)
        if sucesso:
            st.rerun()


def gerar_alertas_operacionais(producao: list[dict], paradas: list[dict]) -> list[str]:
    alertas = []
    por_linha = agrupar_soma(producao, "linha") if producao else []
    for item in por_linha:
        if item["eficiência"] < 90:
            alertas.append(f"{item['linha']} com eficiência abaixo de 90% ({formatar_percentual(item['eficiência'])}).")

    minutos_por_linha = defaultdict(float)
    for parada in paradas:
        minutos_por_linha[parada["linha"]] += numero(parada["duracao_minutos"])
    for linha, minutos in minutos_por_linha.items():
        if minutos >= 60:
            alertas.append(f"{linha} acumula {formatar_decimal(minutos)} minutos de parada.")
    return alertas


def main() -> None:
    renderizar_cabecalho()
    preparar_ambiente()

    producao = carregar_producao()
    paradas = carregar_paradas()
    ocorrencias = carregar_ocorrencias()
    producao_filtrada = filtrar_producao(producao)

    abas = st.tabs(
        [
            "Dashboard",
            "Produção",
            "Paradas",
            "Ocorrências",
            "OEE",
            "Relatórios",
            "IA - Planejamento",
            "Base de Dados",
            "Administração",
        ]
    )

    with abas[0]:
        renderizar_dashboard(producao_filtrada)
    with abas[1]:
        renderizar_formulario_producao()
    with abas[2]:
        renderizar_paradas(paradas)
    with abas[3]:
        renderizar_ocorrencias(ocorrencias)
    with abas[4]:
        renderizar_oee(producao_filtrada)
    with abas[5]:
        renderizar_relatorios(producao, paradas, ocorrencias)
    with abas[6]:
        renderizar_ia_planejamento(producao_filtrada, paradas)
    with abas[7]:
        renderizar_tabela("Produção Registrada", producao, COLUNAS_PRODUCAO)
        renderizar_tabela("Paradas Registradas", paradas, COLUNAS_PARADAS)
        renderizar_tabela("Ocorrências Registradas", ocorrencias, COLUNAS_OCORRENCIAS)
    with abas[8]:
        renderizar_administracao()


if __name__ == "__main__":
    main()
