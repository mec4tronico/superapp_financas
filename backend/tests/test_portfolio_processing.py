import pandas as pd

from backend.services.portfolio import (
    build_portfolio_table,
    classificar_ativo,
    normalize_b3_negotiation_data,
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

    assert list(portfolio.columns) == ["Ativo", "Quantidade", "Preço Médio", "Valor Investido", "Tipo_Ativo"]
    assert portfolio.loc[0, "Ativo"] == "KNCR11"
    assert portfolio.loc[0, "Quantidade"] == 120
    assert portfolio.loc[0, "Preço Médio"] == 101.67
    assert portfolio.loc[0, "Valor Investido"] == 12200.0
    assert portfolio.loc[0, "Tipo_Ativo"] == "FII"


def test_classificar_ativo_uses_local_fii_base() -> None:
    assert classificar_ativo("KNCR11") == "FII"
    assert classificar_ativo("HGLG11") == "FII"
    assert classificar_ativo("PETR4") == "OUTRO"
