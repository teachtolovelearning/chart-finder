"""Convert a lookbook .xlsx into the same '## Sheet name:' CSV text the parser reads,
and write a side file of chart hyperlinks.
Usage: python xlsx_to_text.py in.xlsx out.txt out_links.json"""
import csv, io, json, re, sys
import openpyxl

HL = re.compile(r'^=\s*HYPERLINK\(\s*"([^"]+)"\s*[,;]\s*"([^"]*)"\s*\)', re.I)

def main(src, out_txt, out_links):
    wb_f = openpyxl.load_workbook(src, data_only=False)
    wb_v = openpyxl.load_workbook(src, data_only=True)
    parts, links = [], {}
    for ws in wb_f.worksheets:
        wv = wb_v[ws.title]
        buf = io.StringIO()
        w = csv.writer(buf, lineterminator="\n")
        for r_f, r_v in zip(ws.iter_rows(), wv.iter_rows()):
            row = []
            for cf, cv in zip(r_f, r_v):
                val = cv.value
                url = cf.hyperlink.target if cf.hyperlink is not None and cf.hyperlink.target else None
                if isinstance(cf.value, str):
                    m = HL.match(cf.value)
                    if m:
                        url = url or m.group(1)
                        if val is None or str(val).startswith("="): val = m.group(2)
                if val is None: val = ""
                if isinstance(val, bool): val = "TRUE" if val else "FALSE"
                val = str(val)
                if url and cf.column == 1 and val.strip():
                    links[(ws.title + "|" + val.strip())] = url
                row.append(val)
            while row and row[-1] == "": row.pop()
            w.writerow(row)
        parts.append(f"## Sheet name: {ws.title}\n{buf.getvalue()}")
    open(out_txt, "w", encoding="utf-8").write("\n\n".join(parts))
    json.dump(links, open(out_links, "w"), ensure_ascii=False, indent=0)
    print(f"{src}: {len(wb_f.worksheets)} sheets, {len(links)} chart links")

if __name__ == "__main__":
    main(*sys.argv[1:4])
