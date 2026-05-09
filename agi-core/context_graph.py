#!/usr/bin/env python3
"""Twenty CRM entity graph service — entity matching, event attachment, queries."""

import argparse, json, subprocess, sys
from datetime import datetime

WS = "workspace_4fi60z16hu359ticc16w8z5ff"
PSQL = [
    "docker",
    "exec",
    "twenty-db-1",
    "psql",
    "-U",
    "twenty",
    "-d",
    "twenty",
    "-t",
    "-A",
    "-F",
    "|",
    "-c",
]

def db_exec(sql: str) -> str:
    try:
        r = subprocess.run(PSQL + [sql], capture_output=True, text=True, timeout=15)
        if r.returncode != 0:
            print(f"[FAIL] psql rc={r.returncode}: {r.stderr.strip()}", file=sys.stderr)
            return ""
        return r.stdout.strip()
    except Exception as e:
        print(f"[FAIL] db_exec: {e}", file=sys.stderr)
        return ""

def _esc(v):
    return str(v).replace("'", "''") if v else ""

def _rows(raw):
    return [l.split("|") for l in raw.splitlines() if l.strip()] if raw else []

def _parse_props(s):
    if not s or s == "null":
        return {}
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        return {"raw": s}

def entity_match(text: str) -> dict | None:
    q = _esc(text.strip())
    sp = (
        f'SELECT p.id,p."nameFirstName",p."nameLastName",p."emailsPrimaryEmail",p."companyId" '
        f'FROM "{WS}"."person" p WHERE p."deletedAt" IS NULL AND '
        f"(p.\"nameFirstName\" ILIKE '%{q}%' OR p.\"nameLastName\" ILIKE '%{q}%' "
        f"OR p.\"emailsPrimaryEmail\" ILIKE '%{q}%') LIMIT 5"
    )
    sc = (
        f'SELECT id,name,"domainNamePrimaryLinkLabel" FROM "{WS}"."company" '
        f"WHERE \"deletedAt\" IS NULL AND (name ILIKE '%{q}%' "
        f"OR \"domainNamePrimaryLinkLabel\" ILIKE '%{q}%') LIMIT 5"
    )
    matches = [
        {
            "type": "person",
            "id": r[0],
            "label": f"{r[1] or ''} {r[2] or ''}".strip(),
            "email": r[3],
            "companyId": r[4],
        }
        for r in _rows(db_exec(sp))
        if r[0]
    ]
    matches += [
        {"type": "company", "id": r[0], "label": r[1], "domain": r[2]}
        for r in _rows(db_exec(sc))
        if r[0]
    ]
    if not matches:
        return None
    best: dict = matches[0]
    if len(matches) > 1:
        best["alternatives"] = matches[1:]
    return best

def entity_search(query: str, entity_type: str = "all") -> list[dict]:
    q = _esc(query.strip())
    results = []
    if entity_type in ("all", "person"):
        sql = (
            f'SELECT p.id,p."nameFirstName",p."nameLastName",p."emailsPrimaryEmail",p."jobTitle",c.name '
            f'FROM "{WS}"."person" p LEFT JOIN "{WS}"."company" c ON p."companyId"=c.id '
            f'WHERE p."deletedAt" IS NULL AND (p."nameFirstName" ILIKE \'%{q}%\' '
            f"OR p.\"nameLastName\" ILIKE '%{q}%' OR p.\"emailsPrimaryEmail\" ILIKE '%{q}%') "
            f'ORDER BY p."createdAt" DESC LIMIT 20'
        )
        for r in _rows(db_exec(sql)):
            if r[0]:
                results.append(
                    {
                        "type": "person",
                        "id": r[0],
                        "firstName": r[1],
                        "lastName": r[2],
                        "email": r[3],
                        "jobTitle": r[4],
                        "company": r[5],
                    }
                )
    if entity_type in ("all", "company"):
        sql = (
            f'SELECT id,name,"domainNamePrimaryLinkLabel",employees FROM "{WS}"."company" '
            f"WHERE \"deletedAt\" IS NULL AND (name ILIKE '%{q}%' "
            f'OR "domainNamePrimaryLinkLabel" ILIKE \'%{q}%\') ORDER BY "createdAt" DESC LIMIT 20'
        )
        for r in _rows(db_exec(sql)):
            if r[0]:
                results.append(
                    {
                        "type": "company",
                        "id": r[0],
                        "name": r[1],
                        "domain": r[2],
                        "employees": r[3],
                    }
                )
    return results

def event_attach(
    source: str,
    event_type: str,
    content: str,
    entity_type: str,
    entity_id: str,
    properties: dict | None = None,
) -> str | None:
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S+00")
    tc = f'"target{entity_type.capitalize()}Id"'
    pj = json.dumps(properties or {}, ensure_ascii=False).replace("'", "''")
    sql = (
        f'INSERT INTO "{WS}"."timelineActivity" '
        f'("name","properties","happensAt",{tc},"createdBySource","createdByContext","workspaceId") '
        f"VALUES ('{_esc(event_type)}','{pj}'::jsonb,'{now}'::timestamptz,'{_esc(entity_id)}',"
        f"'{_esc(source)}','{{\"content\":\"{_esc(content)}\"}}'::jsonb,'4fi60z16hu359ticc16w8z5ff') RETURNING id"
    )
    raw = db_exec(sql)
    return raw.splitlines()[0] if raw else None

def entity_timeline(entity_type: str, entity_id: str, limit: int = 20) -> list[dict]:
    tc = f'"target{entity_type.capitalize()}Id"'
    sql = (
        f'SELECT id,"name","properties","happensAt","createdBySource" FROM "{WS}"."timelineActivity" '
        f"WHERE {tc}='{_esc(entity_id)}' ORDER BY \"happensAt\" DESC LIMIT {limit}"
    )
    return [
        {
            "id": r[0],
            "name": r[1],
            "properties": _parse_props(r[2] if len(r) > 2 else ""),
            "happensAt": r[3],
            "source": r[4] if len(r) > 4 else None,
        }
        for r in _rows(db_exec(sql))
        if r[0]
    ]

def entity_query(entity_type: str, entity_id: str) -> dict:
    result: dict | list = {"type": entity_type, "id": entity_id}
    if entity_type == "person":
        sql = (
            f'SELECT p.id,p."nameFirstName",p."nameLastName",p."emailsPrimaryEmail",'
            f'p."phonesPrimaryPhoneNumber",p."jobTitle",p."companyId",c.name '
            f'FROM "{WS}"."person" p LEFT JOIN "{WS}"."company" c ON p."companyId"=c.id WHERE p.id=\'{_esc(entity_id)}\''
        )
        for r in _rows(db_exec(sql)):
            result.update(
                {
                    "firstName": r[1],
                    "lastName": r[2],
                    "email": r[3],
                    "phone": r[4],
                    "jobTitle": r[5],
                    "companyId": r[6],
                    "companyName": r[7],
                }
            )
            break
    elif entity_type == "company":
        sql = f'SELECT id,name,"domainNamePrimaryLinkLabel",employees FROM "{WS}"."company" WHERE id=\'{_esc(entity_id)}\''
        for r in _rows(db_exec(sql)):
            result.update({"name": r[1], "domain": r[2], "employees": r[3]})
            break
    result["timeline"] = entity_timeline(entity_type, entity_id)
    tc = f'"target{entity_type.capitalize()}Id"'
    sql_n = (
        f'SELECT n.id,n.title,n."bodyV2Markdown" FROM "{WS}"."note" n '
        f'JOIN "{WS}"."noteTarget" nt ON n.id=nt."noteId" WHERE nt.{tc}=\'{_esc(entity_id)}\' '
        f'ORDER BY n."createdAt" DESC LIMIT 10'
    )
    result["notes"] = [
        {"id": r[0], "title": r[1], "body": r[2]} for r in _rows(db_exec(sql_n)) if r[0]
    ]
    return result

def company_full_profile(company_id: str) -> dict:
    profile = entity_query("company", company_id)
    sql_p = (
        f'SELECT p.id,p."nameFirstName",p."nameLastName",p."emailsPrimaryEmail",p."jobTitle" '
        f'FROM "{WS}"."person" p WHERE p."companyId"=\'{_esc(company_id)}\' AND p."deletedAt" IS NULL '
        f'ORDER BY p."createdAt" DESC'
    )
    profile["people"] = [
        {
            "id": r[0],
            "firstName": r[1],
            "lastName": r[2],
            "email": r[3],
            "jobTitle": r[4],
        }
        for r in _rows(db_exec(sql_p))
        if r[0]
    ]
    sql_o = (
        f'SELECT id,name,"amountAmountMicros","amountCurrencyCode",stage FROM "{WS}"."opportunity" '
        f'WHERE "companyId"=\'{_esc(company_id)}\' AND "deletedAt" IS NULL ORDER BY "createdAt" DESC'
    )
    opps = []
    for r in _rows(db_exec(sql_o)):
        if r[0]:
            amt = int(r[2]) / 1_000_000 if r[2] and r[2] != "null" else None
            opps.append(
                {
                    "id": r[0],
                    "name": r[1],
                    "amount": amt,
                    "currency": r[3],
                    "stage": r[4],
                }
            )
    profile["opportunities"] = opps
    return profile

def main():
    p = argparse.ArgumentParser(description="Twenty CRM entity graph")
    sub = p.add_subparsers(dest="cmd")
    m = sub.add_parser("match")
    m.add_argument("text")
    s = sub.add_parser("search")
    s.add_argument("query")
    s.add_argument("--type", default="all", choices=["all", "person", "company"])
    t = sub.add_parser("timeline")
    t.add_argument("--type", required=True, choices=["person", "company"])
    t.add_argument("--id", required=True)
    t.add_argument("--limit", type=int, default=20)
    q = sub.add_parser("query")
    q.add_argument("--type", required=True, choices=["person", "company"])
    q.add_argument("--id", required=True)
    pr = sub.add_parser("profile")
    pr.add_argument("--id", required=True)
    a = sub.add_parser("attach")
    a.add_argument("--source", required=True)
    a.add_argument("--event-type", required=True)
    a.add_argument("--content", required=True)
    a.add_argument("--entity-type", required=True, choices=["person", "company"])
    a.add_argument("--entity-id", required=True)
    a.add_argument("--props", default="{}")
    args = p.parse_args()
    if not args.cmd:
        p.print_help()
        sys.exit(1)
    res = None
    if args.cmd == "match":
        res = entity_match(args.text)
    elif args.cmd == "search":
        res = entity_search(args.query, args.type)
    elif args.cmd == "timeline":
        res = entity_timeline(args.type, args.id, args.limit)
    elif args.cmd == "query":
        res = entity_query(args.type, args.id)
    elif args.cmd == "profile":
        res = company_full_profile(args.id)
    elif args.cmd == "attach":
        eid = event_attach(
            args.source,
            args.event_type,
            args.content,
            args.entity_type,
            args.entity_id,
            json.loads(args.props),
        )
        res = {"attached": eid}
    print(json.dumps(res, ensure_ascii=False, indent=2, default=str))

if __name__ == "__main__":
    main()
