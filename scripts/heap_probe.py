#!/usr/bin/env python3
"""Python heap used by src/main.py, measured with tracemalloc started before the script is even compiled.

Prints JSON: algorithm_mb = peak while estimating (probe, two passes, filter); with_compile_mb also counts the
one-off cost of compiling the script, which is the larger of the two. The interpreter's own start-up is not
ours and is excluded. Usage: scripts/heap_probe.py <imu.csv> <out.txt>
"""
import json
import sys
import tracemalloc
from pathlib import Path

MAIN = Path(__file__).resolve().parent.parent / "src" / "main.py"
tracemalloc.start()
code = compile(MAIN.read_text(), str(MAIN), "exec")
compile_peak = tracemalloc.get_traced_memory()[1]
ns = {"__name__": "pathfinder_main", "__file__": str(MAIN)}
exec(code, ns)
tracemalloc.reset_peak()
ns["main"](["main.py", sys.argv[1], sys.argv[2]])
algorithm_peak = tracemalloc.get_traced_memory()[1]
print(json.dumps({"algorithm_mb": round(algorithm_peak / 1e6, 2),
                  "with_compile_mb": round(max(compile_peak, algorithm_peak) / 1e6, 2)}))
