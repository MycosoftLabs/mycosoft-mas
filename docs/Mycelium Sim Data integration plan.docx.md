# Plan for Integrating the MyceliumSeg Dataset into Mycosoft’s Virtual Petri‑Dish Simulator

## Overview of MyceliumSeg and Its Scientific Value

**Dataset summary.** The MyceliumSeg dataset is a large, high‑quality benchmark for mycelium segmentation. It contains **20 176 4 608×3 456‑pixel JPEG images** across the full growth cycle of four fungal species (Ganoderma lucidum, Pleurotus ostreatus, Trametes spp. and Ganoderma sinense) grown on standard 90 mm Petri dishes under multiple culture conditions. A carefully designed imaging device (FPheno2000) captured images daily; culture variables include MYG or PDA medium and incubation at 26 °C – 28 °C. The dataset includes 457 manually annotated samples with pixel‑level masks produced via a multi‑blind, expert‑reviewed annotation process that uses the **mutual average symmetric surface distance (mASSD)** metric to discard inconsistent annotations. Unannotated images are also provided.

**Morphological diversity.** The authors categorise hyphal patterns into features such as **uniform density distribution, concentric density zonation, centripetal densification, irregular edges, peripheral densification, pigmentation, heterogeneous density, wrinkling, rhizomorph formation, spiral stratification and internal concavity** (Table 4 in the paper). Counts for each feature show that many images simultaneously exhibit several patterns. This diversity is ideal for calibrating a simulator, because it exposes how real mycelia respond to media, temperature and contamination.

**Evaluation metrics.** In addition to standard segmentation metrics (F1‑score and Intersection‑over‑Union), the paper introduces **boundary‑aware metrics**: boundary IoU (B‑IoU), 95‑percentile Hausdorff distance (HD95) and average symmetric surface distance (ASSD). The boundary IoU measures how well predicted and ground‑truth boundaries overlap after dilating both by ±1 pixel and dividing the intersection by the union. HD95 represents the 95th percentile of distances between boundary points, while ASSD is the average distance between boundaries. These metrics emphasise accurate contour shape—a key requirement for simulating realistic colony edges.

**Performance baseline.** Baseline experiments with U‑Net, DeepLabv3 and SegFormer achieve F1‑scores around **0.87–0.88** on the labelled set, but boundary IoU remains low (\~0.28), showing that edges are challenging. Robustness experiments across species and culture conditions reveal that cross‑species generalisation is limited and boundary metrics degrade further. A simulator calibrated using this dataset should therefore model subtle edge dynamics and incorporate environmental effects.

## Objectives for the Petri‑Dish Simulator

Mycosoft’s current simulator (available via the **Petri Dish Simulator** app on sandbox.mycosoft.com) allows the user to choose a species, agar type, temperature, pH and humidity and then runs a synthetic growth algorithm. At present the growth patterns appear generic. Integrating MyceliumSeg should:

1. **Ground the simulation in empirical data.** Use the dataset’s annotated masks and time‑lapse images to derive quantitative growth models (rate of radial expansion, density gradients, boundary roughness and morphological features) for each species under each culture condition.

2. **Improve biological realism.** Map morphological features (e.g., concentric zonation, rhizomorphs) to algorithmic rules in the simulator, so simulated colonies resemble real mycelia.

3. **Enable scientific validation.** Evaluate simulated images against the dataset using the same metrics (F1, IoU, boundary IoU, HD95, ASSD and mASSD). Calibration loops should adjust simulation parameters until boundary and area metrics fall within the natural variability observed in the dataset.

4. **Expose dataset‑driven options in the UI.** Allow the user to choose real species (e.g., Ganoderma lucidum) and culture settings (medium, temperature) from the dataset. Provide visualisations of how those choices affect growth patterns.

## Integration Strategy

### 1\. Data acquisition and preprocessing

1. **Download and organise the dataset.** Obtain the labeled and unlabeled partitions from the dataset repository (as described in the paper’s data records). Organise images by species, medium and temperature to mirror the conditions used in the simulator.

2. **Image alignment and time‑series creation.** Many Petri dishes were imaged daily; align sequences to produce growth curves for each colony. Use the dish’s circular boundary to register images and normalise scale.

3. **Segmentation pipeline.** Although the dataset provides manual masks for 457 images, train a segmentation model (e.g., SegFormer or U‑Net) using these masks to generate segmentation masks for the remaining images. Fine‑tune the model per species if necessary. Use classic metrics (IoU, F1) to monitor segmentation performance and cross‑validate using mASSD to ensure boundary consistency.

4. **Boundary extraction.** For each masked image, extract the colony boundary as a set of ordered boundary points. Compute boundary statistics: radius as a function of angle, curvature, fractal dimension and roughness.

5. **Morphological feature identification.** Implement algorithms to detect features listed in Table 4 (e.g., concentric zonation detected via radially periodic density peaks, rhizomorph detection via elongated high‑intensity ridges). Use the counts and descriptions provided in the dataset to verify detection accuracy.

### 2\. Parameter extraction and growth modelling

The simulator’s engine must be parameterised to match empirical growth. The following quantities should be derived from the dataset for each species and culture condition:

1. **Radial growth rate (mm/day).** Fit a curve (e.g., logistic or Gompertz) to the colony radius over time. Derive parameters such as maximum radius, lag time and growth rate constant for each condition. Provide a mapping from simulation time steps to real days.

2. **Density gradients.** Compute radial profiles of mycelial density (pixel intensity) and fit functions representing uniform, concentric or centripetal patterns. Use these to modulate growth probability across the simulation grid.

3. **Edge roughness and curvature.** Measure boundary irregularity using mASSD and boundary IoU metrics. Parameterise noise in the simulation so that the simulated boundary’s roughness distribution matches the observed distribution.

4. **Environmental effects.** For each species, model how growth rate and morphology depend on temperature (e.g., 26 °C vs. 28 °C), medium (MYG vs. PDA) and humidity. Derive functions from the dataset and literature linking these variables to radial expansion and density.

5. **Contamination modelling.** The simulator includes a “contamination” tool. Use images where foreign microorganisms (if any exist in the dataset) or artificially contaminate certain dataset images to model how contamination halts growth or changes morphology (e.g., visible sectors or irregular patches). In absence of contamination in the dataset, integrate literature‑based models.

### 3\. Simulator code integration

1. **Species configuration module.** Extend the simulator’s codebase (likely a JavaScript or TypeScript front‑end with a physics engine) to support dynamic configuration objects for each species. Each species object should include:

2. Growth‑rate curve parameters.

3. Density gradient model.

4. Edge roughness parameters.

5. Morphological features probabilities (e.g., probability of concentric zones). These can be drawn from the feature distribution counts.

6. Environmental response functions (temperature, medium, pH and humidity).

7. **Grid‑based growth algorithm.** Replace or augment the current generic algorithm with a stochastic cellular automaton informed by the extracted parameters. At each time step, cells at the colony boundary evaluate a growth probability P \= f(r, θ, env) where f depends on radial distance, angle and environmental variables. Introduce random perturbations scaled by the roughness parameter to replicate irregular edges.

8. **Morphological feature rendering.** Implement visual overlays to depict concentric rings or rhizomorphs. For example, modulate agar opacity or color along radial bands to render concentric density zonation, or draw branched filaments protruding from the main colony to emulate rhizomorphs.

9. **User interface enhancements.** Populate the “Mushroom Species” drop‑down with the four species from the dataset. When a species is selected, update the underlying species configuration. Add new controls for “medium” (MYG or PDA) and “temperature” (26 °C or 28 °C) that correspond to dataset conditions. Provide tooltips or information icons linking to scientific descriptions of each species and morphological feature.

10. **Backend or service integration.** If the simulator runs client‑side only, embed the parameter datasets in JSON files. For a more dynamic setup, host the parameter extraction pipeline as a service (e.g., a Python API that performs segmentation and analysis on new user‑uploaded Petri dish images and returns parameters). Use the github connector to fetch parameter files automatically when the dataset or analysis code is updated.

### 4\. Scientific validation and calibration

1. **Synthetic image generation for evaluation.** After implementing the new growth engine, generate simulated images at the same resolution and time points as the dataset. Apply the same segmentation pipeline used in section 1 to the simulated images.

2. **Metric comparison.** For each species and condition, compute IoU, F1, boundary IoU, HD95 and ASSD between simulated masks and real masks. Ensure the simulated metrics fall within ±1 standard deviation of the dataset’s baseline model performances (e.g., F1 ≈ 0.87, boundary IoU ≈ 0.28). Where discrepancies exist, adjust parameters (growth rate, roughness, density) via optimisation loops.

3. **mASSD check.** Use the mASSD formula provided in the paper to ensure that any annotation disagreements are mirrored by simulation variability. For two boundaries A and B, the average symmetric surface distance (ASSD) is

ASSDA,B=1ApAqBdp,q+1BqBpAdq,p,

and the mutual ASSD (mASSD) normalises ASSD by the longest diagonal of the bounding box. Use this measure to quantify the similarity between simulated and real colony edges. 4\. **Human expert review.** Collaborate with mycologists to visually inspect simulated colonies. Use the tool’s environment settings to reproduce conditions not present in the dataset (e.g., 30 °C or different pH) and solicit expert feedback on plausibility. 5\. **Iterative refinement.** Where simulation patterns diverge from observed patterns (e.g., if concentric rings appear too pronounced), adjust morphological probabilities and environmental response curves. Document changes and re‑evaluate.

### 5\. Deployment and user support

1. **Update the sandbox site.** Deploy the new simulator to the sandbox.mycosoft.com environment. Ensure the UI displays species and media options and that the simulation runs efficiently in the browser.

2. **Documentation and onboarding.** Provide in‑app help describing the scientific basis of the simulation, citing the MyceliumSeg paper and summarising the culture conditions used. Include a section explaining the evaluation metrics (IoU, boundary IoU, HD95, ASSD and mASSD) and how they were used to calibrate the simulator.

3. **Future expansion.** The dataset emphasises four species, but the modular parameter extraction pipeline can support additional species once data becomes available. Encourage researchers to contribute segmented images via a community upload interface. Use the pipeline to update the parameter database and extend the simulator accordingly.

## Conclusion

Integrating the MyceliumSeg dataset into Mycosoft’s Petri‑Dish Simulator will transform the tool from a generic visualisation into a scientifically grounded growth model. By deriving species‑ and condition‑specific growth parameters from real images, modelling morphological features and calibrating edge dynamics, the simulator can both educate users and support research into mycelial growth. Rigorous validation using boundary‑aware metrics (boundary IoU, HD95, ASSD and mASSD) ensures that the simulated colonies faithfully reproduce the complex and varied behaviours seen in real Petri dishes.

---

