import numpy as np
import scipy.signal
import scipy.stats
from typing import Dict, Any, Tuple

# 6 Gyroscope channels recorded during repetitive finger tapping
GYRO_CHANNELS = [
    "gyroThumbX", "gyroThumbY", "gyroThumbZ",
    "gyroIndexX", "gyroIndexY", "gyroIndexZ"
]

def compute_signal_magnitude(signals: Dict[str, np.ndarray]) -> Dict[str, np.ndarray]:
    """Compute magnitude vectors for thumb, index, and relative finger motion."""
    tx = signals.get("gyroThumbX", np.zeros(1))
    ty = signals.get("gyroThumbY", np.zeros(1))
    tz = signals.get("gyroThumbZ", np.zeros(1))
    thumb_mag = np.sqrt(tx**2 + ty**2 + tz**2)

    ix = signals.get("gyroIndexX", np.zeros(1))
    iy = signals.get("gyroIndexY", np.zeros(1))
    iz = signals.get("gyroIndexZ", np.zeros(1))
    index_mag = np.sqrt(ix**2 + iy**2 + iz**2)

    min_len = min(len(tx), len(ix))
    rel_x = ix[:min_len] - tx[:min_len]
    rel_y = iy[:min_len] - ty[:min_len]
    rel_z = iz[:min_len] - tz[:min_len]
    relative_mag = np.sqrt(rel_x**2 + rel_y**2 + rel_z**2)

    return {
        "thumb_mag": thumb_mag,
        "index_mag": index_mag,
        "relative_mag": relative_mag,
        "rel_mag": relative_mag
    }

def extract_channel_features(sig: np.ndarray, fs: float, prefix: str) -> Dict[str, float]:
    """Extract statistical, spectral, and kinematic features from a single signal trace."""
    feats: Dict[str, float] = {}
    sig = np.asarray(sig, dtype=np.float64).flatten()
    
    if len(sig) < 10:
        return {f"{prefix}_{k}": 0.0 for k in [
            "mean", "std", "rms", "p2p", "skew", "kurtosis",
            "jerk_rms", "dom_freq", "dom_pwr_ratio", "spec_entropy"
        ]}

    mean_val = float(np.mean(sig))
    std_val = float(np.std(sig))
    rms_val = float(np.sqrt(np.mean(sig**2)))
    p2p_val = float(np.ptp(sig))
    skew_val = float(scipy.stats.skew(sig)) if std_val > 1e-6 else 0.0
    kurt_val = float(scipy.stats.kurtosis(sig)) if std_val > 1e-6 else 0.0

    feats[f"{prefix}_mean"] = mean_val
    feats[f"{prefix}_std"] = std_val
    feats[f"{prefix}_rms"] = rms_val
    feats[f"{prefix}_p2p"] = p2p_val
    feats[f"{prefix}_skew"] = skew_val
    feats[f"{prefix}_kurt"] = kurt_val

    diff_sig = np.diff(sig) * fs
    jerk_rms = float(np.sqrt(np.mean(diff_sig**2))) if len(diff_sig) > 0 else 0.0
    feats[f"{prefix}_jerk_rms"] = jerk_rms

    try:
        nperseg = min(len(sig), int(2 * fs))
        if nperseg >= 16:
            freqs, psd = scipy.signal.welch(sig - mean_val, fs=fs, nperseg=nperseg)
            total_pwr = float(np.sum(psd)) + 1e-12
            
            tap_mask = (freqs >= 0.5) & (freqs <= 5.0)
            tap_pwr = float(np.sum(psd[tap_mask]))
            dom_freq_idx = np.argmax(psd)
            dom_freq = float(freqs[dom_freq_idx])
            
            dom_pwr_ratio = tap_pwr / total_pwr
            
            norm_psd = psd / total_pwr
            norm_psd = norm_psd[norm_psd > 0]
            spec_entropy = float(-np.sum(norm_psd * np.log2(norm_psd)))
        else:
            dom_freq = 0.0
            dom_pwr_ratio = 0.0
            spec_entropy = 0.0
    except Exception:
        dom_freq = 0.0
        dom_pwr_ratio = 0.0
        spec_entropy = 0.0

    feats[f"{prefix}_dom_freq"] = dom_freq
    feats[f"{prefix}_dom_pwr_ratio"] = dom_pwr_ratio
    feats[f"{prefix}_spec_entropy"] = spec_entropy

    return feats

def extract_paper_six_features(signals: Dict[str, np.ndarray], fs: float = 200.0) -> Dict[str, float]:
    """
    Implements Table 2 from Heliyon 2023 (PMC10107087, Belic et al.):
    Feature 1: Index x-axis angular velocity RMS
    Feature 2: Index y-axis angular velocity Average of maxima of individual taps
    Feature 3: Index y-axis angular acceleration RMS (differential d/dt)
    Feature 4: Index vector magnitude Fourier spectral centroid
    Feature 5: Thumb x-axis angular velocity Maximum
    Feature 6: Thumb z-axis angular acceleration STD of maxima of individual taps
    """
    tx = signals.get("gyroThumbX", np.zeros(1))
    ty = signals.get("gyroThumbY", np.zeros(1))
    tz = signals.get("gyroThumbZ", np.zeros(1))
    ix = signals.get("gyroIndexX", np.zeros(1))
    iy = signals.get("gyroIndexY", np.zeros(1))
    iz = signals.get("gyroIndexZ", np.zeros(1))

    min_len = min(len(tx), len(ix))
    tx, ty, tz = tx[:min_len], ty[:min_len], tz[:min_len]
    ix, iy, iz = ix[:min_len], iy[:min_len], iz[:min_len]

    # Feature 1: Index x angular velocity RMS
    f1 = float(np.sqrt(np.mean(ix**2))) if min_len > 0 else 0.0

    # Tap segmentation via 4th-order Butterworth bandpass 0.4-5.0 Hz
    nyq = 0.5 * fs
    b, a = scipy.signal.butter(4, [0.4 / nyq, 5.0 / nyq], btype='band')
    iy_filt = scipy.signal.filtfilt(b, a, iy) if min_len > 30 else iy
    iy_sq = iy_filt**2
    min_distance = max(10, int(fs * 0.15))
    tap_peaks, _ = scipy.signal.find_peaks(iy_sq, distance=min_distance, height=np.percentile(iy_sq, 50))

    if len(tap_peaks) >= 2:
        tap_iy_maxima = []
        tz_acc = np.diff(tz) * fs
        tap_tz_acc_maxima = []

        for k in range(len(tap_peaks) - 1):
            t_start = tap_peaks[k]
            t_end = tap_peaks[k+1]
            seg_iy = iy[t_start:t_end]
            if len(seg_iy) > 0:
                tap_iy_maxima.append(np.max(np.abs(seg_iy)))

            seg_tz = tz_acc[t_start:min(t_end, len(tz_acc))]
            if len(seg_tz) > 0:
                tap_tz_acc_maxima.append(np.max(np.abs(seg_tz)))

        f2 = float(np.mean(tap_iy_maxima)) if len(tap_iy_maxima) > 0 else float(np.mean(np.abs(iy)))
        f6 = float(np.std(tap_tz_acc_maxima)) if len(tap_tz_acc_maxima) > 1 else 0.0
    else:
        f2 = float(np.max(np.abs(iy))) if min_len > 0 else 0.0
        tz_acc = np.diff(tz) * fs
        f6 = float(np.std(tz_acc)) if len(tz_acc) > 0 else 0.0

    # Feature 3: Index y angular acceleration RMS
    iy_acc = np.diff(iy) * fs
    f3 = float(np.sqrt(np.mean(iy_acc**2))) if len(iy_acc) > 0 else 0.0

    # Feature 4: Index vector magnitude Fourier spectral centroid
    index_vector = np.sqrt(ix**2 + iy**2 + iz**2)
    n = len(index_vector)
    fft_vals = np.abs(np.fft.rfft(index_vector))
    freqs = np.fft.rfftfreq(n, d=1.0/fs)
    cum_pwr = np.cumsum(fft_vals**2)
    tot_pwr = cum_pwr[-1] if len(cum_pwr) > 0 and cum_pwr[-1] > 0 else 1.0
    half_idx = np.searchsorted(cum_pwr, 0.5 * tot_pwr)
    f4 = float(freqs[min(half_idx, len(freqs)-1)]) if len(freqs) > 0 else 0.0

    # Feature 5: Thumb x angular velocity Maximum
    f5 = float(np.max(tx)) if min_len > 0 else 0.0

    return {
        "paper_feat1_index_x_rms": f1,
        "paper_feat2_index_y_tap_max_mean": f2,
        "paper_feat3_index_y_acc_rms": f3,
        "paper_feat4_index_vec_spec_centroid": f4,
        "paper_feat5_thumb_x_max": f5,
        "paper_feat6_thumb_z_acc_tap_max_std": f6
    }

def extract_all_features(signals: Dict[str, np.ndarray], fs: float = 200.0) -> Dict[str, float]:
    """
    Extract comprehensive 59 features:
    - 6 Original Heliyon 2023 Table-2 features
    - 53 Deep kinematic features across all 6 gyroscope channels
    """
    feats: Dict[str, float] = {}
    
    # 0. Heliyon 2023 Paper 6 features
    p_feats = extract_paper_six_features(signals, fs)
    feats.update(p_feats)

    tx = signals.get("gyroThumbX", np.zeros(1))
    ty = signals.get("gyroThumbY", np.zeros(1))
    tz = signals.get("gyroThumbZ", np.zeros(1))
    ix = signals.get("gyroIndexX", np.zeros(1))
    iy = signals.get("gyroIndexY", np.zeros(1))
    iz = signals.get("gyroIndexZ", np.zeros(1))

    min_len = min(len(tx), len(ix))
    tx, ty, tz = tx[:min_len], ty[:min_len], tz[:min_len]
    ix, iy, iz = ix[:min_len], iy[:min_len], iz[:min_len]

    thumb_mag = np.sqrt(tx**2 + ty**2 + tz**2)
    index_mag = np.sqrt(ix**2 + iy**2 + iz**2)
    rel_x = ix - tx
    rel_y = iy - ty
    rel_z = iz - tz
    rel_mag = np.sqrt(rel_x**2 + rel_y**2 + rel_z**2)

    # 1. Base channel statistics for all 6 axes + 3 magnitudes (9 signal vectors)
    vectors = [
        ("thumb_mag", thumb_mag), ("index_mag", index_mag), ("rel_mag", rel_mag),
        ("gyroThumbX", tx), ("gyroThumbY", ty), ("gyroThumbZ", tz),
        ("gyroIndexX", ix), ("gyroIndexY", iy), ("gyroIndexZ", iz)
    ]

    for name, sig in vectors:
        rms_val = float(np.sqrt(np.mean(sig**2)))
        p2p_val = float(np.ptp(sig))
        diff_s = np.diff(sig) * fs
        jerk_val = float(np.sqrt(np.mean(diff_s**2))) if len(diff_s) > 0 else 0.0

        feats[f"{name}_rms"] = rms_val
        feats[f"{name}_p2p"] = p2p_val
        feats[f"{name}_jerk_rms"] = jerk_val

        # Aliases for relative_mag backwards compatibility
        if name == "rel_mag":
            feats["relative_mag_rms"] = rms_val
            feats["relative_mag_p2p"] = p2p_val
            feats["relative_mag_jerk_rms"] = jerk_val
            feats["relative_mag_mean"] = float(np.mean(sig))
            feats["relative_mag_std"] = float(np.std(sig))

    feats["thumb_mag_mean"] = float(np.mean(thumb_mag))
    feats["thumb_mag_std"] = float(np.std(thumb_mag))
    feats["index_mag_mean"] = float(np.mean(index_mag))
    feats["index_mag_std"] = float(np.std(index_mag))

    # GyroThumbY and GyroIndexY dom_freq for legacy checks
    for y_ch, y_sig in [("gyroThumbY", ty), ("gyroIndexY", iy)]:
        y_feats = extract_channel_features(y_sig, fs, prefix=y_ch)
        feats[f"{y_ch}_dom_freq"] = y_feats[f"{y_ch}_dom_freq"]
        feats[f"{y_ch}_dom_pwr_ratio"] = y_feats[f"{y_ch}_dom_pwr_ratio"]
        feats[f"{y_ch}_spec_entropy"] = y_feats[f"{y_ch}_spec_entropy"]

    # 2. Movement Asymmetry & Inter-Digit Coordination
    t_rms = feats["thumb_mag_rms"]
    i_rms = feats["index_mag_rms"]
    feats["thumb_index_rms_ratio"] = float(t_rms / (i_rms + 1e-6))
    feats["thumb_index_p2p_ratio"] = float(feats["thumb_mag_p2p"] / (feats["index_mag_p2p"] + 1e-6))
    feats["thumb_index_jerk_ratio"] = float(feats["thumb_mag_jerk_rms"] / (feats["index_mag_jerk_rms"] + 1e-6))

    # Phase synchronization between Thumb Y and Index Y (primary tapping plane)
    ty_norm = (ty - np.mean(ty)) / (np.std(ty) + 1e-6)
    iy_norm = (iy - np.mean(iy)) / (np.std(iy) + 1e-6)
    corr = np.correlate(ty_norm, iy_norm, mode='full')
    lags = np.arange(-len(ty) + 1, len(ty))
    max_idx = np.argmax(np.abs(corr))
    feats["phase_cross_corr_max"] = float(corr[max_idx] / len(ty))
    feats["phase_lag_ms"] = float(abs(lags[max_idx]) / fs * 1000.0)

    # 3. Fatigue / Temporal Drift (First Half vs Second Half)
    half = min_len // 2
    if half > int(fs):
        rel_first = rel_mag[:half]
        rel_second = rel_mag[half:]
        rms_first = float(np.sqrt(np.mean(rel_first**2)))
        rms_second = float(np.sqrt(np.mean(rel_second**2)))
        feats["fatigue_rms_ratio"] = float(rms_second / (rms_first + 1e-6))
        feats["fatigue_p2p_ratio"] = float(np.ptp(rel_second) / (np.ptp(rel_first) + 1e-6))
    else:
        feats["fatigue_rms_ratio"] = 1.0
        feats["fatigue_p2p_ratio"] = 1.0

    # 4. Tapping Kinematics, Hesitations & Cycle Segmentation
    min_dist = max(10, int(fs * 0.15))
    h_thresh = np.percentile(rel_mag, 60)
    peaks, _ = scipy.signal.find_peaks(rel_mag, distance=min_dist, height=h_thresh)
    dur_sec = min_len / fs
    tap_count = len(peaks)
    feats["tap_count"] = float(tap_count)
    feats["tap_rate_hz"] = float(tap_count / dur_sec) if dur_sec > 0 else 0.0

    if tap_count >= 3:
        intervals = np.diff(peaks) / fs
        mean_int = float(np.mean(intervals))
        std_int = float(np.std(intervals))
        feats["tap_interval_mean"] = mean_int
        feats["tap_interval_cv"] = float(std_int / mean_int) if mean_int > 1e-6 else 0.0
        feats["tap_interval_skew"] = float(scipy.stats.skew(intervals)) if len(intervals) > 2 else 0.0

        # Motion Hesitations / Freezing
        med_int = np.median(intervals)
        hesitations = np.sum(intervals > 1.5 * med_int)
        feats["hesitation_ratio"] = float(hesitations / len(intervals))

        peak_amps = rel_mag[peaks]
        mean_amp = float(np.mean(peak_amps))
        std_amp = float(np.std(peak_amps))
        feats["tap_amplitude_mean"] = mean_amp
        feats["tap_amplitude_cv"] = float(std_amp / mean_amp) if mean_amp > 1e-6 else 0.0

        x_norm = np.linspace(0, 1, tap_count)
        if np.std(x_norm) > 1e-6 and std_amp > 1e-6:
            slope, _, r_val, _, _ = scipy.stats.linregress(x_norm, peak_amps)
            feats["tap_amplitude_decay"] = float(slope)
            feats["tap_rhythmicity_r2"] = float(r_val**2)
            feats["tap_rhythmicity_idx"] = float(r_val**2)
        else:
            feats["tap_amplitude_decay"] = 0.0
            feats["tap_rhythmicity_r2"] = 0.0
            feats["tap_rhythmicity_idx"] = 0.0

        half_peaks_1 = np.sum(peaks < half)
        half_peaks_2 = np.sum(peaks >= half)
        feats["tap_cadence_fatigue_ratio"] = float((half_peaks_2 + 1e-3) / (half_peaks_1 + 1e-3))
    else:
        feats["tap_interval_mean"] = 0.0
        feats["tap_interval_cv"] = 0.0
        feats["tap_interval_skew"] = 0.0
        feats["hesitation_ratio"] = 0.0
        feats["tap_amplitude_mean"] = 0.0
        feats["tap_amplitude_cv"] = 0.0
        feats["tap_amplitude_decay"] = 0.0
        feats["tap_rhythmicity_r2"] = 0.0
        feats["tap_rhythmicity_idx"] = 0.0
        feats["tap_cadence_fatigue_ratio"] = 1.0

    # 5. Multi-Band Spectral Power Distribution (Welch's Method)
    nperseg = min(min_len, int(2 * fs))
    if nperseg >= 32:
        freqs, psd = scipy.signal.welch(rel_mag - np.mean(rel_mag), fs=fs, nperseg=nperseg)
        tot_pwr = float(np.sum(psd)) + 1e-12
        
        sub_mask = freqs < 1.0
        tap_mask = (freqs >= 1.0) & (freqs <= 4.0)
        tremor_mask = (freqs > 4.0) & (freqs <= 8.0)
        ataxia_mask = (freqs > 8.0) & (freqs <= 14.0)

        sub_pwr = float(np.sum(psd[sub_mask]))
        tap_pwr = float(np.sum(psd[tap_mask]))
        tremor_pwr = float(np.sum(psd[tremor_mask]))
        ataxia_pwr = float(np.sum(psd[ataxia_mask]))

        feats["spec_subharmonic_ratio"] = sub_pwr / tot_pwr
        feats["spec_tap_pwr_ratio"] = tap_pwr / tot_pwr
        feats["spec_tremor_pwr_ratio"] = tremor_pwr / tot_pwr
        feats["spec_ataxia_pwr_ratio"] = ataxia_pwr / tot_pwr
        feats["spec_tremor_to_tap_ratio"] = tremor_pwr / (tap_pwr + 1e-12)
        feats["spec_ataxia_to_tap_ratio"] = ataxia_pwr / (tap_pwr + 1e-12)

        dom_idx = np.argmax(psd)
        feats["spec_dom_freq"] = float(freqs[dom_idx])

        norm_psd = psd / tot_pwr
        norm_psd = norm_psd[norm_psd > 0]
        feats["spec_entropy"] = float(-np.sum(norm_psd * np.log2(norm_psd)))
    else:
        feats["spec_subharmonic_ratio"] = 0.0
        feats["spec_tap_pwr_ratio"] = 0.0
        feats["spec_tremor_pwr_ratio"] = 0.0
        feats["spec_ataxia_pwr_ratio"] = 0.0
        feats["spec_tremor_to_tap_ratio"] = 0.0
        feats["spec_ataxia_to_tap_ratio"] = 0.0
        feats["spec_dom_freq"] = 0.0
        feats["spec_entropy"] = 0.0

    return feats
