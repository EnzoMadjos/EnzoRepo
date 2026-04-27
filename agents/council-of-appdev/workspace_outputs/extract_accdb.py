import jaydebeapi
import json
import os

JARS_DIR = os.path.join(os.path.dirname(__file__), "jars")
DB_PATH = os.path.join(os.path.dirname(__file__), "Pitogo1.0.accdb")
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "Pitogo1.0_schema.json")

JARS = [
    os.path.join(JARS_DIR, "ucanaccess-5.0.1.jar"),
    os.path.join(JARS_DIR, "jackcess-4.0.1.jar"),
    os.path.join(JARS_DIR, "commons-lang3-3.11.jar"),
    os.path.join(JARS_DIR, "commons-logging-1.2.jar"),
    os.path.join(JARS_DIR, "hsqldb-2.5.1.jar"),
]

def extract(db_path):
    conn = jaydebeapi.connect(
        "net.ucanaccess.jdbc.UcanaccessDriver",
        f"jdbc:ucanaccess://{db_path};showSchema=true;ignoreExternalMdb=true",
        ["", ""],
        JARS,
    )
    cursor = conn.cursor()
    schema = {"tables": [], "views": [], "relationships": [], "queries": []}

    meta = conn.jconn.getMetaData()

    # Get ALL table types (TABLE, LINKED TABLE, VIEW, etc.)
    rs = meta.getTables(None, None, "%", None)
    all_objects = []
    while rs.next():
        all_objects.append({
            "name": rs.getString("TABLE_NAME"),
            "type": rs.getString("TABLE_TYPE"),
        })

    for obj in all_objects:
        table = obj["name"]
        ttype = obj["type"]
        table_info = {"name": table, "type": ttype, "fields": []}
        try:
            col_rs = meta.getColumns(None, None, table, "%")
            while col_rs.next():
                table_info["fields"].append({
                    "name": col_rs.getString("COLUMN_NAME"),
                    "type": col_rs.getString("TYPE_NAME"),
                    "nullable": col_rs.getString("IS_NULLABLE"),
                    "size": col_rs.getInt("COLUMN_SIZE"),
                })
        except Exception as e:
            table_info["fields"] = [f"Error: {e}"]

        if ttype in ("TABLE", "LINKED TABLE"):
            schema["tables"].append(table_info)
            try:
                fk_rs = meta.getImportedKeys(None, None, table)
                while fk_rs.next():
                    schema["relationships"].append({
                        "fk_table": fk_rs.getString("FKTABLE_NAME"),
                        "fk_column": fk_rs.getString("FKCOLUMN_NAME"),
                        "pk_table": fk_rs.getString("PKTABLE_NAME"),
                        "pk_column": fk_rs.getString("PKCOLUMN_NAME"),
                    })
            except Exception:
                pass
        elif ttype == "VIEW":
            schema["views"].append(table_info)

    # Extract queries/views SQL
    try:
        cursor.execute("SELECT MSysObjects.Name, MSysQueries.Expression FROM MSysObjects LEFT JOIN MSysQueries ON MSysObjects.Id = MSysQueries.ObjectId WHERE MSysObjects.Type=5 ORDER BY MSysObjects.Name")
        rows = cursor.fetchall()
        seen = set()
        for row in rows:
            qname = row[0]
            if qname not in seen:
                schema["queries"].append({"name": qname, "sql": row[1]})
                seen.add(qname)
    except Exception as e:
        schema["queries"] = [{"error": str(e)}]

    conn.close()
    return schema

def main():
    if not os.path.exists(DB_PATH):
        print(f"File not found: {DB_PATH}")
        return
    print("Connecting to database via UCanAccess...")
    schema = extract(DB_PATH)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(schema, f, indent=2)
    print(f"Done! Schema extracted to {OUTPUT_PATH}")
    print(f"Tables found: {len(schema['tables'])}")
    for t in schema["tables"]:
        print(f"  - [{t['type']}] {t['name']} ({len(t['fields'])} fields)")
    print(f"Views found: {len(schema['views'])}")
    print(f"Queries found: {len(schema['queries'])}")

if __name__ == "__main__":
    main()
