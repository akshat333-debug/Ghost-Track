# Team workflow

3 members, each driving a Claude agent. Git is the only source of truth.

## Daily loop
1. `git pull --rebase`.
2. Read `TASKS.md` Next up + newest handoff note, then `DECISIONS.md`.
3. Claim a task in `TASKS.md`, commit `tasks: claim <task>`, push.
4. Branch `<owner-letter>/<short-name>`; do the work; run tests + format validator.
5. Same commit: code + TASKS tick + handoff note + DECISIONS/EXPERIMENTS entries + doc updates.
6. Merge to `main` (fast-forward or PR), push. Post a 1-line update in the team chat.

## Handoff note template (top of TASKS.md "Handoff notes")
```
### <date> — <task> (<owner>)
- Done:
- Next:
- Gotchas:
- How to run:
```

## Rules
- Held-out sequences are report-only (see DECISIONS D-003).
- No large files in git: datasets under `research/data/` (gitignored); trained weights > 5 MB go to Drive with the link in EXPERIMENTS.
- Colab/Kaggle notebooks: save the final `.ipynb` into `research/nets/notebooks/` with outputs cleared.
- Conflicts: owner of the file wins; the other rebases.
