"""
parser for cadprev actuarial flow csv files.

the cadprev csv format uses semicolons as delimiters and brazilian
number formatting (1.234,56). the file has:
- row 1: title
- row 2: section group headers
- row 3: column ids (100101, 100201, ...)
- row 4: column descriptive names
- row 5: initial values (patrimônio, taxa)
- rows 6+: annual data
"""
from __future__ import annotations

import csv
import io
from pathlib import Path

from app.domain.entities.alm_entities import CashFlowYear


# column ids from the cadprev standard that we need
_COL_MAP = {
    "100101": "instant",
    "100201": "year",
    "100301": "discount_rate",
    "100401": "discount_factor",
    "109001": "contribution_base",
    "190000": "total_revenues",
    "240000": "total_expenditures",
    "250001": "financial_result",
    "260001": "accumulated_balance_pv",
    "270001": "expected_return_pct",
    "280001": "asset_return",
    "290001": "guaranteed_resources",
}


def _parse_br_number(value: str) -> float:
    """parse brazilian number format: 1.234,56 -> 1234.56."""
    if not value or value.strip() == "":
        return 0.0
    cleaned = value.strip().replace(".", "").replace(",", ".")
    try:
        return float(cleaned)
    except ValueError:
        return 0.0


def parse_cadprev_csv(path: str | Path) -> tuple[list[CashFlowYear], dict]:
    """
    parse a cadprev actuarial flow csv and return structured data.

    returns:
        tuple of (list of cashflowyear objects, metadata dict with
        initial patrimony and actuarial rate)
    """
    path = Path(path)

    # try multiple encodings (cadprev files are often latin-1)
    content = None
    for encoding in ["latin-1", "cp1252", "utf-8", "utf-8-sig"]:
        try:
            content = path.read_text(encoding=encoding)
            break
        except (UnicodeDecodeError, UnicodeError):
            continue

    if content is None:
        raise ValueError(f"could not decode csv file: {path}")

    lines = content.strip().split("\n")
    if len(lines) < 6:
        raise ValueError(f"csv file too short ({len(lines)} lines): {path}")

    # row 3 (index 2): column ids
    col_ids = lines[2].strip().split(";")

    # build index mapping: position -> field_name
    col_index_map: dict[int, str] = {}
    for i, col_id in enumerate(col_ids):
        col_id = col_id.strip()
        if col_id in _COL_MAP:
            col_index_map[i] = _COL_MAP[col_id]

    # row 5 (index 4): initial values (extract patrimônio and taxa)
    initial_row = lines[4].strip().split(";")
    metadata = {
        "initial_patrimony": 0.0,
        "actuarial_rate": 0.0,
    }

    # the actuarial rate is typically in the discount_rate column position
    # and the patrimony is the last non-empty value
    for i, val in enumerate(initial_row):
        val = val.strip()
        if val and "%" not in val:
            parsed = _parse_br_number(val)
            if parsed > 100000:  # likely patrimony
                metadata["initial_patrimony"] = parsed
        if val and "%" in val:
            metadata["actuarial_rate"] = _parse_br_number(val.replace("%", ""))

    # check for the rate in the mapped columns
    rate_col = None
    for i, field in col_index_map.items():
        if field == "discount_rate":
            rate_col = i
            break

    # rows 6+ (index 5+): annual data
    cashflows: list[CashFlowYear] = []

    for line_num, line in enumerate(lines[5:], start=6):
        row = line.strip().split(";")
        if len(row) < max(col_index_map.keys(), default=0) + 1:
            continue

        # extract mapped fields
        data: dict[str, float] = {}
        for i, field in col_index_map.items():
            if i < len(row):
                data[field] = _parse_br_number(row[i])

        # skip rows without a valid year
        if "year" not in data or data["year"] == 0:
            continue

        # if actuarial rate not yet set, get it from first data row
        if metadata["actuarial_rate"] == 0.0 and rate_col is not None:
            if rate_col < len(row):
                metadata["actuarial_rate"] = _parse_br_number(row[rate_col])

        cf = CashFlowYear(
            instant=int(data.get("instant", 0)),
            year=int(data.get("year", 0)),
            discount_rate=data.get("discount_rate", 0.0),
            discount_factor=data.get("discount_factor", 0.0),
            contribution_base=data.get("contribution_base", 0.0),
            total_revenues=data.get("total_revenues", 0.0),
            total_expenditures=data.get("total_expenditures", 0.0),
            financial_result=data.get("financial_result", 0.0),
            accumulated_balance_pv=data.get("accumulated_balance_pv", 0.0),
            expected_return_pct=data.get("expected_return_pct", 0.0),
            asset_return=data.get("asset_return", 0.0),
            guaranteed_resources=data.get("guaranteed_resources", 0.0),
        )
        cashflows.append(cf)

    return cashflows, metadata


def get_deficit_years(cashflows: list[CashFlowYear]) -> list[CashFlowYear]:
    """filter cashflows to only years with net deficit (expenditures > revenues)."""
    return [cf for cf in cashflows if cf.net_flow < 0]


def get_flow_summary(cashflows: list[CashFlowYear]) -> dict:
    """compute summary statistics from the actuarial flow."""
    if not cashflows:
        return {}

    total_revenues = sum(cf.total_revenues for cf in cashflows)
    total_expenditures = sum(cf.total_expenditures for cf in cashflows)
    deficit_years = get_deficit_years(cashflows)
    first_deficit_year = deficit_years[0].year if deficit_years else None

    return {
        "n_years": len(cashflows),
        "first_year": cashflows[0].year,
        "last_year": cashflows[-1].year,
        "total_revenues": total_revenues,
        "total_expenditures": total_expenditures,
        "net_total": total_revenues - total_expenditures,
        "n_deficit_years": len(deficit_years),
        "first_deficit_year": first_deficit_year,
        "actuarial_rate": cashflows[0].discount_rate if cashflows else 0.0,
    }
