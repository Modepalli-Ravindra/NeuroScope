import os
import glob
import json
import joblib
import scipy.io
import scipy.signal
import scipy.stats
import numpy as np
import pandas as pd
import shap
from typing import Dict, List, Tuple, Any

from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier, ExtraTreesClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, recall_score,
    precision_score, f1_score, roc_auc_score, confusion_matrix, brier_score_loss
)

import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from advanced_optimization_study import extract_deep_kinematic_features, DATA_DIR, GYRO_CHANNELS
SAVED_MODELS_DIR = os.path.join(PROJECT_ROOT, "backend", "saved_models")

def build_and_save_v2():
    print("Extracting 53 deep kinematic features from all 140 recordings...")
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

    label_map = {"PD": 0, "MSA": 1}
    inv_label_map = {0: "PD", 1: "MSA"}
    y = df["diagnosis"].map(label_map).values
    groups = df["person_id"].values
    X = df[feature_cols].values

    sgkf = StratifiedGroupKFold(n_splits=5)

    models_to_run = {
        "Optimized Logistic Regression v2 (C=0.5, RobustScaler)": (
            RobustScaler(),
            LogisticRegression(C=0.5, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
        ),
        "Linear SVM (C=0.5, RobustScaler)": (
            RobustScaler(),
            SVC(C=0.5, kernel='linear', probability=True, random_state=42)
        ),
        "Baseline Logistic Regression (C=1.0, StandardScaler)": (
            StandardScaler(),
            LogisticRegression(C=1.0, max_iter=1000, random_state=42)
        ),
        "Baseline Random Forest (Trees=100, Depth=6)": (
            StandardScaler(),
            RandomForestClassifier(n_estimators=100, max_depth=6, min_samples_leaf=2, random_state=42)
        ),
        "Baseline KNN (k=5, Distance Weighted)": (
            StandardScaler(),
            KNeighborsClassifier(n_neighbors=5, weights="distance")
        )
    }

    eval_json = {}

    for m_name, (scaler_inst, clf) in models_to_run.items():
        rec_y_true, rec_y_pred, rec_y_prob = [], [], []
        pat_data = {}
        fold_records = []

        for fold_idx, (train_idx, test_idx) in enumerate(sgkf.split(X, y, groups)):
            sc = type(scaler_inst)()
            X_tr = sc.fit_transform(X[train_idx])
            X_te = sc.transform(X[test_idx])
            y_tr = y[train_idx]
            y_te = y[test_idx]
            te_groups = groups[test_idx]

            clf_fold = type(clf)(**clf.get_params())
            clf_fold.fit(X_tr, y_tr)

            preds = clf_fold.predict(X_te)
            probs = clf_fold.predict_proba(X_te)[:, 1] if hasattr(clf_fold, "predict_proba") else preds.astype(float)

            rec_y_true.extend(y_te)
            rec_y_pred.extend(preds)
            rec_y_prob.extend(probs)

            for pid, y_val, p_val in zip(te_groups, y_te, probs):
                if pid not in pat_data:
                    pat_data[pid] = {"y_true": y_val, "probs": []}
                pat_data[pid]["probs"].append(p_val)

            f_bacc = balanced_accuracy_score(y_te, preds)
            try:
                f_auc = roc_auc_score(y_te, probs)
            except Exception:
                f_auc = f_bacc
            fold_records.append({
                "fold": fold_idx + 1,
                "balanced_accuracy": float(f_bacc),
                "roc_auc": float(f_auc)
            })

        # Recording metrics
        rec_bacc = balanced_accuracy_score(rec_y_true, rec_y_pred)
        rec_acc = accuracy_score(rec_y_true, rec_y_pred)
        rec_sens = recall_score(rec_y_true, rec_y_pred, pos_label=1)
        rec_spec = recall_score(rec_y_true, rec_y_pred, pos_label=0)
        rec_f1 = f1_score(rec_y_true, rec_y_pred, average="weighted")
        rec_auc = roc_auc_score(rec_y_true, rec_y_prob)
        rec_brier = brier_score_loss(rec_y_true, rec_y_prob)
        tn, fp, fn, tp = confusion_matrix(rec_y_true, rec_y_pred).ravel()

        # Patient aggregation
        pat_pids = list(pat_data.keys())
        pat_y_true = [pat_data[p]["y_true"] for p in pat_pids]
        pat_y_prob = [float(np.mean(pat_data[p]["probs"])) for p in pat_pids]
        pat_y_pred = [1 if p >= 0.5 else 0 for p in pat_y_prob]
        pat_bacc = balanced_accuracy_score(pat_y_true, pat_y_pred)
        pat_acc = accuracy_score(pat_y_true, pat_y_pred)
        pat_sens = recall_score(pat_y_true, pat_y_pred, pos_label=1)
        pat_spec = recall_score(pat_y_true, pat_y_pred, pos_label=0)
        pat_auc = roc_auc_score(pat_y_true, pat_y_prob)
        p_tn, p_fp, p_fn, p_tp = confusion_matrix(pat_y_true, pat_y_pred).ravel()

        bacc_fold_vals = [f["balanced_accuracy"] for f in fold_records]
        auc_fold_vals = [f["roc_auc"] for f in fold_records]

        eval_json[m_name] = {
            "pooled": {
                "accuracy": round(float(rec_acc), 4),
                "balanced_accuracy": round(float(rec_bacc), 4),
                "sensitivity_msa": round(float(rec_sens), 4),
                "specificity_pd": round(float(rec_spec), 4),
                "f1_score": round(float(rec_f1), 4),
                "roc_auc": round(float(rec_auc), 4),
                "brier_score": round(float(rec_brier), 4),
                "confusion_matrix": {
                    "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
                    "matrix": [[int(tn), int(fp)], [int(fn), int(tp)]]
                }
            },
            "patient_level": {
                "accuracy": round(float(pat_acc), 4),
                "balanced_accuracy": round(float(pat_bacc), 4),
                "sensitivity_msa": round(float(pat_sens), 4),
                "specificity_pd": round(float(pat_spec), 4),
                "roc_auc": round(float(pat_auc), 4),
                "cohort_size": len(pat_pids),
                "confusion_matrix": {
                    "tn": int(p_tn), "fp": int(p_fp), "fn": int(p_fn), "tp": int(p_tp),
                    "matrix": [[int(p_tn), int(p_fp)], [int(p_fn), int(p_tp)]]
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
        print(f"Evaluated {m_name}: Rec BAcc={rec_bacc*100:.2f}%, Pat BAcc={pat_bacc*100:.2f}% (Pat AUC={pat_auc:.3f})")

    # Fit final model on all data
    final_scaler = RobustScaler()
    X_scaled = final_scaler.fit_transform(X)
    final_model = LogisticRegression(C=0.5, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
    final_model.fit(X_scaled, y)

    # Save model v2 artifact
    model_v2_path = os.path.join(SAVED_MODELS_DIR, "neuroscope_model_v2.joblib")
    joblib.dump({
        "model": final_model,
        "scaler": final_scaler,
        "feature_cols": feature_cols,
        "label_mapping": label_map,
        "inv_label_mapping": inv_label_map,
        "expected_value": float(final_model.intercept_[0]),
        "model_type": "LogisticRegression_v2_RobustScaler_53feats",
        "evaluation_metrics": eval_json["Optimized Logistic Regression v2 (C=0.5, RobustScaler)"]
    }, model_v2_path)
    print(f"Saved optimized model v2 to: {model_v2_path}")

    # Save feature schema
    with open(os.path.join(SAVED_MODELS_DIR, "feature_schema_v2.json"), "w") as f:
        json.dump({
            "num_features": len(feature_cols),
            "features": feature_cols,
            "meta_cols": meta_cols
        }, f, indent=2)

    # Save updated evaluation_results.json
    with open(os.path.join(SAVED_MODELS_DIR, "evaluation_results.json"), "w") as f:
        json.dump(eval_json, f, indent=2)
    print("Saved evaluation_results.json successfully.")

if __name__ == "__main__":
    build_and_save_v2()
