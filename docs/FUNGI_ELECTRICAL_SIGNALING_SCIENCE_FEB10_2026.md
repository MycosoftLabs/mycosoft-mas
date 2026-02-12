# Fungal Electrical Signaling - Scientific Foundation (Feb 10, 2026)

## Document Purpose

This document provides the scientific foundation for Mycosoft's Fungal Computer Interface (FCI) and Fungi Compute application, compiled from peer-reviewed research in fungal electrophysiology. All methodologies, signal characteristics, and analysis techniques implemented in our system are based on published scientific studies.

## Executive Summary

Fungi generate electrical signals in their mycelial networks, ranging from nanovolts to millivolts, operating at frequencies of 0.0001-8 Hz. These signals may serve as a rapid communication mechanism across the modular mycelial network, coordinating responses to nutrients, stress, and environmental stimuli. Recent research has validated measurement techniques, characterized species-specific patterns, and demonstrated signal propagation across mycelia.

**Mycosoft's FCI technology enables real-time monitoring and analysis of these biological electrical signals for research and practical applications.**

---

## Key Scientific Papers

### 1. Electrical Signaling in Fungi: Past and Present Challenges
**Authors:** Buffi, M., Kelliher, J.M., Robinson, A.J., et al.  
**Journal:** FEMS Microbiology Reviews (2025)  
**DOI:** 10.1093/femsre/fuaf009  
**Institution:** University of Neuchâtel, Los Alamos National Laboratory

**Key Findings:**
- Comprehensive review of fungal electrical signaling from 1962-2025
- Voltage range: nV to µV (much lower than neurons at mV)
- Hyphal tips produce electrical currents during growth
- Cell wall hydrophobins act as myelin-like insulators
- Septal pores don't block electrical signals (unlike chemical signals)
- Critical methodological challenges identified

### 2. Language of Fungi Derived from Their Electrical Spiking Activity
**Author:** Adamatzky, A.  
**Journal:** Royal Society Open Science (2022)  
**DOI:** 10.1098/rsos.211926  
**Institution:** University of West England, Bristol

**Key Findings:**
- Analyzed 4 fungal species: C. militaris, F. velutipes, S. commune, O. nidiformis
- Spikes cluster into "words" - average 4.4-4.7 spikes per word
- Word length distribution matches human language patterns
- Species-specific electrical "fingerprints"
- S. commune shows most complex "sentences"
- Synchronization observed between neighboring fruit bodies

**Species Characteristics:**
| Species | Avg Interval | Avg Amplitude | Spike Frequency |
|---------|--------------|---------------|-----------------|
| Cordyceps militaris | 116 min | 0.2 mV | 0.0086 Hz |
| Flammulina velutipes | 102 min | 0.3 mV | 0.0098 Hz |
| Schizophyllum commune | 41 min | 0.03 mV | 0.024 Hz |
| Omphalotus nidiformis | 92 min | 0.007 mV | 0.011 Hz |

### 3. Detection of Electrical Signals in Fungal Mycelia
**Authors:** Buffi, M., Giangaspero, S., Foiada, V., et al.  
**Journal:** iScience (2025)  
**DOI:** 10.1016/j.isci.2025.113484  
**Institution:** University of Neuchâtel, Los Alamos National Laboratory

**Key Findings:**
- Developed printed circuit board (PCB) with embedded gold electrodes
- Faraday cage ESSENTIAL for µV measurements
- **Short-Time Fourier Transform (STFT) THE key analysis method**
- Clear frequency shift from <1 Hz to 1.5+ Hz when mycelium colonizes electrode
- 1604% Power Spectral Density increase proves biological origin
- Validated with biocides: cycloheximide kills signal, voriconazole minimal effect

**Critical Method - STFT Analysis:**
```
1. Record voltage at 1 sample per 10-60 seconds
2. Apply STFT with Blackman-Harris window, 80% overlap
3. Generate spectrogram (time vs frequency vs power)
4. Biological signature: emergence of 1.5-8 Hz frequencies
5. Control stays at <1 Hz (abiotic noise)
```

### 4. Electrical Integrity and Week-Long Oscillation
**Authors:** Fukasawa, Y., Akai, D., Takehi, T., Osada, Y.  
**Journal:** Scientific Reports (2024)  
**DOI:** 10.1038/s41598-024-66223-6  
**Institution:** Tohoku University, Japan

**Key Findings:**
- 100+ day monitoring of Pholiota brunnescens
- **7-day oscillation period - LONGEST EVER RECORDED in fungi**
- Transfer Entropy analysis shows causality
- Bait location acts as "pacemaker" - generates signals to rest of mycelium
- Stable causal relationships for first 60 days, then disappear when oscillation starts
- Demonstrates whole-body integration via electrical signaling

**Oscillation Periods in Fungi:**
- Fast: milliseconds to 40 seconds (action potentials)
- Medium: 2.6 - 30 minutes (typical oscillations)
- Circadian: 20-24 hours (daily rhythms)
- Ultra-long: **7 days** (P. brunnescens - unique!)

### 5. On Spiking Behaviour of Oyster Fungi
**Author:** Adamatzky, A.  
**Journal:** Scientific Reports (2018)  
**DOI:** 10.1038/s41598-018-26007-1  
**Institution:** University of West England, Bristol

**Key Findings:**
- First detailed characterization of Pleurotus djamor
- Two spiking modes: high-frequency (2.6 min) and low-frequency (14 min)
- Responds to: fire, salt, water, alcohol, weight
- Signal transfer between neighboring fruit bodies
- Foundation for "fungal computing" concept

### 6. Action Potential-Like Activity in Fungal Mycelia
**Authors:** Olsson, S. & Hansson, B.S.  
**Journal:** Naturwissenschaften (1995)  
**DOI:** 10.1007/BF01167867  
**Institution:** Swedish University of Agricultural Sciences

**Key Findings:**
- First observation of action potential-like signals in fungal cords
- Armillaria bulbosa and Pleurotus ostreatus in cords/rhizomorphs
- Frequency: 0.5-5 Hz, Amplitude: 5-50 mV (HIGH in specialized structures)
- Triggered by wood contact
- Signals similar to animal sensory systems

---

## Voltage and Frequency Ranges

### Voltage Amplitudes by Species

**Ultra-Low Amplitude (<0.01 mV):**
- Omphalotus nidiformis: 0.007 mV average
- General vegetative mycelium: 0.001-0.05 mV

**Low Amplitude (0.01-0.1 mV):**
- Schizophyllum commune: 0.03 mV average
- Fusarium oxysporum: ~0.1 mV (estimated)

**Medium Amplitude (0.1-1 mV):**
- Cordyceps militaris: 0.2 mV average
- Flammulina velutipes: 0.3 mV average (bursts to 2.1 mV)

**High Amplitude (1-100 mV):**
- Pleurotus djamor: 0.5 mV typical, up to 2 mV in bursts
- Armillaria bulbosa (cords): 5-50 mV
- Pleurotus ostreatus (cords): 5-50 mV
- Neurospora crassa: 15 mV average

**Comparison to Other Organisms:**
- Fungal signals: 0.001-50 mV (mostly <1 mV)
- Plant signals (Venus flytrap): 100-200 mV
- Animal neurons: 70-100 mV resting, spikes to +40 mV

### Frequency Ranges

**Ultra-Low (0.0001-0.01 Hz):**
- Week-long oscillations (Pholiota brunnescens)
- Period: 7 days per cycle

**Low (0.01-1 Hz):**
- Baseline metabolic activity
- Background noise level
- Circadian rhythms (0.00001 Hz = 24 hours)

**Medium (1-5 Hz):**
- Action potential-like spikes
- Typical spike activity
- Biological signature band

**High (5-10 Hz):**
- Burst activity
- Rapid signaling events
- Schizophyllum commune wave packets

**Comparison:**
- Fungi: 0.0001-8 Hz
- Plants: 0.01-4 Hz (Venus flytrap)
- Human heart: 1 Hz
- Animal neurons: 1-300 Hz

---

## Measurement Methodologies

### Hardware Requirements

**Essential Equipment:**
1. **Differential Electrode Pairs**
   - Gold-plated (inert, non-toxic)
   - 2mm diameter optimal (Buffi et al. 2025)
   - Spacing: 1-2 cm between pairs
   - Subdermal needle electrodes for fruit bodies
   - Reference electrode required

2. **Faraday Cage** (CRITICAL!)
   - Eliminates 50/60 Hz powerline noise
   - Blocks environmental electromagnetic interference
   - Essential for µV sensitivity
   - Studies without Faraday cage criticized as unreliable

3. **High-Resolution Data Logger**
   - 24-bit ADC minimum
   - µV resolution required
   - Examples: Pico ADC-24, GRAPHTEC GL840-M
   - Shielded twisted cables essential

4. **Environmental Control**
   - Temperature: 20-25°C stable
   - Humidity: 60-80% for agar plates
   - Darkness (unless testing light response)
   - Vibration isolation

### Experimental Design

**1. Single-Point Measurement:**
- One electrode pair
- Monitor single location over time
- Detect oscillations, circadian rhythms
- Response to stimuli

**2. Multi-Electrode Array:**
- 6-8 electrode pairs across mycelium
- Map signal propagation
- Identify pacemaker locations
- Transfer entropy analysis

**3. Differential Pair Configuration:**
- One electrode at measurement point
- Reference electrode in agar/substrate
- Measures local voltage change
- Reduces common-mode noise

### Sampling Strategies

**Fast Sampling (Spike Detection):**
- Rate: 1-10 samples/second
- Duration: Hours to days
- Purpose: Detect action potential-like spikes
- Species: Fast-spiking (S. commune, F. velutipes)

**Standard Sampling (Oscillations):**
- Rate: 1 sample per 10-60 seconds
- Duration: Days to weeks
- Purpose: Track medium-term oscillations
- Most common in literature

**Long-Term Sampling (Rhythms):**
- Rate: 1 sample per 1-10 minutes
- Duration: Weeks to months
- Purpose: Circadian and ultra-long rhythms
- Species: P. brunnescens (7-day cycle)

---

## Signal Processing Algorithms

### 1. Short-Time Fourier Transform (STFT)

**Purpose:** Transform time-domain voltage signal into time-frequency representation

**Algorithm (Buffi et al. 2025):**
```
1. Window selection: Blackman-Harris (reduces spectral leakage)
2. Window size: 1024 samples
3. Overlap: 80% (improves temporal resolution)
4. Output: Spectrogram (time × frequency × power)
```

**Biological Signature:**
- Background: <1 Hz (abiotic noise, electrode artifacts)
- Fungal activity: 1.5-8 Hz (emerges when mycelium colonizes)
- Colonization time: Typically 3-4 days for F. oxysporum

**Critical Use:** THE method to prove signal is biological not artifact

### 2. Power Spectral Density (PSD)

**Purpose:** Quantify signal strength at different frequencies

**Algorithm:**
```python
# Welch's method (preferred)
frequencies, psd = welch(voltage_data, fs=sampling_rate, nperseg=256)

# Integrate to get average power
avg_power = trapz(psd, frequencies)

# Compare conditions
percent_change = ((power_fungus - power_control) / power_control) * 100
```

**Statistical Test:** Welch's t-test (doesn't assume equal variance)

**Interpretation:**
- >1000% increase: Strong biological signal (Buffi et al. observed 1604%)
- 500-1000%: Probable biological activity
- 100-500%: Moderate activity
- <100%: Weak or questionable

### 3. Spike Detection (Adamatzky Algorithm)

**Semi-Automatic Detection:**
```python
# For each sample x_i:
a_i = mean(neighborhood samples around x_i)  # window = species-specific

# Spike if exceeds threshold:
if |x_i| - |a_i| > δ:
    if distance_from_previous_spike > min_distance:
        record_spike(x_i)
```

**Species-Specific Parameters:**
| Species | Window (w) | Threshold (δ) | Min Distance |
|---------|-----------|---------------|--------------|
| C. militaris | 200 | 0.1 mV | 300 samples |
| F. velutipes | 200 | 0.1 mV | 300 samples |
| S. commune | 100 | 0.005 mV | 100 samples |
| O. nidiformis | 50 | 0.003 mV | 100 samples |

### 4. Linguistic Analysis

**Clustering Spikes into "Words":**
```
theta = average_ISI × multiplier  # 1.0 or 2.0

If ISI between spike_i and spike_i+1 < theta:
    same word
Else:
    new word
```

**Human Language Comparison:**
- Fungal word length: 4.4-4.7 spikes per word
- English word length: 4.8 letters per word
- Greek word length: 4.45 letters per word
- Distribution follows: f(l) = β × 0.73 × l^c

**Complexity Metrics:**
- Shannon Entropy: Information content of word distribution
- Lempel-Ziv: Count of unique patterns
- Kolmogorov: Algorithmic complexity estimate

### 5. Transfer Entropy / Causality Analysis

**Purpose:** Detect directional information flow between electrode positions

**Formula:**
```
TE = (1/T) × Σ log[ p(x_t | y_t-p, x_history) / p(x_t | x_history) ]

Where:
- x_t = target electrode at time t
- y_t-p = source electrode at time t - causal_delay
- T = number of time points
```

**Effective Transfer Entropy (bias-corrected):**
```
ETE = TE - mean(TE_surrogates)
```

**Interpretation:**
- High ETE from electrode A → B: A causes B (information flows A to B)
- "Pacemaker" electrode: High outgoing ETE to many electrodes
- Example: Bait location acts as pacemaker in P. brunnescens

**Typical Causal Delays Tested:**
- 10 minutes (short-term)
- 12 hours (medium-term)
- 1 day (standard)
- 5 days (long-term)

---

## Experimental Challenges and Artifacts

### Major Artifacts to Avoid

**1. Donnan Potentials**
- **Source:** Agar-electrode interface
- **Mechanism:** Charged agar creates false voltage gradients
- **Solution:** Use differential electrodes, avoid agar when possible, PCB with no agar (Buffi method)

**2. Environmental Noise**
- **Sources:** Door opening, footsteps, window shades, HVAC
- **Magnitude:** Can exceed fungal signals (µV range)
- **Solution:** Faraday cage, vibration isolation, controlled environment

**3. Powerline Interference**
- **50 Hz (Europe), 60 Hz (USA)** and harmonics (120, 180, 240 Hz)
- **Solution:** Notch filters, differential recording, Faraday cage

**4. Electrode Polarization**
- **Source:** Electrochemical reactions at electrode surface
- **Solution:** Gold-plated electrodes (inert), short measurement bursts

**5. Temperature Drift**
- **Source:** Thermal expansion, metabolic heat
- **Solution:** Temperature control, baseline correction

### Methodological Best Practices

**DO:**
- Use Faraday cage for all measurements
- Employ differential electrode pairs with reference
- Include non-inoculated controls
- Run experiments for days to weeks
- Validate with biocides or growth inhibitors
- Use STFT to separate biological from abiotic signals
- Report statistical significance (p-values)
- Cite prior work and methodologies

**DON'T:**
- Use single electrodes without reference
- Measure without Faraday cage (criticized in literature)
- Assume voltage changes are biological without validation
- Generalize from single time-point observations
- Ignore electrode spacing (1-2 cm optimal)
- Use stainless steel (prone to Donnan potentials)

---

## Biological Functions (Hypothesized)

### 1. Resource Location and Allocation
- Signals increase when hyphae contact nutrients
- Bait location becomes electrical pacemaker
- Coordinates translocation across network
- "Memory" of resource direction

### 2. Stress Response and Defense
- Mechanical damage triggers electrical changes
- Chemical stressors alter spike patterns
- Nematode attack activates trunk hyphae
- Rapid coordination of defensive responses

### 3. Growth Coordination
- Hyphal tip growth correlates with currents
- Galvanotropism (growth toward electrical field)
- Thigmotropism (touch response) mediated by Ca2+ signals
- Branch formation triggered by local signals

### 4. Inter-Organism Communication (Controversial)
- "Wood Wide Web" hypothesis: plants communicate via fungal network
- Electrical signals in mycorrhizal associations
- Transfer between connected plants (debated)
- More evidence needed

### 5. Mycelial Integration
- Modular network lacks central "brain"
- Electrical signals may coordinate distant parts
- Synchronization after hyphal fusion
- Learning and memory in decentralized system

---

## Ion Channels Involved

### Identified in Fungal Membranes

**Calcium (Ca2+) Channels:**
- Cch1 (voltage-gated Ca2+ channel)
- Mid1 (mechanosensor)
- Role in galvanotropism, thigmotropism
- Stress response signaling

**Potassium (K+) Channels:**
- TOK1 family (fungus-specific)
- Outward rectifying
- Maintains ionic balance
- Present across all fungal phyla

**Chloride (Cl-) Channels:**
- Anion-selective efflux channels
- pH homeostasis
- Tip growth regulation

**Proton (H+) Pumps:**
- Electrogenic H+ pump
- Creates resting membrane potential
- -120 mV typical (vs -70 mV in animals)

**Other:**
- Stretch-activated channels (mechanosensing)
- TRP channels
- Glutamate receptors

### Ion Movement Patterns

- **Hyphal tip:** Inward current (cation influx)
- **Behind tip:** Outward current (cation efflux)
- **Nutrient transport:** Coupled to proton symport
- **Action potentials:** Likely Ca2+, Cl-, H+ (NOT Na+ like neurons)

---

## Fungi Compute Implementation

### How Our App Addresses Each Research Question

**Q1: Is the signal truly biological?**
- **Feature:** STFT spectrogram shows 1.5+ Hz emergence
- **Feature:** PSD statistical comparison (control vs fungus)
- **Feature:** Biocide response simulator
- **Export:** Publication-ready figures with significance tests

**Q2: What are the spike patterns?**
- **Feature:** Spike detection with Adamatzky algorithm
- **Feature:** Species-specific parameter presets
- **Feature:** Spike train analyzer with linguistic metrics
- **Export:** Spike raster plots, word length distributions

**Q3: How do signals propagate?**
- **Feature:** Multi-electrode causality graph
- **Feature:** Transfer entropy visualization
- **Feature:** Pacemaker electrode identification
- **Export:** Causality matrices, directional flow diagrams

**Q4: What are species differences?**
- **Feature:** Species database with 8 profiles from literature
- **Feature:** Pattern matching against known species
- **Feature:** Comparative analysis mode
- **Export:** Species comparison tables

**Q5: How to design experiments?**
- **Feature:** Experiment designer with electrode placement tool
- **Feature:** Stimulus scheduler (nutrients, biocides, stress)
- **Feature:** Expected response prediction
- **Export:** Experimental protocol documentation

### Integration with Mycosoft Ecosystem

**MycoBrain FCI Firmware:**
- Optimized for µV sensitivity (ADS1115 16-bit ADC)
- On-device spike detection
- Multi-probe support (up to 8 probes)
- WebSocket streaming to Mycorrhizae Protocol

**Mycorrhizae Protocol:**
- Species pattern library
- Real-time signal classification
- STFT engine for frequency analysis
- Pattern matching against literature

**MAS Backend:**
- SDR filtering pipeline
- PSD analyzer with statistical tests
- Transfer entropy calculator
- Time-series database (PostgreSQL)

**CREP Integration:**
- Correlate fungal signals with environmental data
- Temperature, humidity, barometric pressure
- Seismic events (fungi as earthquake precursors?)
- Time-lag cross-correlation

**Petri Dish Simulator:**
- Overlay electrical activity on growth simulation
- Show "active hyphae" at tips
- Visualize signal propagation through network

---

## Research Questions for Future Study

### Open Questions in the Field

1. **What is the exact molecular mechanism of spike generation?**
   - Which ion channels are involved?
   - What triggers depolarization?
   - How is repolarization achieved?

2. **Do electrical signals encode information?**
   - Is it a true "language"?
   - What information is transmitted?
   - Syntax and semantics?

3. **How are signals integrated across modular network?**
   - Coordination mechanism?
   - Role in decision-making?
   - Memory storage?

4. **Can signals be artificially manipulated?**
   - Apply external electrical fields?
   - Enhance or disrupt growth?
   - Control wood decay rates?

5. **Plant-fungus electrical communication?**
   - Do plants send signals via mycorrhizal network?
   - Can trees "talk" through fungi?
   - Evidence remains controversial

6. **Practical applications?**
   - Fungal biosensors for environment?
   - Living computers?
   - Bio-electronic materials?

---

## Glossary

**Action Potential:** Rapid voltage spike from ion flux across membrane (~1-100 ms in neurons, slower in fungi)

**Causality:** Directional relationship where changes in A cause changes in B

**Differential Recording:** Measures voltage difference between two electrodes (reduces common-mode noise)

**Donnan Potential:** False voltage from ionic gradients in agar (artifact)

**ETE (Effective Transfer Entropy):** Bias-corrected transfer entropy using surrogates

**Faraday Cage:** Conductive enclosure blocking external electromagnetic fields

**FWHM:** Full Width at Half Maximum (spike duration measure)

**Galvanotropism:** Directional growth in response to electrical field

**ISI (Inter-Spike Interval):** Time between consecutive spikes

**PSD (Power Spectral Density):** Power distribution across frequencies

**Resting Membrane Potential:** Baseline voltage across membrane (~-120 mV in fungi)

**Spike Train:** Sequence of action potentials

**STFT (Short-Time Fourier Transform):** Time-frequency analysis method

**Thigmotropism:** Directional growth in response to touch

**Transfer Entropy:** Information-theoretic measure of causal influence

**µV (Microvolt):** 0.000001 volts (typical fungal signal range)

---

## References (Complete List)

1. Adamatzky, A. (2018). On spiking behaviour of oyster fungi Pleurotus djamor. Sci Rep 8, 7873. DOI: 10.1038/s41598-018-26007-1

2. Adamatzky, A. (2022). Language of fungi derived from their electrical spiking activity. R Soc Open Sci 9, 211926. DOI: 10.1098/rsos.211926

3. Buffi, M. et al. (2025). Electrical signaling in fungi: past and present challenges. FEMS Microbiol Rev 49, fuaf009. DOI: 10.1093/femsre/fuaf009

4. Buffi, M. et al. (2025). Detection of electrical signals in fungal mycelia in response to external stimuli. iScience 28(10), 113484. DOI: 10.1016/j.isci.2025.113484

5. Fukasawa, Y. et al. (2024). Electrical integrity and week-long oscillation in fungal mycelia. Sci Rep 14, 15601. DOI: 10.1038/s41598-024-66223-6

6. Gow, N.A. (1984). Transhyphal electrical currents in fungi. J Gen Microbiol 130, 3313-3318.

7. Olsson, S. & Hansson, B.S. (1995). Action potential-like activity found in fungal mycelia is sensitive to stimulation. Naturwissenschaften 82, 30-31. DOI: 10.1007/BF01167867

8. Slayman, C.L. et al. (1976). "Action potentials" in Neurospora crassa, a mycelial fungus. Biochim Biophys Acta 426, 732-744.

9. Hunter, P. (2023). The fungal grid. EMBO Rep 24, e57255. DOI: 10.15252/embr.202357255

10. Mayne, R. et al. (2023). Propagation of electrical signals by fungi. Biosystems 229, 104933.

---

## Contact Scientists

For collaboration or questions about fungal electrophysiology:

- **Prof. Pilar Junier** - University of Neuchâtel - pilar.junier@unine.ch
- **Prof. Andrew Adamatzky** - University of West England - andrew.adamatzy@uwe.ac.uk
- **Dr. Matteo Buffi** - University of Neuchâtel
- **Prof. Yu Fukasawa** - Tohoku University
- **Los Alamos Fungal Biology Group** - Bioscience Division

## Mycosoft Contribution

**What We're Building:**

Fungi Compute is designed to be THE definitive research tool that all fungal electrophysiology researchers would use. It implements every major analysis method from the literature, provides publication-ready outputs, and integrates with environmental monitoring for multi-modal correlation analysis.

**Our Unique Additions:**
- Real-time STFT analysis on live FCI data
- Multi-modal correlation (seismic, weather, growth)
- Educational mode teaching methodologies
- Cloud-based collaboration and data sharing
- Integration with MINDEX biological database
- NLM pattern recognition for automated classification

**Target Users:**
- Academic researchers (universities, national labs)
- Mycology field stations
- Agricultural monitoring (mycorrhizal health)
- Environmental sensors (fungi as biosensors)
- Citizen scientists exploring fungal electrophysiology

---

**Document Version:** 1.0  
**Created:** February 10, 2026  
**Authors:** Mycosoft Research Team  
**Last Updated:** February 10, 2026

This document will be updated as new research is published.
