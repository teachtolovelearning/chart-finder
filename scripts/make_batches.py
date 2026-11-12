"""Write review packets: one file per (state, subject) with each grade's state standards and the charts to match.
python make_batches.py OK [ELA Math Science "Social Studies"]"""
import json, sys, re, collections
import os
ROOT = os.environ.get("ACC_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.argv_saved = list(sys.argv); sys.argv = ["x", "noop"]
exec(open(ROOT + "/scripts/matcher.py").read().split("if __name__")[0])
abbr = sys.argv_saved[1]; subjects = sys.argv_saved[2:] or list(SUBJ_DS)
st = [s for s in STATES if s["abbr"] == abbr][0]; jur = JUR.get(st["state"], st["state"])
def short(t, n=170):
    t = re.sub(r"<[^>]+>|&nbsp;", " ", t); t = re.sub(r"\s+", " ", t).strip(); return t if len(t) <= n else t[:n].rsplit(" ", 1)[0] + "…"
for subj in subjects:
    lines = [f"# {st['state']} — {subj} — {framework_name(jur, SUBJ_DS[subj])}", ""]
    for g in GR:
        charts = [(i, c) for i, c in enumerate(CHARTS) if c["subject"] == subj and c["grade"] == g]
        if not charts: continue
        lines.append(f"## GRADE {g}")
        for gg in [g] + [x for x in (GR[GR.index(g)-1] if GR.index(g) else None, GR[GR.index(g)+1] if GR.index(g) < 5 else None) if x]:
            pool = candidates(jur, SUBJ_DS[subj], gg)
            if subj == "Math" and gg == g: pool = pool + candidates(jur, "Social Studies", g)
            lines.append(f"### {st['state']} standards, grade {gg}{' (adjacent grade)' if gg != g else ''}")
            seen = set()
            for x in sorted(pool, key=lambda x: ITEMS[x]["c"]):
                c = ITEMS[x]["c"]
                if c in seen: continue
                seen.add(c); lines.append(f"{c} :: {short(ITEMS[x]['d'], 220 if gg == g else 120)}")
        lines.append(f"### Charts, grade {g}")
        for i, c in charts:
            refs = []
            for f in ("ccss", "ngss", "teks", "fl"):
                if refs and f in ("teks", "fl"): break
                for s in c["std"].get(f, [])[:2]:
                    refs.append(f"{f.upper()} {s['code']}: {short(s['text'], 85)}")
            lines.append(f"[{i}] {c['chart']} | {', '.join(c['categories'][:1]) or '-'} | " + " || ".join(refs[:2]))
        lines.append("")
    fn = f"{ROOT}/llm/{abbr}_{subj.replace(' ', '_')}.md"
    open(fn, "w").write("\n".join(lines))
    print(fn, len("\n".join(lines)) // 4, "tokens approx")
