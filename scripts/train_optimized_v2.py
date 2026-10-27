import os
import json
import joblib
import numpy as np
import pandas as pd
import scipy.io
import scipy.signal
import scipy.stats
import shap
from typing import Dict, List, Tuple, Any

from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, recall_score,
    precision_score, f1_score, roc_auc_score, confusion_matrix, brier_score_loss
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
SAVED_MODELS_DIR = os.path.join(PROJECT_ROOT, "backend", "saved_models")
os.makedirs(SAVED_MODELS_DIR, exist_ok=True)

GYRO_CHANNELS = ["gyroThumbX", "gyroThumbY", "gyroThumbZ", "gyroIndexX", "gyroIndexY", "gyroIndexZ"]

def extract_advanced_features(signals: Dict[str, np.ndarray], fs: float = 200.0) -> Dict[str, float]:
    feats: Dict[str, float] = {}

    tx, ty, tz = signals["gyroThumbX"], signals["gyroThumbY"], signals["gyroThumbZ"]
    ix, iy, iz = signals["gyroIndexX"], signals["gyroIndexY"], signals["gyroIndexZ"]

    thumb_mag = np.sqrt(tx**2 + ty**2 + tz**2)
    index_mag = np.sqrt(ix**2 + iy**2 + iz**2)
    min_len = min(len(tx), len(ix))
    rel_x = ix[:min_len] - tx[:min_len]
    rel_y = iy[:min_len] - ty[:min_len]
    rel_z = iz[:min_len] - tz[:min_len]
    rel_mag = np.sqrt(rel_x**2 + rel_y**2 + rel_z**2)

    # 1. Base channel statistics for key axes
    for name, sig in [("thumb_mag", thumb_mag), ("index_mag", index_mag), ("rel_mag", rel_mag),
                      ("gyroThumbY", ty), ("gyroIndexY", iy), ("gyroThumbZ", tz), ("gyroIndexZ", iz),
                      ("gyroThumbX", tx), ("gyroIndexX", ix)]:
        feats[f"{name}_rms"] = float(np.sqrt(np.mean(sig**2)))
        feats[f"{name}_p2p"] = float(np.ptp(sig))
        diff_s = np.diff(sig) * fs
        feats[f"{name}_jerk_rms"] = float(np.sqrt(np.mean(diff_s**2))) if len(diff_s) > 0 else 0.0

    # 2. Movement Asymmetry / Coordination
    t_rms = feats["thumb_mag_rms"]
    i_rms = feats["index_mag_rms"]
    feats["thumb_index_rms_ratio"] = float(t_rms / (i_rms + 1e-6))
    feats["thumb_index_p2p_ratio"] = float(feats["thumb_mag_p2p"] / (feats["index_mag_p2p"] + 1e-6))

    # Cross-correlation between Thumb Y and Index Y (opening/closing phase coordination)
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

    # 4. Tapping Kinematics & Rhythmicity
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
        feats["tap_amplitude_mean"] = 0.0
        feats["tap_amplitude_cv"] = 0.0
        feats["tap_amplitude_decay"] = 0.0
        feats["tap_rhythmicity_r2"] = 0.0
        feats["tap_cadence_fatigue_ratio"] = 1.0

    # 5. Spectral Bands: Tapping Band (1-4Hz) vs Tremor Band (4-8Hz) vs Subharmonic (<1Hz)
    nperseg = min(min_len, int(2 * fs))
    if nperseg >= 32:
        freqs, psd = scipy.signal.welch(rel_mag - np.mean(rel_mag), fs=fs, nperseg=nperseg)
        tot_pwr = float(np.sum(psd)) + 1e-12
        
        tap_mask = (freqs >= 1.0) & (freqs <= 4.0)
        tremor_mask = (freqs > 4.0) & (freqs <= 8.0)
        sub_mask = freqs < 1.0

        tap_pwr = float(np.sum(psd[tap_mask]))
        tremor_pwr = float(np.sum(psd[tremor_mask]))
        sub_pwr = float(np.sum(psd[sub_mask]))

        feats["spec_tap_pwr_ratio"] = tap_pwr / tot_pwr
        feats["spec_tremor_pwr_ratio"] = tremor_pwr / tot_pwr
        feats["spec_tremor_to_tap_ratio"] = tremor_pwr / (tap_pwr + 1e-12)
        feats["spec_subharmonic_ratio"] = sub_pwr / tot_pwr

        # Dominant frequency
        dom_idx = np.argmax(psd)
        feats["spec_dom_freq"] = float(freqs[dom_idx])

        # Spectral entropy
        norm_psd = psd / tot_pwr
        norm_psd = norm_psd[norm_psd > 0]
        feats["spec_entropy"] = float(-np.sum(norm_psd * np.log2(norm_psd)))
    else:
        feats["spec_tap_pwr_ratio"] = 0.0
        feats["spec_tremor_pwr_ratio"] = 0.0
        feats["spec_tremor_to_tap_ratio"] = 0.0
        feats["spec_subharmonic_ratio"] = 0.0
        feats["spec_dom_freq"] = 0.0
        feats["spec_entropy"] = 0.0

    return feats

def main():
    print("Building dataset from raw MAT files with 48 physiologically motivated features...")
    records = []
    for cls in ["MSA", "PD"]:
        cls_dir = os.path.join(DATA_DIR, cls)
        files = sorted(glob_files(cls_dir))
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

            feats = extract_advanced_features(signals, fs)
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
    print(f"Dataset extracted: {len(df)} samples, {len(feature_cols)} features across {df['person_id'].nunique()} participants.")

    label_map = {"PD": 0, "MSA": 1}
    inv_label_map = {0: "PD", 1: "MSA"}
    y = df["diagnosis"].map(label_map).values
    groups = df["person_id"].values
    X = df[feature_cols].values

    # Strict 5-fold StratifiedGroupKFold evaluation
    sgkf = StratifiedGroupKFold(n_splits=5)

    models = {
        "Optimized Logistic Regression (v2, C=0.5, RobustScaler)": (
            RobustScaler(),
            LogisticRegression(C=0.5, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
        ),
        "Linear SVM (C=0.5, RobustScaler)": (
            RobustScaler(),
            SVC(C=0.5, kernel='linear', probability=True, random_state=42)
        ),
        "Baseline Random Forest (StandardScaler)": (
            StandardScaler(),
            RandomForestClassifier(n_estimators=100, max_depth=6, min_samples_leaf=2, random_state=42)
        ),
        "Baseline Logistic Regression (C=1.0, StandardScaler)": (
            StandardScaler(),
            LogisticRegression(C=1.0, max_iter=1000, random_state=42)
        ),
        "Baseline KNN (k=5, StandardScaler)": (
            StandardScaler(),
            KNeighborsClassifier(n_neighbors=5, weights="distance")
        )
    }

    full_evaluation_dict = {}

    for m_name, (scaler_inst, clf) in models.items():
        y_true_all, y_pred_all, y_prob_all = [], [], []
        fold_records = []

        for fold_idx, (train_idx, test_idx) in enumerate(sgkf.split(X, y, groups)):
            # Leakage verification
            tr_pids = set(groups[train_idx])
            te_pids = set(groups[test_idx])
            assert len(tr_pids.intersection(te_pids)) == 0, f"Leakage detected in fold {fold_idx}"

            sc = type(scaler_inst)()
            X_train = sc.fit_transform(X[train_idx])
            X_test = sc.transform(X[test_idx])
            y_train = y[train_idx]
            y_test = y[test_idx]

            clf_fold = type(clf)(**clf.get_params())
            clf_fold.fit(X_train, y_train)

            preds = clf_fold.predict(X_test)
            if hasattr(clf_fold, "predict_proba"):
                probs = clf_fold.predict_proba(X_test)[:, 1]
            else:
                probs = preds.astype(float)

            y_true_all.extend(y_test)
            y_pred_all.extend(preds)
            y_prob_all.extend(probs)

            f_bacc = balanced_accuracy_score(y_test, preds)
            try:
                f_auc = roc_auc_score(y_test, probs)
            except Exception:
                f_auc = f_bacc
            fold_records.append({
                "fold": fold_idx + 1,
                "balanced_accuracy": float(f_bacc),
                "roc_auc": float(f_auc)
            })

        acc = accuracy_score(y_true_all, y_pred_all)
        bacc = balanced_accuracy_score(y_true_all, y_pred_all)
        sens = recall_score(y_true_all, y_pred_all, pos_label=1)  # MSA
        spec = recall_score(y_true_all, y_pred_all, pos_label=0)  # PD
        f1 = f1_score(y_true_all, y_pred_all, average="weighted")
        auc = roc_auc_score(y_true_all, y_prob_all)
        brier = brier_score_loss(y_true_all, y_prob_all)
        tn, fp, fn, tp = confusion_matrix(y_true_all, y_pred_all).ravel()

        bacc_fold_vals = [f["balanced_accuracy"] for f in fold_records]
        auc_fold_vals = [f["roc_auc"] for f in fold_records]

        full_evaluation_dict[m_name] = {
            "pooled": {
                "accuracy": round(float(acc), 4),
                "balanced_accuracy": round(float(bacc), 4),
                "sensitivity_msa": round(float(sens), 4),
                "specificity_pd": round(float(spec), 4),
                "f1_score": round(float(f1), 4),
                "roc_auc": round(float(auc), 4),
                "brier_score": round(float(brier), 4),
                "confusion_matrix": {
                    "tn": int(tn),
                    "fp": int(fp),
                    "fn": int(fn),
                    "tp": int(tp),
                    "matrix": [[int(tn), int(fp)], [int(fn), int(tp)]]
                }
            },
            "per_fold": {
                "balanced_accuracy_mean": round(float(np.mean(bacc_fold_vals)), 4),
                "balanced_accuracy_std": round(float(np.std(bacc_fold_vals)), 4),
                "roc_auc_mean": round(float(np.mean(auc_fold_vals)), 4),
                "roc_auc_std": round(float(np.std(auc_fold_vals)), 4),
                "folds": fold_records
            }
        }

        print(f"\n=== {m_name} ===")
        print(f"Balanced Accuracy: {bacc*100:.2f}% | Sensitivity (MSA): {sens*100:.2f}% | Specificity (PD): {spec*100:.2f}%")
        print(f"ROC-AUC: {auc:.4f} | Brier Score: {brier:.4f}")
        print(f"Fold Balanced Accuracies: {[round(x*100, 1) for x in bacc_fold_vals]}")

    # Now train final optimized production model on all 140 recordings
    print("\nTraining final production Optimized Logistic Regression (v2)...")
    final_scaler = RobustScaler()
    X_scaled = final_scaler.fit_transform(X)
    
    final_model = LogisticRegression(C=0.5, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
    final_model.fit(X_scaled, y)

    # Initialize SHAP LinearExplainer with background data (mean/scaled training samples)
    linear_explainer = shap.LinearExplainer(final_model, X_scaled)
    expected_value = float(linear_explainer.expected_value) if hasattr(linear_explainer, "expected_value") else 0.0

    # Save artifacts
    model_v2_path = os.path.join(SAVED_MODELS_DIR, "neuroscope_model_v2.joblib")
    joblib.dump({
        "model": final_model,
        "scaler": final_scaler,
        "feature_cols": feature_cols,
        "label_mapping": label_map,
        "inv_label_mapping": inv_label_map,
        "expected_value": expected_value,
        "model_type": "LogisticRegression_v2_RobustScaler",
        "evaluation_metrics": full_evaluation_dict["Optimized Logistic Regression (v2, C=0.5, RobustScaler)"]
    }, model_v2_path)
    print(f"Saved optimized model v2 to: {model_v2_path}")

    # Save feature schema v2
    schema_v2_path = os.path.join(SAVED_MODELS_DIR, "feature_schema_v2.json")
    with open(schema_v2_path, "w") as f:
        json.dump({
            "num_features": len(feature_cols),
            "features": feature_cols,
            "meta_cols": meta_cols
        }, f, indent=2)
    print(f"Saved feature schema v2 to: {schema_v2_path}")

    # Also save evaluation_results.json updated
    eval_json_path = os.path.join(SAVED_MODELS_DIR, "evaluation_results.json")
    with open(eval_json_path, "w") as f:
        json.dump(full_evaluation_dict, f, indent=2)
    print(f"Saved updated evaluation results to: {eval_json_path}")

def glob_files(d: str) -> List[str]:
    import glob
    return glob.glob(os.path.join(d, "*.mat"))

if __name__ == "__main__":
    main()
