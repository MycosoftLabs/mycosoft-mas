# WEKA ITDX Campaign Run — Sep 14, 2026

**Date:** 14 Sep 2026  
**Status:** Compatibility coverage complete on 149/149 required schemes. Scientific readiness is **not** established.  
**forecast_p:** null  
**WEKA ≠ NLM.** Do not treat any F1 here as travel probability or NLM skill.

## What ran

MAS worker `scripts/itdx_weka_campaign/` drove portable Temurin 17 JRE + lab `weka.jar` (plus bounce, MTJ, java-cup-runtime) against the 149-entry campaign inventory (56 classifiers, 85 filters, 8 clusterers).

| Count | What |
|---|---|
| 10 | ARFFs inventoried (campaign ZIP itself has **zero** ARFFs) |
| 9 | ARFF views actually executed (5 synthetic fixtures + Task 12 train + Task 12 coordinates + trail subsample + trail predictions abstention) |
| 1052 | Ledger jobs |
| 821 | `RAN_*` (710 compatibility + 111 scientific-lane / representation) |
| 86 | FAILED (wrong attribute type or options on that view; scheme still has a compatibility receipt elsewhere) |
| 88 | INAPPLICABLE_WITH_EVIDENCE (mostly unlabeled trail classify) |
| 56 | BLOCKED_DATA (trail prediction ARFF: `actual` and `p` are `?`) |
| 1 | TIMEOUT: `ClusterMembership` on `task12_coordinates` (20s). Same filter **did** run on fixtures. |
| 149/149 | Handoff `check_coverage.py` compatibility receipts (`complete: true`) |
| false | `scientific_readiness_established` |

Results live under the gitignored website tree:

`D:\Users\admin2\Desktop\MYCOSOFT\CODE\WEBSITE\website\.data\weka-campaign\SEP14_2026\`

Key files: `results.jsonl`, `results.csv`, `correlation.json`, `coverage.json`, `arff_inventory.json`, `status.json`, `worker_stdout.log`, `receipts/`, `filtered/`.

## ITDX app (local 3010 only — no Instant Deploy)

- Page: http://localhost:3010/fusarium/itdx  
- Status BFF: `GET /api/fusarium/bluesight-trail/weka-campaign`  
- Start/resume: `POST` same path  
- Downloads: `/api/fusarium/bluesight-trail/weka-campaign/file?name=results.jsonl` (also `results.csv`, `correlation.json`, `status.json`)  
- Glass panel: **WEKA campaign** (collapsible) on the Trail AR math console. Existing **Export WEKA ARFF** dock is unchanged.

## ARFFs found vs executed

| ID | Executed? | Honesty |
|---|---|---|
| `trail-ar-session.arff` (~109k rows, growing session) | Subsample 2000 rows: filter + cluster only | SIMULATION · live: false · class missing/unscored · **F1 not yet scored** |
| `trail-ar-predictions.arff` (~109k rows) | Ledger only | `p` and `actual` are `?` — **do not train J48 as NLM** |
| `task12_raw_train.arff` | Classify / filter / cluster | **SYNTHETIC** archived Task 12. F1 near 1.000 is synthetic only |
| `task12_raw_test.arff` | Inventoried, not a worker view | Same synthetic family |
| `task12_coordinates_test.arff` | Representation probe | Synthetic labels on FormSpace coords — not NLM |
| Frozen Task 12/13 prediction ARFFs | Inventoried, not trained | Score-only distributions; never train as NLM |
| 5 typed fixtures in `SEP14_2026/fixtures/` | Compatibility | Labeled **SYNTHETIC_CONTRACT_FIXTURE** |

Campaign folder `ITDX26_WEKA_FULL_CAMPAIGN_2026-09-14` is a planning kit (149 inventory + 4,760×680 planned matrix). Those matrix cells stay **PLANNED**. This run is the full **scheme list** × applicable real/fixture ARFFs, not the Cartesian filter×model grid.

## Schemes that executed (149 FQCNs)

### Classifiers (56)

BayesNet, NaiveBayes, NaiveBayesMultinomial, NaiveBayesMultinomialText, NaiveBayesMultinomialUpdateable, NaiveBayesUpdateable, GaussianProcesses, LinearRegression, Logistic, MultilayerPerceptron, SGD, SGDText, SMO, SMOreg, SimpleLinearRegression, SimpleLogistic, VotedPerceptron, IBk, KStar, LWL, AdaBoostM1, AdditiveRegression, AttributeSelectedClassifier, Bagging, CVParameterSelection, ClassificationViaRegression, CostSensitiveClassifier, FilteredClassifier, IterativeClassifierOptimizer, LogitBoost, MultiClassClassifier, MultiClassClassifierUpdateable, MultiScheme, RandomCommittee, RandomSubSpace, RandomizableFilteredClassifier, RegressionByDiscretization, Stacking, Vote, WeightedInstancesHandlerWrapper, InputMappedClassifier, SerializedClassifier, DecisionTable, JRip, M5Rules, OneR, PART, ZeroR, DecisionStump, HoeffdingTree, J48, LMT, M5P, REPTree, RandomForest, RandomTree.

### Clusterers (8)

Canopy, Cobweb, EM, FarthestFirst, FilteredClusterer, HierarchicalClusterer, MakeDensityBasedClusterer, SimpleKMeans.

### Filters (85)

AllFilter, MultiFilter, RenameRelation; supervised attribute: AddClassification, AttributeSelection, ClassConditionalProbabilities, ClassOrder, Discretize, MergeNominalValues, NominalToBinary, PartitionMembership; supervised instance: ClassBalancer, Resample, SpreadSubsample, StratifiedRemoveFolds; unsupervised attribute: Add, AddCluster, AddExpression, AddID, AddNoise, AddUserFields, AddValues, CartesianProduct, Center, ChangeDateFormat, ClassAssigner, ClusterMembership, Copy, DateToNumeric, Discretize, FirstOrder, FixedDictionaryStringToWordVector, InterquartileRange, KernelFilter, MakeIndicator, MathExpression, MergeInfrequentNominalValues, MergeManyValues, MergeTwoValues, NominalToBinary, NominalToString, Normalize, NumericCleaner, NumericToBinary, NumericToDate, NumericToNominal, NumericTransform, Obfuscate, OrdinalToNumeric, PKIDiscretize, PartitionedMultiFilter, PrincipalComponents, RandomProjection, RandomSubset, Remove, RemoveByName, RemoveType, RemoveUseless, RenameAttribute, RenameNominalValues, Reorder, ReplaceMissingValues, ReplaceMissingWithUserConstant, ReplaceWithMissingValue, SortLabels, Standardize, StringToNominal, StringToWordVector, SwapValues, TimeSeriesDelta, TimeSeriesTranslate, Transpose; unsupervised instance: NonSparseToSparse, Randomize, RemoveDuplicates, RemoveFolds, RemoveFrequentValues, RemoveMisclassified, RemovePercentage, RemoveRange, RemoveWithValues, Resample, ReservoirSample, SparseToNonSparse, SubsetByExpression.

Exact FQCNs: `correlation.json` → `schemes_executed`.

## Validation / correlation (honest)

- Measured F1/accuracy exists **only** on labeled synthetic fixtures and archived synthetic Task 12. Many rows are F1=1.000 — **synthetic only**. The numeric-nominal fixture is a near-threshold split on `x1`.
- The date fixture is the only labeled view where many classifiers sit near chance (~0.45–0.62). That is expected: timestamps were not designed as a class signal.
- Trail session: **not yet scored**. No independent frame labels.
- Trail clusters: ARI/NMI **not yet scored** (no reference partition).
- Frozen prediction ARFFs were **not** used as training targets.
- `forecast_p` is null on every receipt and on the BFF.

## Improvement loop (no fake lift)

1. Label a real hike independently, then score grouped holdout vs ZeroR. Do not promote Task 12 / fixture F1.
2. Keep prediction ARFF `p`/`actual` as missing until a bound NLM emits real posteriors. Never stub 0.85 / 0.5.
3. Optional later: run the planned 4,760 filter×classifier cells only after labeled data exists. Compatibility is already done.
4. `ClusterMembership` on the 1600×33 coordinates view needs a longer timeout or a subsample if that cell is required scientifically.

## Runtime (not committed)

- Java: `website/.data/weka-runtime/jdk-17.0.20.1+1-jre/bin/java.exe`
- `weka.jar` + `bounce.jar` + `ecj.jar` from Algorithm Lab v1.6 `formspace/weka/deps/`
- `website/.data/weka-runtime/lib/` — mtj, core, arpack, java-cup-runtime

## Honesty locks held

- No Instant Deploy. Local 3010 + existing ITDX BFFs only.
- No marketing hero edits. RJ remains CFO.
- No CUI in this kit or results (unclassified campaign + Trail AR simulation).
- Website dirty branch `fix/launchpad-ingest-bearer-alias` was not reset.
