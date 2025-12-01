
import sys
import os
sys.path.append(os.getcwd())
try:
    from parser.sql_parser_engine import create_sql_parser_engine
    print("Import successful")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
