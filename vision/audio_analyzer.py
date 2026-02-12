import numpy as np
import threading
from dataclasses import dataclass
from typing import Optional, Tuple

@dataclass
class AudioFeatures:
    rms: float
    peak: float
    centroid: float
    energy_low: float   # Bass (<250Hz)
    energy_mid: float   # Mids (250-2000Hz)
    energy_high: float  # Highs (>2000Hz)

class AudioAnalyzer:
    def __init__(self, sample_rate: int = 16000, frame_duration_ms: int = 30):
        self.sample_rate = sample_rate
        self.frame_size = int(sample_rate * frame_duration_ms / 1000)
        self.lock = threading.Lock()
        self.latest_features = AudioFeatures(0, 0, 0, 0, 0, 0)
        
        # Frequency bins for FFT
        self.freqs = np.fft.rfftfreq(self.frame_size, 1 / self.sample_rate)
        
        # Define bands indices
        self.idx_low = (self.freqs < 250)
        self.idx_mid = (self.freqs >= 250) & (self.freqs < 2000)
        self.idx_high = (self.freqs >= 2000)

    def process_frame(self, indata: np.ndarray):
        """
        Process a chunk of audio data. 
        Expected input: numpy array of shape (N, channels) or (N,)
        """
        if indata is None or len(indata) == 0:
            return

        # Ensure mono
        if indata.ndim > 1:
            signal = np.mean(indata, axis=1)
        else:
            signal = indata

        # Remove DC offset
        signal = signal - np.mean(signal)
        
        # 1. RMS Amplitude
        rms = np.sqrt(np.mean(signal**2))
        peak = np.max(np.abs(signal))
        
        # Avoid FFT on silence or near-silence to save CPU
        if rms < 0.001:
            with self.lock:
                self.latest_features = AudioFeatures(rms, peak, 0, 0, 0, 0)
            return

        # 2. FFT
        # Apply Hanning window to reduce spectral leakage
        windowed = signal * np.hanning(len(signal))
        spectrum = np.abs(np.fft.rfft(windowed))
        
        # 3. Spectral Energy Bands
        energy_low = np.sum(spectrum[self.idx_low])
        energy_mid = np.sum(spectrum[self.idx_mid])
        energy_high = np.sum(spectrum[self.idx_high])
        
        # Normalize energies somewhat (heuristic scaling for callbacks)
        # These constants might need tuning based on mic sensitivity
        energy_low /= 10.0
        energy_mid /= 10.0
        energy_high /= 10.0

        # 4. Spectral Centroid
        # Start from index 1 to avoid DC component dominance
        magnitudes = spectrum[1:]
        frequencies = self.freqs[1:]
        
        total_magnitude = np.sum(magnitudes)
        if total_magnitude > 0:
            centroid = np.sum(frequencies * magnitudes) / total_magnitude
        else:
            centroid = 0

        with self.lock:
            self.latest_features = AudioFeatures(
                rms=float(rms),
                peak=float(peak),
                centroid=float(centroid),
                energy_low=float(energy_low),
                energy_mid=float(energy_mid),
                energy_high=float(energy_high)
            )

    def get_audio_features(self) -> AudioFeatures:
        with self.lock:
            return self.latest_features
