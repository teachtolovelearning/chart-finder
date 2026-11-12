"""Chart -> state standard matcher, with an evaluation mode against hand alignments (TX, FL).
python matcher.py eval            # score methods on Texas and Florida
python matcher.py run [ABBR ...]  # write std/out/<ABBR>.json
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
GR = ["K", "1", "2", "3", "4", "5"]
STOP = {"students", "student", "will", "use", "using", "including", "eg", "ie", "grade", "level", "appropriate",
        "standard", "standards", "understand", "understanding", "demonstrate", "identify", "describe", "explain",
        "nbsp", "div", "br", "with", "prompting", "support", "adult", "assistance", "independently"}

def clean(s):
    s = re.sub(r"<[^>]+>|&nbsp;", " ", s.lower())
    s = re.sub(r"\$[^$]*\$", " ", s)
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    return " ".join(w for w in s.split() if w not in STOP)

def ncode(code): return re.sub(r"[^a-z0-9]", "", code.lower())
CCSS_FW = {k for k, f in FW.items() if f["j"] == "Multi-State" and f["n"].startswith("Common Core State Standards")}
CCSS_BY_CODE = collections.defaultdict(list)
for iid, x in ITEMS.items():
    if x["f"] in CCSS_FW and x["c"]:
        CCSS_BY_CODE[ncode(x["c"])].append(iid)
XWALK = collections.defaultdict(list)
for s, t, jac, *_ in ALIGN:
    if s in ITEMS and t in ITEMS:
        XWALK[t].append((s, jac))

_cand_cache = {}
def candidates(jur, subj_ds, grade):
    key = (jur, subj_ds, grade)
    if key in _cand_cache: return _cand_cache[key]
    out = []
    for iid, x in ITEMS.items():
        if x["j"] != jur or x["s"] != subj_ds or x["f"] not in CUR or x["t"] != "Standard" or not x["c"]:
            continue
        gs = x["g"].split(",")
        if grade not in gs or len(gs) > 4: continue
        if re.match(r"^(SEP|CCC|MAP|MP)[.\s\d]", x["c"]): continue
        out.append(iid)
    _cand_cache[key] = out
    return out

def framework_name(jur, subj_ds):
    names = [f["n"] for f in FW.values() if f["j"] == jur and f["s"] == subj_ds and f["c"] == "true"]
    return sorted(names, key=len)[0] if names else ""

FIN = re.compile(r"financ|money|income|wants|needs|saving|spending|budget|jobs|goods|services", re.I)

def match_group(jur, subj, g, lst, ref_fws, method):
    """lst: [(chart_index, chart)] all same subject & grade. Returns {i: [(item, score), ...]} sorted."""
    gi = GR.index(g)
    pool = [(x, 1.0) for x in candidates(jur, SUBJ_DS[subj], g)]
    seen = {p for p, _ in pool}
    for adj in (gi - 1, gi + 1):
        if 0 <= adj < len(GR):
            for x in candidates(jur, SUBJ_DS[subj], GR[adj]):
                if x not in seen: pool.append((x, 0.75)); seen.add(x)
    n_main = len(pool)
    if subj == "Math":
        for x in candidates(jur, "Social Studies", g):
            if x not in seen: pool.append((x, 0.9)); seen.add(x)
    if not pool: return {}
    cands = [p for p, _ in pool]; w = np.array([wt for _, wt in pool]); is_extra = np.arange(len(pool)) >= n_main
    ctext = [clean(ITEMS[x]["d"]) for x in cands]
    names = [clean(" ".join([c["chart"]] + c.get("categories", []))) for _, c in lst]
    refs = [[(clean(s["text"]), 1.0 if f in ("ccss", "ngss") else 0.85) for f in ref_fws for s in c["std"].get(f, []) if s["text"]] for _, c in lst]
    allref = [t for r in refs for t, _ in r]
    vec = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english", min_df=1).fit(ctext + names + allref)
    C = vec.transform(ctext)
    out = {}
    cidx = {x: j for j, x in enumerate(cands)}
    for row, (i, c) in enumerate(lst):
        name_sim = (vec.transform([names[row]]) @ C.T).toarray()[0]
        if method == "concat":
            q = clean(" ".join([c["chart"]] * 3 + c.get("categories", []) + [t for t, _ in refs[row]]))
            s = (vec.transform([q]) @ C.T).toarray()[0]
        else:
            if refs[row]:
                R = vec.transform([t for t, _ in refs[row]])
                rs = (R @ C.T).toarray() * np.array([wt for _, wt in refs[row]])[:, None]
                ref_sim = rs.max(axis=0)
            else:
                ref_sim = np.zeros(len(cands))
            s = 0.65 * ref_sim + 0.35 * name_sim + 0.25 * np.minimum(ref_sim, name_sim)
        s = s * w
        if not FIN.search(" ".join(c.get("categories", [])) + " " + c["chart"]):
            s = np.where(is_extra, 0, s)
        if subj in ("ELA", "Math") and "ccss" in ref_fws:
            for cs in c["std"].get("ccss", []):
                for cid in CCSS_BY_CODE.get(ncode(cs["code"]), []):
                    for sid, jac in XWALK.get(cid, []):
                        if sid in cidx: s[cidx[sid]] += (0.5 * jac + 0.15) * w[cidx[sid]]
        order = np.argsort(-s)[:5]
        out[i] = [(cands[j], float(s[j])) for j in order]
    return out

def pick(ranked, floor, rel=0.72, k=3):
    if not ranked or ranked[0][1] < floor: return []
    top = ranked[0][1]
    return [x for x, sc in ranked[:k] if sc >= max(floor, rel * top)]

# ---------------- evaluation against hand alignments ----------------
def tx_norm(code, grade):
    m = re.match(r"^\d+\.\d+\.[a-z]\.(\d+)\.([A-Z])", code)
    return f"{grade}.{m.group(1)}{m.group(2)}".lower() if m else ncode(code)
def lb_tx_norm(code):
    m = re.match(r"^(K|\d)\.?(\d+)\(?([A-Z])", code, re.I)
    return f"{m.group(1)}.{m.group(2)}{m.group(3)}".lower() if m else ncode(code)
def fl_norm(code): return ncode(code)

def evaluate(method, floors=(0.0, 0.05, 0.08, 0.1, 0.12, 0.15, 0.2)):
    for abbr, jur, fwk in (("TX", "Texas", "teks"), ("FL", "Florida", "fl")):
        ref_fws = [f for f in ("ccss", "ngss", "teks", "fl") if f != fwk]
        stats = {f: collections.Counter() for f in floors}
        per_subj = collections.defaultdict(collections.Counter)
        for subj in SUBJ_DS:
            by_grade = collections.defaultdict(list)
            for i, c in enumerate(CHARTS):
                if c["subject"] == subj and c["std"].get(fwk): by_grade[c["grade"]].append((i, c))
            for g, lst in by_grade.items():
                res = match_group(jur, subj, g, lst, ref_fws, method)
                for i, c in lst:
                    truth = {lb_tx_norm(s["code"]) if fwk == "teks" else fl_norm(s["code"]) for s in c["std"][fwk] if s["code"]}
                    if not truth: continue
                    ranked = res.get(i, [])
                    for f in floors:
                        p = pick(ranked, f)
                        stats[f]["n"] += 1
                        if not p: continue
                        stats[f]["answered"] += 1
                        codes = [tx_norm(ITEMS[x]["c"], ITEMS[x]["g"].split(",")[0]) if fwk == "teks" else fl_norm(ITEMS[x]["c"]) for x in p]
                        if codes[0] in truth: stats[f]["top1"] += 1
                        if any(cd in truth for cd in codes): stats[f]["any"] += 1
                    p = pick(ranked, 0.08)
                    if p:
                        codes = [tx_norm(ITEMS[x]["c"], ITEMS[x]["g"].split(",")[0]) if fwk == "teks" else fl_norm(ITEMS[x]["c"]) for x in p]
                        per_subj[subj]["ans"] += 1; per_subj[subj]["any"] += any(cd in truth for cd in codes)
        print(f"\n{abbr} [{method}]")
        for f in floors:
            s = stats[f]
            print(f"  floor {f:.2f}: answered {s['answered']}/{s['n']}  top1 prec {s['top1']/max(1,s['answered']):.2f}  any-hit prec {s['any']/max(1,s['answered']):.2f}")
        print("  by subject @0.08:", {k: f"{v['any']}/{v['ans']}" for k, v in per_subj.items()})

if __name__ == "__main__":
    if sys.argv[1] == "eval":
        for m in sys.argv[2:] or ["concat", "split"]:
            evaluate(m)
