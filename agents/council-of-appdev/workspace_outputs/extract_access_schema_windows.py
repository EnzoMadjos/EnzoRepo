import pyodbc
import json
import os

def get_connection_string(db_path):
    return (
        r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
        f"DBQ={db_path};"
    )

def extract_schema(db_path):
    conn_str = get_connection_string(db_path)
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    schema = {"tables": []}
    # Get all table names
    for row in cursor.tables(tableType='TABLE'):
        table_name = row.table_name
        table_info = {"name": table_name, "fields": []}
        # Get columns for each table
        for col in cursor.columns(table=table_name):
            table_info["fields"].append({
                "name": col.column_name,
                "type": col.type_name,
                "nullable": col.nullable,
                "column_size": col.column_size
            })
        schema["tables"].append(table_info)
    # Get relationships (foreign keys)
    relationships = []
    for row in cursor.tables(tableType='TABLE'):
        table_name = row.table_name
        for fk in cursor.foreignKeys(table=table_name):
            relationships.append({
                "fk_table": fk.fktable_name,
                "fk_column": fk.fkcolumn_name,
                "pk_table": fk.pktable_name,
                "pk_column": fk.pkcolumn_name,
                "fk_name": fk.fk_name
            })
    schema["relationships"] = relationships
    conn.close()
    return schema

def main():
    db_path = os.path.abspath("Pitogo1.0.accdb")
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return
    schema = extract_schema(db_path)
    with open("Pitogo1.0_schema.json", "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print("Schema extracted to Pitogo1.0_schema.json")

if __name__ == "__main__":
    main()
