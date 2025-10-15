import os
import hashlib
import csv
from pathlib import Path
from typing import Any, Dict, List, Optional

def md5_hash(key: str, depth: int) -> int:
    """Genera hash MD5 y retorna los últimos 'depth' bits como entero."""
    h = hashlib.md5(str(key).encode()).hexdigest()
    bits = bin(int(h, 16))[2:].zfill(128)
    return int(bits[-depth:], 2) if depth > 0 else 0

class TextBucket:
    """Bucket almacenado en archivo de texto plano."""

    def _init_(self, path: Path, capacity: int, local_depth: int = 1):
        self.path = Path(path)
        self.capacity = capacity
        self.local_depth = local_depth
        self.next_bucket_id = 0
        self.records: List[Dict[str, Any]] = []

        if self.path.exists():
            self._load()
        else:
            self._save()

    def _load(self):
        """Carga bucket desde archivo texto."""
        with open(self.path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        if len(lines) < 2:
            return

        meta = lines[0].strip().split(',')
        self.local_depth = int(meta[0])
        self.next_bucket_id = int(meta[1])

        self.records = []
        reader = csv.DictReader(lines[1:])
        for row in reader:
            self.records.append(row)

    def _save(self):
        """Guarda bucket en archivo texto."""
        with open(self.path, 'w', encoding='utf-8', newline='') as f:
            f.write(f"{self.local_depth},{self.next_bucket_id}\n")

            if self.records:
                fieldnames = self.records[0].keys()
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerows(self.records)

    def is_full(self) -> bool:
        return len(self.records) >= self.capacity

    def insert(self, record: Dict[str, Any]):
        """Inserta o actualiza registro."""
        key = record.get('id')
        for i, rec in enumerate(self.records):
            if rec.get('id') == key:
                self.records[i] = record
                self._save()
                return
        self.records.append(record)
        self._save()

    def delete(self, key: str) -> bool:
        """Elimina registro por key."""
        for i, rec in enumerate(self.records):
            if rec.get('id') == key:
                del self.records[i]
                self._save()
                return True
        return False

    def search(self, key: str) -> Optional[Dict[str, Any]]:
        """Busca registro por key."""
        for rec in self.records:
            if rec.get('id') == key:
                return rec
        return None

    def get_all(self) -> List[Dict[str, Any]]:
        return list(self.records)

class TextDirectory:
    """Directorio almacenado en archivo texto."""

    def _init_(self, path: Path, global_depth: int, max_depth: int):
        self.path = Path(path)
        self.global_depth = global_depth
        self.max_depth = max_depth
        self.next_bucket_id = 1
        self.entries: List[int] = []

        if self.path.exists():
            self._load()
        else:
            self._initialize()

    def _load(self):
        """Carga directorio desde archivo."""
        with open(self.path, 'r', encoding='utf-8') as f:
            lines = f.readlines()

        meta = lines[0].strip().split(',')
        self.global_depth = int(meta[0])
        self.max_depth = int(meta[1])
        self.next_bucket_id = int(meta[2])

        self.entries = [int(line.strip()) for line in lines[1:]]

    def _save(self):
        """Guarda directorio en archivo."""
        with open(self.path, 'w', encoding='utf-8') as f:
            f.write(f"{self.global_depth},{self.max_depth},{self.next_bucket_id}\n")
            for bid in self.entries:
                f.write(f"{bid}\n")

    def _initialize(self):
        """Inicializa directorio vacío."""
        size = 2 ** self.global_depth
        self.entries = [self.next_bucket_id] * size
        self.next_bucket_id += 1
        self._save()

    def get_bucket_id(self, key: str) -> int:
        """Obtiene bucket_id para una key."""
        idx = md5_hash(key, self.global_depth)
        return self.entries[idx]

    def double_directory(self):
        """Duplica el directorio (incrementa global_depth)."""
        self.entries = self.entries + self.entries[:]
        self.global_depth += 1
        self._save()

    def allocate_bucket_id(self) -> int:
        """Asigna nuevo bucket_id."""
        bid = self.next_bucket_id
        self.next_bucket_id += 1
        self._save()
        return bid

    def update_pointers(self, old_bid: int, bid1: int, bid2: int, bit_position: int):
        """Actualiza punteros tras split."""
        for i in range(len(self.entries)):
            if self.entries[i] == old_bid:
                if ((i >> bit_position) & 1) == 0:
                    self.entries[i] = bid1
                else:
                    self.entries[i] = bid2
        self._save()

class SQLHashEngine:
    """Motor SQL simple con índice Extendible Hashing en archivos texto."""

    def _init_(self, data_dir: str = "sql_data", bucket_capacity: int = 3,
               initial_depth: int = 1, max_depth: int = 4):
        self.base = Path(data_dir)
        self.buckets_dir = self.base / "buckets"
        self.base.mkdir(parents=True, exist_ok=True)
        self.buckets_dir.mkdir(parents=True, exist_ok=True)

        self.capacity = bucket_capacity
        dir_path = self.base / "directory.txt"

        self.directory = TextDirectory(dir_path, initial_depth, max_depth)

        if not list(self.buckets_dir.glob("bucket_*.txt")):
            bid = self.directory.entries[0]
            self._create_bucket(bid, self.directory.global_depth)

    def _bucket_path(self, bucket_id: int) -> Path:
        return self.buckets_dir / f"bucket_{bucket_id}.txt"

    def _create_bucket(self, bucket_id: int, local_depth: int) -> TextBucket:
        """Crea nuevo bucket."""
        path = self._bucket_path(bucket_id)
        return TextBucket(path, self.capacity, local_depth)

    def _load_bucket(self, bucket_id: int) -> TextBucket:
        """Carga bucket existente."""
        path = self._bucket_path(bucket_id)
        if not path.exists():
            return self._create_bucket(bucket_id, self.directory.global_depth)
        return TextBucket(path, self.capacity)

    def _split_bucket(self, bucket_id: int):
        """Divide un bucket."""
        bucket = self._load_bucket(bucket_id)
        old_ld = bucket.local_depth
        new_ld = old_ld + 1

        bid1 = self.directory.allocate_bucket_id()
        bid2 = self.directory.allocate_bucket_id()
        b1 = self._create_bucket(bid1, new_ld)
        b2 = self._create_bucket(bid2, new_ld)

        all_records = bucket.get_all()
        for rec in all_records:
            key = rec.get('id')
            bits = bin(int(hashlib.md5(str(key).encode()).hexdigest(), 16))[2:].zfill(128)
            if bits[-new_ld] == '0':
                b1.insert(rec)
            else:
                b2.insert(rec)

        self.directory.update_pointers(bucket_id, bid1, bid2, new_ld - 1)

        try:
            os.remove(self._bucket_path(bucket_id))
        except:
            pass

    def INSERT(self, record: Dict[str, Any]):
        """INSERT: Inserta registro con clave 'id'."""
        if 'id' not in record:
            raise ValueError("Record must have 'id' field")

        key = str(record['id'])
        bid = self.directory.get_bucket_id(key)
        bucket = self._load_bucket(bid)

        if bucket.search(key):
            bucket.insert(record)
            return

        if bucket.is_full():
            if bucket.local_depth < self.directory.global_depth:
                self._split_bucket(bid)
                self.INSERT(record)
            elif bucket.local_depth == self.directory.global_depth < self.directory.max_depth:
                self.directory.double_directory()
                self._split_bucket(bid)
                self.INSERT(record)
            else:
                bucket.insert(record)
        else:
            bucket.insert(record)

    def SELECT(self, key: str) -> Optional[Dict[str, Any]]:
        """SELECT: Busca registro por id."""
        bid = self.directory.get_bucket_id(key)
        bucket = self._load_bucket(bid)
        return bucket.search(key)

    def DELETE(self, key: str) -> bool:
        """DELETE: Elimina registro por id."""
        bid = self.directory.get_bucket_id(key)
        bucket = self._load_bucket(bid)
        return bucket.delete(key)

    def SELECT_ALL(self) -> List[Dict[str, Any]]:
        """SELECT *: Retorna todos los registros."""
        all_records = []
        unique_buckets = set(self.directory.entries)
        for bid in unique_buckets:
            bucket = self._load_bucket(bid)
            all_records.extend(bucket.get_all())
        return all_records

    def DUMP_INDEX(self) -> str:
        """Muestra estructura del índice."""
        s = f"=== SQL HASH INDEX ===\n"
        s += f"Global Depth: {self.directory.global_depth}\n"
        s += f"Max Depth: {self.directory.max_depth}\n"
        s += f"Directory Size: {len(self.directory.entries)}\n"
        s += f"Next Bucket ID: {self.directory.next_bucket_id}\n\n"

        for i, bid in enumerate(self.directory.entries):
            bucket = self._load_bucket(bid)
            s += f"[{i:0{self.directory.global_depth}b}] -> bucket_{bid}.txt "
            s += f"(ld={bucket.local_depth}, records={len(bucket.records)})\n"

        return s

if __name__ == "_main_":
    db = SQLHashEngine(data_dir="sql_data", bucket_capacity=2, initial_depth=1, max_depth=3)

    db.INSERT({"id": "001", "name": "Alice", "age": 25})
    db.INSERT({"id": "002", "name": "Bob", "age": 30})
    db.INSERT({"id": "003", "name": "Charlie", "age": 35})
    db.INSERT({"id": "004", "name": "Diana", "age": 28})
    db.INSERT({"id": "005", "name": "Eve", "age": 22})

    print(db.DUMP_INDEX())

    print("\nSELECT id='002':")
    print(db.SELECT("002"))

    print("\nSELECT ALL:")
    for record in db.SELECT_ALL():
        print(record)

    print("\nDELETE id='002':")
    db.DELETE("002")
    print(db.SELECT("002"))

    print("\n" + db.DUMP_INDEX())