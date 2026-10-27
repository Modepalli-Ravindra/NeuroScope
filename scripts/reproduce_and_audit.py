import os
import glob
import json
import hashlib
import scipy.io
import numpy as np
import pandas as pd
from collections import defaultdict
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, recall_score,
    precision_score, f1_score, roc_auc_score, confusion_matrix, brier_score_loss
)
from sklearn.calibration import calibration_curve
import shap

from backend.ml.dataset_loader import load_single_mat, build_dataset_dataframe
from backend.ml.feature_extractor import GYRO_CHANNELS

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")

def phase2_audit_dataset():
    print("=" * 60)
    print("PHASE 2: DATASET AUTHENTICITY, INTEGRITY & LEAKAGE AUDIT")
    print("=" * 60)
    
    classes = ["MSA", "PD", "CTRL", "PSP"]
    dataset_report = {}
    total_parsed = 0
    total_failed = 0
    
    for c in classes:
        c_dir = os.path.join(DATA_DIR, c)
        files = sorted(glob.glob(os.path.join(c_dir, "*.mat")))
        subjects = defaultdict(list)
        file_stats = []
        corrupted = []
        
        for f in files:
            try:
                # Compute SHA256
                with open(f, "rb") as fp:
                    sha256 = hashlib.sha256(fp.read()).hexdigest()
                
                mat = scipy.io.loadmat(f)
                diag = str(mat["diagnosis"][0]).strip() if "diagnosis" in mat else "MISSING"
                pid = str(mat["person_id"][0]).strip() if "person_id" in mat else "MISSING"
                tid = str(mat["trial_id"][0]).strip() if "trial_id" in mat else "MISSING"
                fs = float(mat["fs"].flatten()[0]) if "fs" in mat else -1.0
                
                # Check 6 gyro channels
                missing_channels = [ch for ch in GYRO_CHANNELS if ch not in mat]
                if missing_channels:
                    corrupted.append((f, f"Missing channels: {missing_channels}"))
                    continue
                
                lengths = [len(np.asarray(mat[ch]).flatten()) for ch in GYRO_CHANNELS]
                min_len = min(lengths)
                duration = min_len / fs if fs > 0 else 0
                
                subjects[pid].append((tid, duration, sha256[:8]))
                file_stats.append({
                    "filename": os.path.basename(f),
                    "diagnosis": diag,
                    "person_id": pid,
                    "trial_id": tid,
                    "fs": fs,
                    "duration": duration,
                    "samples": min_len,
                    "sha256": sha256
                })
                total_parsed += 1
            except Exception as e:
                corrupted.append((f, str(e)))
                total_failed += 1
                
        dataset_report[c] = {
            "file_count": len(files),
            "valid_count": len(file_stats),
            "corrupted_count": len(corrupted),
            "unique_subjects": len(subjects),
            "subjects": {k: len(v) for k, v in sorted(subjects.items())},
            "trials_per_subj": [len(v) for v in subjects.values()],
            "avg_trials": float(np.mean([len(v) for v in subjects.values()])) if subjects else 0,
            "corrupted_details": corrupted
        }
        print(f"Class {c:4s}: Files={len(files):2d}, Unique Subjects={len(subjects):2d}, Avg Trials={dataset_report[c]['avg_trials']:.1f}, Corrupted={len(corrupted)}")
        
    print(f"\nTotal Dataset Files: {total_parsed + total_failed} (Valid: {total_parsed}, Failed: {total_failed})")
    return dataset_report

def phase3_audit_models_and_metrics():
    print("\n" + "=" * 60)
    print("PHASE 3: INDEPENDENT MODEL & METRICS REPRODUCTION")
    print("=" * 60)
    
    df, stats = build_dataset_dataframe(DATA_DIR, ["MSA", "PD"])
    meta_cols = ["filename", "diagnosis", "person_id", "trial_id", "duration_sec", "fs"]
    feature_cols = [c for c in df.columns if c not in meta_cols]
    
    X = df[feature_cols].values
    label_map = {"PD": 0, "MSA": 1}
    y = df["diagnosis"].map(label_map).values
    groups = df["person_id"].values
    
    print(f"Primary Task (MSA vs PD): N={len(df)} recordings, D={len(feature_cols)} features")
    print(f"Class counts: PD(0)={np.sum(y == 0)}, MSA(1)={np.sum(y == 1)}")
    print(f"Unique groups (patients): {len(np.unique(groups))}")
    
    n_splits = 5
    sgkf = StratifiedGroupKFold(n_splits=n_splits)
    
    models = {
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, min_samples_leaf=2),
        "Logistic Regression (C=0.5)": LogisticRegression(max_iter=1000, random_state=42, C=0.5),
        "Logistic Regression (C=1.0)": LogisticRegression(max_iter=1000, random_state=42, C=1.0),
        "KNN (k=5, distance)": KNeighborsClassifier(n_neighbors=5, weights="distance")
    }
    
    reproduction_results = {}
    
    for name, model in models.items():
        pooled_y_true = []
        pooled_y_pred = []
        pooled_y_prob = []
        
        fold_metrics = defaultdict(list)
        
        for fold, (train_idx, test_idx) in enumerate(sgkf.split(X, y, groups)):
            # Check subject isolation strictly
            tr_groups = set(groups[train_idx])
            te_groups = set(groups[test_idx])
            leak = tr_groups.intersection(te_groups)
            assert len(leak) == 0, f"LEAKAGE DETECTED in fold {fold}: {leak}"
            
            # FIT PREPROCESSING ONLY ON TRAIN
            scaler = StandardScaler()
            X_tr = scaler.fit_transform(X[train_idx])
            X_te = scaler.transform(X[test_idx])
            y_tr = y[train_idx]
            y_te = y[test_idx]
            
            model.fit(X_tr, y_tr)
            preds = model.predict(X_te)
            probs = model.predict_proba(X_te)[:, 1] if hasattr(model, "predict_proba") else preds.astype(float)
            
            # Store pooled
            pooled_y_true.extend(y_te)
            pooled_y_pred.extend(preds)
            pooled_y_prob.extend(probs)
            
            # Fold-level metrics
            f_acc = accuracy_score(y_te, preds)
            f_bacc = balanced_accuracy_score(y_te, preds)
            f_rec_msa = recall_score(y_te, preds, pos_label=1, zero_division=0)
            f_rec_pd = recall_score(y_te, preds, pos_label=0, zero_division=0)
            f_f1 = f1_score(y_te, preds, average="weighted")
            try:
                f_auc = roc_auc_score(y_te, probs)
            except Exception:
                f_auc = 0.5
                
            fold_metrics["acc"].append(f_acc)
            fold_metrics["bacc"].append(f_bacc)
            fold_metrics["rec_msa"].append(f_rec_msa)
            fold_metrics["rec_pd"].append(f_rec_pd)
            fold_metrics["f1"].append(f_f1)
            fold_metrics["auc"].append(f_auc)
            
        pooled_y_true = np.array(pooled_y_true)
        pooled_y_pred = np.array(pooled_y_pred)
        pooled_y_prob = np.array(pooled_y_prob)
        
        cm = confusion_matrix(pooled_y_true, pooled_y_pred)
        tn, fp, fn, tp = cm.ravel()
        
        pooled_acc = accuracy_score(pooled_y_true, pooled_y_pred)
        pooled_bacc = balanced_accuracy_score(pooled_y_true, pooled_y_pred)
        pooled_sens = tp / (tp + fn)
        pooled_spec = tn / (tn + fp)
        pooled_f1 = f1_score(pooled_y_true, pooled_y_pred, average="weighted")
        pooled_auc = roc_auc_score(pooled_y_true, pooled_y_prob)
        brier = brier_score_loss(pooled_y_true, pooled_y_prob)
        
        reproduction_results[name] = {
            "pooled": {
                "accuracy": round(float(pooled_acc), 4),
                "balanced_accuracy": round(float(pooled_bacc), 4),
                "sensitivity_msa": round(float(pooled_sens), 4),
                "specificity_pd": round(float(pooled_spec), 4),
                "f1_weighted": round(float(pooled_f1), 4),
                "roc_auc": round(float(pooled_auc), 4),
                "brier_score": round(float(brier), 4),
                "confusion_matrix": {"tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp)}
            },
            "per_fold": {
                "balanced_acc_mean": round(float(np.mean(fold_metrics["bacc"])), 4),
                "balanced_acc_std": round(float(np.std(fold_metrics["bacc"])), 4),
                "roc_auc_mean": round(float(np.mean(fold_metrics["auc"])), 4),
                "roc_auc_std": round(float(np.std(fold_metrics["auc"])), 4),
                "f1_mean": round(float(np.mean(fold_metrics["f1"])), 4),
                "f1_std": round(float(np.std(fold_metrics["f1"])), 4)
            }
        }
        
        print(f"\n>>> Model: {name}")
        print(f"    Pooled Out-of-Fold: Balanced Acc={pooled_bacc*100:.2f}%, Sens={pooled_sens*100:.2f}%, Spec={pooled_spec*100:.2f}%, AUC={pooled_auc:.3f}, Brier={brier:.3f}")
        print(f"    Confusion Matrix: TN={tn}, FP={fp}, FN={fn}, TP={tp}")
        print(f"    Per-Fold (Mean ± Std): Balanced Acc={np.mean(fold_metrics['bacc'])*100:.2f}±{np.std(fold_metrics['bacc'])*100:.2f}%, AUC={np.mean(fold_metrics['auc']):.3f}±{np.std(fold_metrics['auc']):.3f}")

    return reproduction_results, df, feature_cols

def phase4_audit_shap():
    print("\n" + "=" * 60)
    print("PHASE 4: SHAP MATHEMATICAL CONSISTENCY AUDIT")
    print("=" * 60)
    
    rf_artifact_path = os.path.join(PROJECT_ROOT, "backend", "saved_models", "neuroscope_rf_model.joblib")
    rf_data = joblib.load(rf_artifact_path)
    model = rf_data["model"]
    scaler = rf_data["scaler"]
    feature_cols = rf_data["feature_cols"]
    
    # Test on arbitrary authentic sample
    sample_path = os.path.join(DATA_DIR, "MSA", "MSABM23_1.mat")
    mat_parsed = load_single_mat(sample_path)
    from backend.ml.feature_extractor import extract_all_features
    feats = extract_all_features(mat_parsed["signals"], mat_parsed["fs"])
    
    x_raw = np.array([feats[f] for f in feature_cols]).reshape(1, -1)
    x_scaled = scaler.transform(x_raw)
    
    # Random Forest predict proba
    prob = model.predict_proba(x_scaled)[0]
    prob_msa = prob[1]
    
    # TreeSHAP explainer
    explainer = shap.TreeExplainer(model)
    shap_vals = explainer.shap_values(x_scaled)
    expected_val = explainer.expected_value
    
    print(f"TreeExplainer expected_value type: {type(expected_val)}, value: {expected_val}")
    print(f"TreeExplainer shap_values type: {type(shap_vals)}")
    
    # Check reconstruction
    if isinstance(shap_vals, list):
        shap_msa = shap_vals[1][0]
        base_msa = expected_val[1]
        reconstructed = base_msa + np.sum(shap_msa)
    elif isinstance(shap_vals, np.ndarray) and shap_vals.ndim == 3:
        shap_msa = shap_vals[0, :, 1]
        base_msa = expected_val[1] if isinstance(expected_val, (list, np.ndarray)) else expected_val
        reconstructed = base_msa + np.sum(shap_msa)
    else:
        shap_msa = shap_vals[0]
        base_msa = expected_val
        reconstructed = base_msa + np.sum(shap_msa)
        
    diff = abs(reconstructed - prob_msa)
    print(f"Target Probability P(MSA): {prob_msa:.5f}")
    print(f"Base Value + Sum(SHAP):   {reconstructed:.5f}")
    print(f"Absolute Reconstruction Error: {diff:.2e}")
    assert diff < 1e-4, f"SHAP values do not reconstruct model output! Error={diff}"
    print(">>> SHAP reconstruction test PASSED (exact mathematical alignment).")

if __name__ == "__main__":
    import joblib
    ds_report = phase2_audit_dataset()
    results, df, feats = phase3_audit_models_and_metrics()
    phase4_audit_shap()
    
    with open(os.path.join(PROJECT_ROOT, "backend", "saved_models", "reproduction_audit_results.json"), "w") as fp:
        json.dump({
            "dataset_audit": ds_report,
            "reproduced_metrics": results
        }, fp, indent=2)
    print("\nAudit results saved to backend/saved_models/reproduction_audit_results.json")
