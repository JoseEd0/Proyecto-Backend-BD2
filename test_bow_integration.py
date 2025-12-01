import sys
import os
import shutil
import nltk

# Ensure NLTK data is available
try:
    nltk.data.find('tokenizers/punkt')
    nltk.data.find('tokenizers/punkt_tab')
except LookupError:
    print("Downloading NLTK data...")
    nltk.download('punkt')
    nltk.download('punkt_tab')

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from parser.unified_adapter import UnifiedDatabaseAdapter, StructureType
from parser.sql_engine import create_sql_parser_engine

def test_bow_integration():
    data_dir = "test_data_bow"
    if os.path.exists(data_dir):
        shutil.rmtree(data_dir)
    
    adapter = UnifiedDatabaseAdapter(data_dir=data_dir)
    engine = create_sql_parser_engine(database_adapter=adapter)
    
    # 1. Create Table with BOW index
    print("\n1. Creating Table 'Articles' with BOW index...")
    sql_create = """
    CREATE TABLE Articles (
        id INT KEY,
        content VARCHAR[1000] INDEX BOW
    );
    """
    res = engine.execute_sql(sql_create)
    if res["success"]:
        print("[OK] Table created successfully.")
        print(f"Table structure: {adapter.table_structures.get('Articles')}")
        from parser.unified_adapter import HAS_BOW
        print(f"HAS_BOW: {HAS_BOW}")
        with open("status.txt", "w") as f:
            f.write(f"Table structure: {adapter.table_structures.get('Articles')}\n")
            f.write(f"HAS_BOW: {HAS_BOW}\n")
    else:
        print(f"[ERROR] Failed to create table: {res['errors']}")
        return

    # 2. Insert Documents
    print("\n2. Inserting documents...")
    docs = [
        (1, "El aprendizaje automático es una rama de la inteligencia artificial."),
        (2, "La inteligencia artificial transforma el mundo."),
        (3, "El aprendizaje profundo es parte del aprendizaje automático."),
        (4, "Los datos son el nuevo petróleo."),
        (5, "Python es excelente para ciencia de datos e inteligencia artificial.")
    ]
    
    for doc_id, content in docs:
        sql_insert = f"INSERT INTO Articles VALUES ({doc_id}, '{content}');"
        res = engine.execute_sql(sql_insert)
        if res["success"]:
            print(f"[OK] Inserted doc {doc_id}")
            with open("status.txt", "a") as f:
                f.write(f"Inserted doc {doc_id}\n")
        else:
            print(f"[ERROR] Failed to insert doc {doc_id}: {res['errors']}")

    # 3. Search by Keyword
    print("\n3. Searching for 'inteligencia'...")
    sql_search = "SELECT * FROM Articles WHERE content = 'inteligencia';"
    res = engine.execute_sql(sql_search)
    if res["success"]:
        print(f"Found {len(res['result'])} results:")
        for row in res['result']:
            print(row)
        if len(res['result']) >= 3:
             print("[OK] Search 'inteligencia' passed (found expected docs)")
        else:
             print(f"[WARNING] Search 'inteligencia' found {len(res['result'])} docs, expected >= 3")
    else:
        print(f"[ERROR] Search failed: {res['errors']}")

    # 4. Search by another Keyword
    print("\n4. Searching for 'aprendizaje'...")
    sql_search = "SELECT * FROM Articles WHERE content = 'aprendizaje';"
    res = engine.execute_sql(sql_search)
    if res["success"]:
        print(f"Found {len(res['result'])} results:")
        for row in res['result']:
            print(row)
    else:
        print(f"[ERROR] Search failed: {res['errors']}")

if __name__ == "__main__":
    test_bow_integration()
