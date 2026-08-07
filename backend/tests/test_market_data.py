from bs4 import BeautifulSoup

from backend.services.market_data import MarketDataService


def test_extrair_dados_html_from_sample_markup() -> None:
    html = """
    <html><body>
        <div>
            <h3>VALOR ATUAL</h3>
            <div><strong class="value">R$ 12,50</strong></div>
        </div>
        <div>
            <small>MIN. 52 SEMANAS</small>
            <div><strong class="value">R$ 10,00</strong></div>
        </div>
        <div>
            <span>MÁX. 52 SEMANAS</span>
            <div><strong class="value">R$ 14,00</strong></div>
        </div>
        <div>
            <h3>DIVIDEND YIELD</h3>
            <div><strong class="value">8,5%</strong></div>
        </div>
        <div>
            <h3>VALORIZAÇÃO (12M)</h3>
            <div><strong class="value">15,2%</strong></div>
        </div>
    </body></html>
    """

    service = MarketDataService(source_name="statusinvest")
    dados = service.extrair_dados_html(html, "KNCR11")

    assert dados["ticker"] == "KNCR11"
    assert dados["dados"]["valor_atual"] == "R$ 12,50"
    assert dados["dados"]["dividend_yield"] == "8,5%"
    assert dados["dados"]["valorizacao_12m"] == "15,2%"


def test_processar_dados_mercado_returns_dataframe() -> None:
    service = MarketDataService(source_name="statusinvest")
    dados_brutos = {
        "ticker": "KNCR11",
        "fonte": "statusinvest",
        "dados": {
            "valor_atual": "R$ 12,50",
            "min_52_semanas": "R$ 10,00",
            "max_52_semanas": "R$ 14,00",
            "dividend_yield": "8,5%",
            "valorizacao_12m": "15,2%",
        },
    }

    dataframe = service.processar_dados_mercado(dados_brutos)

    assert list(dataframe.columns) == [
        "ticker",
        "valor_atual",
        "min_52_semanas",
        "max_52_semanas",
        "dividend_yield",
        "valorizacao_12m",
        "fonte",
    ]
    assert dataframe.loc[0, "ticker"] == "KNCR11"
