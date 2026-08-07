import pandas as pd

from backend.services.portfolio import (
    build_portfolio_table,
    classificar_ativo,
    normalize_b3_negotiation_data,
    normalizar_carteira,
)


def test_normalize_b3_negotiation_data_maps_aliases() -> None:
    dataframe = pd.DataFrame(
        {
            "Data do Negócio": ["2024-01-05", "2024-01-10", "2024-01-15"],
            "Tipo de Operação": ["Compra", "Compra", "Venda"],
            "Ticker": ["KNCR11", "KNCR11", "KNCR11"],
            "Qtde": [100, 50, 30],
            "Preço Unitário": [100.0, 105.0, 110.0],
            "Valor da Operação": [10000.0, 5250.0, 3300.0],
        }
    )

    normalized = normalize_b3_negotiation_data(dataframe)

    assert {"data_negocio", "tipo_movimentacao", "codigo_negociacao", "quantidade", "preco", "valor_operacao"}.issubset(normalized.columns)
    assert normalized.loc[0, "codigo_negociacao"] == "KNCR11"


def test_build_portfolio_table_calculates_current_portfolio() -> None:
    dataframe = pd.DataFrame(
        {
            "Data do Negócio": ["2024-01-05", "2024-01-10", "2024-01-15"],
            "Tipo de Operação": ["Compra", "Compra", "Venda"],
            "Ticker": ["KNCR11", "KNCR11", "KNCR11"],
            "Qtde": [100, 50, 30],
            "Preço Unitário": [100.0, 105.0, 110.0],
            "Valor da Operação": [10000.0, 5250.0, 3300.0],
        }
    )

    portfolio = build_portfolio_table(dataframe)

    assert list(portfolio.columns) == ["Ticker", "Tipo_Ativo", "Primeira_Aquisicao", "Quantidade", "Preco_Medio", "Valor_Investido"]
    assert portfolio.loc[0, "Ticker"] == "KNCR11"
    assert portfolio.loc[0, "Quantidade"] == 120
    assert portfolio.loc[0, "Preco_Medio"] == 101.67
    assert portfolio.loc[0, "Valor_Investido"] == 12200.0
    assert portfolio.loc[0, "Tipo_Ativo"] == "FII"


def test_classificar_ativo_uses_local_fii_base() -> None:
    assert classificar_ativo("KNCR11") == "FII"
    assert classificar_ativo("HGLG11") == "FII"
    assert classificar_ativo("PETR4") == "ACAO"


def test_normalizar_carteira_consolida_tickers_fracionarios() -> None:
    portfolio = pd.DataFrame(
        {
            "Ticker": ["PETR4", "PETR4F", "VALE3", "VALE3F"],
            "Tipo_Ativo": ["ACAO", "ACAO", "ACAO", "ACAO"],
            "Primeira_Aquisicao": ["2025-02-15", "2025-02-15", "2024-01-10", "2024-01-10"],
            "Quantidade": [100, 50, 80, 20],
            "Preco_Medio": [10.0, 10.0, 20.0, 20.0],
            "Valor_Investido": [1000.0, 500.0, 1600.0, 400.0],
        }
    )

    normalized = normalizar_carteira(portfolio)

    assert list(normalized["Ticker"]) == ["PETR4", "VALE3"]
    assert normalized.loc[normalized["Ticker"] == "PETR4", "Quantidade"].iloc[0] == 150
    assert normalized.loc[normalized["Ticker"] == "PETR4", "Valor_Investido"].iloc[0] == 1500.0
    assert normalized.loc[normalized["Ticker"] == "PETR4", "Preco_Medio"].iloc[0] == 10.0
    assert normalized.loc[normalized["Ticker"] == "PETR4", "Primeira_Aquisicao"].iloc[0] == pd.Timestamp("2025-02-15")
    assert normalized.loc[normalized["Ticker"] == "VALE3", "Tipo_Ativo"].iloc[0] == "ACAO"
