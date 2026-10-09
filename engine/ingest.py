"""Phase 1: Tier A warm ingest into Accounts and Contacts.

    python -m engine.ingest connections Connections.csv [--all] [--dry-run]
    python -m engine.ingest past-customers export.csv [--dry-run]
    python -m engine.ingest normalize      # gives warm-form rows their ids

connections: the sender's own LinkedIn export (Settings > Data privacy > Get a copy of your data).
  Imports ICP title matches only unless --all (Airtable's free plan caps a base at 1,000 records).
past-customers: any CSV with a name column (Full Name, or First Name + Last Name) and any of
  Email, Company, Title/Position, LinkedIn/URL, Domain/Website. Everyone is imported.
Re-running is safe: rows merge on contact_id / account_id.
"""
import argparse
import csv
import re

from engine import airtable, config


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def contact_key(row):
    """Stable id: LinkedIn handle, else email, else name+company."""
    handle = re.search(r"linkedin\.com/in/([^/?#]+)", row.get("linkedin_url") or "")
    if handle:
        return "li:" + handle.group(1).lower()
    if row.get("email"):
        return "email:" + row["email"].strip().lower()
    return "name:" + slug(f"{row.get('full_name')} {row.get('company')}")


def _norm(text):
    t = re.sub(r"[^a-z0-9]+", " ", (text or "").lower())
    for long, short in [("vice president", "vp"), ("chief executive officer", "ceo"),
                        ("business development", "bd"), ("svp", "vp"), ("evp", "vp")]:
        t = t.replace(long, short)
    return " ".join(w for w in t.split() if w not in ("of", "the"))


def icp_keywords(icp):
    """'Founder/CEO; VP Sales; Head of BD' -> ['founder', 'ceo', 'vp sales', 'head bd']"""
    return [_norm(k) for k in re.split(r"[;/]", icp["buyer_titles"]) if k.strip()]


def icp_match(title, keywords):
    t = _norm(title)
    return ", ".join(k for k in keywords if re.search(r"\b" + re.escape(k) + r"\b", t))


def _reader(path):
    """DictReader that skips LinkedIn's 'Notes:' preamble before the real header."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        lines = f.read().splitlines()
    start = next((i for i, l in enumerate(lines)
                  if re.match(r'"?(First Name|Full Name|Name)"?,', l, re.I)), 0)
    return csv.DictReader(lines[start:])


def _pick(row, *names):
    low = {k.strip().lower(): (v or "").strip() for k, v in row.items() if k}
    return next((low[n] for n in names if low.get(n)), "")


def parse(path):
    for r in _reader(path):
        name = _pick(r, "full name", "name") or \
            f"{_pick(r, 'first name')} {_pick(r, 'last name')}".strip()
        if not name:
            continue
        yield {
            "full_name": name,
            "email": _pick(r, "email address", "email"),
            "company": _pick(r, "company", "company name", "account"),
            "title": _pick(r, "position", "title", "job title"),
            "linkedin_url": _pick(r, "url", "linkedin url", "linkedin", "profile url"),
            "domain": _pick(r, "domain", "website"),
        }


def build(rows, client_id, ring, keywords, only_icp):
    """Returns (accounts, contacts) as Airtable field dicts, de-duplicated."""
    accounts, contacts = {}, {}
    for r in rows:
        match = icp_match(r["title"], keywords)
        if only_icp and not match:
            continue
        key = contact_key(r)
        acct = f"{client_id}:{slug(r['domain'] or r['company'])}" if (r["company"] or r["domain"]) else None
        if acct and acct not in accounts:
            accounts[acct] = {"account_id": acct, "client_id": client_id, "name": r["company"],
                              "domain": r["domain"], "source_first_seen": "tier_a_import"}
        contacts[f"{client_id}:{key}"] = {
            "contact_id": f"{client_id}:{key}", "client_id": client_id,
            "full_name": r["full_name"], "title": r["title"], "email": r["email"] or None,
            "email_source": "tier_a_import" if r["email"] else None,
            "linkedin_url": r["linkedin_url"] or None, "ring": ring, "icp_match": match,
            "status": "new", "source_tags": ["tier_a_import"], "_account": acct}
    return list(accounts.values()), list(contacts.values())


def write(base, accounts, contacts):
    acct_ids = airtable.upsert_many(base, "Accounts", "account_id",
                                    [{k: v for k, v in a.items() if v} for a in accounts])
    rows = []
    for c in contacts:
        acct = c.pop("_account")
        row = {k: v for k, v in c.items() if v not in (None, "")}
        if acct:
            row["account"] = [acct_ids[acct]]
        rows.append(row)
    airtable.upsert_many(base, "Contacts", "contact_id", rows)


def normalize(base, client_id):
    """Warm-form rows arrive without contact_id; give them one."""
    rows = airtable.list_all(base, "Contacts", "{contact_id}=''")
    for rec in rows:
        f = rec["fields"]
        key = contact_key({"linkedin_url": f.get("linkedin_url"), "email": f.get("email"),
                           "full_name": f.get("full_name"), "company": ""})
        airtable.update(base, "Contacts", rec["id"], {
            "contact_id": f"{f.get('client_id') or client_id}:{key}", "status": "new"})
    print(f"Normalized {len(rows)} warm-form contacts.")


def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument("mode", choices=["connections", "past-customers", "normalize"])
    p.add_argument("csv", nargs="?")
    p.add_argument("--all", action="store_true", help="connections: import non-ICP titles too")
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    c = config.client()
    cid = c["client"]["client_id"]
    if a.mode == "normalize":
        normalize(config.require("AIRTABLE_BASE_ID")[0], cid)
        return
    ring = "network" if a.mode == "connections" else "past_customer"
    only_icp = a.mode == "connections" and not a.all
    accounts, contacts = build(parse(a.csv), cid, ring, icp_keywords(c["icp"]), only_icp)
    print(f"{len(contacts)} contacts, {len(accounts)} accounts "
          f"({'ICP matches only' if only_icp else 'all rows'}).")
    for x in contacts[:10]:
        print(f"  {x['full_name']} | {x['title']} | ICP: {x['icp_match'] or '-'}")
    if not a.dry_run:
        write(config.require("AIRTABLE_BASE_ID")[0], accounts, contacts)
        print("Written to Airtable.")


if __name__ == "__main__":
    main()
