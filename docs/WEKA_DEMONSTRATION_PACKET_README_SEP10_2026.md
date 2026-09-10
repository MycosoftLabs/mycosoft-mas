# Weka demonstration and evidence packet

Start with `WEKA_DEMONSTRATION_RUNBOOK.pdf` or the matching Markdown. It explains Weka's role, exact v1.4 and older-kit commands, Explorer modules, a 12-minute demonstration, current limitations, the field experiment to run next, and the specific FUSARIUM work for Cursor.

## New work completed on 10 September 2026

- Fresh Java replay of the archived NLM probabilities: 14/14 arithmetic checks; 78 artifacts verified.
- Actual Weka ZeroR and default J48 comparators on the original synthetic Task 12 train/test captures.
- A single gas-resistance split gives J48 F1=1.0, showing the clean fixture does not establish an advanced-architecture advantage.
- Trial qualification remains NOT MET; field readiness is not established by this packet.

`evidence/replay/` is the complete new Java-scored run. `baselines/` contains feature ARFFs to open in Explorer, model reports, probabilities, row-ID sidecars and saved Weka models. `BASELINE_COMPARISON.json` records the experiment. The existing v1.4 Weka JARs are reused, not copied into this packet.

`DR_HESS_EMAIL_NOTE.md` is a factual draft to accompany the work. No message was sent. The runbook specifies which claims can be made now and which require the next physical experiment.

From this extracted folder, `python verify_run.py evidence/replay` verifies the complete archived run using Python 3.10+ alone. The original Weka evaluator Java/Python source and arithmetic helper are included unchanged under `formspace/weka/`. Dependencies are supplied by the original v1.4 kit. Verification of saved results does not run fresh Java or NLM inference.

The baseline script reproduces its own comparisons. It does not run or train NLM. The source-level FUSARIUM findings refer to the inspected commit, not a new production audit.
