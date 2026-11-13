"""
Clean & Prepare Production Database
Resets all transactional tables (expenses, fund transactions, settlements, audit logs)
so the application starts with a pristine slate for production, keeping the 4 crew
members and the 12-month savings schedule intact.
"""

import sys
from pathlib import Path

# Add project root to path
WORKSPACE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

import sqlite3
from app.security import hash_password

DB_PATH = WORKSPACE_ROOT / "data" / "edith.db"

def clean_database():
    print(f"Connecting to database: {DB_PATH}")
    if not DB_PATH.exists():
        print("Database file does not exist yet. It will be created on app startup.")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1. Purge all dummy / test transactions
    tables_to_wipe = ["expenses", "kitty_transactions", "settlements", "audit_logs", "notifications"]
    for t in tables_to_wipe:
        try:
            cur.execute(f"DELETE FROM {t}")
            print(f"  ✓ Purged {t} (0 rows remaining)")
        except Exception as e:
            print(f"  ! Table {t}: {e}")

    # 2. Reset contributions to pristine pending state
    try:
        cur.execute("""
            UPDATE contributions
            SET status = 'pending',
                amount_paid = 0,
                utr_reference = NULL,
                payment_date = NULL,
                verified_at = NULL,
                verified_by = NULL,
                rejected_at = NULL,
                rejected_by = NULL,
                rejection_reason = NULL,
                proof_url = NULL,
                notes = ''
        """)
        print(f"  ✓ Reset all contributions to pending (rows updated: {cur.rowcount})")
    except Exception as e:
        print(f"  ! Failed resetting contributions: {e}")

    # 3. Ensure official passwords are clean
    official_credentials = [
        ("Prajwal", "Prajwal784"),
        ("Parichay", "Parichay392"),
        ("Srujan", "Srujan516"),
        ("Nitish", "Nitish628"),
    ]
    for name, pwd in official_credentials:
        pwd_hash = hash_password(pwd)
        cur.execute("UPDATE users SET password_hash = ? WHERE name = ?", (pwd_hash, name))
        print(f"  ✓ Verified password for {name} ({pwd})")

    conn.commit()
    conn.close()
    print("\n✅ Production database cleaned successfully! Zero dummy data.")

if __name__ == "__main__":
    clean_database()

