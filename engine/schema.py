"""Airtable base schema: spec section 6 + brief section 5 + ICP.

Field shorthand: "name", "name:type", "name:sel=a|b", "name:multi=a|b", "name>Table".
The first field of each table is its primary field. Every table carries client_id.
Cap formulas (ramp_week, daily_cap) are plain numbers written by code; the
Airtable API can't create formula fields.
"""

TOUCH = "connect_note|day3_msg|day7_email|day10_useful|reply"
OUTCOME = "meeting|positive|objection|not_now|no_reply|not_interested|opt_out"
SOURCE = "predictleads|company_site|hubspot|tier_a_import|manual|gojiberry"
CONTACT_STATUS = ("new|scored|drafted|in_review|approved|invited|accepted|messaged|emailed|"
                  "replied|meeting_booked|closed_no_reply|dnc|withdrawn")
DRAFT_STATUS = ("pending_review|approved_ready_to_send|rejected|redraft_requested|sent|"
                "expired|cancelled_reply|cancelled_dnc")
SIGNAL_TYPE = ("news|job|hiring_surge|funding|new_leader|award|website_change|hubspot_intent|"
               "warm_engagement|warm_profile_view|network|past_customer")

TABLES = {
    "ICP": [
        "icp_id", "client_id", "name", "industries:long", "employee_min:num", "employee_max:num",
        "min_sellers:num", "geo", "buyer_titles:long", "exclusions:long", "active:check",
    ],
    "Clients": [
        "client_id", "name", "icp_config>ICP", "offer_notes:long", "price_setup:num",
        "price_monthly:num", "risk_disclosure_signed_at:datetime", "gojiberry_allowed:check",
        "hubspot_intent_enabled:check", "status:sel=pilot|active|paused|ended",
    ],
    "Senders": [
        "sender_id", "client_id", "person_name", "linkedin_url:url", "owner_verified:check",
        "plan:sel=free|premium|salesnav_core|salesnav_advanced", "start_date:date",
        "ramp_week:num", "daily_cap:num", "weekly_cap:num",
        "status:sel=active|paused|restricted", "paused_reason", "incidents:long",
        "acceptance_14d:pct",
    ],
    "Accounts": [
        "account_id", "client_id", "domain", "name", "website:url", "employee_count:num",
        "industry", "city", "state", "owner_operated:check", "icp_fit_score:num",
        "last_signal_at:date", "last_contacted_at:date", "active_conversation:check",
        "suppressed:check", "source_first_seen",
    ],
    "Contacts": [
        "contact_id", "client_id", "account>Accounts", "full_name", "title", "linkedin_url:url",
        "email:email", "email_source", "ring:sel=network|engaged|past_customer|cold",
        "icp_match", "score_total:num", "score_breakdown:long", f"status:sel={CONTACT_STATUS}",
        "dnc:check",
        "dnc_reason", "cooldown_until:date", "snooze_until:date", "gojiberry_contact_id",
        f"source_tags:multi={SOURCE}",
    ],
    "Signals": [
        "signal_id", "client_id", "account>Accounts", "contact>Contacts",
        f"type:sel={SIGNAL_TYPE}", "summary:long", "event_date:date", "seen_date:date",
        f"source:sel={SOURCE}", "source_url:url", "verified:check", "verified_by",
        "provider_call_id", "cost_usd:usd", "linkedin_derived:check",
    ],
    "Drafts": [
        "draft_id", "client_id", "contact>Contacts", "sender>Senders", f"touch:sel={TOUCH}",
        "variant:sel=A|B", "segment", "signal_type", "body:long", "original_body:long",
        "final_body:long", "edited_body:long", "edit_diff:long", "word_count:num",
        "prompt_version", "facts_used>Signals", "lint_result:long", "gate_results:long",
        f"status:sel={DRAFT_STATUS}", "reject_reason:sel=too_salesy|wrong_pain|generic|fact_wrong",
        "founder_review_required:check", "approver", "approved_at:datetime",
        "scheduled_for:date",
    ],
    "Send Log": [
        "log_id", "client_id", "sender>Senders", "contact>Contacts", "draft>Drafts",
        "action:sel=invite|message|inmail|email|comment|withdraw", "sent_at:datetime", "sent_by",
        "accepted_at:datetime", "notes:long", f"outcome:sel={OUTCOME}", "outcome_score:num",
        "outcome_set_at:datetime",
    ],
    "Replies": [
        "reply_id", "client_id", "contact>Contacts", "channel:sel=linkedin|email",
        "received_at:datetime", "text:long",
        "bucket:sel=interested|objection|not_now|not_interested", "draft_reply>Drafts",
        "answered_at:datetime", "sla_breached:check", "meeting_booked:check",
    ],
    "Examples": [
        "example_id", "client_id", "segment", "signal_type", "channel:sel=linkedin|email",
        "variant:sel=A|B", f"touch:sel={TOUCH}", "good_or_bad:sel=good|bad",
        "original_body:long", "final_body:long", "reason:long", f"outcome:sel={OUTCOME}",
        "score:num", "source:sel=approval|battle_plan_seed|blueprint_seed",
    ],
    "Rules": [
        "rule_id", "client_id", "rule_text:long", "evidence>Drafts",
        "status:sel=proposed|active|retired", "prompt_version_added", "approved_by",
        "approved_at:datetime",
    ],
    "Experiments": [
        "experiment_id", "client_id", "segment", "hypothesis:long", "variant_a:long",
        "variant_b:long", "accepts_a:num", "accepts_b:num", "positive_a:num", "positive_b:num",
        "status:sel=running|decided", "decision:long", "decided_at:datetime",
    ],
}

_SIMPLE = {
    "text": ("singleLineText", None),
    "long": ("multilineText", None),
    "num": ("number", {"precision": 0}),
    "usd": ("currency", {"precision": 4, "symbol": "$"}),
    "pct": ("percent", {"precision": 0}),
    "check": ("checkbox", {"icon": "check", "color": "greenBright"}),
    "date": ("date", {"dateFormat": {"name": "iso"}}),
    "datetime": ("dateTime", {"timeZone": "America/Chicago", "dateFormat": {"name": "iso"},
                              "timeFormat": {"name": "24hour"}}),
    "url": ("url", None),
    "email": ("email", None),
}


def parse(spec):
    """Returns (name, airtable_field_dict_or_None, linked_table_or_None)."""
    if ">" in spec:
        name, table = spec.split(">")
        return name, None, table
    name, _, kind = spec.partition(":")
    kind = kind or "text"
    if kind.startswith(("sel=", "multi=")):
        tag, _, choices = kind.partition("=")
        ftype = "singleSelect" if tag == "sel" else "multipleSelects"
        return name, {"name": name, "type": ftype,
                      "options": {"choices": [{"name": c} for c in choices.split("|")]}}, None
    ftype, options = _SIMPLE[kind]
    field = {"name": name, "type": ftype}
    if options:
        field["options"] = options
    return name, field, None
