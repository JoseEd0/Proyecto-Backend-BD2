import os
import struct
import hashlib
import pickle
from pathlib import Path

# ---------- Formatos binarios ----------
# Directory header: global_depth (B), max_global_depth (B), next_bucket_id (I), dir_len (I)
DIR_HEADER_FMT = "B B I I"
DIR_HEADER_SIZE = struct.calcsize(DIR_HEADER_FMT)
DIR_ENTRY_FMT = "I"   # bucket_id per directory entry (unsigned int)
DIR_ENTRY_SIZE = struct.calcsize(DIR_ENTRY_FMT)

# Bucket header: local_depth (B), is_overflow (B), next_bucket_id (I), num_items (I)
BUCKET_HEADER_FMT = "B B I I"
BUCKET_HEADER_SIZE = struct.calcsize(BUCKET_HEADER_FMT)
# Each entry: key_len (H), key bytes (utf-8), val_len (I), val bytes (pickle)
KEY_LEN_FMT = "H"
KEY_LEN_SIZE = struct.calcsize(KEY_LEN_FMT)
VAL_LEN_FMT = "I"
VAL_LEN_SIZE = struct.calcsize(VAL_LEN_FMT)

# ---------- Helpers ----------
def md5_bits(key):
    """Devuelve una cadena binaria del hash MD5 (128 bits)."""
    h = hashlib.md5(str(key).encode()).hexdigest()
    return bin(int(h, 16))[2:].zfill(128)

# ---------- Bucket en disco ----------
class DiskBucket:
    def _init_(self, path: Path, capacity: int, local_depth: int = 1, is_overflow: bool = False, next_bucket_id: int = 0):
        self.path = Path(path)
        self.capacity = capacity
        self.local_depth = local_depth
        self.is_overflow = 1 if is_overflow else 0
        self.next_bucket_id = next_bucket_id  # 0 significa 'no next'
        self.items = {}  # key(str) -> value (python object)
        if self.path.exists():
            self._load()
        else:
            self._save()

    def _load(self):
        with open(self.path, "rb") as f:
            header = f.read(BUCKET_HEADER_SIZE)
            ld, is_ov, next_id, n_items = struct.unpack(BUCKET_HEADER_FMT, header)
            self.local_depth = ld
            self.is_overflow = is_ov
            self.next_bucket_id = next_id
            self.items = {}
            for _ in range(n_items):
                key_len_bytes = f.read(KEY_LEN_SIZE)
                if not key_len_bytes:
                    break
                (klen,) = struct.unpack(KEY_LEN_FMT, key_len_bytes)
                kbytes = f.read(klen)
                (vlen,) = struct.unpack(VAL_LEN_FMT, f.read(VAL_LEN_SIZE))
                vbytes = f.read(vlen)
                key = kbytes.decode("utf-8")
                val = pickle.loads(vbytes)
                self.items[key] = val

    def _save(self):
        with open(self.path, "wb") as f:
            header = struct.pack(BUCKET_HEADER_FMT, self.local_depth, self.is_overflow, self.next_bucket_id, len(self.items))
            f.write(header)
            for k, v in self.items.items():
                kbytes = k.encode("utf-8")
                vbytes = pickle.dumps(v)
                f.write(struct.pack(KEY_LEN_FMT, len(kbytes)))
                f.write(kbytes)
                f.write(struct.pack(VAL_LEN_FMT, len(vbytes)))
                f.write(vbytes)

    def is_full(self):
        return len(self.items) >= self.capacity

    def insert(self, key, value):
        self.items[key] = value
        self._save()

    def remove(self, key):
        if key in self.items:
            del self.items[key]
            self._save()
            return True
        return False

    def search(self, key):
        return self.items.get(key, None)

    def all_items(self):
        return dict(self.items)

    def clear(self):
        self.items = {}
        self.next_bucket_id = 0
        self._save()

    def _repr_(self):
        return f"DiskBucket(path={self.path.name}, ld={self.local_depth}, ov={self.is_overflow}, next={self.next_bucket_id}, items={self.items})"

# ---------- Directorio y lógica ----------
class DiskExtendibleHashing:
    def _init_(self, dir_path="eh_data", bucket_capacity=4, initial_global_depth=1, max_global_depth=4):
        """
        dir_path: carpeta donde se crean directory.dat y bucket_*.bin
        bucket_capacity: items por bucket (sin contar overflow)
        initial_global_depth: profundidad inicial (normalmente 1)
        max_global_depth: límite a la profundidad global; si se alcanza, se usa chaining en lugar de duplicar.
        """
        self.base = Path(dir_path)
        self.buckets_dir = self.base / "buckets"
        self.directory_file = self.base / "directory.dat"
        self.bucket_capacity = bucket_capacity
        self.base.mkdir(parents=True, exist_ok=True)
        self.buckets_dir.mkdir(parents=True, exist_ok=True)

        # Si existe directory.dat, cargar; si no, inicializar con 2^initial_global_depth buckets
        if self.directory_file.exists():
            self._load_directory()
        else:
            self.global_depth = initial_global_depth
            self.max_global_depth = max_global_depth
            # next bucket id (start after initial ones)
            self.next_bucket_id = 0
            # crear 2^global_depth buckets
            dir_len = 2 ** self.global_depth
            self.directory = []
            for i in range(dir_len):
                bid = self._new_bucket_id()
                self.directory.append(bid)
                self._create_bucket_file(bid, local_depth=self.global_depth if self.global_depth>1 else 1)
            self._save_directory()

    # ---------- Directory persistence ----------
    def _load_directory(self):
        with open(self.directory_file, "rb") as f:
            header = f.read(DIR_HEADER_SIZE)
            gd, mgd, next_id, dir_len = struct.unpack(DIR_HEADER_FMT, header)
            self.global_depth = gd
            self.max_global_depth = mgd
            self.next_bucket_id = next_id
            self.directory = []
            for _ in range(dir_len):
                (bid,) = struct.unpack(DIR_ENTRY_FMT, f.read(DIR_ENTRY_SIZE))
                self.directory.append(bid)

    def _save_directory(self):
        with open(self.directory_file, "wb") as f:
            dir_len = len(self.directory)
            header = struct.pack(DIR_HEADER_FMT, self.global_depth, self.max_global_depth, self.next_bucket_id, dir_len)
            f.write(header)
            for bid in self.directory:
                f.write(struct.pack(DIR_ENTRY_FMT, bid))

    def _bucket_path(self, bucket_id):
        return self.buckets_dir / f"bucket_{bucket_id}.bin"

    def _new_bucket_id(self):
        # asigna y avanza next_bucket_id
        if not hasattr(self, "next_bucket_id"):
            self.next_bucket_id = 0
        bid = self.next_bucket_id
        self.next_bucket_id += 1
        return bid

    def _create_bucket_file(self, bucket_id, local_depth=1, is_overflow=False, next_bucket_id=0):
        path = self._bucket_path(bucket_id)
        b = DiskBucket(path, capacity=self.bucket_capacity, local_depth=local_depth, is_overflow=is_overflow, next_bucket_id=next_bucket_id)
        b._save()
        return b

    def _load_bucket(self, bucket_id):
        path = self._bucket_path(bucket_id)
        if not path.exists():
            # crear uno vacío si no existe
            return self._create_bucket_file(bucket_id, local_depth=self.global_depth)
        return DiskBucket(path, capacity=self.bucket_capacity)

    # ---------- Hash helpers ----------
    def _get_index(self, key):
        bits = md5_bits(key)
        # tomar los últimos global_depth bits
        idx = int(bits[-self.global_depth:], 2) if self.global_depth > 0 else 0
        return idx

    # ---------- Operaciones públicas ----------
    def search(self, key):
        idx = self._get_index(key)
        bucket_id = self.directory[idx]
        # recorrer cadena (incluyendo overflows)
        bid = bucket_id
        while bid != 0:
            b = self._load_bucket(bid)
            val = b.search(key)
            if val is not None:
                return val
            bid = b.next_bucket_id
        return None

    def add(self, key, value):
        idx = self._get_index(key)
        bucket_id = self.directory[idx]
        bucket = self._load_bucket(bucket_id)

        # si key ya existe en la cadena -> actualizar
        bid = bucket_id
        last_bucket = bucket
        last_bid = bucket_id

        while bid != 0:
            b = self._load_bucket(bid)
            if key in b.items:
                b.insert(key, value)  # sobrescribe
                self._save_directory()
                return
            if b.next_bucket_id == 0:
                last_bucket = b
                last_bid = bid
            bid = b.next_bucket_id

        # si hay espacio en el último bucket de la cadena
        if not last_bucket.is_full():
            last_bucket.insert(key, value)
            self._save_directory()
            return

        # Si bucket (y su cadena) está lleno -> intentar split si es posible
        primary_bucket_id = bucket_id
        primary_bucket = self._load_bucket(primary_bucket_id)

        # Si se puede dividir sin duplicar
        if primary_bucket.local_depth < self.global_depth:
            self._split_bucket(primary_bucket_id)
            self.add(key, value)
            return
        elif primary_bucket.local_depth == self.global_depth and self.global_depth < self.max_global_depth:
            # duplicar directorio y dividir
            self._double_directory()
            self._split_bucket(primary_bucket_id)
            self.add(key, value)
            return
        else:
            # Límite alcanzado -> chaining overflow
            new_bid = self._new_bucket_id()
            new_bucket = self._create_bucket_file(new_bid, local_depth=primary_bucket.local_depth, is_overflow=True,
                                                  next_bucket_id=0)
            last_bucket.next_bucket_id = new_bid
            last_bucket._save()
            new_bucket.insert(key, value)
            self._save_directory()
            return

    def remove(self, key):
        idx = self._get_index(key)
        bucket_id = self.directory[idx]
        prev_bid = None
        bid = bucket_id
        while bid != 0:
            b = self._load_bucket(bid)
            if key in b.items:
                removed = b.remove(key)
                # if this was an overflow bucket and becomes empty, we could reclaim it
                # For simplicity no reclamation now (but we unlink if empty overflow)
                if removed and b.is_overflow and len(b.items) == 0:
                    # unlink from chain
                    if prev_bid is not None:
                        prev_b = self._load_bucket(prev_bid)
                        prev_b.next_bucket_id = b.next_bucket_id
                        prev_b._save()
                    else:
                        # it's the primary bucket (shouldn't be overflow normally), just clear
                        pass
                    # optionally delete file
                    try:
                        os.remove(b.path)
                    except:
                        pass
                self._save_directory()
                return True
            prev_bid = bid
            bid = b.next_bucket_id
        return False

    # ---------- Internals: doubling and splitting ----------
    def _double_directory(self):
        old_len = len(self.directory)
        self.directory = self.directory + self.directory[:]  # duplicate pointers
        self.global_depth += 1
        # persist next_bucket_id in directory header by saving file
        self._save_directory()

    def _gather_chain_items(self, bucket_id):
        """Recoge todos los items del bucket 'principal' y su cadena de overflow
           Devuelve lista de (key, val) y borra los archivos de overflow (manteniendo el principal).
        """
        items = {}
        bid = bucket_id
        b = self._load_bucket(bid)
        items.update(b.items)
        # recorrer siguientes y acumular; luego borrar esos archivos y quitar enlaces
        next_bid = b.next_bucket_id
        while next_bid != 0:
            nb = self._load_bucket(next_bid)
            items.update(nb.items)
            # borrar archivo overflow
            try:
                os.remove(nb.path)
            except:
                pass
            next_bid = nb.next_bucket_id
        # Reset primary bucket chain info
        b.next_bucket_id = 0
        b.items = {}
        b._save()
        return items

    def _split_bucket(self, bucket_id):
        """Divide el bucket indicado. Maneja redistribución y actualización de punteros del directorio."""
        primary = self._load_bucket(bucket_id)
        old_ld = primary.local_depth
        new_ld = old_ld + 1
        primary.local_depth = new_ld

        # Si el local_depth > global_depth, NO duplicar aquí (el llamador decide si duplicar antes)
        # Creamos dos nuevos buckets
        bid1 = self._new_bucket_id()
        bid2 = self._new_bucket_id()
        b1 = self._create_bucket_file(bid1, local_depth=new_ld, is_overflow=False, next_bucket_id=0)
        b2 = self._create_bucket_file(bid2, local_depth=new_ld, is_overflow=False, next_bucket_id=0)

        # Recolectar todos los items del bucket principal y su cadena de overflow (para evitar perder datos)
        items = self._gather_chain_items(bucket_id)  # esto deja primary vacío y sin next

        # Redistribuir items según el bit de decisión (bit en posición local_depth desde el final)
        for k, v in items.items():
            bits = md5_bits(k)
            # bit a usar es el -new_ld'th desde el final (0-index)
            decision_bit = bits[-new_ld]
            if decision_bit == "0":
                b1.insert(k, v)
            else:
                b2.insert(k, v)

        # Ahora actualizar el directorio: las entradas que referían al bucket original deben referir a b1 o b2
        dir_len = len(self.directory)
        for i in range(dir_len):
            if self.directory[i] == bucket_id:
                # elegir según (i >> (new_ld-1)) & 1   OR usando bits
                # otra forma: comprobar el bit en la representacion del indice
                if ((i >> (new_ld - 1)) & 1) == 1:
                    self.directory[i] = bid2
                else:
                    self.directory[i] = bid1

        # sobrescribir el archivo del bucket original con b1 (para ahorrar IDs?) -> en este diseño mantenemos b1,b2
        # Guardar cambios en directorio
        self._save_directory()

    # ---------- Utilidades de inspección ----------
    def dump_status(self):
        s = f"Global depth: {self.global_depth}, Max global depth: {self.max_global_depth}, Dir size: {len(self.directory)}, next_bucket_id: {self.next_bucket_id}\n"
        for i, bid in enumerate(self.directory):
            b = self._load_bucket(bid)
            s += f"  [{i:0{self.global_depth}b}] -> bucket_{bid}.bin  (ld={b.local_depth}, ov={b.is_overflow}, next={b.next_bucket_id}, items={len(b.items)})\n"
        return s


# crear la estructura en disco (carpeta 'eh_data')
eh = DiskExtendibleHashing(dir_path="eh_data", bucket_capacity=2, initial_global_depth=1, max_global_depth=3)

# insertar
eh.add("A", {"val": 1})
eh.add("B", {"val": 2})
eh.add("C", {"val": 3})
eh.add("D", {"val": 4})
eh.add("E", {"val": 5})

print(eh.dump_status())

# buscar
print("B ->", eh.search("B"))

# borrar
eh.remove("B")
print("B ->", eh.search("B"))

# ver status final
print(eh.dump_status())