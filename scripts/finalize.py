"""Assemble std/final/<ABBR>.json for each state from reviewed (llm/*.out.json) or automatic matches.
python finalize.py OK [MORE ...]   or   python finalize.py ALL"""
import json, os, re, sys, collections
import os
ROOT = os.environ.get("ACC_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_argv = list(sys.argv); sys.argv = ["x", "noop"]
exec(open(ROOT + "/scripts/matcher.py").read().split("if __name__")[0])
sys.argv = _argv

GRADES_OF = {}
def code_index(jur, subj_ds):
    idx = {}
    for iid, x in ITEMS.items():
        if x["j"] == jur and x["s"] == subj_ds and x["f"] in CUR and x["c"]:
            gs = x["g"].split(",")
            if any(g in GR for g in gs):
                x = dict(x); x["c"] = re.sub(r"^(Objective|Standard)\s*:\s*", "", x["c"]).strip()
                idx.setdefault(x["c"], re.sub(r"\s+", " ", re.sub(r"<[^>]+>|&nbsp;", " ", x["d"])).strip())
                GRADES_OF.setdefault((jur, x["c"]), set()).update(gs)
    return idx

def auto_subject(jur, subj):
    """Automatic matching for states whose standards reword Common Core / NGSS (and math crosswalks)."""
    out = {}
    by_grade = collections.defaultdict(list)
    for i, c in enumerate(CHARTS):
        if c["subject"] == subj: by_grade[c["grade"]].append((i, c))
    ref_fws = ["ccss", "ngss", "teks", "fl"]
    for g, lst in by_grade.items():
        res = match_group(jur, subj, g, lst, ref_fws, "split")
        for i, _ in lst:
            p = pick(res.get(i, []), 0.12, rel=0.8, k=2)
            if p: out[str(i)] = [ITEMS[x]["c"] for x in p]
    return out

def finalize(abbr, review_subjects=None):
    st = [s for s in STATES if s["abbr"] == abbr][0]
    jur = JUR.get(st["state"], st["state"])
    res = {"state": st["state"], "abbr": abbr, "subjects": {}, "map": {}, "std": {}}
    report = {}
    for subj, sds in SUBJ_DS.items():
        typ = (st.get(SUBJ_KEY.get(subj, ""), {}) or {}).get("type") if subj in SUBJ_KEY else None
        if abbr in ("TX", "FL") or typ in ("ccss", "ngss"):
            res["subjects"][subj] = {"mode": "exact"}; continue
        if sum(len(candidates(jur, sds, g)) for g in GR) < 15:
            res["subjects"][subj] = {"mode": "fallback"}; report[subj] = "fallback (no data)"; continue
        fn = f"{ROOT}/llm/{abbr}_{subj.replace(' ', '_')}.out.json"
        idx = code_index(jur, sds)
        if subj == "Math": idx.update({k: v for k, v in code_index(jur, "Social Studies").items() if k not in idx})
        if os.path.exists(fn):
            m = json.load(open(fn)); src = "reviewed"
        else:
            m = auto_subject(jur, subj); src = "auto"
        bad = 0; n = 0
        for i, codes in m.items():
            loose = {re.sub(r"[^A-Za-z0-9]", "", k).lower(): k for k in idx}
            codes = [c if c in idx else loose.get(re.sub(r"[^A-Za-z0-9]", "", c).lower(), c) for c in codes]
            cg = GR.index(CHARTS[int(i)]["grade"])
            ok_g = {GR[k] for k in (cg - 1, cg, cg + 1) if 0 <= k < len(GR)}
            keep = [c for c in codes if c in idx and (GRADES_OF.get((jur, c), set()) & ok_g)][:2]
            bad += len(codes) - len(keep)
            if keep:
                res["map"].setdefault(i, []); n += 1
                for c in keep:
                    if c not in res["map"][i]: res["map"][i].append(c)
                    res["std"][c] = idx[c]
        res["subjects"][subj] = {"mode": "matched", "fw": framework_name(jur, sds), "src": src}
        total = sum(1 for c in CHARTS if c["subject"] == subj)
        report[subj] = f"{src} {n}/{total}" + (f" ({bad} unknown codes dropped)" if bad else "")
    os.makedirs(ROOT + "/std/final", exist_ok=True)
    json.dump(res, open(f"{ROOT}/std/final/{abbr}.json", "w"), ensure_ascii=False)
    print(abbr, report)

if __name__ == "__main__":
    want = sys.argv[1:]
    abbrs = [s["abbr"] for s in STATES] if want == ["ALL"] else want
    for a in abbrs: finalize(a)
