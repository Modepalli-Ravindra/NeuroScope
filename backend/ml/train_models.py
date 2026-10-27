import os
import json
import joblib
import numpy as np
import pandas as pd
import shap
from typing import Dict, Any, List

from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedGroupKFold
from sklearn.metrics import (
    accuracy_score, balanced_accuracy_score, recall_score,
    precision_score, f1_score, roc_auc_score, confusion_matrix, brier_score_loss
)

from backend.ml.dataset_loader import build_dataset_dataframe

def train_and_evaluate():
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    data_dir = os.path.join(project_root, "data", "raw")
    output_dir = os.path.join(project_root, "backend", "saved_models")
    os.makedirs(output_dir, exist_ok=True)

    print("Step 1: Extracting features from raw dataset...")
    df, stats = build_dataset_dataframe(data_dir, ["MSA", "PD"])
    
    meta_cols = ["filename", "diagnosis", "person_id", "trial_id", "duration_sec", "fs"]
    feature_cols = [c for c in df.columns if c not in meta_cols]
    
    X = df[feature_cols].values
    label_mapping = {"PD": 0, "MSA": 1}
    inv_label_mapping = {0: "PD", 1: "MSA"}
    y = df["diagnosis"].map(label_mapping).values
    groups = df["person_id"].values

    print(f"Dataset shape: {X.shape}, Features: {len(feature_cols)}")
    print(f"Unique participants: {len(np.unique(groups))}")

    # Step 2: Subject-Wise Stratified K-Fold (Strict Leakage Prevention)
    n_splits = 5
    sgkf = StratifiedGroupKFold(n_splits=n_splits)

    models_to_eval = {
        "Random Forest": RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, min_samples_leaf=2),
        "Logistic Regression": LogisticRegression(max_iter=1000, random_state=42, C=0.5),
        "K-Nearest Neighbors": KNeighborsClassifier(n_neighbors=5, weights="distance")
    }

    eval_results = {}

    for model_name, model in models_to_eval.items():
        print(f"\nEvaluating {model_name} with {n_splits}-fold Subject-Wise CV...")
        y_true_all = []
        y_pred_all = []
        y_prob_all = []
        fold_metrics = []

        for fold, (train_idx, test_idx) in enumerate(sgkf.split(X, y, groups)):
            # Check subject isolation
            train_groups = set(groups[train_idx])
            test_groups = set(groups[test_idx])
            assert len(train_groups.intersection(test_groups)) == 0, f"Subject leakage in fold {fold}!"

            scaler = StandardScaler()
            X_train = scaler.fit_transform(X[train_idx])
            X_test = scaler.transform(X[test_idx])
            y_train = y[train_idx]
            y_test = y[test_idx]

            # Fit on training fold
            model.fit(X_train, y_train)
            preds = model.predict(X_test)
            
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba(X_test)[:, 1]
            else:
                probs = preds.astype(float)

            y_true_all.extend(y_test)
            y_pred_all.extend(preds)
            y_prob_all.extend(probs)

            # Record per-fold metrics
            fold_bacc = balanced_accuracy_score(y_test, preds)
            try:
                fold_auc = roc_auc_score(y_test, probs)
            except Exception:
                fold_auc = 0.5
            fold_metrics.append({"fold": fold + 1, "balanced_accuracy": fold_bacc, "roc_auc": fold_auc})

        y_true_all = np.array(y_true_all)
        y_pred_all = np.array(y_pred_all)
        y_prob_all = np.array(y_prob_all)

        cm = confusion_matrix(y_true_all, y_pred_all)
        tn, fp, fn, tp = cm.ravel()
        
        sensitivity = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        specificity = tn / (tn + fp) if (tn + fp) > 0 else 0.0
        bal_acc = balanced_accuracy_score(y_true_all, y_pred_all)
        acc = accuracy_score(y_true_all, y_pred_all)
        f1 = f1_score(y_true_all, y_pred_all, average="weighted")
        try:
            auc = roc_auc_score(y_true_all, y_prob_all)
        except Exception:
            auc = 0.5
        brier = brier_score_loss(y_true_all, y_prob_all)

        fold_baccs = [m["balanced_accuracy"] for m in fold_metrics]
        fold_aucs = [m["roc_auc"] for m in fold_metrics]

        eval_results[model_name] = {
            "pooled": {
                "accuracy": round(float(acc), 4),
                "balanced_accuracy": round(float(bal_acc), 4),
                "sensitivity_msa": round(float(sensitivity), 4),
                "specificity_pd": round(float(specificity), 4),
                "f1_score": round(float(f1), 4),
                "roc_auc": round(float(auc), 4),
                "brier_score": round(float(brier), 4),
                "confusion_matrix": {
                    "tn": int(tn), "fp": int(fp),
                    "fn": int(fn), "tp": int(tp),
                    "matrix": cm.tolist()
                }
            },
            "per_fold": {
                "balanced_accuracy_mean": round(float(np.mean(fold_baccs)), 4),
                "balanced_accuracy_std": round(float(np.std(fold_baccs)), 4),
                "roc_auc_mean": round(float(np.mean(fold_aucs)), 4),
                "roc_auc_std": round(float(np.std(fold_aucs)), 4),
                "folds": fold_metrics
            }
        }
        print(f"Results for {model_name}: Balanced Acc={bal_acc*100:.2f}%, Sens={sensitivity*100:.2f}%, Spec={specificity*100:.2f}%, AUC={auc:.3f}")

    # Step 3: Train final production models on full dataset
    print("\nFitting final production models on full dataset...")
    final_scaler = StandardScaler()
    X_scaled = final_scaler.fit_transform(X)

    # 3a. Random Forest
    final_rf = RandomForestClassifier(n_estimators=100, max_depth=6, random_state=42, min_samples_leaf=2)
    final_rf.fit(X_scaled, y)

    # 3b. Logistic Regression (High linear stability benchmark)
    final_lr = LogisticRegression(max_iter=1000, random_state=42, C=0.5)
    final_lr.fit(X_scaled, y)

    # 3c. KNN Baseline
    final_knn = KNeighborsClassifier(n_neighbors=5, weights="distance")
    final_knn.fit(X_scaled, y)

    # Step 4: Compute TreeSHAP values for Random Forest model
    print("Computing TreeSHAP values for Random Forest model...")
    rf_explainer = shap.TreeExplainer(final_rf)
    shap_values = rf_explainer.shap_values(X_scaled)
    
    if isinstance(shap_values, list):
        shap_msa = shap_values[1]
        base_val = float(rf_explainer.expected_value[1])
    elif isinstance(shap_values, np.ndarray) and shap_values.ndim == 3:
        shap_msa = shap_values[:, :, 1]
        base_val = float(rf_explainer.expected_value[1])
    else:
        shap_msa = shap_values
        base_val = float(rf_explainer.expected_value)

    mean_abs_shap = np.mean(np.abs(shap_msa), axis=0)
    top_indices = np.argsort(mean_abs_shap)[::-1]
    
    global_importance = [
        {
            "rank": int(i + 1),
            "feature": feature_cols[idx],
            "importance": round(float(mean_abs_shap[idx]), 4),
            "description": get_feature_description(feature_cols[idx])
        }
        for i, idx in enumerate(top_indices[:15])
    ]

    # Save artifacts
    print("Saving model artifacts...")
    rf_artifact = {
        "model": final_rf,
        "scaler": final_scaler,
        "feature_cols": feature_cols,
        "label_mapping": label_mapping,
        "inv_label_mapping": inv_label_mapping,
        "expected_value": base_val,
        "model_type": "RandomForestClassifier",
        "version": "1.0.0"
    }
    joblib.dump(rf_artifact, os.path.join(output_dir, "neuroscope_rf_model.joblib"))

    lr_artifact = {
        "model": final_lr,
        "scaler": final_scaler,
        "feature_cols": feature_cols,
        "label_mapping": label_mapping,
        "inv_label_mapping": inv_label_mapping,
        "model_type": "LogisticRegression",
        "version": "1.0.0"
    }
    joblib.dump(lr_artifact, os.path.join(output_dir, "neuroscope_lr_model.joblib"))

    knn_artifact = {
        "model": final_knn,
        "scaler": final_scaler,
        "feature_cols": feature_cols,
        "label_mapping": label_mapping,
        "inv_label_mapping": inv_label_mapping,
        "model_type": "KNeighborsClassifier",
        "version": "1.0.0"
    }
    joblib.dump(knn_artifact, os.path.join(output_dir, "neuroscope_knn_model.joblib"))

    # Save metadata & evaluation results
    with open(os.path.join(output_dir, "evaluation_results.json"), "w") as f:
        json.dump(eval_results, f, indent=2)

    with open(os.path.join(output_dir, "feature_schema.json"), "w") as f:
        json.dump({
            "features": feature_cols,
            "count": len(feature_cols),
            "global_importance": global_importance
        }, f, indent=2)

    with open(os.path.join(output_dir, "dataset_summary.json"), "w") as f:
        json.dump({
            "total_recordings": len(df),
            "unique_subjects": int(len(np.unique(groups))),
            "class_distribution": {
                "MSA": int(np.sum(y == 1)),
                "PD": int(np.sum(y == 0))
            },
            "participants_per_class": {
                "MSA": int(len(set(df[df['diagnosis'] == 'MSA']['person_id']))),
                "PD": int(len(set(df[df['diagnosis'] == 'PD']['person_id'])))
            },
            "source": "FINGER-TAPPING-PARKINSONISMS-DATABASE (Heliyon 2023)",
            "msa_subtype_note": "The MSA cohort in this dataset is predominantly MSA-P (parkinsonian subtype). Generalization to MSA-C (cerebellar subtype) is unverified."
        }, f, indent=2)

    df.to_csv(os.path.join(output_dir, "extracted_features.csv"), index=False)
    print("\nTraining and artifact generation complete!")
    return eval_results

def get_feature_description(feat_name: str) -> str:
    if "tap_interval_cv" in feat_name:
        return "Tapping rhythm irregularity (coefficient of variation of inter-tap intervals)"
    elif "tap_rate_hz" in feat_name:
        return "Tapping cadence / frequency in taps per second"
    elif "tap_amplitude_decay" in feat_name:
        return "Progressive fatigue / decrement slope across consecutive taps"
    elif "tap_amplitude_cv" in feat_name:
        return "Tap amplitude variation (hypometria fluctuation)"
    elif "relative_mag" in feat_name and "p2p" in feat_name:
        return "Peak opening/closing separation velocity between thumb and index"
    elif "relative_mag" in feat_name and "rms" in feat_name:
        return "Root mean square kinetic energy of relative finger tapping"
    elif "jerk" in feat_name:
        return "Angular jerk / motion abruptness (derivative of angular velocity)"
    elif "dom_freq" in feat_name:
        return "Dominant oscillation frequency of angular movement"
    elif "spec_entropy" in feat_name:
        return "Spectral entropy / kinetic motion complexity"
    elif "dom_pwr_ratio" in feat_name:
        return "Ratio of tapping band power (0.5-5Hz) to overall sensor energy"
    elif "p2p" in feat_name:
        return "Peak-to-peak angular velocity range"
    elif "rms" in feat_name:
        return "Root mean square movement magnitude"
    else:
        return "Kinematic movement statistical indicator"

if __name__ == "__main__":
    train_and_evaluate()
