import os
import glob
import json
import scipy.io
import scipy.signal
import scipy.stats
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any
from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif, RFECV
from sklearn.linear_model import LogisticRegression, ElasticNet
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
from sklearn.pipeline import Pipeline

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
GYRO_CHANNELS = ["gyroThumbX", "gyroThumbY", "gyroThumbZ", "gyroIndexX", "gyroIndexY", "gyroIndexZ"]

def extract_advanced_features(signals: Dict[str, np.ndarray], fs: float = 200.0) -> Dict[str, float]:
    """
    Extract comprehensive kinematic features including:
    - Base channel statistics
    - Movement asymmetry (Thumb vs Index)
    - Fatigue drift (First half vs Second half)
    - Tapping cycle kinematics & irregularity
    - Tremor band (4-8Hz) vs Tapping band (1-4Hz) ratio
    """
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

def build_advanced_dataset() -> Tuple[pd.DataFrame, List[str]]:
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
    return df, feature_cols

def run_nested_optimization():
    print("=" * 70)
    print("SCIENTIFIC MODEL & FEATURE OPTIMIZATION EXPERIMENT")
    print("=" * 70)

    df, all_feature_cols = build_advanced_dataset()
    print(f"Dataset: N={len(df)} samples across {df['person_id'].nunique()} participants.")
    print(f"Total Candidate Features Extracted: {len(all_feature_cols)}")

    label_map = {"PD": 0, "MSA": 1}
    y = df["diagnosis"].map(label_map).values
    groups = df["person_id"].values
    X = df[all_feature_cols].values

    # Outer 5-fold Stratified Group K-Fold (Strict Leakage Barrier)
    outer_cv = StratifiedGroupKFold(n_splits=5)

    # Candidate feature counts to test
    k_features_to_test = [12, 16, 20, 25, 30, len(all_feature_cols)]

    # Candidate Models to evaluate
    models_to_test = {
        "Logistic Regression (L2, C=0.5)": lambda: LogisticRegression(max_iter=1000, random_state=42, C=0.5),
        "Logistic Regression (L2, C=1.0)": lambda: LogisticRegression(max_iter=1000, random_state=42, C=1.0),
        "Logistic Regression (ElasticNet, C=0.5)": lambda: LogisticRegression(penalty='elasticnet', solver='saga', l1_ratio=0.5, max_iter=2000, random_state=42, C=0.5),
        "Linear SVM (C=0.5)": lambda: SVC(kernel='linear', C=0.5, probability=True, random_state=42),
        "RBF SVM (C=1.0, gamma='scale')": lambda: SVC(kernel='rbf', C=1.0, probability=True, random_state=42),
        "RBF SVM (C=2.0, gamma='scale')": lambda: SVC(kernel='rbf', C=2.0, probability=True, random_state=42),
        "ExtraTrees (n=100, max_depth=5)": lambda: ExtraTreesClassifier(n_estimators=100, max_depth=5, min_samples_leaf=2, random_state=42),
        "Random Forest (n=100, max_depth=5)": lambda: RandomForestClassifier(n_estimators=100, max_depth=5, min_samples_leaf=2, random_state=42),
        "HistGradientBoosting": lambda: HistGradientBoostingClassifier(max_iter=50, max_depth=3, random_state=42, min_samples_leaf=5)
    }

    results_table = []

    for k_feat in k_features_to_test:
        for model_name, model_fn in models_to_test.items():
            pooled_y_true = []
            pooled_y_pred = []
            pooled_y_prob = []
            fold_baccs = []
            fold_aucs = []

            for fold, (train_idx, test_idx) in enumerate(outer_cv.split(X, y, groups)):
                # Leakage check
                assert len(set(groups[train_idx]).intersection(set(groups[test_idx]))) == 0

                X_tr, y_tr = X[train_idx], y[train_idx]
                X_te, y_te = X[test_idx], y[test_idx]

                # FOLD-ISOLATED PREPROCESSING
                scaler = StandardScaler()
                X_tr_sc = scaler.fit_transform(X_tr)
                X_te_sc = scaler.transform(X_te)

                # FOLD-ISOLATED FEATURE SELECTION (SelectKBest ANOVA F-test)
                if k_feat < len(all_feature_cols):
                    selector = SelectKBest(score_func=f_classif, k=k_feat)
                    X_tr_sel = selector.fit_transform(X_tr_sc, y_tr)
                    X_te_sel = selector.transform(X_te_sc)
                else:
                    X_tr_sel = X_tr_sc
                    X_te_sel = X_te_sc

                # Train model
                clf = model_fn()
                clf.fit(X_tr_sel, y_tr)

                preds = clf.predict(X_te_sel)
                probs = clf.predict_proba(X_te_sel)[:, 1] if hasattr(clf, "predict_proba") else preds.astype(float)

                pooled_y_true.extend(y_te)
                pooled_y_pred.extend(preds)
                pooled_y_prob.extend(probs)

                f_bacc = balanced_accuracy_score(y_te, preds)
                try:
                    f_auc = roc_auc_score(y_te, probs)
                except Exception:
                    f_auc = 0.5
                fold_baccs.append(f_bacc)
                fold_aucs.append(f_auc)

            pooled_y_true = np.array(pooled_y_true)
            pooled_y_pred = np.array(pooled_y_pred)
            pooled_y_prob = np.array(pooled_y_prob)

            cm = confusion_matrix(pooled_y_true, pooled_y_pred)
            tn, fp, fn, tp = cm.ravel()
            bacc = balanced_accuracy_score(pooled_y_true, pooled_y_pred)
            sens = tp / (tp + fn)
            spec = tn / (tn + fp)
            auc = roc_auc_score(pooled_y_true, pooled_y_prob)
            f1 = f1_score(pooled_y_true, pooled_y_pred, average="weighted")
            brier = brier_score_loss(pooled_y_true, pooled_y_prob)

            results_table.append({
                "k_features": k_feat,
                "model": model_name,
                "balanced_acc": bacc,
                "sensitivity_msa": sens,
                "specificity_pd": spec,
                "roc_auc": auc,
                "f1_score": f1,
                "brier_loss": brier,
                "fold_bacc_mean": np.mean(fold_baccs),
                "fold_bacc_std": np.std(fold_baccs),
                "tn": tn, "fp": fp, "fn": fn, "tp": tp
            })

    res_df = pd.DataFrame(results_table)
    res_df = res_df.sort_values(by="balanced_acc", ascending=False).reset_index(drop=True)

    print("\n--- TOP 12 SCIENTIFIC OPTIMIZATION CONFIGURATIONS ---")
    print(res_df[["model", "k_features", "balanced_acc", "sensitivity_msa", "specificity_pd", "roc_auc", "brier_loss", "fold_bacc_std"]].head(12).to_string())

    # Save complete experiment results
    exp_path = os.path.join(PROJECT_ROOT, "backend", "saved_models", "optimization_experiment_results.json")
    res_df.to_json(exp_path, orient="records", indent=2)
    print(f"\nComplete experiment results saved to: {exp_path}")

    # Inspect top model and features
    top_config = res_df.iloc[0]
    print(f"\nTop Performing Architecture: {top_config['model']} with K={top_config['k_features']} features")
    print(f"Balanced Accuracy: {top_config['balanced_acc']*100:.2f}%, Sensitivity: {top_config['sensitivity_msa']*100:.2f}%, Specificity: {top_config['specificity_pd']*100:.2f}%, AUC: {top_config['roc_auc']:.3f}")

if __name__ == "__main__":
    run_nested_optimization()
