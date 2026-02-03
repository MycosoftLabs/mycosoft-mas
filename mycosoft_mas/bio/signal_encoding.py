"""Signal Encoding/Decoding for bio-digital conversion. Created: February 3, 2026"""
import struct
from typing import Any, Dict, List
import base64

class SignalEncoder:
    def __init__(self, sample_rate_hz: int = 1000, bits_per_sample: int = 16):
        self.sample_rate_hz = sample_rate_hz
        self.bits_per_sample = bits_per_sample
    
    def encode_samples(self, samples: List[float]) -> bytes:
        return struct.pack(f"{len(samples)}f", *samples)
    
    def encode_spike_train(self, spike_times: List[float]) -> bytes:
        return struct.pack(f"{len(spike_times)}f", *spike_times)
    
    def to_base64(self, data: bytes) -> str:
        return base64.b64encode(data).decode("ascii")

class SignalDecoder:
    def __init__(self, sample_rate_hz: int = 1000):
        self.sample_rate_hz = sample_rate_hz
    
    def decode_samples(self, data: bytes) -> List[float]:
        count = len(data) // 4
        return list(struct.unpack(f"{count}f", data))
    
    def from_base64(self, data: str) -> bytes:
        return base64.b64decode(data)
    
    def detect_spikes(self, samples: List[float], threshold: float = 0.5) -> List[int]:
        spikes = []
        for i, s in enumerate(samples):
            if s > threshold:
                spikes.append(i)
        return spikes
