import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import time
import psycopg2
from app.config import settings

def test_supabase():
    url = settings.supabase_db_url or settings.database_url
    print(f"Testing connection to: {url.split('@')[-1] if '@' in url else url}")
    start = time.time()
    try:
        conn = psycopg2.connect(url, connect_timeout=35, sslmode="require")
        elapsed = round(time.time() - start, 2)
        print(f">>> SUCCESS! Connected to Supabase PostgreSQL in {elapsed}s!")
        cur = conn.cursor()
        cur.execute("SELECT version();")
        print("PostgreSQL Version:", cur.fetchone()[0])
        cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public';")
        tables = [row[0] for row in cur.fetchall()]
        print(f"Public tables in Supabase ({len(tables)}):", tables)
        
        # Check users in Supabase
        if "users" in tables:
            cur.execute("SELECT count(*) FROM users;")
            print("Total users in Supabase:", cur.fetchone()[0])
            cur.execute("SELECT name, email, role FROM users;")
            for u in cur.fetchall():
                print(f"  - {u[0]} ({u[1]}): {u[2]}")
        else:
            print("Tables not yet created in Supabase. They will auto-initialize on first run!")
        
        conn.close()
        return True
    except Exception as e:
        elapsed = round(time.time() - start, 2)
        print(f"Connection failed after {elapsed}s: {e}")
        return False

if __name__ == "__main__":
    test_supabase()
