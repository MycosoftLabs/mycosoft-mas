# ITDX v1.4 lab integration — 09 September 2026

**Date:** 09 September 2026  
**Status:** Weka replay PASS after Windows path fix. Fusarium walkthrough wired to the real receipt. Not shipped. No 187.  
**CMMC:** Mycosoft is **pursuing** CMMC L2 — not compliant. **RJ Ricasata is CFO.**  
**CUI:** No FOUO ingest. This surface is outside the CUI boundary.  
**Related:** `docs/CURSOR_ITDX26_CODEX_V13_CONNECT_SEP09_2026.md`, `docs/ITDX_EXTERNAL_SOURCES_INTEGRATION_SEP09_2026.md`

---

## Weka root cause (not Java)

Sibling inventory (`12db2008`) already established Java/Weka evaluation itself succeeded:

- 7/7 Weka evaluations
- 14 arithmetic PASS (`weka_checks.json` status PASS)
- `receipt.json` `status=COMPLETE`, `arithmetic_status=PASS`, `weka_execution=FRESH_JAVA_EVALUATION`

`TEST_WEKA.py` still exited 1 because `verify_run.py` rejected the receipt inventory.

| File | Line | Bug |
|---|---|---|
| `formspace/lab_worker.py` | 138 (`source_code`) and 140 (`artifacts`) | `str(p.relative_to(...))` on Windows writes `model\weights.pt` |
| `verify_run.py` | 16 | `if ... or '\\' in name: raise ValueError('Unsafe artifact path')` |

Receipt hashes and Weka JAR SHAs were valid. The fail was the Windows separator treated as path escape.

---

## Fix

Kit: `C:\Users\Owner1\Downloads\Mycosoft_ITDX26_v1.4.0_Standalone_Lab\Mycosoft_ITDX26_v1.4.0`

1. `formspace/lab_worker.py` now records POSIX keys:

```python
PurePosixPath(*p.relative_to(ROOT).parts).as_posix()
PurePosixPath(*p.relative_to(folder).parts).as_posix()
```

`PurePosixPath(windows_path)` alone is wrong: `os.fspath` keeps `\`. Use `.parts` then `as_posix()`.

2. `verify_run.py` normalizes historical `\` → `/` before the unsafe-path check so older Windows receipts can still verify.

Worktree `website-itdx-codex-v13` does **not** vendor `formspace/lab_worker.py`. No copy was required there.

`--mode infer` still needs Torch. Replay is not blocked on that.

---

## Prove (this machine, 09 Sep 2026)

```text
JAVA_HOME = D:\Users\admin2\.antigravity\extensions\redhat.java-1.54.0-win32-x64\jre\21.0.10-win32-x86_64
python TEST_WEKA.py --mode replay --java-home "$env:JAVA_HOME"
```

| Check | Result |
|---|---|
| Exit code | **0** |
| `verify_run` | `status=PASS`, `run_id=20260909T184028798207Z` |
| Artifacts | 78, **0 backslash keys** (`model/model.json`, `weka/task12_frozen_predictions.arff`) |
| Arithmetic | **14** |
| Trial criteria | `TRIAL_CRITERIA_NOT_MET` (honest: Task 13 coverage 0.8 vs 0.9; sample size 5 vs 20) |
| Tokens | Not printed |

Weka evaluates frozen Mycosoft probabilities. It does not train a replacement classifier.

---

## Fusarium integration (worktree only)

Worktree: `D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website-itdx-codex-v13`  
Dev server: port **3010**, this tree. Earth Sim left running. **No 187 deploy.**

| Path | Role |
|---|---|
| `itdx/artifacts/weka-v14-replay-pass.json` | Real PASS summary from the 09 Sep replay (hashes, 14 cases, failed trial gates). Not mock metrics. |
| `lib/itdx/weka-v14-receipt.ts` | Prefers latest kit `local_data/cli_runs/*/receipt.json` if COMPLETE+PASS; else vendored bytes |
| `app/api/fusarium/itdx/weka-receipt` | Owner-gated JSON for the walkthrough |
| `app/api/fusarium/itdx/run-state` | Adds `weka_v14` next to FormSpace (8766 ≠ MAS) |
| `components/itdx/ITDXWekaWalkthrough.tsx` | `/fusarium/itdx` lab / walkthrough / tests / frames / replay |
| Earth Intel Feed | Same walkthrough + math line points at the real receipt |

Live MAS remains `http://192.168.0.188:8001` for situation-assessment (weather/biology already SUPPLIED). FormSpace 8766 is not MAS. NLM stub `0.85` is not treated as `p`.

---

## Honesty

- Arithmetic PASS ≠ field accuracy, source authenticity, or Army acceptance.
- Qualification stays `EXPERIMENTAL_REFERENCE_ONLY` / `TRIAL_CRITERIA_NOT_MET`.
- FormSpace ≠ MAS. No fake BOUND. No FOUO. PR / Sandbox not cut over.
