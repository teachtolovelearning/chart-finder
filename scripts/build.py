"""Combine parsed lookbooks + state research into the guide page.
Usage: python build.py out.html data/g*.n.json  (state file read from research/state_standards.json if present)"""
import json, os, re, sys
import os
ROOT = os.environ.get("ACC_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

FW = ["ccss", "ngss", "teks", "fl"]
SUBJ = ["ELA", "Math", "Science", "Social Studies"]
GRADE_ORDER = {"K": 0, "1": 1, "2": 2, "3": 3, "4": 4, "5": 5}
KINDS = ["full", "mini", "fill", "printable"]

def kinds(files):
    m = 0
    for f in files:
        f = f.lower()
        for i, k in enumerate(KINDS):
            if f.startswith(k): m |= 1 << i
    return m

def main(out, inputs):
    std_idx, S, C = {}, [], []
    for p in inputs:
        for c in json.load(open(p)):
            if c["subject"] not in SUBJ:
                SUBJ.append(c["subject"])
            ids = []
            for fw in FW:
                for s in c["std"].get(fw, []):
                    key = (fw, s["code"], s["text"])
                    if key not in std_idx:
                        std_idx[key] = len(S); S.append([FW.index(fw), s["code"], s["text"]])
                    ids.append(std_idx[key])
            C.append([c["grade"], SUBJ.index(c["subject"]), c["chart"].strip(), c["categories"], ids,
                      kinds(c["files"]), 1 if c["exit"] else 0, c.get("url", "")])
    order = sorted(range(len(C)), key=lambda k: (GRADE_ORDER.get(C[k][0], 9), C[k][1]))
    newpos = {old: new for new, old in enumerate(order)}
    C = [C[k] for k in order]
    import glob
    os.makedirs(ROOT + "/docs/states", exist_ok=True)
    state_files = []
    for fpath in sorted(glob.glob(ROOT + "/std/final/*.json")):
        sf = json.load(open(fpath))
        codes, table, mp = {}, [], {}
        for oi, cl in sf["map"].items():
            ids = []
            for code in cl:
                if code not in codes:
                    codes[code] = len(table); table.append([code, sf["std"].get(code, "")])
                ids.append(codes[code])
            if ids: mp[newpos[int(oi)]] = ids
        sdata = {"subjects": sf["subjects"], "map": mp, "std": table}
        json.dump(sdata, open(f"{ROOT}/docs/states/{sf['abbr']}.json", "w"), ensure_ascii=False, separators=(",", ":"))
        state_files.append(sf["abbr"])
    states = []
    sp = ROOT + "/research/state_standards.json"
    if os.path.exists(sp):
        states = json.load(open(sp))
    states = [{k: v for k, v in st.items() if k in ("state", "abbr", "ela", "math", "science")} for st in states]
    data = {"S": S, "C": C, "subjects": SUBJ, "states": states, "stateFiles": state_files, "checked": "November 2026",
            "sourceNote": "State matches are based on each state education department's current K–5 standards and the NSTA and Education Week standards trackers, checked November 2026. States update standards every few years, so check your state's site when a new set rolls out."}
    tpl = open(ROOT + "/src/app.html", encoding="utf-8").read()
    js = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = tpl.replace("/*__DATA__*/null", js).replace("__FAVICON__", "data:image/png;base64," + open(ROOT + "/src/favicon.clean").read().strip()).replace("__LOGO__", "data:image/webp;base64," + open(ROOT + "/src/logo.clean").read().strip())
    open(out, "w", encoding="utf-8").write(html)
    print(f"{len(C)} charts, {len(S)} standards, {len(states)} states, {len(html)//1024} KB")

if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
