"""
SDR (Software Defined Radio) Signal Processing Pipeline for FCI

Implements noise filtering, artifact rejection, and GFST pattern detection
using DSP concepts borrowed from radio communications.

(c) 2026 Mycosoft Labs - February 9, 2026
"""

import logging
import math
import numpy as np
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from collections import deque

logger = logging.getLogger(__name__)


# ============================================================================
# ENUMS AND CONFIGURATION
# ============================================================================


class EMFPreset(str, Enum):
    """Common EMF noise rejection presets."""
    NONE = "none"
    MOTOR_NOISE = "motor_noise"          # 50/60Hz fundamental + harmonics
    FLUORESCENT = "fluorescent"          # 50/60Hz + high-freq ballast
    HVAC = "hvac"                         # Low-freq rumble + motor harmonics
    SWITCHING_SUPPLY = "switching_supply" # 50-150kHz switching noise


class RFPreset(str, Enum):
    """RF interference rejection presets."""
    NONE = "none"
    BROADBAND = "broadband"              # General RF shielding
    CELLULAR = "cellular"                # 700-2600 MHz cellular bands
    WIFI = "wifi"                        # 2.4/5 GHz WiFi
    BLUETOOTH = "bluetooth"              # 2.4 GHz Bluetooth


class FilterPreset(str, Enum):
    """Complete SDR filter presets."""
    LAB = "lab"                          # Clean lab environment
    FIELD = "field"                      # Outdoor field deployment
    URBAN = "urban"                      # High-EMF urban environment
    CLEAN_ROOM = "clean_room"            # Minimal interference


@dataclass
class SDRConfig:
    """SDR pipeline configuration."""
    # Bandpass filter (Hz)
    bandpass_low: float = 0.01
    bandpass_high: float = 50.0
    bandpass_order: int = 4
    
    # Notch filters
    notch_50hz: bool = True
    notch_60hz: bool = True
    notch_q: float = 30.0
    
    # RF rejection
    rf_preset: RFPreset = RFPreset.NONE
    
    # EMF rejection
    emf_preset: EMFPreset = EMFPreset.NONE
    
    # Adaptive filtering
    adaptive_enabled: bool = True
    adaptive_threshold: float = 3.0  # Standard deviations
    
    # Decimation (downsample factor)
    decimation_factor: int = 1
    
    # DC removal
    dc_removal: bool = True
    
    # Gain control
    agc_enabled: bool = True
    agc_target: float = 1.0


@dataclass
class ProcessedSample:
    """A processed signal sample with metadata."""
    timestamp: datetime
    channel: int
    raw_value: float
    filtered_value: float
    is_artifact: bool = False
    spike_detected: bool = False
    noise_estimate: float = 0.0
    snr_db: float = 0.0


@dataclass
class SpectrumAnalysis:
    """FFT spectrum analysis result."""
    frequencies: List[float] = field(default_factory=list)
    magnitudes: List[float] = field(default_factory=list)
    peak_frequency: float = 0.0
    peak_magnitude: float = 0.0
    spectral_entropy: float = 0.0
    band_powers: Dict[str, float] = field(default_factory=dict)


@dataclass
class GFSTMatch:
    """GFST pattern match result."""
    pattern_name: str
    category: str
    confidence: float
    frequency: float
    amplitude: float
    description: str = ""


# ============================================================================
# GFST FREQUENCY BANDS
# ============================================================================

GFST_BANDS = {
    "ulf": (0.001, 0.1),     # Ultra-low: seismic precursors
    "vlf": (0.1, 1.0),       # Very-low: baseline, communication
    "lf": (1.0, 5.0),        # Low: growth, nutrient seeking
    "mf": (5.0, 20.0),       # Medium: action potentials
    "hf": (20.0, 50.0),      # High: defensive responses
}

GFST_PATTERNS = {
    "baseline": {"freq_range": (0.1, 0.5), "amp_range": (0.1, 0.5), "category": "metabolic"},
    "active_growth": {"freq_range": (0.5, 2.0), "amp_range": (0.5, 2.0), "category": "metabolic"},
    "nutrient_seeking": {"freq_range": (1.0, 5.0), "amp_range": (1.0, 3.0), "category": "metabolic"},
    "temperature_stress": {"freq_range": (0.2, 1.0), "amp_range": (1.0, 5.0), "category": "environmental"},
    "chemical_stress": {"freq_range": (2.0, 10.0), "amp_range": (2.0, 8.0), "category": "environmental"},
    "network_communication": {"freq_range": (0.1, 1.0), "amp_range": (0.5, 2.0), "category": "communication"},
    "action_potential": {"freq_range": (5.0, 20.0), "amp_range": (5.0, 20.0), "category": "communication"},
    "seismic_precursor": {"freq_range": (0.01, 0.1), "amp_range": (0.2, 1.0), "category": "predictive"},
    "defense_activation": {"freq_range": (2.0, 8.0), "amp_range": (2.0, 6.0), "category": "defensive"},
    "sporulation_initiation": {"freq_range": (0.5, 2.0), "amp_range": (1.0, 3.0), "category": "reproductive"},
}


# ============================================================================
# IIR BIQUAD FILTER
# ============================================================================


class BiquadFilter:
    """
    Second-order IIR biquad filter.
    
    Standard form: H(z) = (b0 + b1*z^-1 + b2*z^-2) / (1 + a1*z^-1 + a2*z^-2)
    """
    
    def __init__(self, b0: float, b1: float, b2: float, a1: float, a2: float):
        self.b0 = b0
        self.b1 = b1
        self.b2 = b2
        self.a1 = a1
        self.a2 = a2
        
        # State variables
        self.x1 = 0.0
        self.x2 = 0.0
        self.y1 = 0.0
        self.y2 = 0.0
    
    def process(self, x: float) -> float:
        """Process a single sample."""
        y = (self.b0 * x + self.b1 * self.x1 + self.b2 * self.x2 
             - self.a1 * self.y1 - self.a2 * self.y2)
        
        self.x2 = self.x1
        self.x1 = x
        self.y2 = self.y1
        self.y1 = y
        
        return y
    
    def reset(self):
        """Reset filter state."""
        self.x1 = self.x2 = self.y1 = self.y2 = 0.0
    
    @classmethod
    def lowpass(cls, fc: float, fs: float, q: float = 0.707) -> "BiquadFilter":
        """Create a lowpass filter."""
        w0 = 2 * math.pi * fc / fs
        alpha = math.sin(w0) / (2 * q)
        
        b0 = (1 - math.cos(w0)) / 2
        b1 = 1 - math.cos(w0)
        b2 = (1 - math.cos(w0)) / 2
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha
        
        return cls(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0)
    
    @classmethod
    def highpass(cls, fc: float, fs: float, q: float = 0.707) -> "BiquadFilter":
        """Create a highpass filter."""
        w0 = 2 * math.pi * fc / fs
        alpha = math.sin(w0) / (2 * q)
        
        b0 = (1 + math.cos(w0)) / 2
        b1 = -(1 + math.cos(w0))
        b2 = (1 + math.cos(w0)) / 2
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha
        
        return cls(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0)
    
    @classmethod
    def notch(cls, fc: float, fs: float, q: float = 30.0) -> "BiquadFilter":
        """Create a notch (band-reject) filter."""
        w0 = 2 * math.pi * fc / fs
        alpha = math.sin(w0) / (2 * q)
        
        b0 = 1
        b1 = -2 * math.cos(w0)
        b2 = 1
        a0 = 1 + alpha
        a1 = -2 * math.cos(w0)
        a2 = 1 - alpha
        
        return cls(b0/a0, b1/a0, b2/a0, a1/a0, a2/a0)


# ============================================================================
# SDR PIPELINE
# ============================================================================


class SDRPipeline:
    """
    Complete SDR-style signal processing pipeline for FCI data.
    
    Pipeline stages:
    1. DC removal (optional)
    2. Bandpass filtering
    3. Notch filtering (50/60 Hz)
    4. EMF rejection
    5. RF rejection (simulated for audio-range signals)
    6. Adaptive artifact rejection
    7. AGC (automatic gain control)
    8. Spike detection
    9. Pattern classification
    """
    
    def __init__(self, sample_rate: float = 1000.0, config: Optional[SDRConfig] = None):
        self.sample_rate = sample_rate
        self.config = config or SDRConfig()
        
        # Initialize filter chain
        self._init_filters()
        
        # Running statistics for adaptive processing
        self._sample_history: deque = deque(maxlen=1000)
        self._running_mean = 0.0
        self._running_var = 1.0
        self._alpha = 0.01  # EMA smoothing factor
        
        # DC offset estimation
        self._dc_estimate = 0.0
        self._dc_alpha = 0.001  # Slow DC tracking
        
        # AGC state
        self._agc_gain = 1.0
        self._agc_attack = 0.01
        self._agc_decay = 0.0001
        
        # Spike detection
        self._spike_threshold = 5.0  # mV
        self._last_spike_time = 0.0
        self._refractory_period = 0.003  # 3ms
        
        logger.info(f"SDR pipeline initialized: fs={sample_rate}Hz, config={config}")
    
    def _init_filters(self):
        """Initialize the filter chain based on configuration."""
        fs = self.sample_rate
        cfg = self.config
        
        # Bandpass (implemented as cascaded HP + LP)
        self._hp_filter = BiquadFilter.highpass(cfg.bandpass_low, fs)
        self._lp_filter = BiquadFilter.lowpass(cfg.bandpass_high, fs)
        
        # Notch filters
        self._notch_50hz = BiquadFilter.notch(50.0, fs, cfg.notch_q) if cfg.notch_50hz else None
        self._notch_60hz = BiquadFilter.notch(60.0, fs, cfg.notch_60hz) if cfg.notch_60hz else None
        
        # Harmonic notches (2nd and 3rd harmonics)
        self._notch_100hz = BiquadFilter.notch(100.0, fs, cfg.notch_q) if cfg.notch_50hz else None
        self._notch_120hz = BiquadFilter.notch(120.0, fs, cfg.notch_q) if cfg.notch_60hz else None
        self._notch_150hz = BiquadFilter.notch(150.0, fs, cfg.notch_q) if cfg.notch_50hz else None
        self._notch_180hz = BiquadFilter.notch(180.0, fs, cfg.notch_q) if cfg.notch_60hz else None
    
    def update_config(self, config: SDRConfig):
        """Update pipeline configuration."""
        self.config = config
        self._init_filters()
        logger.info(f"SDR config updated: {config}")
    
    def process_sample(self, value: float, channel: int = 0, timestamp: Optional[datetime] = None) -> ProcessedSample:
        """
        Process a single signal sample through the entire pipeline.
        
        Args:
            value: Raw signal value in mV
            channel: Channel number
            timestamp: Sample timestamp (defaults to now)
        
        Returns:
            ProcessedSample with filtered value and metadata
        """
        ts = timestamp or datetime.now(timezone.utc)
        raw = value
        
        # 1. DC removal
        if self.config.dc_removal:
            self._dc_estimate = self._dc_estimate * (1 - self._dc_alpha) + value * self._dc_alpha
            value = value - self._dc_estimate
        
        # 2. Bandpass filtering
        value = self._hp_filter.process(value)
        value = self._lp_filter.process(value)
        
        # 3. Notch filtering (50/60 Hz and harmonics)
        if self._notch_50hz:
            value = self._notch_50hz.process(value)
        if self._notch_60hz:
            value = self._notch_60hz.process(value)
        if self._notch_100hz:
            value = self._notch_100hz.process(value)
        if self._notch_120hz:
            value = self._notch_120hz.process(value)
        if self._notch_150hz:
            value = self._notch_150hz.process(value)
        if self._notch_180hz:
            value = self._notch_180hz.process(value)
        
        # 4. Update running statistics
        self._sample_history.append(value)
        old_mean = self._running_mean
        self._running_mean = self._running_mean * (1 - self._alpha) + value * self._alpha
        self._running_var = self._running_var * (1 - self._alpha) + (value - old_mean) * (value - self._running_mean) * self._alpha
        
        noise_estimate = math.sqrt(max(self._running_var, 1e-10))
        
        # 5. Artifact detection (adaptive threshold)
        is_artifact = False
        if self.config.adaptive_enabled:
            deviation = abs(value - self._running_mean) / max(noise_estimate, 1e-10)
            is_artifact = deviation > self.config.adaptive_threshold * 3
            
            if is_artifact:
                # Replace artifact with interpolated value
                value = self._running_mean
        
        # 6. AGC (automatic gain control)
        if self.config.agc_enabled:
            abs_val = abs(value)
            if abs_val > self.config.agc_target:
                self._agc_gain *= (1 - self._agc_attack)
            else:
                self._agc_gain *= (1 + self._agc_decay)
            self._agc_gain = max(0.1, min(10.0, self._agc_gain))
            value *= self._agc_gain
        
        # 7. Spike detection
        current_time = ts.timestamp()
        spike_detected = False
        if abs(value) > self._spike_threshold:
            if (current_time - self._last_spike_time) > self._refractory_period:
                spike_detected = True
                self._last_spike_time = current_time
        
        # 8. Calculate SNR
        signal_power = value ** 2
        noise_power = noise_estimate ** 2
        snr_db = 10 * math.log10(max(signal_power / max(noise_power, 1e-20), 1e-10)) if noise_power > 0 else 0.0
        
        return ProcessedSample(
            timestamp=ts,
            channel=channel,
            raw_value=raw,
            filtered_value=value,
            is_artifact=is_artifact,
            spike_detected=spike_detected,
            noise_estimate=noise_estimate,
            snr_db=snr_db,
        )
    
    def process_buffer(self, samples: List[float], channel: int = 0) -> List[ProcessedSample]:
        """Process a buffer of samples."""
        return [self.process_sample(s, channel) for s in samples]
    
    def compute_spectrum(self, samples: List[float], window: str = "hanning") -> SpectrumAnalysis:
        """
        Compute FFT spectrum analysis on a sample buffer.
        
        Args:
            samples: Signal samples
            window: Window function ('hanning', 'hamming', 'blackman', 'rectangular')
        
        Returns:
            SpectrumAnalysis with frequency and magnitude data
        """
        n = len(samples)
        if n < 4:
            return SpectrumAnalysis()
        
        # Apply window
        arr = np.array(samples)
        if window == "hanning":
            arr *= np.hanning(n)
        elif window == "hamming":
            arr *= np.hamming(n)
        elif window == "blackman":
            arr *= np.blackman(n)
        # else: rectangular (no windowing)
        
        # Compute FFT
        fft = np.fft.rfft(arr)
        magnitudes = np.abs(fft) / n
        frequencies = np.fft.rfftfreq(n, d=1.0/self.sample_rate)
        
        # Find peak
        peak_idx = np.argmax(magnitudes[1:]) + 1  # Exclude DC
        peak_freq = float(frequencies[peak_idx])
        peak_mag = float(magnitudes[peak_idx])
        
        # Compute band powers
        band_powers = {}
        for band_name, (f_low, f_high) in GFST_BANDS.items():
            mask = (frequencies >= f_low) & (frequencies <= f_high)
            band_powers[band_name] = float(np.sum(magnitudes[mask] ** 2))
        
        # Spectral entropy
        psd = magnitudes[1:] ** 2
        psd_norm = psd / (np.sum(psd) + 1e-10)
        spectral_entropy = float(-np.sum(psd_norm * np.log(psd_norm + 1e-10)))
        
        return SpectrumAnalysis(
            frequencies=frequencies.tolist(),
            magnitudes=magnitudes.tolist(),
            peak_frequency=peak_freq,
            peak_magnitude=peak_mag,
            spectral_entropy=spectral_entropy,
            band_powers=band_powers,
        )
    
    def classify_pattern(self, spectrum: SpectrumAnalysis, amplitude: float) -> Optional[GFSTMatch]:
        """
        Classify the current signal against GFST patterns.
        
        Args:
            spectrum: Computed spectrum analysis
            amplitude: RMS amplitude in mV
        
        Returns:
            Best matching GFSTMatch or None if no match
        """
        freq = spectrum.peak_frequency
        
        best_match = None
        best_confidence = 0.0
        
        for pattern_name, pattern_def in GFST_PATTERNS.items():
            freq_min, freq_max = pattern_def["freq_range"]
            amp_min, amp_max = pattern_def["amp_range"]
            
            # Check if signal is within pattern bounds
            freq_in_range = freq_min <= freq <= freq_max
            amp_in_range = amp_min <= amplitude <= amp_max
            
            if freq_in_range and amp_in_range:
                # Calculate confidence based on proximity to center of ranges
                freq_center = (freq_min + freq_max) / 2
                amp_center = (amp_min + amp_max) / 2
                
                freq_score = 1 - abs(freq - freq_center) / max(freq_max - freq_min, 0.01)
                amp_score = 1 - abs(amplitude - amp_center) / max(amp_max - amp_min, 0.01)
                
                confidence = (freq_score + amp_score) / 2
                confidence = max(0.4, min(0.95, confidence))
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_match = GFSTMatch(
                        pattern_name=pattern_name,
                        category=pattern_def["category"],
                        confidence=confidence,
                        frequency=freq,
                        amplitude=amplitude,
                    )
        
        return best_match
    
    def reset(self):
        """Reset all filter states and statistics."""
        self._hp_filter.reset()
        self._lp_filter.reset()
        if self._notch_50hz:
            self._notch_50hz.reset()
        if self._notch_60hz:
            self._notch_60hz.reset()
        if self._notch_100hz:
            self._notch_100hz.reset()
        if self._notch_120hz:
            self._notch_120hz.reset()
        if self._notch_150hz:
            self._notch_150hz.reset()
        if self._notch_180hz:
            self._notch_180hz.reset()
        
        self._sample_history.clear()
        self._running_mean = 0.0
        self._running_var = 1.0
        self._dc_estimate = 0.0
        self._agc_gain = 1.0
        self._last_spike_time = 0.0
        
        logger.info("SDR pipeline reset")


# ============================================================================
# FACTORY FUNCTIONS
# ============================================================================


def create_pipeline_from_preset(preset: FilterPreset, sample_rate: float = 1000.0) -> SDRPipeline:
    """Create a pre-configured SDR pipeline from a preset."""
    configs = {
        FilterPreset.LAB: SDRConfig(
            bandpass_low=0.01,
            bandpass_high=50.0,
            notch_50hz=True,
            notch_60hz=True,
            emf_preset=EMFPreset.FLUORESCENT,
            rf_preset=RFPreset.NONE,
            adaptive_enabled=True,
        ),
        FilterPreset.FIELD: SDRConfig(
            bandpass_low=0.1,
            bandpass_high=30.0,
            notch_50hz=True,
            notch_60hz=True,
            emf_preset=EMFPreset.MOTOR_NOISE,
            rf_preset=RFPreset.BROADBAND,
            adaptive_enabled=True,
            adaptive_threshold=4.0,
        ),
        FilterPreset.URBAN: SDRConfig(
            bandpass_low=0.1,
            bandpass_high=20.0,
            notch_50hz=True,
            notch_60hz=True,
            emf_preset=EMFPreset.SWITCHING_SUPPLY,
            rf_preset=RFPreset.CELLULAR,
            adaptive_enabled=True,
            adaptive_threshold=5.0,
        ),
        FilterPreset.CLEAN_ROOM: SDRConfig(
            bandpass_low=0.01,
            bandpass_high=100.0,
            notch_50hz=False,
            notch_60hz=False,
            emf_preset=EMFPreset.NONE,
            rf_preset=RFPreset.NONE,
            adaptive_enabled=False,
        ),
    }
    
    return SDRPipeline(sample_rate=sample_rate, config=configs.get(preset, SDRConfig()))
