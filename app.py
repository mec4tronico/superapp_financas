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
from backend.services.market_data import (  # noqa: E402
    MarketDataService,
)
from backend.services.portfolio import (  # noqa: E402
    build_portfolio_table,
)

st.set_page_config(page_title="SuperApp Finanças", layout="wide")

st.title("SuperApp Finanças")

tab_b3, tab_mercado = st.tabs(["Carteira B3", "Dados Mercado"])

with tab_b3:
    st.subheader("Importação B3")

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

            try:
                portfolio_df = build_portfolio_table(sheet_df)
                if not portfolio_df.empty:
                    st.markdown("---")
                    st.subheader("Carteira Atual")
                    st.dataframe(portfolio_df, use_container_width=True)
                    st.metric(
                        "Valor Total da Carteira (R$)",
                        f"{portfolio_df['Valor Investido'].sum():,.2f}",
                    )
                else:
                    st.info("Não foi possível montar a carteira atual com os dados fornecidos.")
            except ValueError as exc:
                st.info(
                    f"A aba '{selected_sheet}' não apresentou colunas de negociação compatíveis com a carteira atual."
                )
            except Exception as exc:
                st.error(f"Erro inesperado ao construir a carteira: {exc}")

        except B3ExcelReaderError as exc:
            st.error(f"Não foi possível ler o arquivo Excel da B3: {exc}")
        except Exception as exc:
            st.error(f"Ocorreu um erro inesperado ao processar o arquivo: {exc}")
        finally:
            if temp_path is not None:
                try:
                    temp_path.unlink(missing_ok=True)
                except PermissionError:
                    pass

with tab_mercado:
    st.subheader("Dados Mercado")
    st.write("Os dados financeiros serão consultados para os ativos presentes na carteira atual.")

    if "portfolio_df" in locals() and not portfolio_df.empty:
        ativos = portfolio_df["Ativo"].dropna().astype(str).tolist()
        if ativos:
            service = MarketDataService(source_name="statusinvest")
            rows = []
            for ativo in ativos:
                try:
                    dataframe = service.buscar_dados_ativo(ativo)
                    row = dataframe.iloc[0].to_dict()
                    rows.append(
                        {
                            "Ativo": ativo,
                            "Cotação Atual": row.get("valor_atual", "DADO INDISPONÍVEL"),
                            "Mínima 52 semanas": row.get("min_52_semanas", "DADO INDISPONÍVEL"),
                            "Máxima 52 semanas": row.get("max_52_semanas", "DADO INDISPONÍVEL"),
                            "Dividend Yield": row.get("dividend_yield", "DADO INDISPONÍVEL"),
                            "Valorização 12 meses": row.get("valorizacao_12m", "DADO INDISPONÍVEL"),
                            "Status": "OK",
                        }
                    )
                except Exception:
                    rows.append(
                        {
                            "Ativo": ativo,
                            "Cotação Atual": "OFFLINE",
                            "Mínima 52 semanas": "OFFLINE",
                            "Máxima 52 semanas": "OFFLINE",
                            "Dividend Yield": "OFFLINE",
                            "Valorização 12 meses": "OFFLINE",
                            "Status": "OFFLINE",
                        }
                    )

            if rows:
                market_df = pd.DataFrame(rows)
                st.dataframe(market_df, use_container_width=True)
            else:
                st.info("Nenhum ativo disponível para consulta de mercado.")
        else:
            st.info("A carteira atual ainda não contém ativos para consultar.")
    else:
        st.info("Carregue uma carteira na aba Carteira B3 para visualizar os dados de mercado.")
