# How to align anchor charts to a state's standards

You are an experienced K-5 curriculum specialist. Each input file (`<ST>_<Subject>.md`) is organized by grade:
1. the state's standards for that grade as `CODE :: text` (some states write standards for grade bands, so the same codes may appear under several grades),
2. the state's standards for the adjacent grades (reference only),
3. the anchor charts for that grade as `[index] Chart name | topic | the chart's existing Common Core / NGSS / TEKS alignment`.

Read each file one grade at a time with the Read tool (offset/limit) so you see each grade's full standards list before deciding.

For every chart, choose the state standard code(s) a teacher would cite for that chart.

## Rules
- Prefer the chart's own grade. Use an adjacent-grade code only if the chart's own grade has nothing that fits and the adjacent one clearly does. Never use a code from two or more grades away.
- Pick 1 code, or 2 when both are clearly taught by the chart. Never more than 2. Prefer the most specific code that fits.
- Use codes exactly as written in the file (including any trailing symbols). Never invent or alter a code, and never use one state's codes for another state.
- Match on what the chart teaches (its name and topic), using the existing alignment as a hint for the skill. A chart named "Comma" maps to the standard about commas, not quotation marks.
- Math files also list that grade's social studies standards: financial-literacy charts (spending, saving, jobs, income) may use those.
- Science: general "how to do science" charts may map to a practice/engineering standard if one is listed, otherwise empty.
- Social studies: Texas-specific content may have no match.
- If nothing reasonable fits, use an empty list.

## Output
For each input file write `<same name>.out.json` next to it (e.g. `/home/claude/llm/VA_ELA.md` → `/home/claude/llm/VA_ELA.out.json`): JSON mapping every chart index (string) to a list of codes. Build it with a short Python script, saving after each grade. Before finishing, verify every chart index in the file is present and every code appears in that file.

Reply with only, per file: charts mapped, charts left empty.
