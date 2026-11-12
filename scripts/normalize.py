"""Split each standard string into {code, text}. Usage: python normalize.py in.json out.json"""
import json, re, sys

def split(kind, s):
    s = s.strip().strip('"').strip()
    s = s.lstrip("*").strip()
    if re.match(r"(\d(st|nd|rd|th)|kinder\w*)\s+grade\s+standard|not\s+(explicitly|addressed)|addressed\s+in|ccss\s+do\s+not", s, re.I):
        return None
    if re.match(r"(additional content|n/?a$|none$|-+$)", s, re.I):
        return None
    t = s
    if kind == "ccss":
        t = re.sub(r"^CCSS[.\s]*", "", t)
        t = re.sub(r"^(Math[.\s]*Content|ELA[-\s.]?Literacy|Math|ELA)[.\s]*", "", t, flags=re.I)
        t = re.sub(r"^CCSS[.\s]*", "", t)
        m = re.match(r"((?:RL|RI|RF|SL|W|L)\.(?:K|\d)\.\d+(?:\.[a-z])?|(?:K|\d)\.[A-Z]{1,3}\.[A-Z]?\.?\d+(?:\.[a-z])?|(?:K|\d)\.[A-Z]{1,3}\.\d+(?:\.[a-z])?)\s*[:.\-–]?\s*(.*)", t, re.S)
    elif kind == "teks":
        t = re.sub(r"^TEKS\s*", "", t)
        m = re.match(r"((?:K|\d{1,2})\.?\d{1,2}(?:\.?\(?[A-Z]\)?)?(?:\.?\(?[ivx]+\)?)?)(?![\w])\s*[:.\-–]?\s*(.*)", t, re.S)
    elif kind == "fl":
        t = re.sub(r"^(ELA|MA|SC|SS)[\s.]+", lambda x: x.group(1) + ".", t)
        m = re.match(r"((?:ELA|MA|SC|SS)\.(?:K|\d)\.[A-Z]{1,3}(?:\.\d+)+(?:\.[A-Za-z]+\d*[a-z]?)*)\s*[:.\-–]?\s*(.*)", t, re.S)
    elif kind == "ngss":
        m = re.match(r"((?:K|\d)(?:-\d)?-[A-Z]{2,4}\d?-\d+)\s*[:.\-–]?\s*(.*)", t, re.S)
    else:
        m = None
    if m:
        return {"code": m.group(1).rstrip("."), "text": m.group(2).strip()}
    return {"code": "", "text": s}

if __name__ == "__main__":
    d = json.load(open(sys.argv[1]))
    misses = []
    for c in d:
        new = {}
        for k, arr in c["std"].items():
            out = []
            for s in arr:
                r = split(k, s)
                if r is None: continue
                if not r["code"]: misses.append((k, s[:90]))
                if r not in out: out.append(r)
            if out: new[k] = out
        c["std"] = new
    json.dump(d, open(sys.argv[2], "w"), ensure_ascii=False)
    print(len(misses), "without a code", file=sys.stderr)
    for k, s in misses[:60]: print(k, "|", s, file=sys.stderr)
