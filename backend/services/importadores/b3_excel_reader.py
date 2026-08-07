"""Leitor de arquivos Excel exportados da B3."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Union

import pandas as pd

PathLike = Union[str, Path]

SUPPORTED_EXTENSIONS = {".xlsx", ".xlsm", ".xls"}


class B3ExcelReaderError(Exception):
    """Erro base ao ler arquivos Excel da B3."""


class B3ExcelFileNotFoundError(B3ExcelReaderError):
    """Arquivo informado não existe."""


class B3ExcelUnsupportedFormatError(B3ExcelReaderError):
    """Extensão de arquivo não suportada."""


class B3ExcelEmptyWorkbookError(B3ExcelReaderError):
    """Workbook não contém abas legíveis."""


class B3ExcelSheetNotFoundError(B3ExcelReaderError):
    """Aba solicitada não existe no workbook."""


class B3ExcelReadError(B3ExcelReaderError):
    """Falha ao abrir ou interpretar o arquivo Excel."""


@dataclass(frozen=True)
class B3ExcelWorkbook:
    """Representa um workbook B3 já aberto."""

    path: Path
    sheet_names: list[str]

    def read_sheet(
        self,
        sheet_name: str | None = None,
        *,
        sheet_index: int | None = None,
    ) -> pd.DataFrame:
        """Lê uma aba específica e retorna um DataFrame."""
        resolved_name = _resolve_sheet_name(
            sheet_names=self.sheet_names,
            sheet_name=sheet_name,
            sheet_index=sheet_index,
        )
        try:
            df = pd.read_excel(self.path, sheet_name=resolved_name, engine="openpyxl")
        except ValueError as exc:
            raise B3ExcelReadError(
                f"Não foi possível ler a aba '{resolved_name}' de '{self.path}'."
            ) from exc
        except Exception as exc:
            raise B3ExcelReadError(
                f"Erro inesperado ao ler a aba '{resolved_name}' de '{self.path}'."
            ) from exc

        if df.empty:
            raise B3ExcelReadError(
                f"A aba '{resolved_name}' em '{self.path}' está vazia."
            )

        return df


def open_b3_excel(path: PathLike) -> B3ExcelWorkbook:
    """Abre um Excel da B3, valida o arquivo e identifica as abas disponíveis."""
    resolved_path = _validate_path(path)

    try:
        workbook = pd.ExcelFile(resolved_path, engine="openpyxl")
    except FileNotFoundError as exc:
        raise B3ExcelFileNotFoundError(f"Arquivo não encontrado: {resolved_path}") from exc
    except ImportError as exc:
        raise B3ExcelReadError(
            "Dependência 'openpyxl' não encontrada. Instale com: pip install openpyxl"
        ) from exc
    except ValueError as exc:
        raise B3ExcelUnsupportedFormatError(
            f"Formato de arquivo não suportado: {resolved_path.suffix or '(sem extensão)'}"
        ) from exc
    except Exception as exc:
        raise B3ExcelReadError(
            f"Não foi possível abrir o arquivo Excel: {resolved_path}"
        ) from exc

    sheet_names = [str(name) for name in workbook.sheet_names]
    if not sheet_names:
        raise B3ExcelEmptyWorkbookError(
            f"O arquivo '{resolved_path}' não possui abas."
        )

    return B3ExcelWorkbook(path=resolved_path, sheet_names=sheet_names)


def read_b3_excel(
    path: PathLike,
    *,
    sheet_name: str | None = None,
    sheet_index: int | None = None,
) -> pd.DataFrame:
    """Abre o Excel da B3 e retorna a aba selecionada como DataFrame."""
    workbook = open_b3_excel(path)
    return workbook.read_sheet(sheet_name=sheet_name, sheet_index=sheet_index)


def _validate_path(path: PathLike) -> Path:
    resolved_path = Path(path).expanduser().resolve()

    if not resolved_path.exists():
        raise B3ExcelFileNotFoundError(f"Arquivo não encontrado: {resolved_path}")

    if not resolved_path.is_file():
        raise B3ExcelReadError(f"Caminho informado não é um arquivo: {resolved_path}")

    suffix = resolved_path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise B3ExcelUnsupportedFormatError(
            f"Extensão '{suffix or '(sem extensão)'}' não suportada. "
            f"Use uma destas: {', '.join(sorted(SUPPORTED_EXTENSIONS))}"
        )

    return resolved_path


def _resolve_sheet_name(
    *,
    sheet_names: list[str],
    sheet_name: str | None,
    sheet_index: int | None,
) -> str:
    if sheet_name is not None and sheet_index is not None:
        raise B3ExcelReadError(
            "Informe apenas 'sheet_name' ou 'sheet_index', não ambos."
        )

    if sheet_name is not None:
        if sheet_name not in sheet_names:
            available = ", ".join(sheet_names)
            raise B3ExcelSheetNotFoundError(
                f"Aba '{sheet_name}' não encontrada. Abas disponíveis: {available}"
            )
        return sheet_name

    index = 0 if sheet_index is None else sheet_index
    if index < 0 or index >= len(sheet_names):
        raise B3ExcelSheetNotFoundError(
            f"Índice de aba inválido: {index}. Workbook possui {len(sheet_names)} aba(s)."
        )
    return sheet_names[index]
