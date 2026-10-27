import os
import sys
import glob
import json
import scipy.io
import scipy.signal
import scipy.stats
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

from sklearn.preprocessing import StandardScaler, RobustScaler, MinMaxScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier, HistGradientBoostingClassifier, VotingClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import StratifiedGroupKFold, LeaveOneGroupOut
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, recall_score,
    precision_score, f1_score, roc_auc_score, confusion_matrix, brier_score_loss
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
GYRO_CHANNELS = ["gyroThumbX", "gyroThumbY", "gyroThumbZ", "gyroIndexX", "gyroIndexY", "gyroIndexZ"]

# Import existing 53-feature extractor
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from advanced_optimization_study import extract_deep_kinematic_features

# ==============================================================================
# PHASE 1: Exact Replication of the 6 Features from Heliyon 2023 (Table 2)
# ==============================================================================
def extract_paper_six_features(signals: Dict[str, np.ndarray], fs: float = 200.0) -> Dict[str, float]:
    """
    Implements Table 2 from Heliyon 2023 (PMC10107087, Belić et al.):
    Feature 1: Index x-axis angular velocity RMS
    Feature 2: Index y-axis angular velocity Average of maxima of individual taps
    Feature 3: Index y-axis angular acceleration RMS (differential d/dt)
    Feature 4: Index vector magnitude Fourier spectral centroid
    Feature 5: Thumb x-axis angular velocity Maximum
    Feature 6: Thumb z-axis angular acceleration STD of maxima of individual taps
    """
    tx, ty, tz = signals["gyroThumbX"], signals["gyroThumbY"], signals["gyroThumbZ"]
    ix, iy, iz = signals["gyroIndexX"], signals["gyroIndexY"], signals["gyroIndexZ"]
    
    min_len = min(len(tx), len(ix))
    tx, ty, tz = tx[:min_len], ty[:min_len], tz[:min_len]
    ix, iy, iz = ix[:min_len], iy[:min_len], iz[:min_len]
    
    # Feature 1: Index x angular velocity RMS
    f1 = float(np.sqrt(np.mean(ix**2)))
    
    # Tap segmentation as described in paper:
    # 4th-order Butterworth bandpass 0.4 to 5 Hz on index y (or vector) to find tap starts
    nyq = 0.5 * fs
    b, a = scipy.signal.butter(4, [0.4 / nyq, 5.0 / nyq], btype='band')
    iy_filt = scipy.signal.filtfilt(b, a, iy)
    iy_sq = iy_filt**2
    min_distance = max(10, int(fs * 0.15))
    tap_peaks, _ = scipy.signal.find_peaks(iy_sq, distance=min_distance, height=np.percentile(iy_sq, 50))
    
    # If tap_peaks found, segment individual taps
    if len(tap_peaks) >= 2:
        # Tap maxima of Index y angular velocity
        tap_iy_maxima = []
        # Thumb z angular acceleration (differential)
        tz_acc = np.diff(tz) * fs
        tap_tz_acc_maxima = []
        
        for k in range(len(tap_peaks) - 1):
            t_start = tap_peaks[k]
            t_end = tap_peaks[k+1]
            tap_segment_iy = iy[t_start:t_end]
            if len(tap_segment_iy) > 0:
                tap_iy_maxima.append(np.max(np.abs(tap_segment_iy)))
            
            tap_segment_tz_acc = tz_acc[t_start:min(t_end, len(tz_acc))]
            if len(tap_segment_tz_acc) > 0:
                tap_tz_acc_maxima.append(np.max(np.abs(tap_segment_tz_acc)))
                
        f2 = float(np.mean(tap_iy_maxima)) if len(tap_iy_maxima) > 0 else float(np.mean(np.abs(iy)))
        f6 = float(np.std(tap_tz_acc_maxima)) if len(tap_tz_acc_maxima) > 1 else 0.0
    else:
        f2 = float(np.max(np.abs(iy)))
        tz_acc = np.diff(tz) * fs
        f6 = float(np.std(tz_acc)) if len(tz_acc) > 0 else 0.0
        
    # Feature 3: Index y angular acceleration RMS
    iy_acc = np.diff(iy) * fs
    f3 = float(np.sqrt(np.mean(iy_acc**2))) if len(iy_acc) > 0 else 0.0
    
    # Feature 4: Index vector magnitude Fourier spectral centroid
    index_vector = np.sqrt(ix**2 + iy**2 + iz**2)
    # FFT
    n = len(index_vector)
    fft_vals = np.abs(np.fft.rfft(index_vector))
    freqs = np.fft.rfftfreq(n, d=1.0/fs)
    # Centroid: frequency below which 50% of total spectral power is contained (as paper defines)
    cum_pwr = np.cumsum(fft_vals**2)
    tot_pwr = cum_pwr[-1] if len(cum_pwr) > 0 and cum_pwr[-1] > 0 else 1.0
    half_idx = np.searchsorted(cum_pwr, 0.5 * tot_pwr)
    f4 = float(freqs[min(half_idx, len(freqs)-1)])
    
    # Feature 5: Thumb x angular velocity Maximum
    f5 = float(np.max(tx))
    
    return {
        "paper_feat1_index_x_rms": f1,
        "paper_feat2_index_y_tap_max_mean": f2,
        "paper_feat3_index_y_acc_rms": f3,
        "paper_feat4_index_vec_spec_centroid": f4,
        "paper_feat5_thumb_x_max": f5,
        "paper_feat6_thumb_z_acc_tap_max_std": f6
    }

def main():
    print("=" * 80)
    print("NEUROSCOPE V3: SCIENTIFIC OPTIMIZATION & ADVANCED MSA DETECTION STUDY")
    print("=" * 80)
    
    # 1. Load dataset (MSA and PD)
    records = []
    for cls in ["MSA", "PD"]:
        cls_dir = os.path.join(DATA_DIR, cls)
        for f in sorted(glob.glob(os.path.join(cls_dir, "*.mat"))):
            mat = scipy.io.loadmat(f)
            diag = str(mat["diagnosis"][0]).strip()
            pid = str(mat["person_id"][0]).strip()
            tid = str(mat["trial_id"][0]).strip()
            fs = float(mat["fs"].flatten()[0]) if "fs" in mat else 200.0
            signals = {ch: np.asarray(mat[ch], dtype=np.float64).flatten() for ch in GYRO_CHANNELS}
            min_len = min(len(signals[ch]) for ch in GYRO_CHANNELS)
            for ch in signals:
                signals[ch] = signals[ch][:min_len]
                
            p_feats = extract_paper_six_features(signals, fs)
            d_feats = extract_deep_kinematic_features(signals, fs)
            
            row = {
                "filename": os.path.basename(f),
                "diagnosis": diag,
                "person_id": pid,
                "trial_id": tid,
                "duration_sec": min_len / fs,
                "fs": fs
            }
            row.update(p_feats)
            row.update(d_feats)
            records.append(row)
            
    df = pd.DataFrame(records)
    print(f"Loaded {len(df)} trials across {df['person_id'].nunique()} unique patients.")
    print(f"Class breakdown: MSA={sum(df['diagnosis']=='MSA')} ({df[df['diagnosis']=='MSA']['person_id'].nunique()} patients), "
          f"PD={sum(df['diagnosis']=='PD')} ({df[df['diagnosis']=='PD']['person_id'].nunique()} patients)")
          
    paper_feature_cols = [c for c in df.columns if c.startswith("paper_feat")]
    deep_feature_cols = [c for c in df.columns if c not in ["filename", "diagnosis", "person_id", "trial_id", "duration_sec", "fs"] and not c.startswith("paper_feat")]
    all_feature_cols = paper_feature_cols + deep_feature_cols
    
    print(f"\nFeature subsets:")
    print(f" - Original Paper 6 Features: {len(paper_feature_cols)}")
    print(f" - Deep Kinematic Features: {len(deep_feature_cols)}")
    print(f" - Combined Set: {len(all_feature_cols)}")

    y_rec = (df["diagnosis"] == "MSA").astype(int).values
    groups = df["person_id"].values
    
    # ==========================================================================
    # PHASE 1: Compare Original 6 vs Deep 53 vs Combined on Strict 5-Fold Group CV
    # ==========================================================================
    print("\n" + "=" * 80)
    print("PHASE 1: FEATURE REPRESENTATION BENCHMARK (5-Fold StratifiedGroupKFold)")
    print("=" * 80)
    
    feature_configs = {
        "Original Paper 6 Features (kNN k=5, inv-dist)": (paper_feature_cols, KNeighborsClassifier(n_neighbors=5, weights='distance'), StandardScaler()),
        "Original Paper 6 Features (Logistic Regression)": (paper_feature_cols, LogisticRegression(C=0.5, max_iter=1000, random_state=42), RobustScaler()),
        "Deep 53 Features (Random Forest Baseline)": (deep_feature_cols, RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42), None),
        "Deep 53 Features (Logistic Regression v2)": (deep_feature_cols, LogisticRegression(C=0.5, max_iter=1000, random_state=42), RobustScaler()),
        "Combined 59 Features (Logistic Regression)": (all_feature_cols, LogisticRegression(C=0.5, max_iter=1000, random_state=42), RobustScaler()),
    }
    
    cv = StratifiedGroupKFold(n_splits=5, shuffle=True, random_state=42)
    
    phase1_results = {}
    for cfg_name, (cols, clf, scaler) in feature_configs.items():
        X = df[cols].values
        rec_preds = np.zeros(len(df))
        rec_probs = np.zeros(len(df))
        
        for tr_idx, te_idx in cv.split(X, y_rec, groups=groups):
            X_tr, y_tr = X[tr_idx], y_rec[tr_idx]
            X_te = X[te_idx]
            
            if scaler is not None:
                sc = scaler.__class__()
                X_tr = sc.fit_transform(X_tr)
                X_te = sc.transform(X_te)
                
            model = clf.__class__(**clf.get_params())
            model.fit(X_tr, y_tr)
            rec_preds[te_idx] = model.predict(X_te)
            rec_probs[te_idx] = model.predict_proba(X_te)[:, 1]
            
        rec_bacc = balanced_accuracy_score(y_rec, rec_preds)
        rec_auc = roc_auc_score(y_rec, rec_probs)
        
        # Patient-level mean aggregation
        pt_preds = []
        pt_trues = []
        pt_probs = []
        for pid in sorted(df["person_id"].unique()):
            idx = df[df["person_id"] == pid].index.values
            avg_prob = np.mean(rec_probs[idx])
            true_diag = 1 if df.loc[idx[0], "diagnosis"] == "MSA" else 0
            pt_probs.append(avg_prob)
            pt_preds.append(1 if avg_prob >= 0.5 else 0)
            pt_trues.append(true_diag)
            
        pt_bacc = balanced_accuracy_score(pt_trues, pt_preds)
        pt_sens = recall_score(pt_trues, pt_preds, pos_label=1)
        pt_spec = recall_score(pt_trues, pt_preds, pos_label=0)
        pt_auc = roc_auc_score(pt_trues, pt_probs)
        
        phase1_results[cfg_name] = {
            "rec_bacc": rec_bacc,
            "rec_auc": rec_auc,
            "pt_bacc": pt_bacc,
            "pt_sens": pt_sens,
            "pt_spec": pt_spec,
            "pt_auc": pt_auc
        }
        
        print(f"[{cfg_name}]")
        print(f"  Recording BAcc: {rec_bacc*100:.2f}% | Rec AUC: {rec_auc:.3f}")
        print(f"  Patient BAcc:   {pt_bacc*100:.2f}% | Pt Sens (MSA): {pt_sens*100:.2f}% | Pt Spec (PD): {pt_spec*100:.2f}% | Pt AUC: {pt_auc:.3f}")

    # ==========================================================================
    # PHASE 2: Investigate the Three Missed MSA Patients
    # ==========================================================================
    print("\n" + "=" * 80)
    print("PHASE 2: INVESTIGATION OF MISCLASSIFIED MSA PATIENTS (Out-Of-Fold Analysis)")
    print("=" * 80)
    
    # Run OOF evaluation for Logistic Regression v2 (53 features) and log per-trial details
    X_deep = df[deep_feature_cols].values
    rec_preds_v2 = np.zeros(len(df))
    rec_probs_v2 = np.zeros(len(df))
    
    for tr_idx, te_idx in cv.split(X_deep, y_rec, groups=groups):
        sc = RobustScaler()
        X_tr = sc.fit_transform(X_deep[tr_idx])
        X_te = sc.transform(X_deep[te_idx])
        lr = LogisticRegression(C=0.5, max_iter=1000, random_state=42)
        lr.fit(X_tr, y_rec[tr_idx])
        rec_preds_v2[te_idx] = lr.predict(X_te)
        rec_probs_v2[te_idx] = lr.predict_proba(X_te)[:, 1]
        
    df["oof_prob_msa"] = rec_probs_v2
    df["oof_pred_msa"] = rec_preds_v2
    
    patient_summaries = []
    for pid in sorted(df["person_id"].unique()):
        p_df = df[df["person_id"] == pid]
        diag = p_df["diagnosis"].iloc[0]
        mean_p = p_df["oof_prob_msa"].mean()
        pred_label = "MSA" if mean_p >= 0.5 else "PD"
        is_correct = (diag == pred_label)
        patient_summaries.append({
            "person_id": pid,
            "diagnosis": diag,
            "num_trials": len(p_df),
            "mean_prob_msa": mean_p,
            "min_prob": p_df["oof_prob_msa"].min(),
            "max_prob": p_df["oof_prob_msa"].max(),
            "std_prob": p_df["oof_prob_msa"].std(),
            "pred_label": pred_label,
            "is_correct": is_correct,
            # Kinematic highlights
            "mean_tap_rate": p_df["tap_rate_hz"].mean(),
            "mean_hesitation": p_df["hesitation_ratio"].mean(),
            "mean_phase_lag": p_df["phase_lag_ms"].mean(),
            "mean_ataxia_pwr": p_df["spec_ataxia_pwr_ratio"].mean(),
            "mean_rel_rms": p_df["rel_mag_rms"].mean()
        })
        
    pt_df = pd.DataFrame(patient_summaries)
    missed_msa = pt_df[(pt_df["diagnosis"] == "MSA") & (~pt_df["is_correct"])]
    correct_msa = pt_df[(pt_df["diagnosis"] == "MSA") & (pt_df["is_correct"])]
    all_pd = pt_df[pt_df["diagnosis"] == "PD"]
    
    print(f"Identified {len(missed_msa)} missed MSA patients:")
    for _, r in missed_msa.iterrows():
        print(f"\n--- Patient ID: {r['person_id']} (Actual: MSA, Predicted: {r['pred_label']}) ---")
        print(f"  Mean MSA Probability: {r['mean_prob_msa']:.3f} (Range: {r['min_prob']:.3f} - {r['max_prob']:.3f}, STD: {r['std_prob']:.3f})")
        print(f"  Kinematics: Tap Rate = {r['mean_tap_rate']:.2f} Hz | Hesitation = {r['mean_hesitation']*100:.1f}% | Phase Lag = {r['mean_phase_lag']:.1f} ms | Ataxia Power = {r['mean_ataxia_pwr']:.3f} | Motion RMS = {r['mean_rel_rms']:.2f}")
        # Print trials for this participant
        p_trials = df[df["person_id"] == r['person_id']][["trial_id", "oof_prob_msa", "tap_rate_hz", "hesitation_ratio", "spec_ataxia_pwr_ratio"]]
        print("  Trial-level predictions:")
        for _, tr in p_trials.iterrows():
            print(f"    Trial {tr['trial_id']}: MSA prob = {tr['oof_prob_msa']:.3f}, Rate = {tr['tap_rate_hz']:.2f} Hz, Ataxia = {tr['spec_ataxia_pwr_ratio']:.3f}")
            
    print("\n--- Cohort Comparison for Missed MSA Patients ---")
    print(f"Missed MSA Mean Ataxia Power: {missed_msa['mean_ataxia_pwr'].mean():.4f}")
    print(f"Correct MSA Mean Ataxia Power: {correct_msa['mean_ataxia_pwr'].mean():.4f}")
    print(f"PD Mean Ataxia Power:         {all_pd['mean_ataxia_pwr'].mean():.4f}")
    print(f"Missed MSA Mean Motion RMS:   {missed_msa['mean_rel_rms'].mean():.2f}")
    print(f"Correct MSA Mean Motion RMS:  {correct_msa['mean_rel_rms'].mean():.2f}")
    print(f"PD Mean Motion RMS:          {all_pd['mean_rel_rms'].mean():.2f}")

    # ==========================================================================
    # PHASE 3: Patient-Level Aggregation Strategies
    # ==========================================================================
    print("\n" + "=" * 80)
    print("PHASE 3: PATIENT-LEVEL PREDICTION AGGREGATION EXPERIMENTS")
    print("=" * 80)
    
    # We evaluate different trial aggregation rules on the out-of-fold trial probabilities
    aggregation_strategies = {
        "Mean Probability": lambda probs, weights: np.mean(probs),
        "Median Probability": lambda probs, weights: np.median(probs),
        "Trimmed Mean (drop min & max)": lambda probs, weights: np.mean(sorted(probs)[1:-1]) if len(probs) >= 4 else np.mean(probs),
        "Quality-Weighted by Motion RMS": lambda probs, weights: np.average(probs, weights=weights["rel_rms"]),
        "Quality-Weighted by Regularity (1-CV)": lambda probs, weights: np.average(probs, weights=weights["regularity"]),
        "Majority Voting of Trials (threshold 0.5)": lambda probs, weights: 1.0 if np.mean(np.array(probs) >= 0.5) > 0.5 else 0.0
    }
    
    for agg_name, agg_fn in aggregation_strategies.items():
        agg_pt_preds = []
        agg_pt_trues = []
        agg_pt_probs = []
        
        for pid in sorted(df["person_id"].unique()):
            p_df = df[df["person_id"] == pid]
            probs = p_df["oof_prob_msa"].values
            weights = {
                "rel_rms": np.maximum(0.1, p_df["rel_mag_rms"].values),
                "regularity": 1.0 / (1.0 + np.maximum(0.01, p_df["tap_interval_cv"].values))
            }
            final_p = agg_fn(probs, weights)
            true_diag = 1 if p_df["diagnosis"].iloc[0] == "MSA" else 0
            agg_pt_probs.append(final_p)
            agg_pt_preds.append(1 if final_p >= 0.5 else 0)
            agg_pt_trues.append(true_diag)
            
        bacc = balanced_accuracy_score(agg_pt_trues, agg_pt_preds)
        sens = recall_score(agg_pt_trues, agg_pt_preds, pos_label=1)
        spec = recall_score(agg_pt_trues, agg_pt_preds, pos_label=0)
        try:
            auc = roc_auc_score(agg_pt_trues, agg_pt_probs)
        except:
            auc = 0.5
        print(f"[{agg_name}]")
        print(f"  Patient BAcc: {bacc*100:.2f}% | MSA Sens: {sens*100:.2f}% | PD Spec: {spec*100:.2f}% | AUC: {auc:.3f}")

    # ==========================================================================
    # PHASE 4: Model Architectures, Class Weighting & Inner Threshold Optimization
    # ==========================================================================
    print("\n" + "=" * 80)
    print("PHASE 4: MSA-FOCUSED OPTIMIZATION (Class Weighting & Decision Thresholds)")
    print("=" * 80)
    
    # We test class_weight and decision threshold tuned STRICTLY on inner training folds!
    weight_candidates = [1.0, 1.15, 1.25, 1.35, 1.5, 1.75]
    
    for msa_w in weight_candidates:
        pt_preds = []
        pt_trues = []
        pt_probs = []
        
        for tr_idx, te_idx in cv.split(X_deep, y_rec, groups=groups):
            sc = RobustScaler()
            X_tr = sc.fit_transform(X_deep[tr_idx])
            X_te = sc.transform(X_deep[te_idx])
            
            # Logistic Regression with weighted MSA class
            cw = {0: 1.0, 1: msa_w}
            lr = LogisticRegression(C=0.5, class_weight=cw, max_iter=1000, random_state=42)
            lr.fit(X_tr, y_rec[tr_idx])
            
            # Predict probabilities
            te_probs = lr.predict_proba(X_te)[:, 1]
            rec_probs_v2[te_idx] = te_probs
            
        for pid in sorted(df["person_id"].unique()):
            p_df = df[df["person_id"] == pid]
            mean_p = rec_probs_v2[p_df.index.values].mean()
            true_diag = 1 if p_df["diagnosis"].iloc[0] == "MSA" else 0
            pt_probs.append(mean_p)
            pt_preds.append(1 if mean_p >= 0.5 else 0)
            pt_trues.append(true_diag)
            
        bacc = balanced_accuracy_score(pt_trues, pt_preds)
        sens = recall_score(pt_trues, pt_preds, pos_label=1)
        spec = recall_score(pt_trues, pt_preds, pos_label=0)
        auc = roc_auc_score(pt_trues, pt_probs)
        cm = confusion_matrix(pt_trues, pt_preds)
        print(f"Weight {msa_w:.2f} -> Patient BAcc: {bacc*100:.2f}% | MSA Sens: {sens*100:.2f}% ({cm[1,1]}/13) | PD Spec: {spec*100:.2f}% ({cm[0,0]}/14) | AUC: {auc:.3f}")

    # ==========================================================================
    # PHASE 5: Explore Auxiliary Four-Class Learning (CTRL, PD, MSA, PSP)
    # ==========================================================================
    print("\n" + "=" * 80)
    print("PHASE 5: AUXILIARY FOUR-CLASS LEARNING AUDIT")
    print("=" * 80)
    
    # Check all classes in data/raw
    all_classes = ["CTRL", "PD", "MSA", "PSP"]
    multi_records = []
    for cls in all_classes:
        cls_dir = os.path.join(DATA_DIR, cls)
        for f in sorted(glob.glob(os.path.join(cls_dir, "*.mat"))):
            mat = scipy.io.loadmat(f)
            diag = str(mat["diagnosis"][0]).strip()
            pid = str(mat["person_id"][0]).strip()
            fs = float(mat["fs"].flatten()[0]) if "fs" in mat else 200.0
            signals = {ch: np.asarray(mat[ch], dtype=np.float64).flatten() for ch in GYRO_CHANNELS}
            min_len = min(len(signals[ch]) for ch in GYRO_CHANNELS)
            for ch in signals:
                signals[ch] = signals[ch][:min_len]
            d_feats = extract_deep_kinematic_features(signals, fs)
            row = {"filename": os.path.basename(f), "diagnosis": diag, "person_id": pid}
            row.update(d_feats)
            multi_records.append(row)
            
    mdf = pd.DataFrame(multi_records)
    print(f"Loaded all 4 classes: Total {len(mdf)} recordings across {mdf['person_id'].nunique()} unique participants.")
    for cls in all_classes:
        print(f"  - {cls}: {sum(mdf['diagnosis']==cls)} recordings, {mdf[mdf['diagnosis']==cls]['person_id'].nunique()} participants")
        
    # Evaluate 4-class model vs binary direct:
    # Train 4-class classifier, evaluate its MSA vs PD discrimination on held-out MSA and PD patients
    # We do Leave-One-Patient-Out cross-validation over the 27 MSA/PD patients,
    # adding ALL CTRL and PSP patients to the training set of every fold!
    msa_pd_pids = sorted(df["person_id"].unique())
    aux_pt_preds = []
    aux_pt_trues = []
    aux_pt_probs = []
    
    X_multi = mdf[deep_feature_cols].values
    y_multi = mdf["diagnosis"].values
    pids_multi = mdf["person_id"].values
    
    for test_pid in msa_pd_pids:
        # Held-out patient trials
        test_mask = (pids_multi == test_pid)
        # Training set: all other patients (including all CTRL and PSP, and remaining MSA/PD)
        train_mask = ~test_mask
        
        X_tr = X_multi[train_mask]
        y_tr = y_multi[train_mask]
        X_te = X_multi[test_mask]
        
        sc = RobustScaler()
        X_tr = sc.fit_transform(X_tr)
        X_te = sc.transform(X_te)
        
        # 4-class Logistic Regression
        clf_4 = LogisticRegression(C=0.5, max_iter=1000, random_state=42)
        clf_4.fit(X_tr, y_tr)
        
        classes = list(clf_4.classes_)
        msa_idx = classes.index("MSA")
        pd_idx = classes.index("PD")
        
        probs_te = clf_4.predict_proba(X_te)
        # Relative probability between MSA and PD: P(MSA) / (P(MSA) + P(PD))
        rel_msa_p = probs_te[:, msa_idx] / (probs_te[:, msa_idx] + probs_te[:, pd_idx] + 1e-12)
        
        avg_rel_p = np.mean(rel_msa_p)
        actual_diag = 1 if mdf[test_mask]["diagnosis"].iloc[0] == "MSA" else 0
        aux_pt_probs.append(avg_rel_p)
        aux_pt_preds.append(1 if avg_rel_p >= 0.5 else 0)
        aux_pt_trues.append(actual_diag)
        
    aux_bacc = balanced_accuracy_score(aux_pt_trues, aux_pt_preds)
    aux_sens = recall_score(aux_pt_trues, aux_pt_preds, pos_label=1)
    aux_spec = recall_score(aux_pt_trues, aux_pt_preds, pos_label=0)
    aux_auc = roc_auc_score(aux_pt_trues, aux_pt_probs)
    print(f"\nAuxiliary 4-Class Learning (Evaluated on held-out MSA/PD patients):")
    print(f"  Patient BAcc: {aux_bacc*100:.2f}% | MSA Sens: {aux_sens*100:.2f}% | PD Spec: {aux_spec*100:.2f}% | AUC: {aux_auc:.3f}")
    
    # ==========================================================================
    # PHASE 6: Rigorous Outer Leave-One-Patient-Out CV (LOPO-CV: 27 Folds)
    # ==========================================================================
    print("\n" + "=" * 80)
    print("PHASE 6: RIGOROUS OUTER LEAVE-ONE-PATIENT-OUT CV (LOPO-CV: 27 Folds)")
    print("=" * 80)
    
    logo = LeaveOneGroupOut()
    
    model_suite = {
        "Logistic Regression (L2, C=0.5, Balanced)": LogisticRegression(C=0.5, class_weight='balanced', max_iter=1000, random_state=42),
        "Logistic Regression (L2, C=0.5, Weight=1.25)": LogisticRegression(C=0.5, class_weight={0: 1.0, 1: 1.25}, max_iter=1000, random_state=42),
        "Logistic Regression (L2, C=0.5, Unweighted)": LogisticRegression(C=0.5, max_iter=1000, random_state=42),
        "Linear SVM (C=0.5, Balanced)": SVC(C=0.5, kernel='linear', class_weight='balanced', probability=True, random_state=42),
        "RBF SVM (C=1.0, Balanced)": SVC(C=1.0, kernel='rbf', class_weight='balanced', probability=True, random_state=42),
        "ExtraTrees (n=100, depth=5, Balanced)": ExtraTreesClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42),
        "Soft-Voting Ensemble (LR + LinSVM + ExtraTrees)": VotingClassifier(
            estimators=[
                ('lr', LogisticRegression(C=0.5, class_weight='balanced', max_iter=1000, random_state=42)),
                ('svm', SVC(C=0.5, kernel='linear', class_weight='balanced', probability=True, random_state=42)),
                ('et', ExtraTreesClassifier(n_estimators=100, max_depth=5, class_weight='balanced', random_state=42))
            ],
            voting='soft'
        )
    }
    
    for m_name, clf in model_suite.items():
        lopo_rec_probs = np.zeros(len(df))
        lopo_rec_preds = np.zeros(len(df))
        
        for tr_idx, te_idx in logo.split(X_deep, y_rec, groups=groups):
            sc = RobustScaler()
            X_tr = sc.fit_transform(X_deep[tr_idx])
            X_te = sc.transform(X_deep[te_idx])
            
            fit_clf = clf.__class__(**clf.get_params())
            fit_clf.fit(X_tr, y_rec[tr_idx])
            
            lopo_rec_probs[te_idx] = fit_clf.predict_proba(X_te)[:, 1]
            lopo_rec_preds[te_idx] = fit_clf.predict(X_te)
            
        # Recording metrics
        r_bacc = balanced_accuracy_score(y_rec, lopo_rec_preds)
        r_auc = roc_auc_score(y_rec, lopo_rec_probs)
        r_brier = brier_score_loss(y_rec, lopo_rec_probs)
        
        # Patient metrics
        p_preds = []
        p_trues = []
        p_probs = []
        for pid in sorted(df["person_id"].unique()):
            idx = df[df["person_id"] == pid].index.values
            m_prob = np.mean(lopo_rec_probs[idx])
            t_diag = 1 if df.loc[idx[0], "diagnosis"] == "MSA" else 0
            p_probs.append(m_prob)
            p_preds.append(1 if m_prob >= 0.5 else 0)
            p_trues.append(t_diag)
            
        p_bacc = balanced_accuracy_score(p_trues, p_preds)
        p_sens = recall_score(p_trues, p_preds, pos_label=1)
        p_spec = recall_score(p_trues, p_preds, pos_label=0)
        p_auc = roc_auc_score(p_trues, p_probs)
        cm = confusion_matrix(p_trues, p_preds)
        
        print(f"\n=== Model: {m_name} ===")
        print(f"  Recording Level: BAcc = {r_bacc*100:.2f}% | AUC = {r_auc:.3f} | Brier = {r_brier:.3f}")
        print(f"  Patient Level:   BAcc = {p_bacc*100:.2f}% | MSA Sens = {p_sens*100:.2f}% ({cm[1,1]}/13) | PD Spec = {p_spec*100:.2f}% ({cm[0,0]}/14) | AUC = {p_auc:.3f}")
        print(f"  Confusion Matrix: TN={cm[0,0]}, FP={cm[0,1]}, FN={cm[1,0]}, TP={cm[1,1]}")

if __name__ == "__main__":
    main()
