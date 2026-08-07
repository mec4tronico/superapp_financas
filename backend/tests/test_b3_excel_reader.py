from pathlib import Path

import pandas as pd
import pytest

from backend.services.importadores.b3_excel_reader import (
    B3ExcelEmptyWorkbookError,
    B3ExcelFileNotFoundError,
    B3ExcelReadError,
    B3ExcelSheetNotFoundError,
    B3ExcelUnsupportedFormatError,
    open_b3_excel,
    read_b3_excel,
)

pytest.importorskip("openpyxl")


def _create_sample_workbook(path: Path) -> None:
    posicao = pd.DataFrame(
        {
            "Código de Negociação": ["PETR4", "KNCR11"],
            "Quantidade": [200, 100],
            "Preço de Fechamento": [28.35, 12.50],
        }
    )
    movimentacao = pd.DataFrame(
        {
            "Data": ["2026-01-10", "2026-02-01"],
            "Movimentação": ["Compra", "Compra"],
        }
    )

    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        posicao.to_excel(writer, sheet_name="Posição", index=False)
        movimentacao.to_excel(writer, sheet_name="Movimentação", index=False)


def test_open_b3_excel_identifies_sheets(tmp_path: Path) -> None:
    workbook_path = tmp_path / "posicao_b3.xlsx"
    _create_sample_workbook(workbook_path)

    workbook = open_b3_excel(workbook_path)

    assert workbook.path == workbook_path.resolve()
    assert workbook.sheet_names == ["Posição", "Movimentação"]


def test_read_b3_excel_returns_dataframe_for_selected_sheet(tmp_path: Path) -> None:
    workbook_path = tmp_path / "posicao_b3.xlsx"
    _create_sample_workbook(workbook_path)

    df = read_b3_excel(workbook_path, sheet_name="Posição")

    assert list(df.columns) == [
        "Código de Negociação",
        "Quantidade",
        "Preço de Fechamento",
    ]
    assert len(df) == 2
    assert df.loc[0, "Código de Negociação"] == "PETR4"


def test_read_b3_excel_raises_for_missing_file(tmp_path: Path) -> None:
    missing_path = tmp_path / "inexistente.xlsx"

    with pytest.raises(B3ExcelFileNotFoundError):
        read_b3_excel(missing_path)


def test_read_b3_excel_raises_for_unsupported_extension(tmp_path: Path) -> None:
    invalid_path = tmp_path / "posicao_b3.txt"
    invalid_path.write_text("conteudo invalido", encoding="utf-8")

    with pytest.raises(B3ExcelUnsupportedFormatError):
        read_b3_excel(invalid_path)


def test_read_b3_excel_raises_for_unknown_sheet(tmp_path: Path) -> None:
    workbook_path = tmp_path / "posicao_b3.xlsx"
    _create_sample_workbook(workbook_path)

    with pytest.raises(B3ExcelSheetNotFoundError):
        read_b3_excel(workbook_path, sheet_name="Resumo")


def test_read_b3_excel_raises_for_empty_sheet(tmp_path: Path) -> None:
    workbook_path = tmp_path / "posicao_b3.xlsx"

    with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
        pd.DataFrame({"A": []}).to_excel(writer, sheet_name="Vazia", index=False)

    with pytest.raises(B3ExcelReadError):
        read_b3_excel(workbook_path, sheet_name="Vazia")


def test_open_b3_excel_raises_for_workbook_without_sheets(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    workbook_path = tmp_path / "posicao_b3.xlsx"
    _create_sample_workbook(workbook_path)

    class FakeExcelFile:
        sheet_names: list[str] = []

        def __init__(self, path: Path, engine: str | None = None) -> None:
            pass

    monkeypatch.setattr(
        "backend.services.importadores.b3_excel_reader.pd.ExcelFile",
        FakeExcelFile,
    )

    with pytest.raises(B3ExcelEmptyWorkbookError):
        open_b3_excel(workbook_path)
