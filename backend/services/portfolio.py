"""Processamento de dados de negociação da B3 para montar a carteira atual."""

from __future__ import annotations

import re
import unicodedata
from typing import Any

import pandas as pd


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

    return normalized


def build_portfolio_table(dataframe: pd.DataFrame) -> pd.DataFrame:
    """Constrói a tabela de carteira atual a partir de uma aba de negociação da B3."""
    normalized = normalize_b3_negotiation_data(dataframe)

    if normalized.empty:
        return pd.DataFrame(
            columns=["Ativo", "Quantidade", "Preço Médio", "Valor Investido"]
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

        portfolio.append(
            {
                "Ativo": ativo,
                "Quantidade": int(quantidade_atual)
                if abs(quantidade_atual - round(quantidade_atual)) < 1e-9
                else round(quantidade_atual, 2),
                "Preço Médio": round(preco_medio, 2),
                "Valor Investido": round(valor_investido, 2),
            }
        )

    return pd.DataFrame(portfolio, columns=["Ativo", "Quantidade", "Preço Médio", "Valor Investido"])


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
