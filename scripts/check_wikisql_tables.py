"""Check WikiSQL_VALUE table names in database."""

import sqlite3
import json
from pathlib import Path

data_dir = Path("data/datasets/wikisql_value/extracted/data")
db_file = data_dir / "dev.db"

# Check tables in database
conn = sqlite3.connect(str(db_file))
cursor = conn.cursor()
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = [r[0] for r in cursor.fetchall()]
print(f"Tables in database: {tables[:10]}")

# Check table schema from JSONL
tables_file = data_dir / "dev.tables.jsonl"
with open(tables_file, 'r') as f:
    first_line = f.readline()
    table_data = json.loads(first_line)
    print(f"\nFirst table from JSONL:")
    print(f"  ID: {table_data.get('id')}")
    print(f"  Name: {table_data.get('name')}")
    print(f"  Header: {table_data.get('header', [])[:5]}")

conn.close()
