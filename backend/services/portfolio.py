"""Processamento de dados de negociação da B3 para montar a carteira atual."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path
from typing import Any

import pandas as pd


DATA_DIR = Path(__file__).resolve().parent.parent / "data"
FIIS_CSV_PATH = DATA_DIR / "fiis.csv"


def normalize_b3_negotiation_data(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Normaliza as colunas de uma aba de negociação da B3 para um formato comum."""
    if dataframe is None:
        raise ValueError("O dataframe de entrada não pode ser nulo.")

    normalized = dataframe.copy()
    column_mapping = {
        "data_negocio": _find_matching_column(
            normalized,
            [
                "data do negocio",
                "data do negócio",
                "data da negociacao",
                "data da negociação",
                "data da operacao",
                "data da operação",
                "data negociacao",
                "data negociação",
                "data",
            ],
        ),
        "tipo_movimentacao": _find_matching_column(
            normalized,
            [
                "tipo de movimentacao",
                "tipo de movimentação",
                "tipo de operacao",
                "tipo de operação",
                "movimentacao",
                "movimentação",
                "operacao",
                "operação",
                "tipo",
            ],
        ),
        "codigo_negociacao": _find_matching_column(
            normalized,
            [
                "codigo de negociacao",
                "codigo de negociação",
                "codigo negociacao",
                "codigo negociação",
                "ticker",
                "codigo",
                "ativo",
            ],
        ),
        "quantidade": _find_matching_column(
            normalized,
            [
                "quantidade",
                "qtde",
                "qtd",
                "quant",
                "qty",
            ],
        ),
        "preco": _find_matching_column(
            normalized,
            [
                "preco",
                "preço",
                "preco unitario",
                "preço unitário",
                "preco unitario da operacao",
                "preço unitário da operação",
                "price",
            ],
        ),
        "valor_operacao": _find_matching_column(
            normalized,
            [
                "valor da operacao",
                "valor da operação",
                "valor operacao",
                "valor operação",
                "valor da movimentacao",
                "valor da movimentação",
                "valor",
            ],
        ),
    }

    missing_columns = [name for name, column in column_mapping.items() if column is None]
    if missing_columns:
        raise ValueError(
            "Não foi possível localizar todas as colunas esperadas na aba. Faltando: "
            + ", ".join(missing_columns)
        )

    renamed = {
        source: target
        for target, source in column_mapping.items()
        if source is not None
    }
    normalized = normalized.rename(columns=renamed)

    normalized["data_negocio"] = pd.to_datetime(
        normalized["data_negocio"], errors="coerce"
    )
    normalized["tipo_movimentacao"] = normalized["tipo_movimentacao"].astype(str)
    normalized["quantidade"] = pd.to_numeric(normalized["quantidade"], errors="coerce")
    normalized["preco"] = pd.to_numeric(normalized["preco"], errors="coerce")
    normalized["valor_operacao"] = pd.to_numeric(
        normalized["valor_operacao"], errors="coerce"
    )

    if normalized["valor_operacao"].isna().all() and not normalized[["quantidade", "preco"]].isna().all().all():
        normalized["valor_operacao"] = normalized["quantidade"] * normalized["preco"]

    normalized["tipo_movimentacao"] = normalized["tipo_movimentacao"].apply(
        _classify_movement
    )
    normalized["quantidade_liquida"] = normalized["quantidade"].fillna(0)
    normalized.loc[normalized["tipo_movimentacao"] == "venda", "quantidade_liquida"] = (
        normalized.loc[normalized["tipo_movimentacao"] == "venda", "quantidade_liquida"] * -1
    )
    normalized["quantidade_liquida"] = normalized["quantidade_liquida"].abs()
    normalized.loc[normalized["tipo_movimentacao"] == "venda", "quantidade_liquida"] = (
        normalized.loc[normalized["tipo_movimentacao"] == "venda", "quantidade_liquida"] * -1
    )

    normalized["codigo_negociacao"] = normalized["codigo_negociacao"].astype(str).str.strip()
    normalized["codigo_negociacao"] = normalized["codigo_negociacao"].replace({"nan": pd.NA})
    normalized = normalized.dropna(subset=["codigo_negociacao"])
    normalized["codigo_negociacao"] = normalized["codigo_negociacao"].apply(_normalizar_ticker)

    return normalized


def build_portfolio_table(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Constrói a tabela de carteira atual a partir de uma aba de negociação da B3."""
    normalized = normalize_b3_negotiation_data(dataframe)

    if normalized.empty:
        return pd.DataFrame(
            columns=["Ticker", "Tipo_Ativo", "Primeira_Aquisicao", "Quantidade", "Preco_Medio", "Valor_Investido"]
        )

    portfolio: list[dict[str, Any]] = []
    for ativo, grupo in normalized.groupby("codigo_negociacao", sort=True):
        compras = grupo[grupo["tipo_movimentacao"] == "compra"]
        vendas = grupo[grupo["tipo_movimentacao"] == "venda"]

        quantidade_total_comprada = compras["quantidade"].sum()
        valor_total_compras = compras["valor_operacao"].sum()
        quantidade_atual = float(
            quantidade_total_comprada - vendas["quantidade"].sum()
        )

        if quantidade_atual <= 0:
            continue

        preco_medio = (
            valor_total_compras / quantidade_total_comprada
            if quantidade_total_comprada > 0
            else 0.0
        )
        valor_investido = quantidade_atual * preco_medio
        primeira_aquisicao = compras["data_negocio"].dropna().min() if not compras["data_negocio"].dropna().empty else pd.NaT

        portfolio.append(
            {
                "Ticker": ativo,
                "Tipo_Ativo": classificar_ativo(str(ativo)),
                "Primeira_Aquisicao": primeira_aquisicao,
                "Quantidade": int(quantidade_atual)
                if abs(quantidade_atual - round(quantidade_atual)) < 1e-9
                else round(quantidade_atual, 2),
                "Preco_Medio": round(preco_medio, 2),
                "Valor_Investido": round(valor_investido, 2),
            }
        )

    carteira = pd.DataFrame(
        portfolio,
        columns=["Ticker", "Tipo_Ativo", "Primeira_Aquisicao", "Quantidade", "Preco_Medio", "Valor_Investido"],
    )
    return normalizar_carteira(carteira)


def normalizar_carteira(carteira: pd.DataFrame) -> pd.DataFrame:
    """Normaliza a carteira consolidando ativos fracionários e classificando o tipo."""
    if carteira is None:
        raise ValueError("A carteira de entrada não pode ser nula.")

    if carteira.empty:
        return pd.DataFrame(
            columns=["Ticker", "Tipo_Ativo", "Primeira_Aquisicao", "Quantidade", "Preco_Medio", "Valor_Investido"]
        )

    normalized = carteira.copy()
    normalized["Ticker"] = normalized["Ticker"].astype(str).str.strip().str.upper()
    normalized["Ticker"] = normalized["Ticker"].apply(_normalizar_ticker)
    normalized["Quantidade"] = pd.to_numeric(normalized["Quantidade"], errors="coerce")
    normalized["Preco_Medio"] = pd.to_numeric(normalized["Preco_Medio"], errors="coerce")
    normalized["Valor_Investido"] = pd.to_numeric(normalized["Valor_Investido"], errors="coerce")
    normalized["Tipo_Ativo"] = normalized["Ticker"].apply(classificar_ativo)

    normalized["Primeira_Aquisicao"] = pd.to_datetime(
        normalized["Primeira_Aquisicao"], errors="coerce"
    )

    normalized["Ativo_Base"] = normalized["Ticker"].apply(_normalizar_ticker)

    resultado: list[dict[str, Any]] = []
    for ativo_base, grupo in normalized.groupby("Ativo_Base", sort=True):
        quantidade_total = float(grupo["Quantidade"].sum())
        valor_total = float(grupo["Valor_Investido"].sum())
        preco_medio = (
            valor_total / quantidade_total if quantidade_total > 0 else 0.0
        )
        primeira_aquisicao = grupo["Primeira_Aquisicao"].dropna().min() if not grupo["Primeira_Aquisicao"].dropna().empty else pd.NaT

        resultado.append(
            {
                "Ticker": ativo_base,
                "Tipo_Ativo": classificar_ativo(ativo_base),
                "Primeira_Aquisicao": primeira_aquisicao,
                "Quantidade": int(quantidade_total)
                if abs(quantidade_total - round(quantidade_total)) < 1e-9
                else round(quantidade_total, 2),
                "Preco_Medio": round(preco_medio, 2),
                "Valor_Investido": round(valor_total, 2),
            }
        )

    return pd.DataFrame(
        resultado,
        columns=["Ticker", "Tipo_Ativo", "Primeira_Aquisicao", "Quantidade", "Preco_Medio", "Valor_Investido"],
    )


def _normalizar_ticker(ticker: str) -> str:
    """Normaliza o ticker removendo espaços, padronizando maiúsculas e removendo o sufixo F quando for fracionário."""
    cleaned = str(ticker).strip().upper()
    if cleaned.endswith("F") and len(cleaned) > 1:
        return cleaned[:-1]
    return cleaned


def classificar_ativo(ticker: str) -> str:
    """Classifica um ativo consultando a base local de FIIs."""
    if not ticker:
        return "ACAO"

    normalized_ticker = str(ticker).strip().upper()
    if not FIIS_CSV_PATH.exists():
        return "ACAO"

    fiis_df = pd.read_csv(FIIS_CSV_PATH)
    if fiis_df.empty:
        return "ACAO"

    known_tickers = fiis_df["ticker"].astype(str).str.strip().str.upper()
    if normalized_ticker in set(known_tickers):
        return "FII"

    return "ACAO"


def _find_matching_column(dataframe: pd.DataFrame, aliases: list[str]) -> str | None:
    """Procura uma coluna compatível com os aliases informados."""
    normalized_aliases = {
        _normalize_label(alias): alias for alias in aliases
    }
    normalized_columns = {
        _normalize_label(column): column for column in dataframe.columns
    }

    for alias in normalized_aliases:
        if alias in normalized_columns:
            return normalized_columns[alias]

    for alias in normalized_aliases:
        matches = _best_match(alias, normalized_columns.keys())
        if matches:
            return normalized_columns[matches]

    return None


def _best_match(target: str, candidates: set[str]) -> str | None:
    if not candidates:
        return None

    best_score = 0.0
    best_match: str | None = None
    for candidate in candidates:
        score = _similarity(target, candidate)
        if score > best_score:
            best_score = score
            best_match = candidate

    return best_match if best_score >= 0.72 else None


def _similarity(left: str, right: str) -> float:
    if left == right:
        return 1.0
    return len(set(left.split()) & set(right.split())) / max(1, len(set(left.split()) | set(right.split())))


def _normalize_label(value: Any) -> str:
    text = str(value).strip().lower()
    text = unicodedata.normalize("NFKD", text)
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def _classify_movement(value: Any) -> str:
    text = str(value).strip().lower()
    if any(token in text for token in ["compra", "buy", "c"]):
        return "compra"
    if any(token in text for token in ["venda", "sell", "s"]):
        return "venda"
    return "desconhecido"
