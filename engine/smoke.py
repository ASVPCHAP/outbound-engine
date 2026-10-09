"""Write, read back and delete one record in every table.

    python -m engine.smoke
"""
import time

from engine import airtable, config
from engine.schema import TABLES


def main():
    (base,) = config.require("AIRTABLE_BASE_ID")
    tag = f"smoke-{int(time.time())}"
    for table, specs in TABLES.items():
        key = specs[0]
        fields = {key: tag} if key == "client_id" else {key: tag, "client_id": "smoke"}
        rec = airtable.create(base, table, fields)
        assert airtable.get(base, table, rec["id"])["fields"][key] == tag, table
        airtable.delete(base, table, rec["id"])
        print(f"  ok {table}")
    print(f"Smoke test passed on {len(TABLES)} tables.")


if __name__ == "__main__":
    main()
