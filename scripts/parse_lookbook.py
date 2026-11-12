"""Parse an Anchor Chart Club lookbook (text export with '## Sheet name:' headers)
into a list of chart records. Usage: python parse_lookbook.py <grade> <file> [<grade> <file> ...] > out.json
Only the '<grade> <Subject> ACs' tabs are read; the standards reference tabs are skipped.
"""
import csv, io, json, re, sys

SUBJECTS = {"math": "Math", "elar": "ELA", "ela": "ELA", "science": "Science",
            "social studies": "Social Studies", "sel": "SEL"}

def norm_col(h):
    h = h.strip().lower()
    if h.startswith("anchor"): return "chart"
    if h.startswith("product"): return "files"
    if h.startswith("ccss"): return "ccss"
    if h.startswith("ngss"): return "ngss"
    if h.startswith("teks"): return "teks"
    if h.startswith("florida") or h.startswith("fl"): return "fl"
    if h.startswith("exit"): return "exit"
    if h.startswith("va") or "sol" in h: return "va"
    return h or None

def subject_of(sheet):
    s = sheet.lower()
    s = re.sub(r"^\s*(kinder\w*|k\b|\d(st|nd|rd|th)?)\s*(grade)?\s*", "", s)
    s = s.replace(" acs", "").replace(" ac", "").strip()
    for k, v in SUBJECTS.items():
        if s.startswith(k): return v
    return s.title()

CODE_START = re.compile(r"^(CCSS|ELA|MA\b|MA\.|SC\b|SC\.|SS\b|SS\.|TEKS|K\.|K-|\d|(RL|RI|RF|SL|W|L)\.|Additional)", re.I)

def clean_std(s):
    s = re.sub(r"\s+", " ", s).strip()
    return s

def split_files(s):
    return [f.strip() for f in s.splitlines() if f.strip()]

def parse(grade, path, links=None):
    links = links or {}
    text = open(path, encoding="utf-8").read()
    parts = re.split(r"^## Sheet name: (.*)$", text, flags=re.M)
    out = []
    for i in range(1, len(parts), 2):
        sheet, body = parts[i].strip(), parts[i + 1]
        if not re.search(r"\bACs?\b", sheet): continue
        subject = subject_of(sheet)
        rows = list(csv.reader(io.StringIO(body.strip("\n"))))
        if not rows: continue
        cols = [norm_col(h) for h in rows[0]]
        category, cur = None, None
        for r in rows[1:]:
            r = r + [""] * (len(cols) - len(r))
            cells = {c: r[j] for j, c in enumerate(cols) if c}
            name, files = cells.get("chart", "").strip(), cells.get("files", "").strip()
            stdcells = [v for k, v in cells.items() if k in ("ccss", "ngss", "teks", "fl", "va") and v.strip()]
            if name and not files and not stdcells and not links.get(sheet + "|" + name):
                category = name; cur = None; continue
            if name:
                cur = {"grade": grade, "subject": subject, "category": category, "chart": name,
                       "files": split_files(files), "std": {}, "exit": False, "url": links.get(sheet + "|" + name, "")}
                out.append(cur)
            if cur is None: continue
            for k in ("ccss", "ngss", "teks", "fl", "va"):
                v = cells.get(k, "")
                dest = "ngss" if (k == "ccss" and subject == "Science") else k
                if v and v.strip():
                    items = []
                    for line in v.splitlines():
                        line = line.strip()
                        if not line: continue
                        if items and not CODE_START.match(line):
                            items[-1] += " " + line
                        else:
                            items.append(line)
                    for line in items:
                        line = clean_std(line)
                        if line and line not in cur["std"].setdefault(dest, []):
                            cur["std"][dest].append(line)
            if cells.get("exit", "").strip().upper() == "TRUE": cur["exit"] = True
    # merge duplicates (same chart listed under several categories)
    merged = {}
    for c in out:
        key = (c["grade"], c["subject"], c["chart"].strip().lower())
        if key not in merged:
            c["categories"] = [c.pop("category")] if c.get("category") else []
            c.pop("category", None)
            merged[key] = c
        else:
            m = merged[key]
            if c["category"] and c["category"] not in m["categories"]: m["categories"].append(c["category"])
            for f in c["files"]:
                if f not in m["files"]: m["files"].append(f)
            for k, v in c["std"].items():
                for s in v:
                    if s not in m["std"].setdefault(k, []): m["std"][k].append(s)
            m["exit"] = m["exit"] or c["exit"]
            m["url"] = m.get("url") or c.get("url", "")
    return list(merged.values())

if __name__ == "__main__":
    a = sys.argv[1:]
    res = []
    i = 0
    while i < len(a):
        g, p = a[i], a[i + 1]; i += 2
        links = {}
        if i < len(a) and a[i].endswith(".json"):
            links = json.load(open(a[i])); i += 1
        res += parse(g, p, links)
    json.dump(res, sys.stdout, ensure_ascii=False, indent=1)
