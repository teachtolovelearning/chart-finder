"""python prep_state.py ABBR -> builds review packets for that state's review subjects, prints them."""
import json, subprocess, sys
import os
ROOT = os.environ.get("ACC_ROOT") or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
abbr = sys.argv[1]
plan = {p[0]: p for p in json.load(open(ROOT + '/llm/plan.json'))}
_, name, rev, auto = plan[abbr]
sys.argv = ['x', 'noop']
src = open(ROOT + '/scripts/matcher.py').read(); exec(src[:src.rindex('\nif __name__')])
jur = JUR.get(name, name)
todo = [s for s in rev if sum(len(candidates(jur, SUBJ_DS[s], g)) for g in GR) >= 15]
if todo:
    subprocess.run(['python3', '-I', ROOT + '/scripts/make_batches.py', abbr] + todo, check=True)
print("REVIEW:", todo, "AUTO:", auto)
