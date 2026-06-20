# Copiloto de Produção

Aplicativo Streamlit para gestão diária da produção industrial, com dashboard executivo, OEE, paradas, ocorrências de turno, relatórios e armazenamento em SQLite.

## Funcionalidades

- Lançamento de produção diária por data, linha, turno e produto.
- Cálculo automático de eficiência, produtividade, disponibilidade, performance, qualidade e OEE.
- Dashboard executivo com KPIs coloridos.
- Gestão de paradas com duração automática.
- Registro de ocorrências entre turnos.
- Exportação em CSV, Excel `.xlsx` e PDF.
- Migração automática do CSV legado `data/producao_diaria.csv` para SQLite.
- Validação de campos obrigatórios e bloqueio de registros duplicados.
- Área de Administração com backup do SQLite e limpeza segura da base.
- Estrutura inicial para futura camada de inteligência artificial.

## Como executar

```bash
pip install -r requirements.txt
streamlit run app.py
```

O banco principal é criado automaticamente em:

```text
data/copiloto_producao.db
```

O CSV legado é mantido para compatibilidade e migração inicial.

## Uso em Demonstração

Na aba `Administração`, baixe um backup do banco e use a opção `Limpar todos os dados` para entregar o app vazio para outra pessoa testar.

Em hospedagens públicas como Streamlit Community Cloud, o SQLite funciona bem para MVP e demonstração. Para uso real com vários usuários simultâneos, prefira um banco externo como PostgreSQL, Supabase, Neon ou outro serviço gerenciado.
