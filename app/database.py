import os
import json
import uuid
import logging
import asyncio
from datetime import datetime, date, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from sqlalchemy import create_engine, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.pool import NullPool
from app.config import settings

logger = logging.getLogger("edith.database")


class DuplicateKeyError(IntegrityError):
    """Raised when an insert or update violates a unique constraint."""
    def __init__(self, message="Duplicate key constraint violated"):
        super().__init__(message, params=None, orig=None)


class ObjectId(str):
    """
    Lightweight string-based ID generator & validator compatible with legacy ObjectId call signatures.
    Generates 24-char hex IDs by default.
    """
    def __new__(cls, val=None):
        if val is None:
            val = uuid.uuid4().hex[:24]
        return super().__new__(cls, str(val))

    @classmethod
    def is_valid(cls, val: Any) -> bool:
        if not val:
            return False
        val_str = str(val).strip()
        return len(val_str) >= 4


def _serialize_for_db(val: Any) -> Any:
    if isinstance(val, (dict, list)):
        return json.dumps(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    return val


def _deserialize_from_db(val: Any, is_json_col: bool = False) -> Any:
    if is_json_col and isinstance(val, str):
        try:
            return json.loads(val)
        except Exception:
            return val
    return val


JSON_COLUMNS = {
    "groups": {"trip_stops"},
    "expenses": {"splits"},
    "audit_logs": {"before_state", "after_state"},
    "notifications": {"gateway_response"},
}


class InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class UpdateResult:
    def __init__(self, matched_count=1, modified_count=1):
        self.matched_count = matched_count
        self.modified_count = modified_count


class Cursor:
    def __init__(self, query_fn):
        self._query_fn = query_fn
        self._sort_fields = []
        self._limit_num = None
        self._docs = None

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            self._sort_fields = key_or_list
        else:
            self._sort_fields = [(key_or_list, direction)]
        return self

    def limit(self, n: int):
        self._limit_num = n
        return self

    def _fetch_sync(self):
        if self._docs is None:
            self._docs = self._query_fn(self._sort_fields, self._limit_num)
        return self._docs

    async def to_list(self, length: Optional[int] = None) -> List[Dict]:
        docs = self._fetch_sync()
        if length is not None:
            return docs[:length]
        return list(docs)

    def __aiter__(self):
        self._docs = self._fetch_sync()
        self._index = 0
        return self

    async def __anext__(self):
        if self._index < len(self._docs):
            item = self._docs[self._index]
            self._index += 1
            return item
        raise StopAsyncIteration


class TableCollection:
    def __init__(self, table_name: str, db_manager):
        self.table_name = table_name
        self.db = db_manager

    async def create_index(self, *args, **kwargs):
        return "index_ok"

    def _clean_doc_out(self, row_dict: Dict) -> Dict:
        if not row_dict:
            return None
        doc = dict(row_dict)
        # Ensure both _id and id are accessible
        raw_id = doc.get("id") or doc.get("_id")
        doc["_id"] = str(raw_id)
        doc["id"] = str(raw_id)

        # Deserialize JSON fields
        json_fields = JSON_COLUMNS.get(self.table_name, set())
        for f in json_fields:
            if f in doc and doc[f] is not None:
                doc[f] = _deserialize_from_db(doc[f], is_json_col=True)
            elif f in doc and doc[f] is None:
                doc[f] = [] if f in ("trip_stops", "splits") else None

        return doc

    def _build_where(self, query: Optional[Dict]) -> (str, Dict):
        if not query:
            return "1=1", {}

        clauses = []
        params = {}
        idx = 0

        for k, v in query.items():
            col = "id" if k in ("_id", "id") else k
            if isinstance(v, dict):
                for op, op_val in v.items():
                    idx += 1
                    p_name = f"p_{idx}"
                    if op == "$in":
                        if not op_val:
                            clauses.append("1=0")
                        else:
                            in_keys = []
                            for i, item in enumerate(op_val):
                                item_p = f"{p_name}_{i}"
                                in_keys.append(f":{item_p}")
                                params[item_p] = str(item) if col == "id" else item
                            clauses.append(f"{col} IN ({', '.join(in_keys)})")
                    elif op == "$ne":
                        params[p_name] = str(op_val) if col == "id" else op_val
                        clauses.append(f"({col} IS NULL OR {col} != :{p_name})")
                    elif op == "$nin":
                        if op_val:
                            in_keys = []
                            for i, item in enumerate(op_val):
                                item_p = f"{p_name}_{i}"
                                in_keys.append(f":{item_p}")
                                params[item_p] = str(item) if col == "id" else item
                            clauses.append(f"({col} IS NULL OR {col} NOT IN ({', '.join(in_keys)}))")
            else:
                idx += 1
                p_name = f"p_{idx}"
                # Special handle for group_code case insensitivity
                if col == "group_code" and isinstance(v, str):
                    params[p_name] = v.upper()
                    clauses.append(f"UPPER({col}) = :{p_name}")
                else:
                    params[p_name] = str(v) if col == "id" else v
                    clauses.append(f"{col} = :{p_name}")

        return " AND ".join(clauses), params

    def _find_one_sync(self, query: Dict, projection: Optional[Dict] = None) -> Optional[Dict]:
        where_sql, params = self._build_where(query)
        sql = f"SELECT * FROM {self.table_name} WHERE {where_sql} LIMIT 1"
        with self.db.engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().fetchone()
            if row:
                return self._clean_doc_out(dict(row))
        return None

    async def find_one(self, query: Dict, projection: Optional[Dict] = None) -> Optional[Dict]:
        return self._find_one_sync(query, projection)

    def _query_cursor_sync(self, query: Optional[Dict], sort_fields: List, limit_num: Optional[int]) -> List[Dict]:
        where_sql, params = self._build_where(query)
        order_clauses = []
        if sort_fields:
            for field, direction in sort_fields:
                col = "id" if field in ("_id", "id") else field
                order_clauses.append(f"{col} {'DESC' if direction == -1 else 'ASC'}")
        order_sql = f"ORDER BY {', '.join(order_clauses)}" if order_clauses else ""
        limit_sql = f"LIMIT {limit_num}" if limit_num else ""

        sql = f"SELECT * FROM {self.table_name} WHERE {where_sql} {order_sql} {limit_sql}".strip()
        with self.db.engine.connect() as conn:
            rows = conn.execute(text(sql), params).mappings().fetchall()
            return [self._clean_doc_out(dict(r)) for r in rows]

    def find(self, query: Optional[Dict] = None, projection: Optional[Dict] = None) -> Cursor:
        return Cursor(lambda sorts, lim: self._query_cursor_sync(query, sorts, lim))

    def _insert_one_sync(self, document: Dict) -> InsertResult:
        doc = dict(document)
        doc_id = str(doc.get("id") or doc.get("_id") or uuid.uuid4().hex[:24])
        doc["id"] = doc_id
        if "_id" in doc:
            doc.pop("_id")

        # Normalize JSON columns
        json_fields = JSON_COLUMNS.get(self.table_name, set())
        for f in json_fields:
            if f in doc and isinstance(doc[f], (list, dict)):
                doc[f] = json.dumps(doc[f])

        # Normalize boolean values
        for k, v in doc.items():
            if isinstance(v, (datetime, date)):
                doc[k] = v.isoformat()

        cols = list(doc.keys())
        placeholders = [f":{c}" for c in cols]
        sql = f"INSERT INTO {self.table_name} ({', '.join(cols)}) VALUES ({', '.join(placeholders)})"

        try:
            with self.db.engine.begin() as conn:
                conn.execute(text(sql), doc)
            return InsertResult(doc_id)
        except IntegrityError as exc:
            raise DuplicateKeyError(f"Duplicate key on {self.table_name}: {exc}")

    async def insert_one(self, document: Dict) -> InsertResult:
        return self._insert_one_sync(document)

    def _update_one_sync(self, query: Dict, update: Dict) -> UpdateResult:
        set_vals = update.get("$set", update)
        if not set_vals:
            return UpdateResult(0, 0)

        clean_set = {}
        for k, v in set_vals.items():
            col = "id" if k in ("_id", "id") else k
            if col in JSON_COLUMNS.get(self.table_name, set()) and isinstance(v, (list, dict)):
                clean_set[col] = json.dumps(v)
            elif isinstance(v, (datetime, date)):
                clean_set[col] = v.isoformat()
            else:
                clean_set[col] = v

        where_sql, params = self._build_where(query)
        set_clauses = []
        for k, v in clean_set.items():
            p_name = f"set_{k}"
            set_clauses.append(f"{k} = :{p_name}")
            params[p_name] = v

        sql = f"UPDATE {self.table_name} SET {', '.join(set_clauses)} WHERE {where_sql}"
        with self.db.engine.begin() as conn:
            res = conn.execute(text(sql), params)
            return UpdateResult(res.rowcount, res.rowcount)

    async def update_one(self, query: Dict, update: Dict) -> UpdateResult:
        return self._update_one_sync(query, update)

    def _count_sync(self, query: Optional[Dict] = None) -> int:
        where_sql, params = self._build_where(query)
        sql = f"SELECT COUNT(*) AS c FROM {self.table_name} WHERE {where_sql}"
        with self.db.engine.connect() as conn:
            row = conn.execute(text(sql), params).mappings().fetchone()
            return int(row["c"]) if row else 0

    async def count_documents(self, query: Optional[Dict] = None) -> int:
        return self._count_sync(query)


class DatabaseManager:
    def __init__(self):
        self.engine = None
        self.is_supabase = False
        self.url = ""
        self._collections = {}

    def _get_collection(self, name: str) -> TableCollection:
        if name not in self._collections:
            self._collections[name] = TableCollection(name, self)
        return self._collections[name]

    @property
    def users(self): return self._get_collection("users")
    @property
    def groups(self): return self._get_collection("groups")
    @property
    def memberships(self): return self._get_collection("memberships")
    @property
    def contributions(self): return self._get_collection("contributions")
    @property
    def kitty_transactions(self): return self._get_collection("kitty_transactions")
    @property
    def expenses(self): return self._get_collection("expenses")
    @property
    def settlements(self): return self._get_collection("settlements")
    @property
    def notifications(self): return self._get_collection("notifications")
    @property
    def audit_logs(self): return self._get_collection("audit_logs")

    def __getitem__(self, name: str) -> TableCollection:
        return self._get_collection(name)

    def connect(self):
        db_url = settings.supabase_db_url or settings.database_url
        if db_url and db_url.strip():
            url = db_url.strip()
            # PostgreSQL URL normalizations for SQLAlchemy
            if url.startswith("postgres://"):
                url = "postgresql+psycopg2://" + url[len("postgres://"):]
            elif url.startswith("postgresql://"):
                url = "postgresql+psycopg2://" + url[len("postgresql://"):]
            if "supabase.co" in url and "sslmode" not in url:
                sep = "&" if "?" in url else "?"
                url = f"{url}{sep}sslmode=require"
            try:
                self.engine = create_engine(
                    url,
                    pool_pre_ping=True,
                    pool_size=10,
                    max_overflow=20,
                    connect_args={"connect_timeout": 3},
                )
                # Test connection
                with self.engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                self.is_supabase = True
                self.url = url
                print("\n" + "="*70)
                print("✓ [Database] Connected successfully to Supabase PostgreSQL!")
                print("="*70 + "\n")
                self._init_tables()
                return
            except Exception as exc:
                print("\n" + "="*70)
                print(f"⚠️ [Database Warning] Failed to connect to Supabase ({exc}).")
                print("  Falling back to local SQLite database...")
                print("="*70 + "\n")

        # Local SQLite fallback
        Path("data").mkdir(parents=True, exist_ok=True)
        sqlite_path = Path("data/edith.db").resolve()
        url = f"sqlite:///{sqlite_path}"
        self.engine = create_engine(
            url,
            poolclass=NullPool,
            connect_args={"check_same_thread": False, "timeout": 20},
        )
        self.is_supabase = False
        self.url = url
        print("\n" + "="*70)
        print("✓ [Database] Connected to local SQLite database (data/edith.db).")
        print("  Zero configuration required! The app is 100% operational.")
        print("  To connect to live Supabase, set SUPABASE_DB_URL in your .env file.")
        print("="*70 + "\n")
        self._init_tables()

    def _init_tables(self):
        """Auto-create tables if they don't exist yet."""
        is_pg = self.is_supabase
        text_type = "TEXT"
        json_type = "JSONB" if is_pg else "TEXT"
        ts_type = "TIMESTAMPTZ" if is_pg else "TEXT"
        bool_type = "BOOLEAN"

        ddl = [
            f"""
            CREATE TABLE IF NOT EXISTS users (
                id VARCHAR(64) PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                email VARCHAR(255) UNIQUE NOT NULL,
                phone VARCHAR(32),
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(32) NOT NULL DEFAULT 'member',
                is_active {bool_type} NOT NULL DEFAULT TRUE,
                created_at {ts_type} NOT NULL,
                created_by VARCHAR(64),
                must_change_password {bool_type} NOT NULL DEFAULT FALSE
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS groups (
                id VARCHAR(64) PRIMARY KEY,
                name VARCHAR(120) NOT NULL,
                group_code VARCHAR(32) UNIQUE NOT NULL,
                monthly_contribution INTEGER NOT NULL DEFAULT 2000,
                duration_months INTEGER NOT NULL DEFAULT 12,
                start_date {ts_type},
                custody_holder_name VARCHAR(120),
                currency VARCHAR(10) NOT NULL DEFAULT 'INR',
                created_by VARCHAR(64),
                trip_destination VARCHAR(255) DEFAULT 'To be decided',
                trip_start_date TEXT,
                trip_end_date TEXT,
                planned_trip_budget INTEGER DEFAULT 0,
                trip_notes {text_type} DEFAULT '',
                trip_stops {json_type} DEFAULT '[]',
                trip_title VARCHAR(255),
                is_active {bool_type} NOT NULL DEFAULT TRUE,
                created_at {ts_type} NOT NULL
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS memberships (
                id VARCHAR(64) PRIMARY KEY,
                group_id VARCHAR(64) NOT NULL,
                user_id VARCHAR(64) NOT NULL,
                role VARCHAR(32) NOT NULL DEFAULT 'member',
                joined_at {ts_type} NOT NULL,
                is_active {bool_type} NOT NULL DEFAULT TRUE,
                UNIQUE(group_id, user_id)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS contributions (
                id VARCHAR(64) PRIMARY KEY,
                group_id VARCHAR(64) NOT NULL,
                user_id VARCHAR(64) NOT NULL,
                month_index INTEGER NOT NULL,
                cycle_month VARCHAR(32),
                due_date {ts_type} NOT NULL,
                amount INTEGER NOT NULL DEFAULT 2000,
                amount_due INTEGER NOT NULL DEFAULT 2000,
                amount_paid INTEGER NOT NULL DEFAULT 0,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                utr_reference VARCHAR(64),
                payment_date {ts_type},
                proof_url {text_type},
                submitted_at {ts_type},
                verified_at {ts_type},
                verified_by VARCHAR(64),
                rejected_at {ts_type},
                rejected_by VARCHAR(64),
                rejection_reason {text_type},
                notes {text_type},
                created_at {ts_type} NOT NULL,
                UNIQUE(group_id, month_index, user_id)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS kitty_transactions (
                id VARCHAR(64) PRIMARY KEY,
                group_id VARCHAR(64) NOT NULL,
                type VARCHAR(32) NOT NULL,
                amount INTEGER NOT NULL,
                description {text_type} NOT NULL,
                recipient_name VARCHAR(120),
                created_by VARCHAR(64),
                created_at {ts_type} NOT NULL,
                balance_after INTEGER NOT NULL,
                reference_id VARCHAR(64)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS expenses (
                id VARCHAR(64) PRIMARY KEY,
                group_id VARCHAR(64) NOT NULL,
                title VARCHAR(255) NOT NULL,
                amount INTEGER NOT NULL,
                paid_by_user_id VARCHAR(64) NOT NULL,
                split_type VARCHAR(32) NOT NULL DEFAULT 'equal',
                category VARCHAR(64) NOT NULL DEFAULT 'Other',
                expense_date {ts_type} NOT NULL,
                notes {text_type} DEFAULT '',
                splits {json_type} NOT NULL DEFAULT '[]',
                status VARCHAR(32) NOT NULL DEFAULT 'active',
                is_reversal {bool_type} NOT NULL DEFAULT FALSE,
                reversed_expense_id VARCHAR(64),
                reversal_reason {text_type},
                created_at {ts_type} NOT NULL,
                created_by VARCHAR(64)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS settlements (
                id VARCHAR(64) PRIMARY KEY,
                group_id VARCHAR(64) NOT NULL,
                from_user_id VARCHAR(64) NOT NULL,
                to_user_id VARCHAR(64) NOT NULL,
                amount INTEGER NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                reference_note {text_type},
                created_at {ts_type} NOT NULL,
                settled_at {ts_type},
                verified_by VARCHAR(64)
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS notifications (
                id VARCHAR(64) PRIMARY KEY,
                recipient_user_id VARCHAR(64) NOT NULL,
                channel VARCHAR(32) NOT NULL DEFAULT 'sms',
                recipient_phone VARCHAR(32),
                recipient_email VARCHAR(255),
                template_id VARCHAR(64),
                message_text {text_type} NOT NULL,
                status VARCHAR(32) NOT NULL DEFAULT 'pending',
                gateway_response {json_type},
                created_at {ts_type} NOT NULL,
                sent_at {ts_type}
            )
            """,
            f"""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id VARCHAR(64) PRIMARY KEY,
                timestamp {ts_type} NOT NULL,
                actor_user_id VARCHAR(64),
                actor_name VARCHAR(120),
                actor_email VARCHAR(255),
                action VARCHAR(64) NOT NULL,
                resource_type VARCHAR(64) NOT NULL,
                resource_id VARCHAR(64),
                before_state {json_type},
                after_state {json_type},
                notes {text_type},
                ip_address VARCHAR(64)
            )
            """
        ]

        with self.engine.begin() as conn:
            for statement in ddl:
                conn.execute(text(statement))


_db_manager = DatabaseManager()


async def connect_to_db() -> None:
    _db_manager.connect()


async def close_db_connection() -> None:
    if _db_manager.engine:
        _db_manager.engine.dispose()


def get_database() -> DatabaseManager:
    if _db_manager.engine is None:
        _db_manager.connect()
    return _db_manager


# Backward-compatible aliases for legacy imports
connect_to_mongo = connect_to_db
close_mongo_connection = close_db_connection
