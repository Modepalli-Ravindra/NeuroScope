import os
import sys
import glob
import json
import scipy.io
import scipy.signal
import scipy.stats
import numpy as np
import pandas as pd

from sklearn.preprocessing import StandardScaler, RobustScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import SVC
from sklearn.ensemble import ExtraTreesClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.model_selection import LeaveOneGroupOut, StratifiedGroupKFold
from sklearn.metrics import balanced_accuracy_score, recall_score, roc_auc_score, confusion_matrix, brier_score_loss

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "raw")
GYRO_CHANNELS = ["gyroThumbX", "gyroThumbY", "gyroThumbZ", "gyroIndexX", "gyroIndexY", "gyroIndexZ"]

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from advanced_optimization_study import extract_deep_kinematic_features
from v3_optimization_study import extract_paper_six_features

def run_suite():
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
    y_rec = (df["diagnosis"] == "MSA").astype(int).values
    groups = df["person_id"].values
    
    paper_cols = [c for c in df.columns if c.startswith("paper_feat")]
    deep_cols = [c for c in df.columns if c not in ["filename", "diagnosis", "person_id", "trial_id", "duration_sec", "fs"] and not c.startswith("paper_feat")]
    all_cols = paper_cols + deep_cols
    
    logo = LeaveOneGroupOut()
    
    # Candidates to evaluate under LeaveOneGroupOut (27 folds)
    candidates = [
        ("Candidate A: Paper 6 Features + kNN (k=5, inv-dist)", paper_cols, KNeighborsClassifier(n_neighbors=5, weights='distance'), StandardScaler(), "mean"),
        ("Candidate A2: Paper 6 Features + kNN (k=5, inv-dist) + Majority Vote", paper_cols, KNeighborsClassifier(n_neighbors=5, weights='distance'), StandardScaler(), "majority"),
        ("Candidate B: Paper 6 Features + Logistic Regression (C=0.5)", paper_cols, LogisticRegression(C=0.5, max_iter=1000, random_state=42), RobustScaler(), "mean"),
        ("Candidate C: Deep 53 Features + LR (C=0.5, MSA Weight 1.25)", deep_cols, LogisticRegression(C=0.5, class_weight={0: 1.0, 1: 1.25}, max_iter=1000, random_state=42), RobustScaler(), "mean"),
        ("Candidate C2: Deep 53 Features + LR (C=0.5, MSA Weight 1.25) + Median", deep_cols, LogisticRegression(C=0.5, class_weight={0: 1.0, 1: 1.25}, max_iter=1000, random_state=42), RobustScaler(), "median"),
        ("Candidate D: Combined 59 Features + LR (C=0.5, Balanced)", all_cols, LogisticRegression(C=0.5, class_weight='balanced', max_iter=1000, random_state=42), RobustScaler(), "mean"),
        ("Candidate D2: Combined 59 Features + LR (C=0.5, MSA Weight 1.25)", all_cols, LogisticRegression(C=0.5, class_weight={0: 1.0, 1: 1.25}, max_iter=1000, random_state=42), RobustScaler(), "mean"),
        ("Candidate D3: Combined 59 Features + LR (C=0.5, MSA Weight 1.25) + Median", all_cols, LogisticRegression(C=0.5, class_weight={0: 1.0, 1: 1.25}, max_iter=1000, random_state=42), RobustScaler(), "median"),
    ]
    
    print("=" * 80)
    print("LEAVE-ONE-PATIENT-OUT CV (LOPO-CV: 27 FOLDS) CANDIDATE COMPARISON")
    print("=" * 80)
    
    for name, cols, clf, scaler, agg_mode in candidates:
        X = df[cols].values
        rec_probs = np.zeros(len(df))
        rec_preds = np.zeros(len(df))
        
        for tr_idx, te_idx in logo.split(X, y_rec, groups=groups):
            sc = scaler.__class__()
            X_tr = sc.fit_transform(X[tr_idx])
            X_te = sc.transform(X[te_idx])
            
            fit_clf = clf.__class__(**clf.get_params())
            fit_clf.fit(X_tr, y_rec[tr_idx])
            
            probs = fit_clf.predict_proba(X_te)[:, 1]
            rec_probs[te_idx] = probs
            rec_preds[te_idx] = fit_clf.predict(X_te)
            
        r_bacc = balanced_accuracy_score(y_rec, rec_preds)
        r_auc = roc_auc_score(y_rec, rec_probs)
        r_brier = brier_score_loss(y_rec, rec_probs)
        
        # Patient aggregation
        p_preds = []
        p_trues = []
        p_probs = []
        for pid in sorted(df["person_id"].unique()):
            idx = df[df["person_id"] == pid].index.values
            p_trial_probs = rec_probs[idx]
            if agg_mode == "mean":
                agg_p = np.mean(p_trial_probs)
                pred_label = 1 if agg_p >= 0.5 else 0
            elif agg_mode == "median":
                agg_p = np.median(p_trial_probs)
                pred_label = 1 if agg_p >= 0.5 else 0
            elif agg_mode == "majority":
                agg_p = np.mean(p_trial_probs)
                trial_votes = (p_trial_probs >= 0.5).astype(int)
                pred_label = 1 if np.mean(trial_votes) > 0.5 else 0
                
            t_diag = 1 if df.loc[idx[0], "diagnosis"] == "MSA" else 0
            p_probs.append(agg_p)
            p_preds.append(pred_label)
            p_trues.append(t_diag)
            
        p_bacc = balanced_accuracy_score(p_trues, p_preds)
        p_sens = recall_score(p_trues, p_preds, pos_label=1)
        p_spec = recall_score(p_trues, p_preds, pos_label=0)
        p_auc = roc_auc_score(p_trues, p_probs)
        cm = confusion_matrix(p_trues, p_preds)
        
        print(f"\n[{name}]")
        print(f"  Rec Level: BAcc = {r_bacc*100:.2f}% | AUC = {r_auc:.3f} | Brier = {r_brier:.3f}")
        print(f"  Patient Level: BAcc = {p_bacc*100:.2f}% | Sens (MSA) = {p_sens*100:.2f}% ({cm[1,1]}/13) | Spec (PD) = {p_spec*100:.2f}% ({cm[0,0]}/14) | AUC = {p_auc:.3f}")
        print(f"  Patient CM: TN={cm[0,0]}, FP={cm[0,1]}, FN={cm[1,0]}, TP={cm[1,1]}")

if __name__ == "__main__":
    run_suite()
