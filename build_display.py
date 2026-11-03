"""Fill the public display template with sanitized board data.
Usage: python3 build_display.py <db_dir> <template.html> <out.html|out.json>
(out.json writes only the data file; the template argument is then ignored)
<db_dir> holds ArtifactData exports: tasks/*.json, employees/*.json, meta/calendar.json, meta/display.json (optional).
Public copy keeps only: first names, task number, project code, title, status, priority, due date,
and short (160-char) update lines. No emails, scopes, job/site text, or full names."""
import sys, json, glob, os, re, datetime
from zoneinfo import ZoneInfo

db, tpl, out = sys.argv[1], sys.argv[2], sys.argv[3]
ET = ZoneInfo("America/New_York")
now = datetime.datetime.now(datetime.timezone.utc)
today = now.astimezone(ET).date()
OPEN = {"assigned", "in_progress", "blocked", "returned", "submitted"}

def load(p):
    d = json.load(open(p))
    return d.get("data", d) if isinstance(d, dict) and "data" in d and isinstance(d["data"], dict) else d

emps_raw = {os.path.basename(p)[:-5]: load(p) for p in glob.glob(os.path.join(db, "employees", "*.json"))}
tasks_raw = {os.path.basename(p)[:-5]: load(p) for p in glob.glob(os.path.join(db, "tasks", "*.json"))}

full_to_first = {}
emps = []
for eid, e in emps_raw.items():
    if e.get("active") is False:
        continue
    first = (e.get("name") or "").split(" ")[0] or "Team"
    full_to_first[e.get("name") or ""] = first
    last_up = ""
    for t in tasks_raw.values():
        if t.get("employeeId") == eid:
            for m in t.get("thread") or []:
                if m.get("by") == "employee" and (m.get("at") or "") > last_up:
                    last_up = m.get("at") or ""
    emps.append({"id": eid, "name": first, "lastUpdate": last_up})
emps.sort(key=lambda x: x["name"])

def scrub(text):
    text = re.sub(r"[\w.+-]+@[\w-]+\.[\w.]+", "[email]", text or "")
    for full, first in full_to_first.items():
        if full:
            text = text.replace(full, first)
    text = " ".join(text.split())
    return text[:157] + "…" if len(text) > 160 else text

cutoff = (today - datetime.timedelta(days=10)).isoformat()
tasks = []
for tid, t in sorted(tasks_raw.items()):
    if t.get("status") not in OPEN:
        continue
    th = []
    notes = [m for m in (t.get("thread") or []) if m.get("by") == "employee" or (m.get("by") == "dave" and m.get("kind") in ("feedback", "return"))]
    keep = [m for m in notes if (m.get("at") or "") >= cutoff and m.get("kind") not in ("status", "priority", "due", "reassign")]
    if notes and notes[-1] not in keep:
        keep.append(notes[-1])
    for m in sorted(keep, key=lambda m: (m.get("at") or "")):
        th.append({"at": m.get("at"), "by": m.get("by"), "kind": m.get("kind"), "text": scrub(m.get("text")), "loggedAt": m.get("loggedAt")})
    tasks.append({"id": tid, "projectCode": t.get("projectCode") or "", "title": scrub(t.get("title")), "status": t.get("status"),
                  "priority": t.get("priority") or "normal", "due": t.get("due"), "employeeId": t.get("employeeId"), "thread": th})

cal = None
cp = os.path.join(db, "meta", "calendar.json")
if os.path.exists(cp):
    c = load(cp)
    cal = {"updatedAt": c.get("updatedAt"), "events": [{"subject": scrub(e.get("subject")), "start": e.get("start"), "end": e.get("end"), "allDay": bool(e.get("allDay"))} for e in c.get("events") or []]}

sayings = []
dp = os.path.join(db, "meta", "display.json")
if os.path.exists(dp):
    sayings = load(dp).get("sayings") or []

data = {"generatedAt": now.isoformat().replace("+00:00", "Z"), "emps": emps, "tasks": tasks, "calendar": cal, "sayings": sayings}
if out.endswith(".json"):
    open(out, "w").write(json.dumps(data, ensure_ascii=False, indent=1))
    print(f"open tasks {len(tasks)}, people {len(emps)}, calendar events {len(cal['events']) if cal else 0}")
    sys.exit(0)
js = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
html = open(tpl).read()
assert "__BOARD_DATA__" in html
open(out, "w").write(html.replace("__BOARD_DATA__", js))
print(f"open tasks {len(tasks)}, people {len(emps)}, calendar events {len(cal['events']) if cal else 0}, bytes {len(js)}")
