"""Load this install's clients/<CLIENT_ID>.json into Airtable. Safe to re-run.

    python -m engine.seed
"""
from engine import airtable, config


def upsert(base, table, key, fields):
    rows = airtable.find(base, table, f"{{{key}}}='{fields[key]}'")
    if rows:
        airtable.update(base, table, rows[0]["id"], fields)
        return rows[0]["id"]
    return airtable.create(base, table, fields)["id"]


def main():
    (base,) = config.require("AIRTABLE_BASE_ID")
    c = config.client()
    cid = c["client"]["client_id"]
    icp = upsert(base, "ICP", "icp_id", {**c["icp"], "client_id": cid})
    upsert(base, "Clients", "client_id", {**c["client"], "icp_config": [icp]})
    for s in c["senders"]:
        upsert(base, "Senders", "sender_id", {**s, "client_id": cid})
    for e in c["examples"]:
        upsert(base, "Examples", "example_id", {**e, "client_id": cid})
    print(f"Seeded {cid}: 1 ICP, 1 client, {len(c['senders'])} senders, "
          f"{len(c['examples'])} examples.")


if __name__ == "__main__":
    main()
