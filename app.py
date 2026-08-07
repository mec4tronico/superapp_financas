import sys
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.services.importadores.b3_excel_reader import (  # noqa: E402
    B3ExcelReaderError,
    open_b3_excel,
)

st.set_page_config(page_title="SuperApp Finanças", layout="wide")

st.title("SuperApp Finanças")

# Dados de exemplo — serão substituídos pelo importador CSV da B3
data = [
    {"Ativo": "KNCR11", "Tipo": "FII", "Quantidade": 100, "Preço Atual": 12.50},
    {"Ativo": "KNIP11", "Tipo": "FII", "Quantidade": 50, "Preço Atual": 7.80},
    {"Ativo": "PETR4", "Tipo": "Ação", "Quantidade": 200, "Preço Atual": 28.35},
    {"Ativo": "VALE3", "Tipo": "Ação", "Quantidade": 150, "Preço Atual": 95.10},
]

df = pd.DataFrame(data)

# Calcular valor investido por ativo
df["Valor Investido"] = df["Quantidade"] * df["Preço Atual"]

# Formatação simples
df["Preço Atual"] = df["Preço Atual"].round(2)
df["Valor Investido"] = df["Valor Investido"].round(2)

# Patrimônio total
patrimonio_total = df["Valor Investido"].sum()

st.subheader("Carteira de Investimentos (exemplo)")
st.dataframe(df, use_container_width=True)

st.markdown("---")
st.metric("Patrimônio Total (R$)", f"{patrimonio_total:,.2f}")

st.write("Dados de exemplo. Em entregas futuras, esses valores serão preenchidos a partir dos CSVs da B3.")

st.markdown("---")
st.subheader("Teste Importação B3")

uploaded_file = st.file_uploader(
    "Envie um arquivo Excel exportado da B3",
    type=["xlsx"],
    help="Formato aceito: .xlsx",
)

if uploaded_file is not None:
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx") as tmp:
            tmp.write(uploaded_file.getbuffer())
            temp_path = Path(tmp.name)

        workbook = open_b3_excel(temp_path)

        st.success(f"Arquivo carregado: **{uploaded_file.name}**")
        st.write("**Abas encontradas:**", ", ".join(workbook.sheet_names))

        selected_sheet = st.selectbox(
            "Selecione a aba para visualizar",
            workbook.sheet_names,
        )

        sheet_df = workbook.read_sheet(sheet_name=selected_sheet)

        st.metric("Quantidade de linhas", len(sheet_df))
        st.write(f"**Prévia da aba '{selected_sheet}':**")
        st.dataframe(sheet_df.head(), use_container_width=True)

    except B3ExcelReaderError as exc:
        st.error(f"Não foi possível ler o arquivo Excel da B3: {exc}")
    except Exception as exc:
        st.error(f"Ocorreu um erro inesperado ao processar o arquivo: {exc}")
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
