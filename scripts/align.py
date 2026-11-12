"""Align Anchor Chart Club charts to each state's own K-5 standards.
Usage: python align.py [STATE_ABBR ...]   (default: all states that need it)
Writes std/out/<ABBR>.json with, per subject, chart index -> list of state standard ids, and the standards used.
"""
import gzip, json, re, sys, os, collections
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

ROOT = os.environ.get("ACC_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = json.load(gzip.open(f"{ROOT}/std/state-standards-k5.json.gz"))
FW, ITEMS, ALIGN = D["fw"], D["items"], D["align"]
CHARTS = json.load(open(f"{ROOT}/data/alln.json"))
STATES = json.load(open(f"{ROOT}/research/state_standards.json"))
SUBJ_DS = {"ELA": "English Language Arts", "Math": "Mathematics", "Science": "Science", "Social Studies": "Social Studies"}
SUBJ_KEY = {"ELA": "ela", "Math": "math", "Science": "science"}
JUR = {"District of Columbia": "Washington, D.C."}
CUR = {k for k, f in FW.items() if f["c"] == "true"}

STOP_EXTRA = {"students", "student", "will", "use", "using", "including", "e.g", "eg", "ie", "grade", "level", "appropriate",
              "text", "texts", "standard", "standards", "understand", "understanding", "demonstrate", "identify", "describe"}

def clean(s):
    s = s.lower()
    s = re.sub(r"\$[^$]*\$", " ", s)
    s = re.sub(r"[^a-z0-9\s-]", " ", s)
    return " ".join(w for w in s.split() if w not in STOP_EXTRA)

def chart_query(c):
    parts = [c["chart"]] * 3 + c.get("categories", [])
    for fwk in ("ccss", "ngss", "teks", "fl"):
        for s in c["std"].get(fwk, []):
            parts.append(s["text"])
    return clean(" ".join(parts))

# CCSS item lookup (Multi-State CCSS frameworks) by normalized code
def ncode(code):
    return re.sub(r"[^a-z0-9]", "", code.lower())
CCSS_FW = {k for k, f in FW.items() if f["j"] == "Multi-State" and f["n"].startswith("Common Core State Standards")}
CCSS_BY_CODE = collections.defaultdict(list)
for iid, x in ITEMS.items():
    if x["f"] in CCSS_FW and x["c"]:
        CCSS_BY_CODE[ncode(x["c"])].append(iid)
XWALK = collections.defaultdict(list)  # ccss item id -> [(state item id, jaccard)]
for s, t, jac, *_ in ALIGN:
    if s in ITEMS and t in ITEMS:
        XWALK[t].append((s, jac))

def candidates(jur, subj_ds, grade):
    out = []
    for iid, x in ITEMS.items():
        if x["j"] != jur or x["s"] != subj_ds or x["f"] not in CUR or x["t"] != "Standard" or not x["c"]:
            continue
        gs = x["g"].split(",")
        if grade not in gs or len(gs) > 3:
            continue
        if re.match(r"^(SEP|CCC|MAP|MP)\b", x["c"]) or re.match(r"^(SEP|CCC)\.", x["c"]):
            continue
        out.append(iid)
    return out

def framework_name(jur, subj_ds):
    names = [(f["n"]) for k, f in FW.items() if f["j"] == jur and f["s"] == subj_ds and f["c"] == "true"]
    return sorted(names, key=len)[0] if names else ""

def align_state(st):
    jur = JUR.get(st["state"], st["state"])
    result = {"state": st["state"], "abbr": st["abbr"], "subjects": {}, "std": {}}
    for subj, subj_ds in SUBJ_DS.items():
        if st["abbr"] in ("TX", "FL"):
            continue
        typ = (st.get(SUBJ_KEY.get(subj, ""), {}) or {}).get("type") if subj in SUBJ_KEY else None
        if typ in ("ccss", "ngss"):
            result["subjects"][subj] = {"mode": "exact"}
            continue
        charts = [(i, c) for i, c in enumerate(CHARTS) if c["subject"] == subj]
        by_grade = collections.defaultdict(list)
        for i, c in charts:
            by_grade[c["grade"]].append((i, c))
        mapping, scores = {}, {}
        GR = ["K", "1", "2", "3", "4", "5"]
        for g, lst in by_grade.items():
            gi = GR.index(g) if g in GR else 0
            pool = [(x, 1.0, g) for x in candidates(jur, subj_ds, g)]
            for adj in (gi - 1, gi + 1):
                if 0 <= adj < len(GR):
                    seen = {p for p, _, _ in pool}
                    pool += [(x, 0.75, GR[adj]) for x in candidates(jur, subj_ds, GR[adj]) if x not in seen]
            ss_pool = []
            if subj == "Math":
                seen = {p for p, _, _ in pool}
                ss_pool = [(x, 0.9, g) for x in candidates(jur, "Social Studies", g) if x not in seen]
            if not pool:
                continue
            allp = pool + ss_pool
            cands = [p for p, _, _ in allp]
            w = np.array([wt for _, wt, _ in allp])
            is_ss = np.array([i >= len(pool) for i in range(len(allp))])
            ctext = [clean(ITEMS[x]["d"]) for x in cands]
            qtext = [chart_query(c) for _, c in lst]
            vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english", min_df=1)
            vec.fit(ctext + qtext)
            C = vec.transform(ctext); Q = vec.transform(qtext)
            sim = (Q @ C.T).toarray()
            cidx = {x: j for j, x in enumerate(cands)}
            for row, (i, c) in enumerate(lst):
                s = sim[row] * w
                fin = bool(re.search(r"financ|money|income|wants|needs|saving|spending|budget|jobs", " ".join(c.get("categories", [])) + " " + c["chart"], re.I))
                if not fin:
                    s = np.where(is_ss, 0, s)
                if subj in ("ELA", "Math"):
                    for cs in c["std"].get("ccss", []):
                        for cid in CCSS_BY_CODE.get(ncode(cs["code"]), []):
                            for sid, jac in XWALK.get(cid, []):
                                if sid in cidx:
                                    s[cidx[sid]] += (0.5 * jac + 0.15) * w[cidx[sid]]
                order = np.argsort(-s)
                top = s[order[0]]
                if top < 0.07:
                    continue
                picks = [cands[j] for j in order[:3] if s[j] >= max(0.07, 0.72 * top)]
                mapping[i] = picks
                scores[i] = round(float(top), 3)
        for picks in mapping.values():
            for p in picks:
                x = ITEMS[p]
                result["std"][p] = [x["c"], re.sub(r"\s+", " ", x["d"]).strip()]
        result["subjects"][subj] = {"mode": "matched", "fw": framework_name(jur, subj_ds), "map": mapping, "score": scores,
                                    "n_charts": len(charts)}
    return result

if __name__ == "__main__":
    os.makedirs(f"{ROOT}/std/out", exist_ok=True)
    want = set(sys.argv[1:])
    for st in STATES:
        if want and st["abbr"] not in want:
            continue
        r = align_state(st)
        json.dump(r, open(f"{ROOT}/std/out/{st['abbr']}.json", "w"), ensure_ascii=False)
        summ = {s: (v["mode"] if v["mode"] == "exact" else f'{len(v["map"])}/{v["n_charts"]}') for s, v in r["subjects"].items()}
        print(st["abbr"], summ, len(r["std"]), "standards")
