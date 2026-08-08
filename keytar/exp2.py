import json, sys
sys.path.insert(0, "/workspace/keytar")
from experiment import run
print(json.dumps(run("flags", [
    "--disable-background-timer-throttling",
    "--disable-backgrounding-occluded-windows",
    "--disable-renderer-backgrounding",
    "--disable-ipc-flooding-protection",
]), indent=2))
