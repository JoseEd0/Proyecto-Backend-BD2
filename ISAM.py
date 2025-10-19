import os
import struct

BLOCK_FACTOR = 3
INDEX_BLOCK_FACTOR = 3

DATA_FILE = 'data_isam.bin'
INDEX_FILE = 'index_isam.bin'

RECORD_FORMAT = 'i'
RECORD_SIZE = struct.calcsize(RECORD_FORMAT)

class Record:
    def __init__(self, id_):
        self.id = id_

    def pack(self):
        return struct.pack(RECORD_FORMAT, self.id)

    @staticmethod
    def unpack(data):
        id_, = struct.unpack(RECORD_FORMAT, data)
        return Record(id_)

    def __repr__(self):
        return f"Record(id={self.id})"

class DataPage:
    def __init__(self, records=None, overflow=None):
        self.records = records or []
        self.overflow = overflow

    def is_full(self):
        return len(self.records) >= BLOCK_FACTOR

    def add_record(self, record):
        self.records.append(record)
        self.records.sort(key=lambda r: r.id)

    def __repr__(self):
        ids = [r.id for r in self.records]
        return f"DataPage(records={ids}, overflow={self.overflow})"

class ISAMFile:
    def __init__(self):
        self.data_pages = []
        self.index_level_1 = []
        self.index_root = []

    def build_from_records(self, records):
        records.sort(key=lambda r: r.id)
        for i in range(0, len(records), BLOCK_FACTOR):
            page_records = records[i:i + BLOCK_FACTOR]
            page = DataPage(page_records)
            self.data_pages.append(page)
        for i, page in enumerate(self.data_pages):
            max_key = max(r.id for r in page.records)
            self.index_level_1.append((max_key, i))
        for i in range(0, len(self.index_level_1), INDEX_BLOCK_FACTOR):
            chunk = self.index_level_1[i:i + INDEX_BLOCK_FACTOR]
            max_key = chunk[-1][0]
            self.index_root.append((max_key, i))
        self.save_to_disk()

    def save_to_disk(self):
        with open(DATA_FILE, 'wb') as df:
            for page in self.data_pages:
                for r in page.records:
                    df.write(r.pack())
        with open(INDEX_FILE, 'wb') as idxf:
            for key, page_index in self.index_level_1:
                idxf.write(struct.pack('ii', key, page_index))
            for key, page_index in self.index_root:
                idxf.write(struct.pack('ii', key, page_index))

    def search(self, key):
        index_block = None
        for max_key, i_index in self.index_root:
            if key <= max_key:
                index_block = i_index
                break
        if index_block is None:
            return None
        page_index = None
        for max_key, p_index in self.index_level_1[index_block:index_block + INDEX_BLOCK_FACTOR]:
            if key <= max_key:
                page_index = p_index
                break
        if page_index is None:
            return None
        page = self.data_pages[page_index]
        for r in page.records:
            if r.id == key:
                return r
        return None

    def add(self, record):
        for i, (max_key, page_index) in enumerate(self.index_level_1):
            if record.id <= max_key:
                page = self.data_pages[page_index]
                if not page.is_full():
                    page.add_record(record)
                else:
                    overflow_page = DataPage([record])
                    page.overflow = len(self.data_pages)
                    self.data_pages.append(overflow_page)
                break
        else:
            new_page = DataPage([record])
            self.data_pages.append(new_page)
            self.index_level_1.append((record.id, len(self.data_pages) - 1))
        self.save_to_disk()

    def range_search(self, start_key, end_key):
        result = []
        for page in self.data_pages:
            for r in page.records:
                if start_key <= r.id <= end_key:
                    result.append(r)
        return result

if __name__ == "__main__":
    records = [Record(id_) for id_ in
               [101, 105, 108, 110, 112, 115, 118, 120, 122, 125,
                128, 130, 133, 136, 139, 142, 145, 147, 149, 150]]

    isam = ISAMFile()
    isam.build_from_records(records)

    print("Índice raíz:", isam.index_root)
    print("Índice nivel 1:", isam.index_level_1)
    print("Páginas de datos:")
    for i, p in enumerate(isam.data_pages):
        print(f"  Página {i}: {p}")

    print("\nBuscar id=115 →", isam.search(115))
    print("Buscar rango [110, 130] →", isam.range_search(110, 130))

    print("\nInsertando id=111...")
    isam.add(Record(111))
    for i, p in enumerate(isam.data_pages):
        print(f"  Página {i}: {p}")