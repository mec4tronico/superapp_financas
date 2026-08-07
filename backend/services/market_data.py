"""Serviço de dados financeiros via scraping de página web."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any, Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
NOME_ATIVOS_PATH = DATA_DIR / "nome_ativos.csv"
DADOS_MERCADO_PATH = DATA_DIR / "dados_mercado.csv"


class MarketDataService:
    """Interface para consultar páginas financeiras e extrair dados de mercado."""

    def __init__(self, source_name: str | None = None) -> None:
        self.source_name = source_name or "statusinvest"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        }
        self.last_error: str | None = None

    def acessar_pagina(self, url: str) -> str:
        """Realiza a requisição HTTP da página financeira."""
        if not url:
            raise ValueError("A URL da fonte não pode estar vazia.")

        try:
            response = requests.get(url, headers=self.headers, timeout=15)
        except requests.RequestException as exc:
            self.last_error = f"Erro ao executar: {exc}"
            raise RuntimeError(self.last_error) from exc

        if response.status_code != 200:
            self.last_error = f"Erro no acesso à página. Status Code: {response.status_code}"
            raise RuntimeError(self.last_error)

        self.last_error = None
        return response.text

    def extrair_dados_html(self, html: str, ticker: str) -> dict[str, Any]:
        """Extrai os principais indicadores financeiros do HTML da página."""
        soup = BeautifulSoup(html, "html.parser")

        def get_value_by_title(title_text: str) -> str | None:
            title_elem = soup.find(
                lambda tag: tag.name in ["h3", "small", "span"]
                and title_text in tag.text.upper()
            )
            if title_elem:
                parent = title_elem.find_parent("div")
                if parent:
                    val_elem = parent.find("strong", class_="value")
                    if val_elem:
                        return val_elem.text.strip()
            return None

        return {
            "ticker": ticker,
            "fonte": self.source_name,
            "dados": {
                "valor_atual": get_value_by_title("VALOR ATUAL"),
                "min_52_semanas": get_value_by_title("MIN. 52 SEMANAS"),
                "max_52_semanas": get_value_by_title("MÁX. 52 SEMANAS"),
                "dividend_yield": get_value_by_title("DIVIDEND YIELD"),
                "valorizacao_12m": get_value_by_title("VALORIZAÇÃO (12M)"),
            },
        }

    def processar_dados_mercado(self, dados_brutos: dict[str, Any]) -> pd.DataFrame:
        """Organiza os dados extraídos em um DataFrame estruturado."""
        dados = dados_brutos.get("dados", {})
        return pd.DataFrame(
            [
                {
                    "ticker": dados_brutos.get("ticker"),
                    "valor_atual": dados.get("valor_atual"),
                    "min_52_semanas": dados.get("min_52_semanas"),
                    "max_52_semanas": dados.get("max_52_semanas"),
                    "dividend_yield": dados.get("dividend_yield"),
                    "valorizacao_12m": dados.get("valorizacao_12m"),
                    "fonte": dados_brutos.get("fonte"),
                }
            ]
        )

    def buscar_dados_ativo(self, ticker: str, url: str | None = None) -> dict[str, Any]:
        """Busca os dados financeiros de um ativo a partir de uma URL de página."""
        if not ticker:
            raise ValueError("O ticker do ativo não pode estar vazio.")

        pagina_url = url or self._montar_url(ticker)
        try:
            html = self.acessar_pagina(pagina_url)
            dados_brutos = self.extrair_dados_html(html, ticker)
            dados = dados_brutos.get("dados", {})
            valores = {
                "ticker": ticker.upper(),
                "valor_atual": dados.get("valor_atual") or "DADO INDISPONÍVEL",
                "minima_52_semanas": dados.get("min_52_semanas") or "DADO INDISPONÍVEL",
                "maxima_52_semanas": dados.get("max_52_semanas") or "DADO INDISPONÍVEL",
                "dividend_yield": dados.get("dividend_yield") or "DADO INDISPONÍVEL",
                "valorizacao_12_meses": dados.get("valorizacao_12m") or "DADO INDISPONÍVEL",
                "data_consulta": date.today().isoformat(),
                "status": "OK",
            }
            if any(val in {None, "", "DADO INDISPONÍVEL"} for val in valores.values() if isinstance(val, str) and val != "status"):
                valores["status"] = "DADO INDISPONÍVEL"
            return valores
        except Exception as exc:
            return {
                "ticker": ticker.upper(),
                "valor_atual": "OFFLINE",
                "minima_52_semanas": "OFFLINE",
                "maxima_52_semanas": "OFFLINE",
                "dividend_yield": "OFFLINE",
                "valorizacao_12_meses": "OFFLINE",
                "data_consulta": date.today().isoformat(),
                "status": "OFFLINE",
                "erro": str(exc),
            }

    def buscar_cotacoes(self, ativos: Iterable[str]) -> pd.DataFrame:
        """Busca cotações para a lista de ativos informada."""
        ativos_lista = list(ativos)
        if not ativos_lista:
            return pd.DataFrame(columns=["ticker", "valor_atual", "fonte"])

        registros = [self.buscar_dados_ativo(ativo) for ativo in ativos_lista]
        return pd.DataFrame(registros)

    def buscar_dividendos(self, ativos: Iterable[str]) -> pd.DataFrame:
        """Busca dividendos para a lista de ativos informada."""
        ativos_lista = list(ativos)
        if not ativos_lista:
            return pd.DataFrame(columns=["ticker", "dividend_yield", "fonte"])

        registros = [self.buscar_dados_ativo(ativo) for ativo in ativos_lista]
        return pd.DataFrame(registros)

    def atualizar_dados_mercado(self, ativos: Iterable[str]) -> dict[str, pd.DataFrame]:
        """Atualiza em um único passo os dados financeiros dos ativos."""
        return {
            "cotacoes": self.buscar_cotacoes(ativos),
            "dividendos": self.buscar_dividendos(ativos),
        }

    def _montar_url(self, ticker: str) -> str:
        """Monta a URL da página da fonte para o ticker informado."""
        ticker_normalizado = str(ticker).strip().upper()
        fiis_path = DATA_DIR / "fiis.csv"
        if fiis_path.exists():
            fiis_df = pd.read_csv(fiis_path)
            if not fiis_df.empty:
                known_tickers = (
                    fiis_df["ticker"].astype(str).str.strip().str.upper()
                )
                if ticker_normalizado in set(known_tickers):
                    return f"https://statusinvest.com.br/fundos-imobiliarios/{ticker_normalizado.lower()}"

        return f"https://statusinvest.com.br/acoes/{ticker_normalizado.lower()}"


def criar_servico_mercado(source_name: str | None = None) -> MarketDataService:
    """Factory simples para criar o serviço de dados de mercado."""
    return MarketDataService(source_name=source_name)


def criar_lista_ativos(
    portfolio_data: pd.DataFrame | Iterable[str] | None,
    output_path: str | Path | None = None,
) -> Path:
    """Cria o CSV de ativos a partir de uma tabela de carteira ou de uma lista de tickers."""
    if portfolio_data is None:
        raise ValueError("A tabela da carteira ou a lista de ativos é obrigatória.")

    if isinstance(portfolio_data, pd.DataFrame):
        source_df = portfolio_data.copy()
        coluna_ativos = None
        for candidate in ["Ativo", "codigo_negociacao", "ticker", "codigo", "ativo"]:
            if candidate in source_df.columns:
                coluna_ativos = candidate
                break
        if coluna_ativos is None:
            raise ValueError("Não foi possível localizar a coluna de ativos na tabela fornecida.")
        tickers = source_df[coluna_ativos]
    else:
        tickers = list(portfolio_data)

    ativos = []
    for value in tickers:
        ticker = str(value).strip().upper()
        if ticker:
            ativos.append(ticker)

    ativos_sem_duplicados = list(dict.fromkeys(ativos))
    dataframe = pd.DataFrame({"ticker": ativos_sem_duplicados})

    destino = Path(output_path) if output_path is not None else NOME_ATIVOS_PATH
    destino.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(destino, index=False)
    return destino


def acessar_pagina(url: str) -> str:
    """Wrapper simples para a consulta HTTP da página."""
    return MarketDataService().acessar_pagina(url)


def extrair_dados_html(html: str, ticker: str) -> dict[str, Any]:
    """Wrapper simples para a extração de dados do HTML."""
    return MarketDataService().extrair_dados_html(html, ticker)


def buscar_dados_ativo(ticker: str, url: str | None = None) -> dict[str, Any]:
    """Wrapper simples para a consulta completa de um ticker."""
    return MarketDataService().buscar_dados_ativo(ticker=ticker, url=url)


def gerar_dados_mercado_csv(
    ativos_path: str | Path | None = None,
    output_path: str | Path | None = None,
) -> Path:
    """Gera o CSV de dados de mercado a partir de um arquivo com a lista de ativos."""
    origem = Path(ativos_path) if ativos_path is not None else NOME_ATIVOS_PATH
    destino = Path(output_path) if output_path is not None else DADOS_MERCADO_PATH

    if not origem.exists():
        raise FileNotFoundError(f"Arquivo de ativos não encontrado: {origem}")

    ativos_df = pd.read_csv(origem)
    if ativos_df.empty:
        dataframe = pd.DataFrame(
            columns=[
                "ticker",
                "valor_atual",
                "minima_52_semanas",
                "maxima_52_semanas",
                "dividend_yield",
                "valorizacao_12_meses",
                "data_consulta",
                "status",
            ]
        )
        destino.parent.mkdir(parents=True, exist_ok=True)
        dataframe.to_csv(destino, index=False)
        return destino

    registros = []
    for ticker in ativos_df["ticker"].dropna().astype(str):
        valor_limpo = ticker.strip().upper()
        if not valor_limpo:
            continue
        try:
            resultado = buscar_dados_ativo(valor_limpo)
        except Exception as exc:
            resultado = {
                "ticker": valor_limpo,
                "valor_atual": "OFFLINE",
                "minima_52_semanas": "OFFLINE",
                "maxima_52_semanas": "OFFLINE",
                "dividend_yield": "OFFLINE",
                "valorizacao_12_meses": "OFFLINE",
                "data_consulta": date.today().isoformat(),
                "status": "OFFLINE",
                "erro": str(exc),
            }
        registros.append(
            {
                "ticker": resultado.get("ticker", valor_limpo),
                "valor_atual": resultado.get("valor_atual", "DADO INDISPONÍVEL"),
                "minima_52_semanas": resultado.get("minima_52_semanas", "DADO INDISPONÍVEL"),
                "maxima_52_semanas": resultado.get("maxima_52_semanas", "DADO INDISPONÍVEL"),
                "dividend_yield": resultado.get("dividend_yield", "DADO INDISPONÍVEL"),
                "valorizacao_12_meses": resultado.get("valorizacao_12_meses", "DADO INDISPONÍVEL"),
                "data_consulta": resultado.get("data_consulta", date.today().isoformat()),
                "status": resultado.get("status", "OFFLINE"),
            }
        )

    dataframe = pd.DataFrame(registros)
    destino.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(destino, index=False)
    return destino
