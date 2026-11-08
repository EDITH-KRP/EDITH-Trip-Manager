# tests/mock_db.py
from datetime import datetime
from bson import ObjectId


def _match_val(doc_val, query_val):
    if isinstance(query_val, dict):
        for op, op_val in query_val.items():
            if op == "$in":
                if doc_val not in op_val:
                    return False
            elif op == "$ne":
                if doc_val == op_val:
                    return False
            elif op == "$nin":
                if doc_val in op_val:
                    return False
        return True
    return doc_val == query_val


def match_doc(doc, query):
    for k, v in query.items():
        doc_val = doc.get(k)
        if not _match_val(doc_val, v):
            return False
    return True


class InsertResult:
    def __init__(self, inserted_id):
        self.inserted_id = inserted_id


class MockCursor:
    def __init__(self, docs):
        self.docs = [dict(d) for d in docs]

    def sort(self, key_or_list, direction=1):
        if isinstance(key_or_list, list):
            for k, d in reversed(key_or_list):
                self.docs.sort(key=lambda x: (x.get(k) is None, x.get(k)), reverse=(d == -1))
        else:
            self.docs.sort(key=lambda x: (x.get(key_or_list) is None, x.get(key_or_list)), reverse=(direction == -1))
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


class MockCollection:
    def __init__(self, name):
        self.name = name
        self.docs = {}

    async def create_index(self, *args, **kwargs):
        return "index_ok"

    async def insert_one(self, document):
        doc = dict(document)
        if "_id" not in doc:
            doc["_id"] = ObjectId()
        self.docs[str(doc["_id"])] = doc
        return InsertResult(doc["_id"])

    async def find_one(self, query=None, projection=None):
        query = query or {}
        for doc in self.docs.values():
            if match_doc(doc, query):
                res = dict(doc)
                if projection and isinstance(projection, dict):
                    # handle projection
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
        return MockCursor(matched)

    async def update_one(self, query, update):
        for doc in self.docs.values():
            if match_doc(doc, query):
                if "$set" in update:
                    for k, v in update["$set"].items():
                        doc[k] = v
                return {"modified_count": 1}
        return {"modified_count": 0}

    async def count_documents(self, query=None):
        query = query or {}
        return sum(1 for doc in self.docs.values() if match_doc(doc, query))


class MockDatabase:
    def __init__(self):
        self._collections = {}

    def __getattr__(self, name):
        if name not in self._collections:
            self._collections[name] = MockCollection(name)
        return self._collections[name]

    def __getitem__(self, name):
        return getattr(self, name)
