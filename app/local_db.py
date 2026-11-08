import json
import os
from pathlib import Path
from datetime import datetime, date, timezone
from bson import ObjectId


def _serialize_val(val):
    if isinstance(val, ObjectId):
        return str(val)
    if isinstance(val, (datetime, date)):
        return val.isoformat()
    if isinstance(val, dict):
        return {k: _serialize_val(v) for k, v in val.items()}
    if isinstance(val, list):
        return [_serialize_val(x) for x in val]
    return val


def _match_val(doc_val, query_val):
    if isinstance(query_val, dict):
        for op, op_val in query_val.items():
            if op == "$in":
                # Compare as strings or values
                op_strs = [str(x) for x in op_val]
                if doc_val not in op_val and str(doc_val) not in op_strs:
                    return False
            elif op == "$ne":
                if doc_val == op_val or str(doc_val) == str(op_val):
                    return False
            elif op == "$nin":
                op_strs = [str(x) for x in op_val]
                if doc_val in op_val or str(doc_val) in op_strs:
                    return False
        return True
    return doc_val == query_val or str(doc_val) == str(query_val)


def match_doc(doc, query):
    for k, v in query.items():
        doc_val = doc.get(k)
        if not _match_val(doc_val, v):
            return False
    return True


class InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class LocalCursor:
    def __init__(self, docs):
        self.docs = [dict(d) for d in docs]

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            for k, d in reversed(key_or_list):
                self.docs.sort(key=lambda x: (x.get(k) is None, str(x.get(k) or "")), reverse=(d == -1))
        else:
            self.docs.sort(key=lambda x: (x.get(key_or_list) is None, str(x.get(key_or_list) or "")), reverse=(direction == -1))
        return self

    def limit(self, n):
        self.docs = self.docs[:n]
        return self

    def __aiter__(self):
        self._iter = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration


class LocalCollection:
    def __init__(self, name, parent_db):
        self.name = name
        self.parent_db = parent_db

    @property
    def docs(self):
        return self.parent_db.data.setdefault(self.name, {})

    async def create_index(self, *args, **kwargs):
        return "index_ok"

    async def insert_one(self, document):
        doc = dict(document)
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        elif isinstance(doc["_id"], str) and ObjectId.is_valid(doc["_id"]):
            doc["_id"] = ObjectId(doc["_id"])
        
        self.docs[str(doc["_id"])] = doc
        self.parent_db.save()
        return InsertResult(doc["_id"])

    async def find_one(self, query=None, projection=None):
        query = query or {}
        for doc in self.docs.values():
            if match_doc(doc, query):
                res = dict(doc)
                if projection and isinstance(projection, dict):
                    filtered = {}
                    for k, v in projection.items():
                        if v == 1 and k in res:
                            filtered[k] = res[k]
                    if "_id" not in projection or projection["_id"] == 1:
                        filtered["_id"] = res["_id"]
                    return filtered
                return res
        return None

    def find(self, query=None, projection=None):
        query = query or {}
        matched = []
        for doc in self.docs.values():
            if match_doc(doc, query):
                res = dict(doc)
                if projection and isinstance(projection, dict):
                    filtered = {}
                    for k, v in projection.items():
                        if v == 1 and k in res:
                            filtered[k] = res[k]
                    if "_id" not in projection or projection["_id"] == 1:
                        filtered["_id"] = res["_id"]
                    matched.append(filtered)
                else:
                    matched.append(res)
        return LocalCursor(matched)

    async def update_one(self, query, update):
        for doc in self.docs.values():
            if match_doc(doc, query):
                if "$set" in update:
                    for k, v in update["$set"].items():
                        doc[k] = v
                self.parent_db.save()
                return {"modified_count": 1}
        return {"modified_count": 0}

    async def count_documents(self, query=None):
        query = query or {}
        return sum(1 for doc in self.docs.values() if match_doc(doc, query))


class LocalDatabase:
    def __init__(self, filepath="data/edith_dev_db.json"):
        self.filepath = Path(filepath)
        self.data = {}
        self._collections = {}
        self.load()

    def load(self):
        if self.filepath.exists():
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for col_name, docs in raw.items():
                        self.data[col_name] = {}
                        for doc_id, doc in docs.items():
                            # Restore ObjectId
                            if ObjectId.is_valid(doc_id):
                                doc["_id"] = ObjectId(doc_id)
                            # Restore common datetime fields
                            for dt_field in ["created_at", "updated_at", "submitted_at", "verified_at", "start_date", "due_date", "timestamp"]:
                                if dt_field in doc and isinstance(doc[dt_field], str):
                                    try:
                                        doc[dt_field] = datetime.fromisoformat(doc[dt_field])
                                    except Exception:
                                        pass
                            self.data[col_name][doc_id] = doc
            except Exception as e:
                print(f"[LocalDB] Could not load dev database: {e}")

    def save(self):
        try:
            self.filepath.parent.mkdir(parents=True, exist_ok=True)
            serializable = {}
            for col_name, docs in self.data.items():
                serializable[col_name] = {}
                for doc_id, doc in docs.items():
                    serializable[col_name][str(doc_id)] = _serialize_val(doc)
            with open(self.filepath, "w", encoding="utf-8") as f:
                json.dump(serializable, f, indent=2)
        except Exception as e:
            print(f"[LocalDB] Could not persist dev database: {e}")

    def __getattr__(self, name):
        if name not in self._collections:
            self._collections[name] = LocalCollection(name, self)
        return self._collections[name]

    def __getitem__(self, name):
        return getattr(self, name)

