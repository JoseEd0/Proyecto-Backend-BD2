# test_bplustree.py
"""
TEST de B+Tree (CS2702) usando tu implementación persistente.

Preparación:
1) Crea un archivo `bplustree.py` en la misma carpeta con tus clases:
   - BPlusTreeNode, BPlusFile, BPlusTree (pega tu código tal cual).
2) Genera los datasets con:
       python make_testdata.py
3) Ejecuta pruebas:
       python test_bplustree.py --index-name prueba --dataset small
       python test_bplustree.py --index-name prueba2 --dataset large
"""

import json
import time
import argparse
from pathlib import Path

from bplustree import BPlusTree, BPlusFile   # <-- importa tu implementación

# =====(OPCIONAL) Contadores de I/O por monkey patch =====
# Descomenta para ver lecturas/escrituras reales desde tus métodos de archivo.
"""
_or_read_node = BPlusFile.read_node
_or_write_node = BPlusFile.write_node
_or_write_header = BPlusFile.write_header
BPLUS_IO = {"reads":0, "writes":0, "wh":0}

def _count_read(self, node_id):
    BPLUS_IO["reads"] += 1
    return _or_read_node(self, node_id)

def _count_write(self, node, node_id=None):
    BPLUS_IO["writes"] += 1
    return _or_write_node(self, node, node_id)

def _count_write_header(self, root_position):
    BPLUS_IO["wh"] += 1
    return _or_write_header(self, root_position)

BPlusFile.read_node = _count_read
BPlusFile.write_node = _count_write
BPlusFile.write_header = _count_write_header
"""

def load_dataset(which):
    fn = "testdata_restaurantes_small.json" if which == "small" else "testdata_restaurantes_large.json"
    with open(fn, "r", encoding="utf-8") as f:
        return json.load(f)

def ensure_clean_dir(dirpath):
    p = Path(dirpath)
    p.mkdir(parents=True, exist_ok=True)
    for f in p.iterdir():
        if f.is_file():
            f.unlink()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--index-name", default="test_json", help="Nombre lógico del índice/archivo .dat")
    ap.add_argument("--dataset", choices=["small","large"], default="small")
    ap.add_argument("--order", type=int, default=4, help="Orden lógico del B+Tree (usa BLOCK_FACTOR si None).")
    args = ap.parse_args()

    storage = "bplustree_nodes"
    ensure_clean_dir(storage)  # reinicia carpeta de nodos

    # Carga dataset
    rows = load_dataset(args.dataset)
    keys = [row["id"] for row in rows]

    # Construye árbol y limpia
    tree = BPlusTree(order=args.order, storage_path=storage, index_name=args.index_name)
    tree.clear()

    # Inserción
    t0 = time.perf_counter()
    for row in rows:
        k = row["id"]
        # referencia simple; puedes guardar más info si deseas
        ref = {"dataset": args.dataset, "id": k}
        tree.add(k, ref)
    t1 = time.perf_counter()

    print("="*60)
    print(f"INSERTADOS: {len(rows)}   (dataset={args.dataset})")
    print(f"Tiempo inserción: {(t1-t0)*1000:.2f} ms")

    # Búsquedas exactas (muestra representativos)
    probe = [keys[0], keys[len(keys)//2], keys[-1], max(keys)//2, min(keys)+1]
    print("\nBUSQUEDAS EXACTAS:")
    for k in probe:
        res = tree.search(k)
        print(f"  search({k}) -> {res}")

    # Range search
    a = min(keys) + (max(keys)-min(keys))//3
    b = min(keys) + 2*((max(keys)-min(keys))//3)
    t2 = time.perf_counter()
    rs = tree.range_search(a, b)
    t3 = time.perf_counter()
    print("\nRANGE SEARCH:")
    print(f"  rango [{a}, {b}] -> {len(rs)} resultados  (en {(t3-t2)*1000:.2f} ms)")
    if len(rs) <= 20:
        print("  ", rs)

    # Eliminaciones básicas
    todel = [keys[0], keys[-1], keys[len(keys)//2]]
    print("\nELIMINACIONES:")
    for k in todel:
        tree.remove(k)
        after = tree.search(k)
        print(f"  remove({k}); search({k}) -> {after}")

    # Recorrer todo en orden
    all_pairs = tree.get_all()
    print("\nGET_ALL (primeros 20):")
    print(all_pairs[:20])
    print(f"TOTAL EN ÁRBOL TRAS ELIMINAR: {len(all_pairs)}")

    # Ver estructura
    print("\nESTRUCTURA DEL ÁRBOL:")
    tree.print_tree()

    # Mostrar contadores I/O si activaste el bloque
    # print("\nI/O:", BPLUS_IO)

if __name__ == "__main__":
    main()