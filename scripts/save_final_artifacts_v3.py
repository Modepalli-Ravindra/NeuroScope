import os
import sys
import glob
import json
import joblib
import scipy.io
import scipy.signal
import scipy.stats
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

from sklearn.preprocessing import RobustScaler, StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import LeaveOneGroupOut, StratifiedGroupKFold
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, recall_score,
    precision_score, f1_score, roc_auc_score, confusion_matrix, brier_score_loss
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
GYRO_CHANNELS = ["gyroThumbX", "gyroThumbY", "gyroThumbZ", "gyroIndexX", "gyroIndexY", "gyroIndexZ"]
SAVED_MODELS_DIR = os.path.join(PROJECT_ROOT, "backend", "saved_models")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from advanced_optimization_study import extract_deep_kinematic_features
from v3_optimization_study import extract_paper_six_features

def build_and_save_v3():
    print("=" * 80)
    print("SAVING NEUROSCOPE V3 ARTIFACTS (59 COMBINED FEATURES, LOGISTIC REGRESSION)")
    print("=" * 80)
    
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
    print(f"Total trials: {len(df)} across {df['person_id'].nunique()} participants.")
    
    paper_cols = [c for c in df.columns if c.startswith("paper_feat")]
    deep_cols = [c for c in df.columns if c not in ["filename", "diagnosis", "person_id", "trial_id", "duration_sec", "fs"] and not c.startswith("paper_feat")]
    feature_cols = paper_cols + deep_cols
    print(f"Total features in v3 schema: {len(feature_cols)} ({len(paper_cols)} paper + {len(deep_cols)} deep)")
    
    X = df[feature_cols].values
    y = (df["diagnosis"] == "MSA").astype(int).values
    groups = df["person_id"].values
    
    # 1. Out-of-Fold Evaluation under LOPO-CV (27 folds)
    logo = LeaveOneGroupOut()
    oof_probs = np.zeros(len(df))
    oof_preds = np.zeros(len(df))
    
    for tr_idx, te_idx in logo.split(X, y, groups=groups):
        scaler = RobustScaler()
        X_tr = scaler.fit_transform(X[tr_idx])
        X_te = scaler.transform(X[te_idx])
        
        clf = LogisticRegression(C=0.5, class_weight='balanced', max_iter=1000, random_state=42)
        clf.fit(X_tr, y[tr_idx])
        
        oof_probs[te_idx] = clf.predict_proba(X_te)[:, 1]
        oof_preds[te_idx] = clf.predict(X_te)
        
    # Recording metrics
    rec_bacc = float(balanced_accuracy_score(y, oof_preds))
    rec_sens = float(recall_score(y, oof_preds, pos_label=1))
    rec_spec = float(recall_score(y, oof_preds, pos_label=0))
    rec_auc = float(roc_auc_score(y, oof_probs))
    rec_brier = float(brier_score_loss(y, oof_probs))
    rec_cm = confusion_matrix(y, oof_preds)
    
    # Patient metrics (mean trial probability aggregation)
    pt_probs = []
    pt_preds = []
    pt_trues = []
    pt_ids = sorted(df["person_id"].unique())
    
    for pid in pt_ids:
        idx = df[df["person_id"] == pid].index.values
        avg_p = float(np.mean(oof_probs[idx]))
        t_diag = 1 if df.loc[idx[0], "diagnosis"] == "MSA" else 0
        pt_probs.append(avg_p)
        pt_preds.append(1 if avg_p >= 0.5 else 0)
        pt_trues.append(t_diag)
        
    pt_bacc = float(balanced_accuracy_score(pt_trues, pt_preds))
    pt_sens = float(recall_score(pt_trues, pt_preds, pos_label=1))
    pt_spec = float(recall_score(pt_trues, pt_preds, pos_label=0))
    pt_auc = float(roc_auc_score(pt_trues, pt_probs))
    pt_acc = float(accuracy_score(pt_trues, pt_preds))
    pt_cm = confusion_matrix(pt_trues, pt_preds)
    
    print("\n--- Out-of-Fold Evaluation Metrics (v3 LOPO-CV) ---")
    print(f"Recording Level: Balanced Acc = {rec_bacc*100:.2f}% | Sensitivity = {rec_sens*100:.2f}% | Specificity = {rec_spec*100:.2f}% | AUC = {rec_auc:.3f}")
    print(f"Patient Level:   Balanced Acc = {pt_bacc*100:.2f}% | Sensitivity = {pt_sens*100:.2f}% ({pt_cm[1,1]}/13) | Specificity = {pt_spec*100:.2f}% ({pt_cm[0,0]}/14) | AUC = {pt_auc:.3f}")
    print(f"Patient CM: TN={pt_cm[0,0]}, FP={pt_cm[0,1]}, FN={pt_cm[1,0]}, TP={pt_cm[1,1]}")
    
    # 2. Fit final production model on full cohort
    final_scaler = RobustScaler()
    X_scaled = final_scaler.fit_transform(X)
    
    final_model = LogisticRegression(C=0.5, class_weight='balanced', max_iter=1000, random_state=42)
    final_model.fit(X_scaled, y)
    
    # 3. Save model bundle
    bundle_v3 = {
        "model": final_model,
        "scaler": final_scaler,
        "feature_cols": feature_cols,
        "classes": ["PD", "MSA"],
        "model_type": "LogisticRegression_v3",
        "description": "NeuroScope v3 Combined 59-Feature Classifier (6 Heliyon + 53 Deep Kinematic, C=0.5, Balanced, RobustScaler)",
        "metrics": {
            "patient_level": {
                "balanced_accuracy": pt_bacc,
                "sensitivity_msa": pt_sens,
                "specificity_pd": pt_spec,
                "overall_accuracy": pt_acc,
                "roc_auc": pt_auc,
                "total_patients": len(pt_ids),
                "confusion_matrix": {
                    "tn": int(pt_cm[0,0]),
                    "fp": int(pt_cm[0,1]),
                    "fn": int(pt_cm[1,0]),
                    "tp": int(pt_cm[1,1])
                }
            },
            "recording_level": {
                "balanced_accuracy": rec_bacc,
                "sensitivity_msa": rec_sens,
                "specificity_pd": rec_spec,
                "roc_auc": rec_auc,
                "brier_score": rec_brier,
                "total_recordings": len(df),
                "confusion_matrix": {
                    "tn": int(rec_cm[0,0]),
                    "fp": int(rec_cm[0,1]),
                    "fn": int(rec_cm[1,0]),
                    "tp": int(rec_cm[1,1])
                }
            }
        }
    }
    
    os.makedirs(SAVED_MODELS_DIR, exist_ok=True)
    v3_path = os.path.join(SAVED_MODELS_DIR, "neuroscope_model_v3.joblib")
    joblib.dump(bundle_v3, v3_path)
    print(f"Saved v3 model bundle to: {v3_path}")
    
    # 4. Save feature schema v3
    schema_v3_path = os.path.join(SAVED_MODELS_DIR, "feature_schema_v3.json")
    with open(schema_v3_path, "w") as f:
        json.dump({
            "features": feature_cols,
            "feature_count": len(feature_cols),
            "paper_features": paper_cols,
            "deep_features": deep_cols,
            "model_type": "LogisticRegression_v3",
            "scaler": "RobustScaler"
        }, f, indent=2)
    print(f"Saved feature schema v3 to: {schema_v3_path}")
    
    # 5. Update evaluation_results.json
    eval_json_path = os.path.join(SAVED_MODELS_DIR, "evaluation_results.json")
    existing_eval = {}
    if os.path.exists(eval_json_path):
        with open(eval_json_path, "r") as f:
            existing_eval = json.load(f)
            
    existing_eval["primary_model"] = "Optimized Logistic Regression v3 (Selected)"
    existing_eval["v3_metrics"] = bundle_v3["metrics"]["recording_level"]
    existing_eval["v3_patient_metrics"] = bundle_v3["metrics"]["patient_level"]
    
    existing_eval["Optimized Logistic Regression v3 (Selected)"] = {
        "pooled": {
            "accuracy": float(accuracy_score(y, oof_preds)),
            "balanced_accuracy": rec_bacc,
            "sensitivity_msa": rec_sens,
            "specificity_pd": rec_spec,
            "f1_score": float(f1_score(y, oof_preds, pos_label=1)),
            "roc_auc": rec_auc,
            "brier_score": rec_brier,
            "confusion_matrix": {
                "tn": int(rec_cm[0,0]),
                "fp": int(rec_cm[0,1]),
                "fn": int(rec_cm[1,0]),
                "tp": int(rec_cm[1,1]),
                "matrix": [[int(rec_cm[0,0]), int(rec_cm[0,1])], [int(rec_cm[1,0]), int(rec_cm[1,1])]]
            }
        },
        "patient_level": {
            "accuracy": pt_acc,
            "balanced_accuracy": pt_bacc,
            "sensitivity_msa": pt_sens,
            "specificity_pd": pt_spec,
            "roc_auc": pt_auc,
            "cohort_size": len(pt_ids),
            "confusion_matrix": {
                "tn": int(pt_cm[0,0]),
                "fp": int(pt_cm[0,1]),
                "fn": int(pt_cm[1,0]),
                "tp": int(pt_cm[1,1]),
                "matrix": [[int(pt_cm[0,0]), int(pt_cm[0,1])], [int(pt_cm[1,0]), int(pt_cm[1,1])]]
            }
        }
    }
    
    existing_eval["Heliyon 2023 Paper Baseline (6 Features, kNN k=5)"] = {
        "pooled": {
            "accuracy": 0.85,
            "balanced_accuracy": 0.8489,
            "sensitivity_msa": 0.9028,
            "specificity_pd": 0.7941,
            "f1_score": 0.8609,
            "roc_auc": 0.896,
            "brier_score": 0.123,
            "confusion_matrix": {
                "tn": 54, "fp": 14, "fn": 7, "tp": 65,
                "matrix": [[54, 14], [7, 65]]
            }
        },
        "patient_level": {
            "accuracy": 0.8889,
            "balanced_accuracy": 0.8929,
            "sensitivity_msa": 1.0000,
            "specificity_pd": 0.7857,
            "roc_auc": 0.909,
            "cohort_size": 27,
            "confusion_matrix": {
                "tn": 11, "fp": 3, "fn": 0, "tp": 13,
                "matrix": [[11, 3], [0, 13]]
            }
        }
    }
    
    with open(eval_json_path, "w") as f:
        json.dump(existing_eval, f, indent=2)
    print(f"Updated evaluation results JSON at: {eval_json_path}")
    print("\nSUCCESSFULLY SAVED NEUROSCOPE V3 ARTIFACTS!")

if __name__ == "__main__":
    build_and_save_v3()
