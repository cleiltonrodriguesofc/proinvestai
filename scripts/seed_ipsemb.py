import sqlite3
import json
import uuid
import os
from datetime import datetime

# Convert string UUID to 16-byte binary for SQLite UUID type if needed, or just store as string
# SQLAlchemy UUID is stored as 32-char hex string in SQLite
def to_db_uuid(u):
    return u.hex

def run():
    db_path = "proinvestai.db"
    json_path = "app/alm/config/ipsemb_2026.json"
    
    if not os.path.exists(json_path):
        print(f"File not found: {json_path}")
        return
        
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
        
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 1. Create tables if they do not exist
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS rpps_institutes (
        id VARCHAR(32) NOT NULL,
        user_id VARCHAR(32) NOT NULL,
        cnpj VARCHAR(255) NOT NULL,
        name VARCHAR(255) NOT NULL,
        municipality VARCHAR(255) NOT NULL,
        state VARCHAR(255) NOT NULL,
        type_regime VARCHAR(255) NOT NULL,
        total_assets NUMERIC,
        actuarial_target_index VARCHAR(255),
        actuarial_target_rate NUMERIC,
        pro_gestao_level NUMERIC,
        created_at DATETIME,
        PRIMARY KEY (id),
        UNIQUE (cnpj)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS fund_positions (
        id VARCHAR(32) NOT NULL,
        rpps_id VARCHAR(32) NOT NULL,
        cnpj_fund VARCHAR(255) NOT NULL,
        name_fund VARCHAR(255) NOT NULL,
        segment_cmn VARCHAR(255) NOT NULL,
        current_balance NUMERIC,
        date_entry DATE,
        manager_name VARCHAR(255),
        admin_name VARCHAR(255),
        updated_at DATETIME,
        PRIMARY KEY (id),
        FOREIGN KEY(rpps_id) REFERENCES rpps_institutes (id)
    )
    """)
    
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id VARCHAR(32) NOT NULL,
        email VARCHAR(255) NOT NULL,
        name VARCHAR(255) NOT NULL,
        hashed_password VARCHAR(255) NOT NULL,
        phone VARCHAR(255),
        plan VARCHAR(255) NOT NULL,
        created_at DATETIME,
        PRIMARY KEY (id),
        UNIQUE (email)
    )
    """)
    
    # 2. Check if user exists, else create a dummy one
    cursor.execute("SELECT id FROM users LIMIT 1")
    user_row = cursor.fetchone()
    if not user_row:
        user_id = uuid.uuid4()
        cursor.execute(
            "INSERT INTO users (id, email, name, hashed_password, plan, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (to_db_uuid(user_id), "admin@ipsemb.com.br", "Gestor IPSEMB", "dummyhash", "pro", datetime.utcnow())
        )
        print("Created dummy user.")
    else:
        user_id = uuid.UUID(user_row[0])
        print("Found existing user.")
        
    # 3. Create or update RPPS Institute
    cursor.execute("SELECT id FROM rpps_institutes WHERE cnpj = ?", (data['cnpj'],))
    rpps_row = cursor.fetchone()
    if not rpps_row:
        rpps_id = uuid.uuid4()
        cursor.execute(
            """INSERT INTO rpps_institutes 
               (id, user_id, cnpj, name, municipality, state, type_regime, total_assets, 
                actuarial_target_index, actuarial_target_rate, pro_gestao_level, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                to_db_uuid(rpps_id), to_db_uuid(user_id), data['cnpj'], data['rpps_name'],
                "Buriticupu", "MA", "capitalization", data['patrimony'],
                "IPCA", data['actuarial_rate'], data.get('pro_gestao_level', 0) or 0, datetime.utcnow()
            )
        )
        print(f"Inserted RPPS Institute {data['rpps_name']}")
    else:
        rpps_id = uuid.UUID(rpps_row[0])
        cursor.execute(
            "UPDATE rpps_institutes SET total_assets = ?, actuarial_target_rate = ? WHERE id = ?",
            (data['patrimony'], data['actuarial_rate'], to_db_uuid(rpps_id))
        )
        print(f"Updated RPPS Institute {data['rpps_name']}")
        
    # 4. Clear old positions for this institute
    cursor.execute("DELETE FROM fund_positions WHERE rpps_id = ?", (to_db_uuid(rpps_id),))
    
    # 5. Insert new positions
    portfolio = data.get('portfolio', [])
    for fund in portfolio:
        fund_id = uuid.uuid4()
        # Create a dummy CNPJ for now since JSON only has names
        dummy_cnpj = f"00.000.000/{str(uuid.uuid4())[:4]}-00"
        
        cursor.execute(
            """INSERT INTO fund_positions 
               (id, rpps_id, cnpj_fund, name_fund, segment_cmn, current_balance, date_entry, updated_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                to_db_uuid(fund_id), to_db_uuid(rpps_id), dummy_cnpj, fund['fund_name'], 
                fund['segment'], fund['balance'], datetime.utcnow().date(), datetime.utcnow()
            )
        )
        
    conn.commit()
    conn.close()
    print(f"Successfully seeded {len(portfolio)} funds for IPSEMB.")

if __name__ == "__main__":
    run()
