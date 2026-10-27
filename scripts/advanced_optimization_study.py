import os
import glob
import json
import scipy.io
import scipy.signal
import scipy.stats
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import (
    RandomForestClassifier, ExtraTreesClassifier,
    HistGradientBoostingClassifier, VotingClassifier
)
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, recall_score,
    precision_score, f1_score, roc_auc_score, confusion_matrix, brier_score_loss
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
GYRO_CHANNELS = ["gyroThumbX", "gyroThumbY", "gyroThumbZ", "gyroIndexX", "gyroIndexY", "gyroIndexZ"]

def extract_deep_kinematic_features(signals: Dict[str, np.ndarray], fs: float = 200.0) -> Dict[str, float]:
    feats: Dict[str, float] = {}

    tx, ty, tz = signals["gyroThumbX"], signals["gyroThumbY"], signals["gyroThumbZ"]
    ix, iy, iz = signals["gyroIndexX"], signals["gyroIndexY"], signals["gyroIndexZ"]

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
    min_dist = max(10, int(fs * 0.15)) # max 6.7 Hz tapping
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

        # Motion Hesitations / Freezing: intervals > 1.5 * median interval
        med_int = np.median(intervals)
        hesitations = np.sum(intervals > 1.5 * med_int)
        feats["hesitation_ratio"] = float(hesitations / len(intervals))

        # Peak amplitudes & Decay slope
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
        else:
            feats["tap_amplitude_decay"] = 0.0
            feats["tap_rhythmicity_r2"] = 0.0

        # Tap frequency drift (cadence in second half vs first half)
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
        feats["tap_cadence_fatigue_ratio"] = 1.0

    # 5. Multi-Band Spectral Power Distribution (Welch's Method)
    nperseg = min(min_len, int(2 * fs))
    if nperseg >= 32:
        freqs, psd = scipy.signal.welch(rel_mag - np.mean(rel_mag), fs=fs, nperseg=nperseg)
        tot_pwr = float(np.sum(psd)) + 1e-12
        
        # Sub-bands:
        # Subharmonic: < 1.0 Hz
        # Voluntary tapping: 1.0 - 4.0 Hz
        # Parkinsonian resting/action tremor: 4.0 - 8.0 Hz
        # Cerebellar / postural ataxia: 8.0 - 14.0 Hz
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

        # Dominant frequency
        dom_idx = np.argmax(psd)
        feats["spec_dom_freq"] = float(freqs[dom_idx])

        # Spectral entropy
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

def run_study():
    print("Loading all 140 recordings from authentic dataset...")
    records = []
    for cls in ["MSA", "PD"]:
        cls_dir = os.path.join(DATA_DIR, cls)
        files = sorted(glob.glob(os.path.join(cls_dir, "*.mat")))
        for f in files:
            mat = scipy.io.loadmat(f)
            diag = str(mat["diagnosis"][0]).strip()
            pid = str(mat["person_id"][0]).strip()
            tid = str(mat["trial_id"][0]).strip()
            fs = float(mat["fs"].flatten()[0]) if "fs" in mat else 200.0

            signals = {ch: np.asarray(mat[ch], dtype=np.float64).flatten() for ch in GYRO_CHANNELS}
            min_len = min(len(signals[ch]) for ch in GYRO_CHANNELS)
            for ch in signals:
                signals[ch] = signals[ch][:min_len]

            feats = extract_deep_kinematic_features(signals, fs)
            row = {
                "filename": os.path.basename(f),
                "diagnosis": diag,
                "person_id": pid,
                "trial_id": tid,
                "duration_sec": min_len / fs,
                "fs": fs
            }
            row.update(feats)
            records.append(row)

    df = pd.DataFrame(records)
    meta_cols = ["filename", "diagnosis", "person_id", "trial_id", "duration_sec", "fs"]
    feature_cols = [c for c in df.columns if c not in meta_cols]
    print(f"Dataset extracted: {len(df)} samples, {len(feature_cols)} features, {df['person_id'].nunique()} unique participants.")

    label_map = {"PD": 0, "MSA": 1}
    y = df["diagnosis"].map(label_map).values
    groups = df["person_id"].values
    X = df[feature_cols].values

    sgkf = StratifiedGroupKFold(n_splits=5)

    # Models to benchmark
    models = {
        "Logistic Regression (L2, C=0.5, RobustScaler)": (
            RobustScaler(),
            LogisticRegression(C=0.5, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
        ),
        "Logistic Regression (L2, C=0.2, RobustScaler)": (
            RobustScaler(),
            LogisticRegression(C=0.2, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
        ),
        "Linear SVM (C=0.5, RobustScaler)": (
            RobustScaler(),
            SVC(C=0.5, kernel='linear', probability=True, random_state=42)
        ),
        "RBF SVM (C=1.0, gamma='scale', RobustScaler)": (
            RobustScaler(),
            SVC(C=1.0, kernel='rbf', probability=True, random_state=42)
        ),
        "Random Forest (n=100, depth=6, RobustScaler)": (
            RobustScaler(),
            RandomForestClassifier(n_estimators=100, max_depth=6, min_samples_leaf=2, random_state=42)
        ),
        "ExtraTrees (n=100, depth=6, RobustScaler)": (
            RobustScaler(),
            ExtraTreesClassifier(n_estimators=100, max_depth=6, min_samples_leaf=2, random_state=42)
        ),
        "HistGradientBoosting (depth=4, RobustScaler)": (
            RobustScaler(),
            HistGradientBoostingClassifier(max_depth=4, min_samples_leaf=5, random_state=42)
        )
    }

    # Also test Feature Selection (K=10, 15, 20, 25, 30)
    print("\n" + "="*80)
    print("PHASE 1 - 4: MULTI-MODEL BENCHMARK (RECORDING-LEVEL VS. PATIENT-LEVEL AGGREGATION)")
    print("="*80)

    summary_results = []

    for name, (scaler_inst, clf) in models.items():
        # Store recording-level predictions
        rec_y_true, rec_y_pred, rec_y_prob = [], [], []
        # Store patient-level data: {pid: {"y_true": int, "probs": list}}
        pat_data = {}

        for fold, (train_idx, test_idx) in enumerate(sgkf.split(X, y, groups)):
            # Verify isolation
            tr_pids = set(groups[train_idx])
            te_pids = set(groups[test_idx])
            assert len(tr_pids.intersection(te_pids)) == 0, f"Leakage in fold {fold}"

            sc = type(scaler_inst)()
            X_tr = sc.fit_transform(X[train_idx])
            X_te = sc.transform(X[test_idx])
            y_tr = y[train_idx]
            y_te = y[test_idx]
            te_groups = groups[test_idx]

            model_fold = type(clf)(**clf.get_params())
            model_fold.fit(X_tr, y_tr)

            preds = model_fold.predict(X_te)
            probs = model_fold.predict_proba(X_te)[:, 1] if hasattr(model_fold, "predict_proba") else preds.astype(float)

            rec_y_true.extend(y_te)
            rec_y_pred.extend(preds)
            rec_y_prob.extend(probs)

            # Collect for patient-level aggregation
            for pid, y_true_val, p_val in zip(te_groups, y_te, probs):
                if pid not in pat_data:
                    pat_data[pid] = {"y_true": y_true_val, "probs": []}
                pat_data[pid]["probs"].append(p_val)

        # 1. Recording-Level Metrics
        rec_bacc = balanced_accuracy_score(rec_y_true, rec_y_pred)
        rec_auc = roc_auc_score(rec_y_true, rec_y_prob)
        rec_sens = recall_score(rec_y_true, rec_y_pred, pos_label=1) # MSA
        rec_spec = recall_score(rec_y_true, rec_y_pred, pos_label=0) # PD
        rec_brier = brier_score_loss(rec_y_true, rec_y_prob)

        # 2. Patient-Level Aggregation (Mean probability across patient's trials)
        pat_pids = list(pat_data.keys())
        pat_y_true = [pat_data[p]["y_true"] for p in pat_pids]
        pat_y_prob = [float(np.mean(pat_data[p]["probs"])) for p in pat_pids]
        pat_y_pred = [1 if p >= 0.5 else 0 for p in pat_y_prob]

        pat_bacc = balanced_accuracy_score(pat_y_true, pat_y_pred)
        pat_auc = roc_auc_score(pat_y_true, pat_y_prob)
        pat_sens = recall_score(pat_y_true, pat_y_pred, pos_label=1)
        pat_spec = recall_score(pat_y_true, pat_y_pred, pos_label=0)
        pat_cm = confusion_matrix(pat_y_true, pat_y_pred)

        print(f"\nModel: {name}")
        print(f"  Recording-Level: BAcc={rec_bacc*100:.2f}% | Sens={rec_sens*100:.2f}% | Spec={rec_spec*100:.2f}% | AUC={rec_auc:.3f} | Brier={rec_brier:.3f}")
        print(f"  PATIENT-LEVEL:   BAcc={pat_bacc*100:.2f}% | Sens={pat_sens*100:.2f}% | Spec={pat_spec*100:.2f}% | AUC={pat_auc:.3f}")
        print(f"  Patient Confusion Matrix (N={len(pat_pids)}): TN={pat_cm[0,0]}, FP={pat_cm[0,1]}, FN={pat_cm[1,0]}, TP={pat_cm[1,1]}")

        summary_results.append({
            "model": name,
            "rec_bacc": rec_bacc,
            "rec_auc": rec_auc,
            "rec_sens": rec_sens,
            "rec_spec": rec_spec,
            "rec_brier": rec_brier,
            "pat_bacc": pat_bacc,
            "pat_auc": pat_auc,
            "pat_sens": pat_sens,
            "pat_spec": pat_spec,
            "pat_cm": pat_cm.tolist()
        })

    # Save results to scratch
    scratch_dir = os.path.join(PROJECT_ROOT, "backend", "saved_models")
    with open(os.path.join(scratch_dir, "deep_optimization_results.json"), "w") as f:
        json.dump(summary_results, f, indent=2)

if __name__ == "__main__":
    run_study()
