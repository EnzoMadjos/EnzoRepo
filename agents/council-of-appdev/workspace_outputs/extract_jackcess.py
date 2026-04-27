import jpype
import jpype.imports
import json
import os

JARS_DIR = os.path.join(os.path.dirname(__file__), "jars")
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "Pitogo1.0.accdb"))
OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "Pitogo1.0_full_schema.json")

CLASSPATH = ":".join([
    os.path.join(JARS_DIR, "ucanaccess-5.0.1.jar"),
    os.path.join(JARS_DIR, "jackcess-4.0.1.jar"),
    os.path.join(JARS_DIR, "commons-lang3-3.11.jar"),
    os.path.join(JARS_DIR, "commons-logging-1.2.jar"),
    os.path.join(JARS_DIR, "hsqldb-2.5.1.jar"),
])

def main():
    jpype.startJVM(classpath=[CLASSPATH])
    from com.healthmarketscience.jackcess import DatabaseBuilder
    from java.io import File

    db = DatabaseBuilder.open(File(DB_PATH))

    result = {
        "tables": [],
        "linked_tables": [],
        "queries": [],
        "relationships": [],
        "summary": {}
    }

    # Get all tables (linked tables will throw FileNotFoundException — catch gracefully)
    for table_name in db.getTableNames():
        try:
            table = db.getTable(table_name)
            fields = []
            for col in table.getColumns():
                fields.append({
                    "name": str(col.getName()),
                    "type": str(col.getType()),
                    "length": col.getLengthInUnits(),
                    "required": col.isRequired(),
                })
            result["tables"].append({
                "name": str(table_name),
                "fields": fields,
                "row_count": table.getRowCount()
            })
        except Exception:
            # Linked table - backend not available, just record the name
            result["linked_tables"].append({"name": str(table_name), "note": "linked table - backend not present"})

    # Get linked table definitions from MSysObjects
    try:
        msys = db.getSystemTable("MSysObjects")
        if msys:
            for row in msys:
                obj_type = row.get("Type")
                obj_name = row.get("Name")
                connect = row.get("Connect")
                foreign_name = row.get("ForeignName")
                if obj_type == 6:  # Linked tables
                    result["linked_tables"].append({
                        "name": str(obj_name) if obj_name else None,
                        "source_table": str(foreign_name) if foreign_name else None,
                        "connection": str(connect) if connect else None,
                    })
    except Exception as e:
        result["linked_tables"] = [{"error": str(e)}]

    # Get queries
    try:
        for q in db.getQueries():
            result["queries"].append({
                "name": str(q.getName()),
                "sql": str(q.toSQLString()),
                "type": str(q.getType()),
            })
    except Exception as e:
        result["queries"] = [{"error": str(e)}]

    # Get relationships
    try:
        for rel in db.getRelationships():
            result["relationships"].append({
                "name": str(rel.getName()),
                "from_table": str(rel.getFromTable().getName()),
                "to_table": str(rel.getToTable().getName()),
                "columns": [
                    {"from": str(c.getFromColumn().getName()), "to": str(c.getToColumn().getName())}
                    for c in rel.getColumns()
                ],
            })
    except Exception as e:
        result["relationships"] = [{"error": str(e)}]

    result["summary"] = {
        "tables_count": len(result["tables"]),
        "linked_tables_count": len(result["linked_tables"]),
        "queries_count": len(result["queries"]),
        "relationships_count": len(result["relationships"]),
    }

    db.close()
    jpype.shutdownJVM()

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Done! Full schema saved to {OUTPUT_PATH}")
    print(f"  Tables: {result['summary']['tables_count']}")
    print(f"  Linked Tables: {result['summary']['linked_tables_count']}")
    print(f"  Queries: {result['summary']['queries_count']}")
    print(f"  Relationships: {result['summary']['relationships_count']}")

if __name__ == "__main__":
    main()
