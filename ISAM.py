import os
import struct
from fileinput import filename

BLOCK_FACTOR = 3
INDEX_BLOCK_FACTOR = 3

class Record:
    FORMAT = 'i'
    SIZE_OF_RECORD = struct.calcsize(FORMAT)
    def __init__(self, id_: int):
        self.id = id_

    def pack(self) -> bytes:
        return struct.pack(
            self.FORMAT,
            self.id
        )

    @staticmethod
    def unpack(data):
        id_, = struct.unpack(Record.FORMAT, data)
        return Record(id_)

    def __repr__(self):
        return f"Record(id={self.id})"

class DataPage:
    HEADER_FORMAT = 'ii'
    HEADER_SIZE = struct.calcsize(HEADER_FORMAT)
    SIZE_OF_PAGE = HEADER_SIZE + BLOCK_FACTOR * Record.SIZE_OF_RECORD

    def __init__(self, records=None, next_page=-1):
        self.records = list(records) if records else []
        self.next_page = next_page

    def has_space(self):
        return len(self.records) < BLOCK_FACTOR

    def is_full(self):
        return len(self.records) >= BLOCK_FACTOR

    def pack(self) -> bytes:
        header_data = struct.pack(self.HEADER_FORMAT, len(self.records), self.next_page)
        records_data = b''.join(r.pack() for r in self.records)
        pad = BLOCK_FACTOR - len(self.records)
        if pad > 0:
            records_data += b'\x00' * (pad * Record.SIZE_OF_RECORD)
        return header_data + records_data

    @staticmethod
    def unpack(data: bytes):
        size, next_page = struct.unpack(DataPage.HEADER_FORMAT, data[:DataPage.HEADER_SIZE])
        records = []
        offset = DataPage.HEADER_SIZE
        for _ in range(size):
            chunk = data[offset: offset + Record.SIZE_OF_RECORD]
            records.append(Record.unpack(chunk))
            offset += Record.SIZE_OF_RECORD
        return DataPage(records, next_page)

class ISAMFile:
    INDEX_ENTRY_FMT = 'ii'
    INDEX_ENTRY_SIZE = struct.calcsize(INDEX_ENTRY_FMT)

    def __init__(self, filename):
        self.filename = filename
        self.filename_idx = filename + '_idx'
        self.leaf = []
        self.root = []
        self.primary_page_count = 0

    @staticmethod
    def _first_ge_index(keys, key):
        for i, v in enumerate(keys):
            if v >= key:
                return i
        return len(keys)

    def _file_size(self):
        return os.path.getsize(self.filename) if os.path.exists(self.filename) else 0

    def _total_pages(self):
        return self._file_size() // DataPage.SIZE_OF_PAGE

    def _read_page(self, f, page_no) -> DataPage:
        f.seek(page_no * DataPage.SIZE_OF_PAGE)
        data = f.read(DataPage.SIZE_OF_PAGE)
        return DataPage.unpack(data)

    def _write_page(self, f, page_no, page: DataPage):
        f.seek(page_no * DataPage.SIZE_OF_PAGE)
        f.write(page.pack())

    def _append_page(self, f, page: DataPage) -> int:
        f.seek(0, os.SEEK_END)
        pos = f.tell()
        f.write(page.pack())
        return pos // DataPage.SIZE_OF_PAGE

    def _save_index(self):
        with open(self.filename_idx, 'wb') as f:
            f.write(struct.pack('i', len(self.leaf)))
            for mx, pno in self.leaf:
                f.write(struct.pack(self.INDEX_ENTRY_FMT, mx, pno))
            f.write(struct.pack('i', len(self.root)))
            for mx, start in self.root:
                f.write(struct.pack(self.INDEX_ENTRY_FMT, mx, start))

    def _load_index(self):
        self.leaf, self.root = [], []
        if not os.path.exists(self.filename_idx):
            self.primary_page_count = 0
            return
        with open(self.filename_idx, 'rb') as f:
            b = f.read(4)
            if not b:
                self.primary_page_count = 0
                return
            n_leaf = struct.unpack('i', b)[0]
            for _ in range(n_leaf):
                mx, pno = struct.unpack(self.INDEX_ENTRY_FMT, f.read(self.INDEX_ENTRY_SIZE))
                self.leaf.append((mx, pno))
            n_root_b = f.read(4)
            if not n_root_b:
                return
            n_root = struct.unpack('i', n_root_b)[0]
            for _ in range(n_root):
                mx, start = struct.unpack(self.INDEX_ENTRY_FMT, f.read(self.INDEX_ENTRY_SIZE))
                self.root.append((mx, start))
        self.primary_page_count = len(self.leaf)

    def build_index(self):
        self.leaf, self.root = [], []
        if not os.path.exists(self.filename):
            self._save_index()
            return
        total = self._total_pages()
        with open(self.filename, 'rb') as f:
            for i in range(total):
                page = self._read_page(f, i)
                if len(page.records) == 0:
                    break
                max_key = max(r.id for r in page.records)
                self.leaf.append((max_key, i))
        self.primary_page_count = len(self.leaf)
        for i in range(0, len(self.leaf), INDEX_BLOCK_FACTOR):
            bloque = self.leaf[i:i + INDEX_BLOCK_FACTOR]
            max_key = bloque[-1][0]
            self.root.append((max_key, i))
        self._save_index()

    def _root_find_block(self, key):
        if not self.root:
            return None
        keys = [mx for mx, _ in self.root]
        i = self._first_ge_index(keys, key)
        return self.root[i][1] if i < len(self.root) else None

    def _leaf_find_primary(self, start_idx, key):
        sub = self.leaf[start_idx:start_idx + INDEX_BLOCK_FACTOR]
        if not sub:
            return None
        keys = [mx for mx, _ in sub]
        j = self._first_ge_index(keys, key)
        return sub[j][1] if j < len(sub) else sub[-1][1]

    def _find_primary_page_for_key(self, key):
        self._load_index()
        if not self.leaf:
            return None
        start = self._root_find_block(key)
        if start is None:
            return self.leaf[-1][1]
        return self._leaf_find_primary(start, key)

    def build_from_records(self, records):
        recs = sorted(records, key=lambda r: r.id)
        with open(self.filename, 'wb') as f:
            for i in range(0, len(recs), BLOCK_FACTOR):
                chunk = recs[i:i + BLOCK_FACTOR]
                page = DataPage(chunk, -1)
                self._append_page(f, page)
        self.build_index()

    def add(self, record: Record):
        self._load_index()
        if not os.path.exists(self.filename):
            with open(self.filename, 'wb') as f:
                self._append_page(f, DataPage([record], -1))
            self.build_index()
            return
        target_page = self._find_primary_page_for_key(record.id)
        if target_page is None:
            with open(self.filename, 'wb') as f:
                self._append_page(f, DataPage([record], -1))
            self.build_index()
            return
        with open(self.filename, 'r+b') as f:
            page = self._read_page(f, target_page)
            if page.has_space():
                ids = [r.id for r in page.records]
                pos = 0
                for i, v in enumerate(ids):
                    if record.id <= v:
                        pos = i
                        break
                else:
                    pos = len(ids)
                page.records.insert(pos, record)
                self._write_page(f, target_page, page)
                return
            prev = target_page
            curr = page.next_page
            while curr != -1:
                p = self._read_page(f, curr)
                if p.has_space():
                    p.records.append(record)
                    self._write_page(f, curr, p)
                    return
                prev = curr
                curr = p.next_page
            new_page = DataPage([record], -1)
            new_no = self._append_page(f, new_page)
            if prev == target_page:
                page.next_page = new_no
                self._write_page(f, target_page, page)
            else:
                last = self._read_page(f, prev)
                last.next_page = new_no
                self._write_page(f, prev, last)

    def search(self, key):
        self._load_index()
        if not os.path.exists(self.filename):
            return []
        page_no = self._find_primary_page_for_key(key)
        if page_no is None:
            return []
        result = []
        with open(self.filename, 'rb') as f:
            p = self._read_page(f, page_no)
            for r in p.records:
                if r.id == key:
                    result.append(r)
                elif r.id > key:
                    break
            ov = p.next_page
            while ov != -1:
                op = self._read_page(f, ov)
                for r in op.records:
                    if r.id == key:
                        result.append(r)
                ov = op.next_page
        return result

    def range_search(self, start, end):
        self._load_index()
        if not os.path.exists(self.filename):
            return []
        if start > end:
            start, end = end, start
        res = []
        start_page = self._find_primary_page_for_key(start)
        if start_page is None:
            return res
        total = self.primary_page_count
        with open(self.filename, 'rb') as f:
            p = start_page
            while p < total:
                page = self._read_page(f, p)
                for r in page.records:
                    if start <= r.id <= end:
                        res.append(r)
                    elif r.id > end:
                        return res
                ov = page.next_page
                while ov != -1:
                    op = self._read_page(f, ov)
                    for r in op.records:
                        if start <= r.id <= end:
                            res.append(r)
                    ov = op.next_page
                p += 1
        return res

    def remove(self, key):
        self._load_index()
        if not os.path.exists(self.filename):
            return 0
        removed = 0
        page_no = self._find_primary_page_for_key(key)
        if page_no is None:
            return 0
        with open(self.filename, 'r+b') as f:
            page = self._read_page(f, page_no)
            before = len(page.records)
            page.records = [r for r in page.records if r.id != key]
            removed += before - len(page.records)
            self._write_page(f, page_no, page)
            ov = page.next_page
            while ov != -1:
                op = self._read_page(f, ov)
                before = len(op.records)
                op.records = [r for r in op.records if r.id != key]
                removed += before - len(op.records)
                self._write_page(f, ov, op)
                ov = op.next_page
        return removed

    def scanAll(self):
        if not os.path.exists(self.filename):
            print("(Archivo vacío)")
            return
        total = self._total_pages()
        with open(self.filename, 'rb') as f:
            for pno in range(total):
                page = self._read_page(f, pno)
                print(f"Página {pno} [size={len(page.records)}, next={page.next_page}]")
                for i, r in enumerate(page.records, 1):
                    print(f"  - {r}")
        self._load_index()
        print("==== LEAF ====")
        for mx, pno in self.leaf:
            print(f"  ({mx} -> {pno})")
        print("==== ROOT ====")
        for mx, start in self.root:
            print(f"  ({mx} -> {start})")

if __name__ == "__main__":
    for fn in ["isam_data.dat", "isam_data.dat_idx"]:
        try: os.remove(fn)
        except: pass
    isam = ISAMFile("isam_data.dat")
    base = [Record(i) for i in [101, 105, 108, 110, 112, 115, 118, 120, 122, 125]]
    isam.build_from_records(base)
    print("== Estructura inicial ==")
    isam.scanAll()
    print("\nInsertando nuevos registros...")
    isam.add(Record(111))
    isam.add(Record(113))
    isam.add(Record(114))
    isam.scanAll()
    print("\nsearch(112) ->", isam.search(112))
    print("range_search [108,115] ->", isam.range_search(108,115))
    print("\nremove(111) -> eliminados:", isam.remove(111))
    isam.scanAll()