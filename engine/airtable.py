"""Minimal Airtable Web API client (stdlib only)."""
import json
import time
import urllib.error
import urllib.parse
import urllib.request

from engine import config

API = "https://api.airtable.com/v0"


def _request(method, path, body=None, params=None):
    (pat,) = config.require("AIRTABLE_PAT")
    url = f"{API}/{path}"
    if params:
        url += "?" + urllib.parse.urlencode(params, doseq=True)
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(4):
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Bearer {pat}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < 3:
                time.sleep(30)  # Airtable's rate-limit penalty window
                continue
            raise SystemExit(f"Airtable {method} {path} failed {e.code}: {e.read().decode()}")


def _t(table):
    return urllib.parse.quote(table, safe="")


# --- schema (Meta API) ---
def create_base(name, workspace_id, tables):
    return _request("POST", "meta/bases", {"name": name, "workspaceId": workspace_id,
                                           "tables": tables})


def get_tables(base):
    return _request("GET", f"meta/bases/{base}/tables")["tables"]


def create_table(base, name, fields):
    return _request("POST", f"meta/bases/{base}/tables", {"name": name, "fields": fields})


def create_field(base, table_id, field):
    return _request("POST", f"meta/bases/{base}/tables/{table_id}/fields", field)


# --- records ---
def find(base, table, formula):
    return _request("GET", f"{base}/{_t(table)}", params={"filterByFormula": formula})["records"]


def create(base, table, fields):
    return _request("POST", f"{base}/{_t(table)}",
                    {"records": [{"fields": fields}], "typecast": True})["records"][0]


def upsert_many(base, table, key, rows):
    """Native Airtable upsert on `key`, 10 rows per request. Returns {key value: record id}."""
    ids = {}
    for i in range(0, len(rows), 10):
        resp = _request("PATCH", f"{base}/{_t(table)}", {
            "performUpsert": {"fieldsToMergeOn": [key]}, "typecast": True,
            "records": [{"fields": r} for r in rows[i:i + 10]]})
        ids.update({r["fields"][key]: r["id"] for r in resp["records"]})
    return ids


def list_all(base, table, formula=None):
    rows, offset = [], None
    while True:
        params = {"filterByFormula": formula} if formula else {}
        if offset:
            params["offset"] = offset
        resp = _request("GET", f"{base}/{_t(table)}", params=params)
        rows += resp["records"]
        offset = resp.get("offset")
        if not offset:
            return rows


def update(base, table, record_id, fields):
    return _request("PATCH", f"{base}/{_t(table)}/{record_id}",
                    {"fields": fields, "typecast": True})


def get(base, table, record_id):
    return _request("GET", f"{base}/{_t(table)}/{record_id}")


def delete(base, table, record_id):
    return _request("DELETE", f"{base}/{_t(table)}/{record_id}")
