"""
Seed script: populates the database with IPSEMB data from ipsemb_2026.json.
Targets the user specified by TARGET_EMAIL.
Run from project root: python scripts/seed_ipsemb.py
"""
import sqlite3
import json
import uuid
from datetime import datetime, date

TARGET_EMAIL = "rc.cleiltonrodrigues@gmail.com"
DB_PATH = "proinvestai.db"
JSON_PATH = "app/alm/config/ipsemb_2026.json"

# CNPJs reais dos fundos do IPSEMB (mapeamento por nome parcial)
FUND_CNPJ_MAP = {
    "CAIXA BRASIL GESTÃO ESTRATÉGICA": "00.068.305/0001-56",
    "BB IRF-M 1 TP FIC RF PREVID":     "17.495.699/0001-33",
    "CAIXA BRASIL IRF-M 1 TP FI RF":   "11.328.882/0001-35",
    "BRADESCO IRF-M 1 TP FI RF":       "11.111.786/0001-56",
    "BB PREVIDENCIÁRIO RENDA FIXA":     "26.183.531/0001-79",
    "BRADESCO PODER PÚBLICO":           "03.557.475/0001-10",
    "BB IRF-M TP FI RF PREVID":        "03.737.206/0001-10",
    "CAIXA BRASIL ESPECIAL 2026":       "35.635.933/0001-48",
    "BB PERFIL FIC RF":                 "03.737.206/0002-91",
    "BRADESCO PREMIUM FI RF":           "04.305.327/0001-07",
    "BB IMA-B FI RF PREVID":            "28.280.836/0001-63",
    "FI CAIXA BRASIL MATRIZ RF":        "11.758.741/0001-52",
    "BRADESCO MID SMALL CAPS":          "11.183.297/0001-94",
    "BB FATORIAL FIC AÇÕES":            "20.774.695/0001-10",
    "BB AÇÕES DIVIDENDOS":              "28.307.160/0001-43",
    "CAIXA JUROS E MOEDAS":             "13.364.135/0001-25",
}

SEGMENT_LABELS = {
    "renda_fixa": "Renda Fixa",
    "renda_variavel": "Renda Variável",
    "estruturados": "Estruturados",
    "fundos_imobiliarios": "Fundos Imobiliários",
    "exterior": "Exterior",
}


def to_hex(u: uuid.UUID) -> str:
    return u.hex


def find_cnpj(fund_name: str) -> str:
    """Match fund name to real CNPJ using partial key match."""
    upper = fund_name.upper()
    for key, cnpj in FUND_CNPJ_MAP.items():
        if key.upper() in upper or upper.startswith(key.upper()[:20]):
            return cnpj
    # Generate a deterministic placeholder CNPJ if not found
    short = abs(hash(fund_name)) % 99999999
    return f"{short:08d}/0001-00"


def run():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # ── Ensure new columns exist in fund_positions ──────────────────────────
    existing_cols = {row[1] for row in cursor.execute("PRAGMA table_info(fund_positions)")}
    new_cols = {
        "regulatory_article": "TEXT",
        "benchmark": "TEXT",
        "weight_pct": "REAL DEFAULT 0",
        "liquidity_days": "REAL DEFAULT 0",
        "monthly_return_pct": "REAL",
        "admin_fee_pct": "REAL",
        "is_legacy": "INTEGER DEFAULT 0",
        "maturity_date": "TEXT",
    }
    for col, col_type in new_cols.items():
        if col not in existing_cols:
            cursor.execute(f"ALTER TABLE fund_positions ADD COLUMN {col} {col_type}")
            print(f"  Added column: {col}")

    conn.commit()

    # ── Find target user ─────────────────────────────────────────────────────
    cursor.execute("SELECT id FROM users WHERE email = ?", (TARGET_EMAIL,))
    row = cursor.fetchone()
    if not row:
        print(f"ERROR: user {TARGET_EMAIL} not found in DB.")
        conn.close()
        return
    user_id = uuid.UUID(row[0])
    print(f"Found user: {TARGET_EMAIL} ({user_id})")

    # ── Upsert RPPS Institute ────────────────────────────────────────────────
    cursor.execute("SELECT id FROM rpps_institutes WHERE cnpj = ?", (data["cnpj"],))
    rpps_row = cursor.fetchone()
    if not rpps_row:
        rpps_id = uuid.uuid4()
        cursor.execute(
            """INSERT INTO rpps_institutes
               (id, user_id, cnpj, name, municipality, state, type_regime,
                total_assets, actuarial_target_index, actuarial_target_rate,
                pro_gestao_level, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                to_hex(rpps_id), to_hex(user_id), data["cnpj"], data["rpps_name"],
                "Buriticupu", "MA", "capitalization", data["patrimony"],
                "IPCA", data["actuarial_rate"],
                data.get("pro_gestao_level") or 0,
                datetime.now().isoformat(),
            ),
        )
        print(f"Inserted: {data['rpps_name']}")
    else:
        rpps_id = uuid.UUID(rpps_row[0])
        cursor.execute(
            """UPDATE rpps_institutes
               SET user_id=?, total_assets=?, actuarial_target_rate=?
               WHERE id=?""",
            (to_hex(user_id), data["patrimony"], data["actuarial_rate"], to_hex(rpps_id)),
        )
        print(f"Updated: {data['rpps_name']}")

    # ── Clear and re-insert fund positions ──────────────────────────────────
    cursor.execute("DELETE FROM fund_positions WHERE rpps_id = ?", (to_hex(rpps_id),))
    total_balance = sum(f["balance"] for f in data["portfolio"])

    for fund in data["portfolio"]:
        fid = uuid.uuid4()
        cnpj = find_cnpj(fund["fund_name"])
        maturity_raw = fund.get("maturity_date")
        maturity = maturity_raw if maturity_raw else None
        weight = round(fund["balance"] / total_balance * 100, 2) if total_balance else 0

        cursor.execute(
            """INSERT INTO fund_positions
               (id, rpps_id, cnpj_fund, name_fund, segment_cmn,
                regulatory_article, benchmark, current_balance, weight_pct,
                liquidity_days, monthly_return_pct, admin_fee_pct,
                is_legacy, maturity_date, date_entry, updated_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                to_hex(fid), to_hex(rpps_id), cnpj, fund["fund_name"],
                fund["segment"], fund.get("regulatory_article", ""),
                fund.get("benchmark", ""),
                fund["balance"], weight,
                fund.get("liquidity_days", 0),
                fund.get("monthly_return", None),
                fund.get("admin_fee", None),
                1 if fund.get("is_legacy") else 0,
                maturity,
                date.today().isoformat(),
                datetime.now().isoformat(),
            ),
        )

    conn.commit()
    conn.close()
    print(f"Seeded {len(data['portfolio'])} funds for IPSEMB successfully.")


if __name__ == "__main__":
    run()
