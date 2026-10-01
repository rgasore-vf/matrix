import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
DS = os.environ.get("SMV_DS", "/tmp/ds")  # dossier des jeux de setups (setup_dataset.py / gen.py)
import sys, json
sys.path.insert(0,os.path.join(HERE,"..")); sys.path.insert(0,os.path.join(HERE,"..",".."))
from setup_dataset import build
from smv import Config
sym, tag = sys.argv[1], sys.argv[2]
cfg = {"schema": Config(golden_schema_only=True), "be": Config(be_at_r=1.0),
       "schema_be": Config(golden_schema_only=True, be_at_r=1.0)}[tag]
with open(f"{DS}/{sym}.{tag}.jsonl","w") as f:
    for r in build(sym, cfg=cfg): f.write(json.dumps(r)+"\n")
