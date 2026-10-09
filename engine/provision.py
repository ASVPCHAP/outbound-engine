"""Create or upgrade this install's Airtable base to match engine/schema.py.

    python -m engine.provision

No AIRTABLE_BASE_ID in .env: creates a new base in AIRTABLE_WORKSPACE_ID and prints its id.
With one: adds any missing tables and fields (never deletes or changes existing ones).
"""
from engine import airtable, config
from engine.schema import TABLES, parse


def plain_fields(specs):
    return [f for _, f, link in map(parse, specs) if f]


def sync(base):
    existing = {t["name"]: t for t in airtable.get_tables(base)}
    for name, specs in TABLES.items():
        if name not in existing:
            existing[name] = airtable.create_table(base, name, plain_fields(specs))
            print(f"  + table {name}")
            continue
        have = {f["name"] for f in existing[name]["fields"]}
        for field in plain_fields(specs):
            if field["name"] not in have:
                airtable.create_field(base, existing[name]["id"], field)
                print(f"  + field {name}.{field['name']}")
    # Links last: every target table exists by now.
    existing = {t["name"]: t for t in airtable.get_tables(base)}
    for name, specs in TABLES.items():
        have = {f["name"] for f in existing[name]["fields"]}
        for fname, _, target in map(parse, specs):
            if target and fname not in have:
                airtable.create_field(base, existing[name]["id"], {
                    "name": fname, "type": "multipleRecordLinks",
                    "options": {"linkedTableId": existing[target]["id"]}})
                print(f"  + link {name}.{fname} -> {target}")


def main():
    base = config.get("AIRTABLE_BASE_ID")
    if not base:
        (ws,) = config.require("AIRTABLE_WORKSPACE_ID")
        name = f"Outbound Engine - {config.client()['client']['name']}"
        first = next(iter(TABLES))
        base = airtable.create_base(name, ws, [{"name": first,
                                                "fields": plain_fields(TABLES[first])}])["id"]
        print(f"Created base {name}: {base}\nPut AIRTABLE_BASE_ID={base} in .env.")
    sync(base)
    print("Schema in sync.")


if __name__ == "__main__":
    main()
