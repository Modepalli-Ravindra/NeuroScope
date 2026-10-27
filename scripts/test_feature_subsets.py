import os
import glob
import json
import scipy.io
import scipy.signal
import scipy.stats
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any

from sklearn.preprocessing import RobustScaler
from sklearn.feature_selection import SelectKBest, f_classif, mutual_info_classif
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import balanced_accuracy_score, roc_auc_score, confusion_matrix, recall_score

import sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)
from advanced_optimization_study import extract_deep_kinematic_features, DATA_DIR, GYRO_CHANNELS

def test_feature_selection():
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
    y = df["diagnosis"].map(label_map).values
    groups = df["person_id"].values
    X = df[feature_cols].values

    sgkf = StratifiedGroupKFold(n_splits=5)

    print("\n--- Testing Feature Selection Subsets (fitted inside training folds) ---")
    for k in [5, 8, 12, 15, 20, 25, 30, len(feature_cols)]:
        rec_y_true, rec_y_pred, rec_y_prob = [], [], []
        pat_data = {}

        for fold, (train_idx, test_idx) in enumerate(sgkf.split(X, y, groups)):
            sc = RobustScaler()
            X_tr = sc.fit_transform(X[train_idx])
            X_te = sc.transform(X[test_idx])
            y_tr = y[train_idx]
            y_te = y[test_idx]
            te_groups = groups[test_idx]

            if k < len(feature_cols):
                selector = SelectKBest(score_func=f_classif, k=k)
                X_tr = selector.fit_transform(X_tr, y_tr)
                X_te = selector.transform(X_te)

            clf = LogisticRegression(C=0.5, penalty='l2', solver='lbfgs', max_iter=1000, random_state=42)
            clf.fit(X_tr, y_tr)

            preds = clf.predict(X_te)
            probs = clf.predict_proba(X_te)[:, 1]

            rec_y_true.extend(y_te)
            rec_y_pred.extend(preds)
            rec_y_prob.extend(probs)

            for pid, y_val, p_val in zip(te_groups, y_te, probs):
                if pid not in pat_data:
                    pat_data[pid] = {"y_true": y_val, "probs": []}
                pat_data[pid]["probs"].append(p_val)

        rec_bacc = balanced_accuracy_score(rec_y_true, rec_y_pred)
        rec_auc = roc_auc_score(rec_y_true, rec_y_prob)

        pat_pids = list(pat_data.keys())
        pat_y_true = [pat_data[p]["y_true"] for p in pat_pids]
        pat_y_prob = [float(np.mean(pat_data[p]["probs"])) for p in pat_pids]
        pat_y_pred = [1 if p >= 0.5 else 0 for p in pat_y_prob]
        pat_bacc = balanced_accuracy_score(pat_y_true, pat_y_pred)
        pat_auc = roc_auc_score(pat_y_true, pat_y_prob)

        print(f"K={k:2d} features -> Recording BAcc={rec_bacc*100:.2f}%, AUC={rec_auc:.3f} | Patient BAcc={pat_bacc*100:.2f}%, Patient AUC={pat_auc:.3f}")

if __name__ == "__main__":
    test_feature_selection()
