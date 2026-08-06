import streamlit as st
import pandas as pd

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
