"""Match Scope & Sequence charts (data/scope.json) to Chart Finder charts (data/alln.json).
Writes data/scope-match.json  ({row index: chart key or null}) and data/scope-unmatched.txt.
Chart key = "grade|chart|url" so it survives re-sorting."""
import json, os, re, difflib
from collections import defaultdict
ROOT = os.environ.get("ACC_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
G = ["K","1","2","3","4","5"]
def path(u):
    u = (u or "").split("?")[0].split("#")[0].rstrip("/")
    m = re.search(r"/categories/\d+/posts/\d+", u)
    return m.group(0) if m else re.sub(r"^https?://[^/]+", "", u)
def norm(s): return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()
key = lambda c: f'{c["grade"]}|{c["chart"]}|{c.get("url") or ""}'

def match(D, C):
    """Return (list of chart keys or None, one per D["rows"] entry, counts by method, unmatched report lines)."""
    by_path = defaultdict(list); by_name = defaultdict(list); names_by_grade = defaultdict(list)
    for c in C:
        if c.get("url"): by_path[path(c["url"])].append(c)
        by_name[(c["grade"], norm(c["chart"]))].append(c)
        names_by_grade[c["grade"]].append(norm(c["chart"]))
    out, how, left = [], defaultdict(int), []
    for u, name, p, tail in D["rows"]:
        g = G[D["units"][u][0]]
        cands = [c for c in by_path.get(path("/categories/" + tail), []) if c["grade"] == g]
        hit = None
        if len(cands) == 1: hit, h = cands[0], "link"
        elif len(cands) > 1:
            same = [c for c in cands if norm(c["chart"]) == norm(name)]
            hit, h = (same or cands)[0], "link"
        if not hit and by_name.get((g, norm(name))): hit, h = by_name[(g, norm(name))][0], "name"
        if not hit:
            close = difflib.get_close_matches(norm(name), names_by_grade[g], n=1, cutoff=0.88)
            if close: hit, h = by_name[(g, close[0])][0], "close"
        if hit: out.append(key(hit)); how[h] += 1
        else:
            out.append(None); how["none"] += 1
            left.append(f'{g:>2} | {D["subjects"][D["units"][u][1]]:<20} | {D["units"][u][2][:40]:<40} | {name}')
    return out, dict(how), left

if __name__ == "__main__":
    D = json.load(open(ROOT + "/data/scope.json"))
    C = json.load(open(ROOT + "/data/alln.json"))
    out, how, left = match(D, C)
    with open(ROOT + "/data/scope-unmatched.txt", "w") as f:
        f.write(f"Scope & Sequence charts with no Chart Finder match: {len(left)} of {len(D['rows'])}\n")
        f.write("They still show in the year plan with their library link, without a details panel.\n\n")
        f.write("\n".join(left) + "\n")
    print(how)
