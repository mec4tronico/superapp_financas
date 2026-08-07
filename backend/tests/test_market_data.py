from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

import backend.services.market_data as market_data_module
from backend.services.market_data import (
    MarketDataService,
    criar_lista_ativos,
    gerar_dados_mercado_csv,
)


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


def test_montar_url_usa_base_local_para_fiis_e_acoes(tmp_path: Path, monkeypatch) -> None:
    fiis_path = tmp_path / "fiis.csv"
    pd.DataFrame({"ticker": ["KNCR11", "MCCI11"]}).to_csv(fiis_path, index=False)

    monkeypatch.setattr(market_data_module, "DATA_DIR", tmp_path)

    service = MarketDataService(source_name="statusinvest")
    assert service._montar_url("KNCR11") == "https://statusinvest.com.br/fundos-imobiliarios/kncr11"
    assert service._montar_url("PETR4") == "https://statusinvest.com.br/acoes/petr4"


def test_criar_lista_ativos_escreve_csv_sem_duplicados(tmp_path: Path) -> None:
    carteira = pd.DataFrame(
        {
            "Ativo": ["KNCR11", "", "MCCI11", "KNCR11", "PETR4"],
            "Qtde": [1, 2, 3, 4, 5],
        }
    )

    output_path = tmp_path / "nome_ativos.csv"
    criado = criar_lista_ativos(carteira, output_path=output_path)

    assert criado == output_path
    assert output_path.exists()

    dataframe = pd.read_csv(output_path)
    assert list(dataframe.columns) == ["ticker"]
    assert dataframe["ticker"].tolist() == ["KNCR11", "MCCI11", "PETR4"]


def test_gerar_dados_mercado_csv_ler_arquivo_de_ativos(tmp_path: Path, monkeypatch) -> None:
    ativos_path = tmp_path / "nome_ativos.csv"
    pd.DataFrame({"ticker": ["KNCR11", "PETR4"]}).to_csv(ativos_path, index=False)

    def fake_buscar_dados_ativo(ticker: str, url: str | None = None) -> dict[str, object]:
        if ticker == "KNCR11":
            return {
                "ticker": ticker,
                "valor_atual": "R$ 104,20",
                "minima_52_semanas": "R$ 98,50",
                "maxima_52_semanas": "R$ 107,30",
                "dividend_yield": "13,5%",
                "valorizacao_12_meses": "4,2%",
                "status": "OK",
            }

        raise RuntimeError("offline")

    monkeypatch.setattr("backend.services.market_data.buscar_dados_ativo", fake_buscar_dados_ativo)

    output_path = tmp_path / "dados_mercado.csv"
    resultado = gerar_dados_mercado_csv(ativos_path=ativos_path, output_path=output_path)

    assert resultado == output_path
    assert output_path.exists()

    dataframe = pd.read_csv(output_path)
    assert dataframe.loc[0, "ticker"] == "KNCR11"
    assert dataframe.loc[0, "status"] == "OK"
    assert dataframe.loc[1, "status"] == "OFFLINE"
