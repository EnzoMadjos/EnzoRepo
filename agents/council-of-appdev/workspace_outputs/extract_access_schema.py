import subprocess
import json
import os

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"Command failed: {cmd}\n{result.stderr}")
    return result.stdout.strip()

def extract_schema(db_path):
    schema = {}
    # Get table names
    tables = run_cmd(f"mdb-tables -1 '{db_path}'").splitlines()
    schema['tables'] = []
    for table in tables:
        if not table.strip():
            continue
        table_info = {'name': table, 'fields': []}
        # Get columns for each table
        try:
            columns = run_cmd(f"mdb-export -D '%Y-%m-%d' -H '{db_path}' '{table}' | head -1")
            table_info['fields'] = [col.strip() for col in columns.split(',')]
        except Exception as e:
            table_info['fields'] = [f"Error: {e}"]
        schema['tables'].append(table_info)
    # Get relationships (if possible)
    try:
        relations = run_cmd(f"mdb-schema '{db_path}' access")
        schema['relationships'] = relations
    except Exception as e:
        schema['relationships'] = f"Error: {e}"
    return schema

def main():
    db_path = os.path.join(os.path.dirname(__file__), 'Pitogo1.0.accdb')
    if not os.path.exists(db_path):
        print(f"Database file not found: {db_path}")
        return
    schema = extract_schema(db_path)
    with open('Pitogo1.0_schema.json', 'w') as f:
        json.dump(schema, f, indent=2)
    print("Schema extracted to Pitogo1.0_schema.json")

if __name__ == "__main__":
    main()
