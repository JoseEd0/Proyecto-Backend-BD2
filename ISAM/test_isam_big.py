# test_grande_isam.py
from ISAM import ISAMFile, Record
import os

def print_index_hierarchy(isam):
    isam._load_index()
    leaf = isam.leaf
    root = isam.root
    sroot = isam.super_root

    print("\n================= MAPA JERÁRQUICO DEL ÍNDICE =================")
    print(f"Leaf entries: {len(leaf)}  |  Root entries: {len(root)}  |  SuperRoot entries: {len(sroot)}\n")

    def leaf_block_to_str(start_leaf_idx, block_len):
        pairs = leaf[start_leaf_idx:start_leaf_idx + block_len]
        return ", ".join([f"(max={mx}, pág={p})" for (mx, p) in pairs])

    for i, (mx_s, root_start) in enumerate(sroot):

        ROOT_BLOCK_FACTOR = getattr(isam, "ROOT_BLOCK_FACTOR", 3)
        LEAF_BLOCK_FACTOR = getattr(isam, "LEAF_BLOCK_FACTOR", 3)

        root_block = root[root_start: root_start + ROOT_BLOCK_FACTOR]
        print(f"SR[{i}] max_key={mx_s}  -> Root idx [{root_start} .. {root_start + len(root_block) - 1}]")


        for j, (mx_r, leaf_start) in enumerate(root_block):
            leaf_block = leaf[leaf_start: leaf_start + LEAF_BLOCK_FACTOR]
            print(f"   R[{root_start + j}] max_key={mx_r}  -> Leaf idx [{leaf_start} .. {leaf_start + len(leaf_block) - 1}]")

            print(f"      Leaf block: {leaf_block_to_str(leaf_start, len(leaf_block))}")
    print("================================================================\n")


def make_name(i):
    return f"R{i:03d}"

def make_date(i):
    day = (i % 28) + 1
    return f"2025-10-{day:02d}"

def test_grande_isam():
    for fn in ["rest_isam.dat", "rest_isam.dat_idx"]:
        try: os.remove(fn)
        except: pass

    isam = ISAMFile("rest_isam.dat")

    base = [Record(i, make_name(i), make_date(i), 3.0 + (i % 20) * 0.05) for i in range(1, 55)]
    isam.build_from_records(base)

    print("== Estructura inicial (solo índice) ==")
    print_index_hierarchy(isam)

    inserts = [6, 7, 8, 20, 21, 22, 37, 38, 39, 52, 53, 54, 60, 60, 60]
    for x in inserts:
        isam.add(Record(x, make_name(x), make_date(x), 4.0))

    print("== Índice tras inserciones (el índice sigue estático; cambian overflows) ==")
    print_index_hierarchy(isam)

    print("search(id=20) ->", isam.search(20))
    print("range_search [18, 23] ->", isam.range_search(18, 23))
    print("search(id=60) ->", isam.search(60))

    print("\nremove(id=60) -> eliminados:", isam.remove(60))
    print("search(id=60) ->", isam.search(60))

if __name__ == "__main__":
    test_grande_isam()