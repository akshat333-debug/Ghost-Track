"""Frozen data split (DECISIONS.md D-003). Held-out needs PF_HELDOUT=1, set only by run_heldout.sh."""
import os

SPLITS = {
    "train": ["MH_01", "MH_02", "MH_03", "V1_01", "V1_02", "V2_01", "V2_03",
              "room1", "room2", "room3", "room4"],
    "val": ["MH_05", "room5"],
    "heldout": ["MH_04", "V1_03", "V2_02", "room6"],
}


# D-007: grouped CV inside train. Each fold leaves out a whole environment.
FOLDS = [["MH_01", "MH_02", "MH_03"], ["V1_01", "V1_02"], ["V2_01", "V2_03"], ["room1", "room2"], ["room3", "room4"]]
assert sorted(sum(FOLDS, [])) == sorted(SPLITS["train"])


def sequences(split):
    if split == "heldout" and os.environ.get("PF_HELDOUT") != "1":
        raise PermissionError("held-out is report-only: run scripts/run_heldout.sh (D-003, D-006)")
    return SPLITS[split]
