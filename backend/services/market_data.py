"""Serviço de dados financeiros via scraping de página web."""

from __future__ import annotations

from typing import Any, Iterable

import pandas as pd
import requests
from bs4 import BeautifulSoup


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

    def buscar_dados_ativo(self, ticker: str, url: str | None = None) -> pd.DataFrame:
        """Busca os dados financeiros de um ativo a partir de uma URL de página."""
        if not ticker:
            raise ValueError("O ticker do ativo não pode estar vazio.")

        pagina_url = url or self._montar_url(ticker)
        html = self.acessar_pagina(pagina_url)
        dados_brutos = self.extrair_dados_html(html, ticker)
        return self.processar_dados_mercado(dados_brutos)

    def buscar_cotacoes(self, ativos: Iterable[str]) -> pd.DataFrame:
        """Busca cotações para a lista de ativos informada."""
        ativos_lista = list(ativos)
        if not ativos_lista:
            return pd.DataFrame(columns=["ticker", "valor_atual", "fonte"])

        return pd.concat(
            [self.buscar_dados_ativo(ativo) for ativo in ativos_lista],
            ignore_index=True,
        )

    def buscar_dividendos(self, ativos: Iterable[str]) -> pd.DataFrame:
        """Busca dividendos para a lista de ativos informada."""
        ativos_lista = list(ativos)
        if not ativos_lista:
            return pd.DataFrame(columns=["ticker", "dividend_yield", "fonte"])

        return pd.concat(
            [self.buscar_dados_ativo(ativo) for ativo in ativos_lista],
            ignore_index=True,
        )

    def atualizar_dados_mercado(self, ativos: Iterable[str]) -> dict[str, pd.DataFrame]:
        """Atualiza em um único passo os dados financeiros dos ativos."""
        return {
            "cotacoes": self.buscar_cotacoes(ativos),
            "dividendos": self.buscar_dividendos(ativos),
        }

    def _montar_url(self, ticker: str) -> str:
        """Monta a URL da página da fonte para o ticker informado."""
        return f"https://statusinvest.com.br/fundos-imobiliarios/{ticker.lower()}"


def criar_servico_mercado(source_name: str | None = None) -> MarketDataService:
    """Factory simples para criar o serviço de dados de mercado."""
    return MarketDataService(source_name=source_name)
