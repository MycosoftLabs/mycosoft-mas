# Perplexity handoff — Dr. Hess emails and attachments

**Date**: September 10, 2026  
**Author**: Cursor for Morgan Rockcoons (CEO/CTO/COO/SAO). RJ Ricasata is CFO.  
**Status**: Complete — paste-ready  
**Classification**: UNCLASSIFIED commercial briefing only. No CUI. No FOUO.

## How to use (Morgan — do this first)

1. Open a **new** Perplexity thread (or Space) used only for this Hess packet.
2. **Copy everything between the two `PASTE INTO PERPLEXITY` markers** below. Do **not** copy this “How to use” block and do **not** copy the **Internal only** section at the bottom of this file.
3. **Then attach** the files you intend Hess (or the draft) to see:
   - White papers / Nature Learning Model / FormSpace math (your PDFs)
   - WEKA demonstration runbook (PDF or Markdown)
   - WEKA evidence ZIP or the extracted demonstration folder (or the small JSON/ARFF subset if the ZIP is too large)
   - Your **modified** `DR_HESS_EMAIL_NOTE` (this is the email skeleton)
   - Any catalogs or figure packs you want cited
4. Send. Tell Perplexity: “Draft from my attachments. Follow the constraints in the pasted prompt. Attachments win on math/numbers; the prompt wins on claims/limits.”
5. Review every draft before sending. You send the email. Perplexity does not send it.
6. If an attachment and this prompt disagree on a **number or equation**, keep the attachment. If they disagree on a **claim** (field-ready, live COP, FormSpace superiority, CMMC), keep this prompt.

---

## PASTE INTO PERPLEXITY — START

You are drafting **UNCLASSIFIED commercial scientific/partner communications** for **Dr. Hess**, an external scientific / ITDX collaborator.

The human sender is **Morgan Rockcoons**, CEO, CTO, COO, and SAO of **Mycosoft**. **RJ Ricasata is CFO.** Do not use any other last name for Morgan. Do not title RJ as COO.

Mycosoft is **pursuing** CMMC Level 2. Never write that Mycosoft “is CMMC compliant,” “is CMMC L2,” or that any control is Met unless an attached evidence artifact explicitly says so — and even then do not put compliance claims in Hess-facing text.

This surface is **outside** any CUI boundary. Produce **no CUI, no FOUO, no live COP claims, no secrets, no passwords, no API keys, no internal IP addresses, no VM hostnames, no NAS paths, no credential filenames.**

### Source of truth

1. **Attachments Morgan uploads in this thread** are the source for white papers, NLM/FormSpace mathematics, WEKA data, catalogs, figures, and his **modified email note**.
2. If an attachment and this prompt **conflict on math, equations, parameter counts, hashes, or measured numbers**, **the attachments win**. Cite the figure, equation, or table. Do not rewrite the math.
3. If an attachment and this prompt **conflict on claims or limits** (accuracy, field readiness, live operations, architecture advantage, Army requirements), **this prompt wins**. Do not “improve” the story into a stronger claim.
4. Do not invent results Hess would treat as published science. If a number is not in an attachment, write **not supplied** or omit it.

### What Weka is (quote this accurately; do not rebrand it)

Weka is the **evaluation workbench around the algorithm**. **NLM produces predictions; Weka measures how those predictions compare with known outcomes.** You do **not** need Weka to operate NLM in the field. You use it to make evaluation reproducible, inspect mistakes, and compare against simpler methods.

The adapter supplies **NLM probability distributions** to Weka’s `Evaluation` API (score the supplied distributions; do **not** train a replacement classifier and call that NLM). Official API: https://weka.sourceforge.io/doc.dev/weka/classifiers/Evaluation.html

Example: NLM reports p = 0.9 for a candidate event; later an independently established outcome says whether it occurred. Across withheld examples:

- **Precision / recall** — false alarms / missed events
- **Brier** — how wrong the probabilities were (especially confident mistakes)
- **Calibration** — do ~90% forecasts occur ~90% of the time in the tested population
- **Abstention** — insufficient evidence for a supported prediction

A convincing probability alone cannot establish accuracy. **Outcomes are required.**

### Cursor insights — constraints. Do not “improve” these away.

Treat the following as hard limits unless an attachment **explicitly** records a stronger, independently evidenced result (and even then, keep the wording conservative).

**Evaluation vs operation**

- NLM / FormSpace computes states and probabilities. Weka scores them. FUSARIUM (the operator UI) **reads saved receipts**. Opening a Fusarium / ITDX panel does **not** launch a new test.
- ITDX on Fusarium Earth Simulator is a **collapsible panel** for demonstration / evidence, not a live common operational picture. Demo overlays are **not** live COP. Do not write `live: true` or equivalent unless an attachment shows an independently verified live ingest with that flag.
- MYCA may propose a task; AVANI may dispose it. Do **not** claim droids, missions, or physical responses already executed unless an attachment contains an **execution receipt** plus a later independent measurement.

**What was actually run (10 September 2026 packet)**

- Fresh **Java** replay of **recorded** NLM probabilities: **14/14 arithmetic checks**, **78 artifacts verified**. This **rescored recorded NLM predictions**. It did **not** rerun NLM inference, train NLM, or collect new field data.
- Trial / local qualification remains **NOT MET** if the packet says so. Field readiness is **not established**. Local trial criteria are **not** Army requirements.
- ZeroR and default **J48** were trained on original **synthetic** Task 12 training captures and evaluated on separate synthetic test captures. **J48 F1 = 1.0 using one gas-resistance split.** That means the **clean synthetic set is too easily separable** to show FormSpace or temporal advantage. The fixture is still useful for execution, missingness, bias, and abstention. A stronger experiment must show **where the architecture adds value**.
- Do not present clean synthetic F1 = 1.0 as proof that NLM, FormSpace, or temporal memory is necessary.

**How to use Weka now**

| Component | Purpose |
|---|---|
| Explorer → Preprocess | Inspect prediction files, features, labels, missing values |
| Evaluation API via adapter | Score **actual NLM** probabilities |
| Classify → rules → ZeroR | Simplest baseline |
| Classify → trees → J48 | Check whether a simple rule already solves the set |
| Supplied test set | Separate captures; **not** random cross-validation on correlated rows |

NLM is **not** an Explorer-selectable Java classifier. The adapter is the evaluation route. Prediction ARFFs (`p_background`, `p_candidate`, `actual`) are outputs to score. Feature ARFFs are for ZeroR / J48. Do not train a Weka classifier on prediction ARFFs and call that NLM validation.

**Next useful demonstration (design with Hess; do not claim it is done)**

One complete environmental event:

1. Sensor measurements, model identity, defined event
2. Fresh inference + Weka evaluation
3. Connect probability to supporting observations
4. Bias, missingness, unsupported-input behavior
5. Follow through MYCA proposal → AVANI disposition → map
6. If physical response: execution receipt + later independent measurement
7. Export that exact run

Usefulness / readiness study still needs: **independent outcomes**, **unseen captures**, **predictions recorded before outcomes are revealed**. Measure warning time, missed events, false alerts per hour, and whether the response helped the operator.

**Task 8** (governance / courses of action) and **Task 14** (map correctness) need **their own checks**. **Task 12 / 13 F1 does not validate them.**

**Ask Dr. Hess (must appear in the emails)**

- Preferred interface: current Weka API evaluation of frozen distributions, an Explorer-selectable classifier wrapper, or an organizer-provided harness?
- Confirm task labels, forecast horizons, holdout protocol, and the meaning of any **1–5** rubric. Do not divide a 1–5 rating by five and call it a probability.

**NLM identity**

- **NLM ≠ Llama, Ollama, or Nemotron chat.** FormSpace NLM is a scientific / numerical model, not a conversational LLM.
- Cursor’s archived blueprint reference (use **attachment numbers if they differ**): **25,728 parameters / 47 tensors / 49 equations**.
- Specification checks **21/21** mean **specified arithmetic passed**, **not** a live trained production model and **not** field validation.
- Never invent a probability such as **0.85**. If probability is unknown, say unknown / not supplied / null.

**Honesty about what is not claimed**

- Do not say the model is production-validated if only spec arithmetic or a synthetic replay passed.
- Do not claim Army acceptance, official injects, or FOUO evaluation unless an attachment is clearly UNCLASSIFIED public science and Hess already has it.
- Audio / NotebookLM companions, if mentioned, are explanatory only. Written sources and receipts are authoritative.

### Outputs you must produce

Draft all of the following in this thread. Label each output clearly. Keep Hess-facing text free of internal infrastructure.

**A. Primary email to Dr. Hess**  
Use Morgan’s **modified `DR_HESS_EMAIL_NOTE` attachment as the skeleton**. Preserve his intent and questions. Correct only: sender name (**Morgan Rockcoons**), RJ as **CFO**, CMMC wording (**pursuing L2**), Weka role, and over-claims. Include: subject line, greeting, one-page body, closing. Factual, humble, invitation to design the next experiment together. No hype. No “we proved FormSpace superiority.”

**B. Short follow-up / questions email**  
A brief second note Hess can answer: evaluation interface (API vs Explorer classifier vs organizer harness); task labels; horizons; 1–5 rubric; what independent outcomes he wants next.

**C. Attachment list for the send**  
Suggested filenames (UNCLASSIFIED, no secrets in names) and a one-line description of each. Prefer: runbook PDF, white paper(s), NLM math paper, a short evidence summary, selected ARFF/JSON receipts if small. If the full evidence ZIP is huge, recommend attaching the runbook + verification JSON + baseline comparison + J48 report, and offering the full packet on a channel Hess already uses.

**D. Slide outline or one-pager**  
10–14 slides **or** a one-page brief that **summarizes the attached white papers and NLM math**. Do **not** rewrite equations. Cite figure numbers and equation numbers from the attachments. Must include: problem; Weka as evaluation (not field NLM); 14/14 replay scope; J48 = 1.0 synthetic caveat; MYCA/AVANI as proposal path not executed-droid claim; honest gaps; proposed joint tests.

**E. Optional cover letter for the WEKA evidence packet**  
One short letter: what the packet is, what Java replay did and did not do, where ZeroR/J48 live, that trial criteria are local and not met, that the next experiment needs independent outcomes.

**F. What not to attach**  
List: anything FOUO/CUI; credential files; `.env` / `.credentials`; internal IP lists; VM passwords; owner-only API routes; Army injects; live COP dumps; unreviewed audio if it contradicts the written receipts.

### Tone

Scientific colleague. Short sentences. Numbers with scope. Invitation, not a victory lap.

---

## PASTE INTO PERPLEXITY — END

---

## Related Cursor docs (Morgan — optional; do not paste unless you want Perplexity to see them)

Perplexity should draft from **your** attachments. These MAS files are Cursor working copies, not Hess-facing unless you attach them:

| File | Role |
|---|---|
| [DR_HESS_EMAIL_NOTE_SOURCE_SEP10_2026.md](DR_HESS_EMAIL_NOTE_SOURCE_SEP10_2026.md) | Unmodified packet email note (uses a non-canonical last name — do not send as-is) |
| [WEKA_DEMONSTRATION_RUNBOOK_SEP10_2026.md](WEKA_DEMONSTRATION_RUNBOOK_SEP10_2026.md) | Dated copy of the official runbook |
| [WEKA_DEMONSTRATION_RUNBOOK_SEP10_2026.pdf](WEKA_DEMONSTRATION_RUNBOOK_SEP10_2026.pdf) | Same runbook, PDF |
| [WEKA_BASELINE_COMPARISON_SEP10_2026.json](WEKA_BASELINE_COMPARISON_SEP10_2026.json) | ZeroR / J48 scope and numbers |
| [WEKA_TRIAL_QUALIFICATION_SEP10_2026.json](WEKA_TRIAL_QUALIFICATION_SEP10_2026.json) | 14/14 arithmetic PASS; trial criteria NOT MET |
| [WEKA_REPLAY_VERIFICATION_SEP10_2026.json](WEKA_REPLAY_VERIFICATION_SEP10_2026.json) | 78 artifacts; run `new_replay_20260910` |
| [ITDX_NLM_E2E_STATE_SEP10_2026.md](ITDX_NLM_E2E_STATE_SEP10_2026.md) | Internal E2E; forecast not promoted |

Cursor-authored Hess email / slides / test-requirements drafts (`DR_HESS_ITDX_WEKA_NLM_*_SEP10_2026.md`, `ITDX_WEKA_TEST_REQUIREMENTS_SEP10_2026.md`) were **not** the send path after this handoff. **Perplexity drafts those from your attachments.**

---

## Internal only — NOT FOR PERPLEXITY PASTE

Local evidence packet (114 files). Leave large binaries here; do not copy `input_dataset.json` / `result.json` onto MAS 188 root.

`C:\Users\Owner1\Downloads\ITDX26_WEKA_DEMONSTRATION_AND_EVIDENCE_2026-09-10\ITDX26_WEKA_DEMONSTRATION`

Parent folder (contains the extracted packet; ZIP of the same name may also exist under Downloads):

`C:\Users\Owner1\Downloads\ITDX26_WEKA_DEMONSTRATION_AND_EVIDENCE_2026-09-10`

v1.4 lab (TEST_WEKA.py; JARs stay in the kit, not this packet):

`C:\Users\Owner1\Downloads\Mycosoft_ITDX26_v1.4.0_Standalone_Lab\Mycosoft_ITDX26_v1.4.0`

Replay verify (Python 3.10+, no Java/Torch): `python verify_run.py evidence/replay` → 14/14 arithmetic PASS, 78 artifacts, trial criteria NOT MET.

Do not push, merge, or blue-green from this handoff. Another agent owns ship. Do not reset website main.
