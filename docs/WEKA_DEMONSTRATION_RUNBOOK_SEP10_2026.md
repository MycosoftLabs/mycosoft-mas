---
title: "Demonstrating NLM in Weka"
subtitle: "An operator runbook for ITDX26 and FUSARIUM"
author: "Mycosoft"
date: "10 September 2026"
---

# 1. What Weka does for us

**Weka measures how well predictions match withheld outcomes and provides comparison algorithms. It does not supply the NLM algorithm.** NLM/FormSpace computes the states and probabilities. Our adapter hands those probabilities to Weka's Java evaluation engine. FUSARIUM shows the evidence and the result.

This is why Dr. Hess's suggestion is useful. An evaluator can inspect a standard data format, rerun familiar scoring code, compare simple alternatives, and review mistakes. Weka is not required to run NLM in the field, but it is a useful evaluation instrument. Mathematical equations explain the mechanism; a frozen run with independently labeled outcomes tests whether that mechanism is useful.

The current adapter calls `Evaluation.evaluateModelOnceAndRecordPrediction(double[], Instance)`. This is an official Weka API for evaluating a supplied probability distribution. It does not fit J48, RandomForest or another replacement classifier. [Weka Evaluation](https://weka.sourceforge.io/doc.dev/weka/classifiers/Evaluation.html).

## What I actually ran for this packet

On 10 September 2026, the recovered v1.4 kit ran a **new Java evaluation of recorded NLM probabilities**. It passed 14/14 task-condition arithmetic checks and verified 78 artifacts. Its run ID is `new_replay_20260910`. The request, input data, model artifact, ARFFs, task reports and verification output are included.

This execution did **not** rerun NLM inference, train NLM, contact MAS 188, or operate physical sensors. The current documentation environment has Java 17 but no Torch; the already-working laptop Python can run fresh NLM inference using the commands below.

I also trained and evaluated **ZeroR and default J48** on the archived synthetic Task 12 data: 1,280 training rows from four captures, and 1,600 test rows from five different captures. Both received seven raw scalar channels plus seven presence flags. IDs, timestamps, labels-as-features, NLM probabilities and learned coordinates were excluded from their predictors. Labels were removed from each test instance passed to prediction.

| Method | Task 12 positive-class F1 | Brier | Meaning |
|---|---:|---:|---|
| ZeroR | 0 by confusion-count convention; Weka undefined | 0.226553 | No event predictions; misses all 555 positives |
| J48 | 1.000000 | 0 | A very simple rule solves this clean test |
| Recorded NLM, freshly scored in Java | 1.000000 | About $1.81\times10^{-19}$ | The NLM reference also solves this clean test |

**The important new finding:** J48 learned a single split on gas resistance. Clean F1 = 1 cannot establish a temporal or FormSpace advantage on this population. This is an exploratory comparator on previously inspected synthetic data, not a preregistered architecture ablation or field benchmark.

\newpage

# 2. What the comparator teaches us

The tree learned from the training partition is:

~~~text
gas_resistance_ohms <= 160820.8517: candidate
gas_resistance_ohms >  160820.8517: background
~~~

That threshold is specific to this synthetic generator. It is not an environmental safety threshold or a proposed production rule.

![Actual clean synthetic Task 12 results and the single-feature separation that explains the J48 result.](figures/clean_comparison.png){width=96%}

## What a convincing next test must answer

- Does temporal memory help when instantaneous measurements are ambiguous but histories differ?
- Does combining modalities improve accuracy, calibration or warning time when one modality alone is insufficient?
- Does FormSpace add measurable benefit beyond the same NLM without its chart constraints, prototypes or support checks?
- Does the system remain useful on unseen devices, locations and recording periods?
- Does the decision loop help an operator collect evidence or respond earlier, within an acceptable false-alert and workload budget?

Use representative physical data or justified simulated dynamics. Do not design a generator around NLM's answers simply to make a baseline lose. Specify the test and training rules before exposing the new test labels. Compare against a majority/base-rate model, a simple threshold, a persistence or moving-average detector, and a modest learned model with equivalent information access.

The existing synthetic fixture remains useful for installation, regression, missingness and stress demonstrations. It is an executable reference experiment. Its role is different from proving that the advanced architecture is necessary.

\newpage

# 3. The Weka modules you actually need

| Weka component | Use it for | How it applies here |
|---|---|---|
| Explorer: Preprocess | Inspect attributes, row count, class labels and missing values | Open this run's ARFF files and check their schema |
| Evaluation API + our adapter | Score NLM's existing probability distributions | This is the authoritative native-model scoring path |
| Explorer: Classify / rules / ZeroR | Establish a no-sensor-skill baseline | Included train/test feature files are ready to use |
| Explorer: Classify / trees / J48 | Test whether a small decision tree is sufficient | Included comparison already runs and saves the tree |
| Explorer: Classify / functions / Logistic | A further simple probabilistic comparator | Optional next baseline; not run in this packet |
| Explorer: Classify / trees / RandomForest | A stronger tabular comparator | Optional; fix hyperparameters using training/validation only |
| Explorer: Visualize | Inspect relationships and suspiciously easy separation | View gas resistance colored by actual class |
| Classify result visualizations | Confusion errors, ROC/threshold plots where supported | Available for classifiers run in Explorer; command-line NLM reports do not automatically appear in its history |
| Experimenter | Repeated comparative experiments | Later; it does not automatically enforce custom capture/site/temporal splits for our Python model |

Explorer's Classify panel supports a supplied separate test set; Weka's baseline classes are documented in its official API. [Classifier panel](https://weka.sourceforge.io/doc.stable/weka/gui/explorer/ClassifierPanel.html), [ZeroR](https://weka.sourceforge.io/doc.stable/weka/classifiers/rules/ZeroR.html), [J48](https://weka.sourceforge.io/doc.stable/weka/classifiers/trees/J48.html), [Logistic](https://weka.sourceforge.io/doc.stable/weka/classifiers/functions/Logistic.html).

**No extra Weka package is needed for the current adapter, ZeroR or J48.** The v1.4 kit already includes Weka, Bounce and ECJ JARs. Java 17+ is required. ECJ compiles the adapter without requiring a system `javac`. Fresh NLM inference additionally needs the kit's Python/Torch environment. Keep the working runtimes; do not update packages during the demonstration.

The pinned Maven Weka artifact is 3.8.7, while its runtime reports `3.8.8-SNAPSHOT`. The adapter records both identities and the JAR hash. Report that discrepancy explicitly instead of inventing one version label.

## Two kinds of ARFF must stay separate

**Prediction ARFF:** `p_background, p_candidate, actual`. These are outputs to score. Do not train a Weka classifier on them and call that NLM validation.

**Feature ARFF:** actual predictor columns plus a class attribute. These are inputs for ZeroR, J48 and other baselines. The included `baselines/task12_raw_train.arff` and `task12_raw_test.arff` are this kind. The row-ID sidecars retain capture identity without exposing it as a predictor. [ARFF format](https://waikato.github.io/weka-wiki/formats_and_processing/arff_stable/).

\newpage

# 4. Exact commands for the existing laptop kit

Use the folder containing the actual launcher. The two historical kits have different commands; do not mix their options.

## Standalone Algorithm Lab v1.4

From the directory containing `TEST_WEKA.py`:

~~~powershell
python start_lab.py --diagnose
python TEST_WEKA.py --mode replay
python TEST_WEKA.py --mode infer
~~~

- **replay:** new Java scoring, recorded NLM probabilities.
- **infer:** load frozen NLM weights, recompute predictions, then run Java scoring.
- **train:** a new training experiment; it changes the model and is not a routine frozen-model demonstration.

If the current interpreter lacks Torch, reuse the Python that completed the earlier inference test:

~~~powershell
python TEST_WEKA.py --mode infer --python "C:\path\to\working-venv\Scripts\python.exe" --java-home "C:\path\to\working-jre"
~~~

Replace the two paths with the actual local paths. `--java-home` is the folder containing `bin/java.exe`. Omit either option if the active runtime is already correct.

For a genuinely new, schema-valid capture:

~~~powershell
python TEST_WEKA.py --mode infer --dataset "C:\path\to\heldout_capture.json" --no-stress
~~~

The dataset input must follow the lab's JSON contract. The schema example is:

~~~text
examples/formspace_dataset.json
~~~

Put labels in the separate `truth` mapping. Raw CSV or ARFF requires conversion first. Do not change an imported real record to `SYNTHETIC_TEST` to force a stress run. The built-in six-condition stress suite belongs to the bundled synthetic fixture.

CLI runs are saved under `local_data/cli_runs/<run-id>`. Inspect:

~~~text
receipt.json
request.json
weka_checks.json
qualification.json
quality.json
weka/task12_weka.txt
weka/task13_weka.txt
weka/weka_evaluation.json
~~~

Verify a selected run with:

~~~powershell
python verify_run.py "C:\path\to\selected-run"
~~~

## Older ITDX_Weka_Demo_Kit

From the folder containing `RUN_WEKA.py`:

~~~powershell
python RUN_WEKA.py --mode infer --check
python RUN_WEKA.py --mode infer
~~~

This older wrapper supports `--check`; `TEST_WEKA.py` does not. Its receipts use a different schema and live under `weka-demo/runs`. Retain the complete run folder and corresponding kit version.

\newpage

# 5. Exactly what to click in Weka and the app

## Inspect NLM predictions in Weka

1. Run `OPEN_WEKA.bat` in the v1.4 kit, or `sh OPEN_WEKA.sh` on Linux/macOS. A graphical desktop is required.
2. Select **Explorer**, then **Preprocess**, then **Open file**.
3. Open the fresh run's `weka/task12_frozen_predictions.arff`.
4. Confirm the three attributes, the row count and class order `{background,candidate}`. Set the class selection to `actual` if it is not already selected.
5. Inspect missing probability pairs. `?,?` means abstention, not a zero-probability event. `actual=?` means no known outcome, so accuracy cannot be scored for that row.
6. Show the Java-produced Task 12 text report and the matching input digest in `weka_evaluation.json`. Repeat for Task 13.

Our current model is not an installed Java `Classifier` plugin; loading a `.pt` file in Explorer cannot run it. The adapter is the correct existing route. If Dr. Hess requires an Explorer-selectable algorithm, Cursor must add and validate a proper wrapper that respects fit/predict boundaries, label isolation and sequence resets. That is an integration requirement to confirm, not something this kit already provides.

## Run the supplied comparison in Explorer

1. In **Preprocess**, load `baselines/task12_raw_train.arff` from this packet.
2. Set **Class** to the final `actual` attribute.
3. Open **Classify**. Choose **rules -> ZeroR**.
4. Under **Test options**, choose **Supplied test set**, then **Set**, and open `baselines/task12_raw_test.arff`.
5. Click **Start**. Read the `candidate` class row, not only overall accuracy. ZeroR classifies every row as background here.
6. Choose **trees -> J48**, keep defaults, and run against the same supplied test set.
7. Inspect the printed tree. In desktop builds supporting it, right-click the completed result and choose **Visualize tree**. The included report already contains the exact one-split tree.

Do not choose training-set evaluation or ordinary random ten-fold cross-validation for this demonstration. Adjacent rows from one capture are correlated. This packet supplies the original distinct capture-role split; new field tests also need site/device/time separation. The desktop clicks are documented workflow instructions; this session ran the actual Java components headlessly, not a visual desktop rehearsal.

## In standalone v1.4

Run `python start_lab.py`, use the printed URL, select **Fresh NLM inference**, leave **Evaluate with Weka** enabled and click **Run test**. Show Execution, Weka & confidence, Task 12, Task 13, Task 8, map products and Evidence exports for the same selected run. CLI receipts are not automatically added to the standalone web run history.

## In FUSARIUM

The inspected Weka component fetches `/api/fusarium/itdx/weka-receipt`. Its source reads completed local receipts from configured paths and falls back to a bundled historical PASS summary. Opening it does not launch Java. The source also selects a successful receipt instead of exposing a failed newest attempt. Check the actual current branch before applying a fix.

For a fresh demonstration, show run ID, timestamp, input/model hash, `prediction_execution=FRESH_INFERENCE`, `weka_execution=FRESH_JAVA_EVALUATION` and whether the receipt is historical/bundled. A refreshed screen is not evidence of a fresh run. [Receipt loader](https://github.com/MycosoftLabs/website/blob/045eaa29637135c932829df36e862c832f3eb7d0/lib/itdx/weka-v14-receipt.ts), [walkthrough component](https://github.com/MycosoftLabs/website/blob/045eaa29637135c932829df36e862c832f3eb7d0/components/itdx/ITDXWekaWalkthrough.tsx).

\newpage

# 6. A useful 12-minute demonstration for Dr. Hess

**Before the timer starts:** rehearse on the same laptop, keep a verified replay as fallback, freeze the model and test definition, and arrange the app, terminal and Weka Explorer side by side. State which system is local and which is connected to MAS.

| Time | Show | Explain |
|---|---|---|
| 0-1 min | A named event, sensor inputs, known outcome source and model ID | What operational question is being answered |
| 1-3 min | Start fresh frozen-model inference and Java evaluation | Mycosoft computes the predictions; Weka scores them |
| 3-4 min | A Task 12 observation and Task 13 pair with evidence IDs | Connect a number to the actual input and defined target |
| 4-5 min | Confusion counts and probability error | Show misses and false alarms as well as correct predictions |
| 5-7 min | Clean, bias, missingness and unknown-ontology cases | Show where the model works, degrades and abstains |
| 7-8 min | The ZeroR/J48 comparisons | Explain why clean synthetic perfection is not enough |
| 8-10 min | MYCA candidate, AVANI disposition and matching map record | Show how evidence affects a useful advisory response |
| 10-11 min | Execution receipt/outcome, if a real device run exists | Distinguish proposed, acknowledged, completed and independently observed |
| 11-12 min | Export the run and independently verify it | Hand the evaluator the exact records, not just screenshots |

For today's reference, Task 8 is a governed environmental advisory fixture and Task 14 displays observed/synthetic geography. Show them accurately. Do not describe a map animation as a physical command or call an advisory gate a successful intervention.

## The current stress evidence

| Condition | Task 12 | Task 13 | Interpretation |
|---|---|---|---|
| Clean synthetic | F1 1.000 | F1 1.000 | Solves the defined clean fixture |
| Temperature +20 C | F1 0.558; Brier 0.537 | F1 0.566; Brier 0.501 | Bias substantially damages predictions |
| All measurements missing | 1,600 abstentions | 2,400 abstentions | No supported scores |
| No geography | Pattern remains scored | 2,400 abstentions | Pair relation lacks required geographic support |
| Unknown ontology | 1,600 abstentions | 2,400 abstentions | Unsupported inputs are not forced into classes |
| Information erased | Positive-class F1 0 by count convention | Same | Predictions can be wrong without abstaining |

The seven evaluated case directories include `main` and an identical `baseline`. Fourteen checks mean two tasks across seven case entries; they are not fourteen independent experiments. Undefined Weka F1 can mean zero positive predictions or all abstention. Show counts to disambiguate.

The saved local criteria still fail: five test captures are below the kit's illustrative minimum of twenty, and Task 13 whole-capture coverage is 4/5 against the selected 0.9 criterion. Those are **local trial criteria, not Army requirements**. Merely changing the minimum or duplicating captures would not improve the evidence.

\newpage

# 7. What readiness and field function require next

## Five separate claims

| Claim | Evidence that tests it |
|---|---|
| The algorithm executed | Runtime log, input/model identities and outputs |
| The scoring arithmetic is correct | Java/Python agreement on the same distributions and labels |
| The model generalizes | Previously withheld representative captures, independent labels and simple comparators |
| The output is useful | Warning time, false-alert burden, evidence-collection benefit and operator evaluation |
| The platform works in the field | Live ingestion, latency, offline recovery, authoritative governance, device receipts and recorded outcomes |

Weka directly supports the second and part of the third. It does not establish all five by itself. You can demonstrate useful field function before claiming broad accuracy, but the claim must match the observed operation.

## Run one complete real environmental experiment

Choose a supported phenomenon and a controlled, appropriate test setup. Define the event using an independent reference measurement or blinded adjudication. Record actual sensor values, calibration, device identity, timestamps and any intervention. Include uneventful periods and competing disturbances, not just the event of interest.

Freeze the model and thresholds. Make predictions from inputs available at each decision time, record them before outcomes are revealed, and retain all failures. Show a bounded response such as requesting an additional waveform or temporarily increasing an approved sampling rate. Capture AVANI's disposition, the local controller response, actual execution times and the subsequent evidence.

A model that successfully accepts a real recording is not automatically calibrated for it. If it needs adaptation, train on a separate development set and use new untouched captures for testing. Do not tune repeatedly on the evaluator's test outcomes. There is no universal capture count that establishes field readiness; plan enough independent events/background exposure to estimate the required error rates and their uncertainty.

## Early warning must be measured before onset

The archived Task 12 output is primarily current-pattern classification. Its auxiliary forecast predicts the same source's next normalized measurements. That is not yet a validated event-onset probability at a chosen future horizon.

For an early-warning claim, define the target as an event during a future interval. At forecast time $t$, use only evidence with `available_at <= t`, save the score, and reveal the eventual label separately. Link-graph buckets must close at an explicit cutoff; a complete ten-second bucket must not be treated as available before its last required report arrives. The existing batch pipeline needs this timing test before calling its entire output live early warning.

Report:

$$
\mathrm{lead\ time}=t_{\mathrm{onset}}-t_{\mathrm{first\ valid\ warning}},
\qquad
\mathrm{false\ alerts/hour}=\frac{N_{\mathrm{false\ alert\ episodes}}}{\mathrm{background\ exposure\ hours}}.
$$

Predefine warning horizons, event-to-alert matching, cooldown and alert-episode grouping. Report missed events and late warnings separately; a positive lead time conditional on a few detected events can hide many misses. Include confidence intervals at event/capture level. Weka's row-level F1 cannot substitute for this event-based evaluation.

\newpage

# 8. How to interpret confidence and all four tasks

**Precision:** of the declared candidates, how many were correct? **Recall:** of the real events, how many were detected? **F1:** a balance of those two at a declared threshold. **Brier:** probability error that penalizes confident mistakes.

$$
F_1=\frac{2TP}{2TP+FP+FN},\qquad
\mathrm{Brier}=\frac1n\sum_i(p_i-y_i)^2.
$$

Our Java adapter computes one-probability binary Brier itself and also reports Weka RMSE. The Python checker independently recomputes Brier and checks it against Weka RMSE squared for these normalized binary, unit-weight, scored rows. Weka supplies the confusion/F1/ROC/RMSE machinery. Do not describe the adapter's separate Brier accumulator as a native Weka Brier module.

The adapter uses argmax; tied probabilities select background. The app's classification threshold is recorded separately and may differ. Report app-threshold decision metrics alongside Weka argmax metrics if the operator sees a different decision rule.

Calibration means, for example, that forecasts near 0.8 occur at an appropriate empirical frequency in a stated population. It is not the same as correct classification. Add reliability diagrams, Brier skill against a training-fitted base rate, and grouped uncertainty intervals. Our current adapter records AUROC but does not export AUPRC or reliability bins for NLM; these are explicit Cursor additions. The baseline helper in this packet does export AUPRC for its classifiers.

Never replace null or abstention with 0.5 to obtain a convenient score. Report total, labeled, scored and abstained counts. Define how abstention affects operational missed-event rates; abstention is not automatically a successful field response. A conformal prediction set and a confidence interval for measured performance are different objects.

| Task | Mathematical product | Appropriate evaluation |
|---|---|---|
| 12: Pattern analysis | Defined class or future-event probability | Withheld labels; precision/recall, Brier, calibration, event lead time |
| 13: Link analysis | Probability of the declared same-event relation | Independently labeled pairs, candidate coverage, grouped split, missing-geography behavior |
| 8: Courses of action | Candidate scores, Borda preferences, governance disposition | Feasibility, completeness, correct constraint handling, operator utility; measured outcomes where available |
| 14: Map products | Geometry with temporal support and evidence lineage | Coordinate/CRS accuracy, aging, source traceability, observed-versus-predicted labeling, display latency |

Classification F1 does not validate Task 8 or Task 14. A Borda preference is not P(success). A class score is not a positional error radius. A source signature is not sensor truth. Keep those meanings separate on the screen and in exported files.

If the organizer's 1-5 values are ratings, confirm their meaning. They could be ordinal assessments, input variables or outcome categories. Do not divide them by five and call them probabilities. Confirm the task definitions, input format, evaluation unit and output rubric with Dr. Hess before fixing the formal trial.

\newpage

# 9. What Cursor needs to finish in FUSARIUM

1. **Create a real run job.** An authorized Run action must launch the appropriate worker, record the input/model identities and produce an immutable job ID. Reuse existing worker contracts where available; do not assume a new API route exists.
2. **Display the selected run.** Bind every task panel, map view and download to the same job. Show fresh inference versus replay versus bundled history prominently.
3. **Expose failures.** Show the latest attempted run and its status. Do not fall back to an earlier PASS without explicit historical labeling. Poll/refresh a selected job until terminal status; the inspected component loads once on mount.
4. **Make artifact verification real.** Verify per-file digests and the expected input/model binding before displaying a verification claim. An existing JSON field saying PASS is not itself a fresh verifier execution.
5. **Separate labels from serving.** Keep truth out of the NLM inference request. Commit predictions before the evaluation join; preserve record and capture IDs in sidecars.
6. **Keep NLM ownership clear.** Weka must score the native probabilities. Baseline modules have distinct names and results. The archived small chart must not be labeled as whichever larger production model is running on 188.
7. **Add missing metrics.** Export NLM AUPRC using recorded predictions; add reliability bins, log loss with declared clipping, app-threshold confusion counts, operational abstention rates, and grouped intervals.
8. **Add forward-only replay.** Enforce availability time, causal windows, graph-bucket closure and isolated stream caches. Test batch/prefix/stream behavior; report required buffering latency.
9. **Connect the actual decision loop.** Persist NMF, inference, MYCA proposal, AVANI disposition, command intent, receipt and outcome in MINDEX. The model score must not bypass controller checks.
10. **Export one self-contained evidence bundle.** Include request, model identity, data snapshot or approved references, prediction outputs, truth provenance, evaluator/JAR identities, logs, criteria, results, failures and re-run commands.

These are implementation targets from inspected source. Cursor should compare them against the actual latest branch and demonstrate existing fixes before changing code.

## Email sequence

Send the technical paper and runbook, the verified synthetic replay receipt, and the comparator finding with clear scope. Include the NotebookLM audio as an explanatory companion, with the written sources and results as the authoritative evidence. Do not claim the audio is an independent review or that every narration statement was validated.

Ask Dr. Hess whether he wants (a) frozen-distribution Weka API evaluation, (b) a Weka `Classifier` interface, or (c) an organizer harness. Also request the task-specific labels, holdout protocol, forecast horizons and 1-5 rubric. This is the last necessary clarification before designing the formal evaluator-run experiment.

The next milestone is **a fresh, blinded, representative environmental capture producing a useful warning or evidence-collection response, with Weka scores and a complete MINDEX outcome trail**. That is how the mathematical design becomes a demonstrated function.

\newpage

# 10. Reproduce this packet and inspect the evidence

## New replay

`evidence/replay/` contains the complete newly scored v1.4 run, including its archived model and input snapshot. This packet includes an unchanged copy of the original v1.4 verifier and its arithmetic helper. From the extracted packet folder, with Python 3.10 or later:

~~~powershell
python verify_run.py evidence/replay
~~~

The numerical result is **14/14 arithmetic PASS, 78 artifacts verified, trial criteria NOT MET**. This verification needs no Java or Torch. It checks saved bytes and arithmetic; fresh Java scoring is a separate operation. Timestamps embedded in synthetic observations are scenario dates, not acquisition dates of real sensors. The run receipt records the actual execution time.

## Weka comparators

The `baselines/` folder includes ready-to-open feature ARFFs, sidecar IDs, actual J48/ZeroR reports, predictions and serialized Weka models. Use the matching Weka runtime when loading saved models. Only load model files from trusted sources.

Rebuild and run the comparator using the v1.4 kit's existing JARs:

~~~powershell
python build_and_run_baselines.py --dataset "evidence/replay/input_dataset.json" --deps "C:\path\to\v1.4\formspace\weka\deps"
~~~

This builds default J48 and ZeroR from the existing training captures, evaluates the test captures, and checks the resulting Brier/F1 arithmetic. It does not train NLM. `BASELINE_COMPARISON.json` records the features, partitions, dependency hashes and scope. The Java helper is included for inspection.

## Source evidence

- Recovered `Mycosoft_ITDX26_v1.4.0_Standalone_Lab.zip`: `TEST_WEKA.py`, `verify_run.py`, `README_V14.md`, `formspace/lab_worker.py`, `formspace/weka/evaluate.py`, `checks.py`, `MycosoftPredictionEvaluator.java`, `nlm_formspace/data.py` and `engine.py` were read for the commands and algorithm boundaries.
- Recovered `ITDX_Weka_Demo_Kit.zip`: `RUN_WEKA.py` was read to distinguish the older launcher.
- FUSARIUM website source snapshot: `045eaa29637135c932829df36e862c832f3eb7d0`. Receipt-loader and walkthrough-component links appear in Section 5. These are source findings, not a fresh inspection of production runtime behavior.
- [Official Weka documentation](https://waikato.github.io/weka-wiki/documentation/) and [command-line primer](https://waikato.github.io/weka-wiki/primer/) describe the workbench and standard train/test interfaces.

## What has not been completed here

Fresh NLM inference on this machine, a production deployment, new physical recordings, an independent field-accuracy study, desktop GUI rehearsal and an email send. The actual completed work is the source review, new Java replay, new Weka comparators and the implementation/demo package. Use the existing laptop runtime for the next frozen-inference demonstration.
