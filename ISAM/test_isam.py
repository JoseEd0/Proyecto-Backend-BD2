# test_isam_adaptado.py
# Prueba del ISAM (3 niveles) con heap JSONL variable-length
# Requiere: ISAM/ISAM.py (el que te pasé)

import os
import shutil
from ISAM import create_isam_index, ISAMIndex



def banner(title):
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def main():
    base_dir = os.path.join("data", "isam_test", "Productos")
    os.makedirs(os.path.dirname(base_dir), exist_ok=True)

    # Limpia carpeta de pruebas si existe para empezar “desde cero”
    if os.path.exists(os.path.dirname(base_dir)):
        shutil.rmtree(os.path.dirname(base_dir), ignore_errors=True)
    os.makedirs(os.path.dirname(base_dir), exist_ok=True)

    # Crea índice
    idx = create_isam_index(file_path=base_dir, block_factor=3)  # bucket size pequeño para forzar overflow
    idx.clear()  # asegúrate de partir vacío

    # ---------------- Inserciones ----------------
    banner("INSERTANDO REGISTROS")
    rows = [
        (10, {"id": 10, "nombre": "A",  "precio": 100}),
        (11, {"id": 11, "nombre": "B",  "precio": 120}),
        (15, {"id": 15, "nombre": "C",  "precio": 90}),
        (20, {"id": 20, "nombre": "D",  "precio": 130}),
        (20, {"id": 20, "nombre": "D2", "precio": 140}),  # duplicado → overflow
        (25, {"id": 25, "nombre": "E",  "precio": 110}),
        (30, {"id": 30, "nombre": "F",  "precio": 95}),
    ]
    for k, row in rows:
        ok = idx.add(k, row)
        print(f"add({k}) -> {ok}")
        assert ok

    all_rows = idx.get_all()
    print(f"get_all() -> {len(all_rows)} filas")
    assert len(all_rows) == len(rows)

    # ---------------- Igualdad ----------------
    banner("BUSQUEDA POR IGUALDAD (id = 20)")
    eq_20 = idx.search(20)
    print("search(20) ->", eq_20)
    # Deben existir 2 filas con id=20
    assert len(eq_20) == 2
    assert {r["nombre"] for r in eq_20} == {"D", "D2"}

    # ---------------- Rango ----------------
    banner("BUSQUEDA POR RANGO [11, 18]")
    rng = idx.range_search(11, 18)
    print("range_search(11, 18) ->", rng)
    ids = {r["id"] for r in rng}
    assert ids == {11, 15}

    banner("BUSQUEDA POR RANGO [15, 30]")
    rng2 = idx.range_search(15, 30)
    print("range_search(15, 30) ->", [r["id"] for r in rng2])
    ids2 = [r["id"] for r in rng2]
    # Debe incluir 15, 20, 20, 25, 30 (con duplicado 20)
    assert sorted(ids2) == [15, 20, 20, 25, 30]

    # ---------------- Eliminar ----------------
    banner("ELIMINACIÓN id=11")
    removed = idx.remove(11)
    print("remove(11) ->", removed)
    assert removed >= 1
    post = idx.search(11)
    print("search(11) ->", post)
    assert post == []

    # ---------------- Persistencia ----------------
    banner("VERIFICANDO PERSISTENCIA (re-abrir índice)")
    idx2 = create_isam_index(file_path=base_dir, block_factor=3)  # reabre desde disco
    again_all = idx2.get_all()
    print(f"get_all() tras reabrir -> {len(again_all)} filas")
    # Original eran 7, quitamos id=11 → 6
    assert len(again_all) == 6

    # Igualdad y rango siguen consistentes
    eq_20_b = idx2.search(20)
    print("search(20) (reabierto) ->", eq_20_b)
    assert len(eq_20_b) == 2

    rng_b = idx2.range_search(10, 20)
    print("range_search(10, 20) (reabierto) ->", [r['id'] for r in rng_b])
    assert sorted([r["id"] for r in rng_b]) == [10, 15, 20, 20]

    banner("OK — Todas las pruebas pasaron")


if __name__ == "__main__":
    main()
