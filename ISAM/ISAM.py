import json
import os
from bisect import bisect_right
from typing import Any, Dict, List, Tuple, Optional


class ISAMIndex:
    """
    ISAM (3 niveles) con:
      - Área primaria en buckets ordenados por key (tamaño fijo: block_factor)
      - Directorio de 3 niveles: leaf (mínimos por bucket), root (agrupa leaves), super_root (agrupa roots)
      - Área de overflow por bucket (ordenado por key)
      - Heap file (JSONL) para almacenar el payload completo de cada fila (puntero = offset en bytes)

    Métodos:
      add(key:int, row:dict) -> bool
      search(key:int) -> List[dict]
      range_search(begin:int, end:int) -> List[dict]
      remove(key:int) -> int
      get_all() -> List[dict]
      clear() -> None
    """

    def __init__(self, file_path: str, block_factor: int = 4, root_factor: int = 8, super_factor: int = 8):
        self.file_path = file_path                   # base path sin extensión
        self.index_path = f"{file_path}.index.json"  # índice (directorios + buckets sin payload)
        self.heap_path = f"{file_path}.heap"         # heap con registros JSONL (binario)
        self.block_factor = int(block_factor)
        self.root_factor = int(root_factor)
        self.super_factor = int(super_factor)

        # Estructuras en memoria
        self.leaves: List[List[Tuple[int, int]]] = []   # lista de buckets; cada entrada: (key, offset_en_heap)
        self.dir_keys: List[int] = []                   # mínimas por bucket
        self.overflow: Dict[int, List[Tuple[int, int]]] = {}  # bi -> lista (key, offset)

        # índices superiores (3 niveles)
        self.root: List[Tuple[int, int]] = []        # (max_key del grupo de leaves, start_leaf_index)
        self.super_root: List[Tuple[int, int]] = []  # (max_key del grupo de roots, start_root_index)

        self._load_if_exists()

    # ------------------ Persistencia índice ------------------

    def _load_if_exists(self):
        if os.path.exists(self.index_path):
            try:
                with open(self.index_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                self.block_factor = int(data.get("block_factor", self.block_factor))
                self.root_factor = int(data.get("root_factor", self.root_factor))
                self.super_factor = int(data.get("super_factor", self.super_factor))
                self.leaves = [ [ (int(k), int(off)) for k, off in bucket ] for bucket in data.get("leaves", []) ]
                self.dir_keys = [ int(x) for x in data.get("dir_keys", []) ]
                self.overflow = { int(bi): [ (int(k), int(off)) for k, off in lst ]
                                  for bi, lst in data.get("overflow", {}).items() }
                self.root = [ (int(mx), int(start)) for mx, start in data.get("root", []) ]
                self.super_root = [ (int(mx), int(start)) for mx, start in data.get("super_root", []) ]
            except Exception:
                self._init_empty()
        else:
            self._init_empty()

    def _init_empty(self):
        self.leaves = [[]]          # al menos 1 bucket vacío
        self.dir_keys = []          # sin mínimas al inicio
        self.overflow = {}
        self.root = []
        self.super_root = []
        self._save()

    def _save(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        data = {
            "block_factor": self.block_factor,
            "root_factor": self.root_factor,
            "super_factor": self.super_factor,
            "leaves": self.leaves,
            "dir_keys": self.dir_keys,
            "overflow": { str(bi): lst for bi, lst in self.overflow.items() },
            "root": self.root,
            "super_root": self.super_root,
        }
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False)

    # ------------------ Heap (payload) ------------------

    def _heap_append(self, row: Dict) -> int:
        """Escribe una fila en el heap (JSONL binario). Retorna offset en bytes."""
        os.makedirs(os.path.dirname(self.heap_path), exist_ok=True)
        b = (json.dumps(row, ensure_ascii=False) + "\n").encode("utf-8")
        with open(self.heap_path, "ab") as f:
            pos = f.tell()
            f.write(b)
            return pos

    def _heap_read_at(self, offset: int) -> Optional[Dict]:
        """Lee una fila desde el heap usando el offset. Retorna dict o None si falla."""
        if not os.path.exists(self.heap_path):
            return None
        try:
            with open(self.heap_path, "rb") as f:
                f.seek(offset)
                line = f.readline()
            if not line:
                return None
            return json.loads(line.decode("utf-8"))
        except Exception:
            return None

    # ------------------ Directorio de 3 niveles ------------------

    def _rebuild_directories(self):
        """Reconstruye dir_keys (leaf), root y super_root basado en leaves."""
        self.dir_keys = []
        for bucket in self.leaves:
            if bucket:
                self.dir_keys.append(bucket[0][0])
            else:
                self.dir_keys.append(2**63-1)  # placeholder "infinito"

        # Root: agrupa leaves en bloques de root_factor
        self.root = []
        if self.dir_keys:
            leaf_max = []
            for i, bucket in enumerate(self.leaves):
                mx = bucket[-1][0] if bucket else 2**63-1
                leaf_max.append((mx, i))
            for gstart in range(0, len(leaf_max), self.root_factor):
                group = leaf_max[gstart:gstart+self.root_factor]
                gmax = max(mx for mx, _ in group)
                self.root.append((gmax, group[0][1]))

        # Super-root: agrupa roots en bloques de super_factor
        self.super_root = []
        if self.root:
            for gstart in range(0, len(self.root), self.super_factor):
                group = self.root[gstart:gstart+self.super_factor]
                gmax = max(mx for mx, _ in group)
                self.super_root.append((gmax, gstart))

    # ------------------ Navegación ------------------

    def _leaf_index_for_key(self, key: int) -> int:
        """Busca bucket usando dir_keys con bisect. Si no hay dir_keys, retorna 0."""
        if not self.dir_keys:
            return 0
        idx = bisect_right(self.dir_keys, key) - 1
        if idx < 0:
            idx = 0
        if idx >= len(self.leaves):
            idx = len(self.leaves) - 1
        return idx

    # ------------------ API ------------------

    def add(self, key: int, row: Dict) -> bool:
        """Inserta (key,row). Si el bucket está lleno, inserta en overflow."""
        if not isinstance(key, int):
            raise ValueError("ISAMIndex: la key debe ser int")
        off = self._heap_append(row)

        bi = self._leaf_index_for_key(key)
        bucket = self.leaves[bi]
        if len(bucket) < self.block_factor:
            i = 0
            while i < len(bucket) and bucket[i][0] <= key:
                i += 1
            bucket.insert(i, (key, off))
            if not self.dir_keys:
                self.dir_keys = [key] + [2**63-1]*(len(self.leaves)-1)
                self._rebuild_directories()
            else:
                if key < self.dir_keys[bi]:
                    self.dir_keys[bi] = key
                    self._rebuild_directories()
            self._save()
            return True

        of = self.overflow.setdefault(bi, [])
        j = 0
        while j < len(of) and of[j][0] <= key:
            j += 1
        of.insert(j, (key, off))
        self._save()
        return True

    def search(self, key: int) -> List[Dict]:
        """Igualdad por key. Devuelve una lista de filas (puede haber duplicados)."""
        if not isinstance(key, int):
            return []
        bi = self._leaf_index_for_key(key)
        out: List[Dict] = []
        for k, off in self.leaves[bi]:
            if k == key:
                rec = self._heap_read_at(off)
                if rec is not None:
                    out.append(rec)
        for k, off in self.overflow.get(bi, []):
            if k == key:
                rec = self._heap_read_at(off)
                if rec is not None:
                    out.append(rec)
        return out

    def range_search(self, begin_key: int, end_key: int) -> List[Dict]:
        """Rango inclusivo [begin, end]."""
        if begin_key > end_key:
            begin_key, end_key = end_key, begin_key
        out: List[Dict] = []
        if not self.leaves:
            return out
        start_bi = self._leaf_index_for_key(begin_key)
        last_idx = bisect_right(self.dir_keys, end_key) - 1 if self.dir_keys else len(self.leaves)-1
        if last_idx < 0:
            last_idx = 0
        if last_idx >= len(self.leaves):
            last_idx = len(self.leaves) - 1
        for bi in range(start_bi, last_idx + 1):
            for k, off in self.leaves[bi]:
                if begin_key <= k <= end_key:
                    rec = self._heap_read_at(off)
                    if rec is not None:
                        out.append(rec)
            for k, off in self.overflow.get(bi, []):
                if begin_key <= k <= end_key:
                    rec = self._heap_read_at(off)
                    if rec is not None:
                        out.append(rec)
        return out

    def remove(self, key: int) -> int:
        """Elimina todas las ocurrencias de 'key' del índice (no compacta heap). Retorna # entradas eliminadas."""
        removed = 0
        if not self.leaves:
            return 0
        bi = self._leaf_index_for_key(key)
        before = len(self.leaves[bi])
        self.leaves[bi] = [kv for kv in self.leaves[bi] if kv[0] != key]
        removed += before - len(self.leaves[bi])
        if bi in self.overflow:
            before = len(self.overflow[bi])
            self.overflow[bi] = [kv for kv in self.overflow[bi] if kv[0] != key]
            removed += before - len(self.overflow[bi])
            if not self.overflow[bi]:
                self.overflow.pop(bi, None)
        # actualizar mínimas
        new_min = self.leaves[bi][0][0] if self.leaves[bi] else 2**63-1
        if self.dir_keys and self.dir_keys[bi] != new_min:
            self.dir_keys[bi] = new_min
            self._rebuild_directories()
        self._save()
        return removed

    def get_all(self) -> List[Dict]:
        out: List[Dict] = []
        for bi, bucket in enumerate(self.leaves):
            for _, off in bucket:
                rec = self._heap_read_at(off)
                if rec is not None:
                    out.append(rec)
            for _, off in self.overflow.get(bi, []):
                rec = self._heap_read_at(off)
                if rec is not None:
                    out.append(rec)
        return out

    # ------------- Utilidades -------------

    def build_from_records(self, items: List[Tuple[int, Dict]]):
        """Construye la primaria desde cero con items (key,row). Overflow vacía, heap reconstruido."""
        items = sorted(items, key=lambda x: x[0])
        if os.path.exists(self.heap_path):
            try:
                os.remove(self.heap_path)
            except Exception:
                pass
        self.leaves = []
        bucket: List[Tuple[int, int]] = []
        for key, row in items:
            off = self._heap_append(row)
            bucket.append((int(key), off))
            if len(bucket) >= self.block_factor:
                self.leaves.append(bucket)
                bucket = []
        if bucket or not self.leaves:
            self.leaves.append(bucket)
        self.overflow = {}
        self._rebuild_directories()
        self._save()

    def clear(self):
        """Vacia índice y heap."""
        if os.path.exists(self.heap_path):
            try:
                os.remove(self.heap_path)
            except Exception:
                pass
        self._init_empty()
        self._save()


def create_isam_index(file_path: str, block_factor: int = 4) -> ISAMIndex:
    return ISAMIndex(file_path=file_path, block_factor=block_factor)

# Alias para compatibilidad con adaptadores existentes
ISAMFile = ISAMIndex

def Record(id: int, *args, **kwargs):
    class _R:
        def __init__(self, id):
            self.id = id
        def __repr__(self):
            return f"<Record id={self.id}>"
    return _R(id)
