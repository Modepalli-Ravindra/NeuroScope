import os
import json
import joblib
import io
import scipy.io
import numpy as np
import shap
from typing import Dict, Any, List, Optional

from backend.ml.feature_extractor import extract_all_features, GYRO_CHANNELS

MODELS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "saved_models")

class InferenceEngine:
    _instance = None

    def __init__(self):
        print("Initializing NeuroScope Inference Engine from saved artifacts...")
        v3_path = os.path.join(MODELS_DIR, "neuroscope_model_v3.joblib")
        v2_path = os.path.join(MODELS_DIR, "neuroscope_model_v2.joblib")
        rf_path = os.path.join(MODELS_DIR, "neuroscope_rf_model.joblib")
        knn_path = os.path.join(MODELS_DIR, "neuroscope_knn_model.joblib")
        schema_v3_path = os.path.join(MODELS_DIR, "feature_schema_v3.json")
        schema_v2_path = os.path.join(MODELS_DIR, "feature_schema_v2.json")
        schema_v1_path = os.path.join(MODELS_DIR, "feature_schema.json")
        summary_path = os.path.join(MODELS_DIR, "dataset_summary.json")
        eval_path = os.path.join(MODELS_DIR, "evaluation_results.json")

        if not os.path.exists(rf_path):
            raise FileNotFoundError(f"Model artifact not found at {rf_path}. Run train_models.py first.")

        # 1. Primary Model: Optimized Logistic Regression v3 (RobustScaler, 59 features, 92.58% Patient Balanced Accuracy)
        self.v3_available = os.path.exists(v3_path)
        if self.v3_available:
            v3_artifact = joblib.load(v3_path)
            self.v3_model = v3_artifact["model"]
            self.v3_scaler = v3_artifact["scaler"]
            self.v3_feature_cols = v3_artifact["feature_cols"]
            self.v3_expected_value = v3_artifact.get("expected_value", 0.0)
            print(f"Loaded primary model v3 with {len(self.v3_feature_cols)} features and RobustScaler.")
        else:
            self.v3_model = None
            self.v3_scaler = None
            self.v3_feature_cols = []
            self.v3_expected_value = 0.0

        # Backup Model: v2
        self.v2_available = os.path.exists(v2_path)
        if self.v2_available:
            v2_artifact = joblib.load(v2_path)
            self.v2_model = v2_artifact["model"]
            self.v2_scaler = v2_artifact["scaler"]
            self.v2_feature_cols = v2_artifact["feature_cols"]
        else:
            self.v2_model = None
            self.v2_scaler = None
            self.v2_feature_cols = []

        # 2. Benchmark Model: Random Forest (StandardScaler, 45 features, TreeSHAP)
        rf_artifact = joblib.load(rf_path)
        self.rf_model = rf_artifact["model"]
        self.rf_scaler = rf_artifact["scaler"]
        self.rf_feature_cols = rf_artifact["feature_cols"]
        self.label_mapping = rf_artifact["label_mapping"]
        self.inv_label_mapping = rf_artifact["inv_label_mapping"]
        self.rf_expected_value = rf_artifact.get("expected_value", 0.5)

        # Backwards compatible alias for active feature columns
        if self.v3_available:
            self.feature_cols = self.v3_feature_cols
        elif self.v2_available:
            self.feature_cols = self.v2_feature_cols
        else:
            self.feature_cols = self.rf_feature_cols

        # 3. Benchmark Model: KNN Baseline
        knn_artifact = joblib.load(knn_path)
        self.knn_model = knn_artifact["model"]

        # Feature schemas
        active_schema_path = schema_v3_path if os.path.exists(schema_v3_path) else (schema_v2_path if os.path.exists(schema_v2_path) else schema_v1_path)
        with open(active_schema_path, "r") as f:
            self.feature_schema = json.load(f)

        with open(summary_path, "r") as f:
            self.dataset_summary = json.load(f)

        with open(eval_path, "r") as f:
            self.eval_results = json.load(f)

        # Pre-initialize TreeSHAP explainer for Random Forest
        self.tree_explainer = shap.TreeExplainer(self.rf_model)
        
        # Set up Linear SHAP explainer for primary model (Logistic Regression v3 or v2)
        # Using exact closed-form linear Shapley weights: phi_i = w_i * (x_i - mean(x_i))
        if self.v3_available:
            bg_zeros = np.zeros((1, len(self.v3_feature_cols)))
            self.linear_explainer = shap.LinearExplainer(self.v3_model, bg_zeros)
        elif self.v2_available:
            bg_zeros = np.zeros((1, len(self.v2_feature_cols)))
            self.linear_explainer = shap.LinearExplainer(self.v2_model, bg_zeros)
        else:
            self.linear_explainer = None

        print("Inference Engine successfully initialized with v3 primary LinearSHAP and TreeSHAP explainers ready.")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def parse_mat_bytes(self, content: bytes, filename: str = "upload.mat") -> Dict[str, Any]:
        """Safely parse MAT bytes in-memory with strict input validation."""
        if len(content) > 25 * 1024 * 1024:
            raise ValueError("File exceeds maximum allowed size limit of 25 MB.")

        try:
            mat = scipy.io.loadmat(io.BytesIO(content))
        except Exception as e:
            raise ValueError(f"Corrupted or invalid MATLAB .mat file: {e}")

        # Diagnosis
        diag = "UNKNOWN"
        if "diagnosis" in mat:
            diag = str(mat["diagnosis"][0]).strip()

        person_id = "ANONYMOUS"
        if "person_id" in mat:
            person_id = str(mat["person_id"][0]).strip()

        trial_id = "trial1"
        if "trial_id" in mat:
            trial_id = str(mat["trial_id"][0]).strip()

        fs = 200.0
        if "fs" in mat:
            fs_val = mat["fs"]
            if isinstance(fs_val, np.ndarray):
                fs = float(fs_val.flatten()[0])
            else:
                fs = float(fs_val)

        signals: Dict[str, np.ndarray] = {}
        lengths = []
        for ch in GYRO_CHANNELS:
            if ch in mat:
                arr = np.asarray(mat[ch], dtype=np.float64).flatten()
                signals[ch] = arr
                lengths.append(len(arr))
            else:
                raise ValueError(f"Missing required sensor channel '{ch}'. NeuroScope requires all 6 gyroscope channels.")

        min_len = min(lengths)
        if min_len < int(fs * 2.0):
            raise ValueError(f"Recording too short: {min_len} samples ({min_len/fs:.1f}s). Minimum required is 2.0 seconds.")

        for ch in signals:
            signals[ch] = signals[ch][:min_len]

        return {
            "filename": filename,
            "diagnosis": diag,
            "person_id": person_id,
            "trial_id": trial_id,
            "fs": fs,
            "duration_sec": min_len / fs,
            "num_samples": min_len,
            "signals": signals
        }

    def predict(self, parsed_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform feature extraction, multi-model inference (Optimized Logistic Regression v2,
        Random Forest, KNN), and genuine SHAP explanation (LinearSHAP for v2, TreeSHAP for RF).
        """
        signals = parsed_data["signals"]
        fs = parsed_data["fs"]
        
        # 1. Feature extraction
        raw_features = extract_all_features(signals, fs)

        # 2. Primary Model Inference: Optimized Logistic Regression v3 (59 features, RobustScaler)
        if self.v3_available:
            v3_vec = np.array([raw_features.get(f, 0.0) for f in self.v3_feature_cols]).reshape(1, -1)
            v3_vec_scaled = self.v3_scaler.transform(v3_vec)
            v3_proba = self.v3_model.predict_proba(v3_vec_scaled)[0]
            v3_prob_pd = float(v3_proba[0])
            v3_prob_msa = float(v3_proba[1])
            v3_pred_idx = int(np.argmax(v3_proba))
            primary_pred_class = self.inv_label_mapping[v3_pred_idx]
            primary_confidence = v3_prob_msa if primary_pred_class == "MSA" else v3_prob_pd
            prob_msa = v3_prob_msa
            prob_pd = v3_prob_pd
            
            # Genuine LinearSHAP values for Logistic Regression v3:
            # phi_i = w_i * x_scaled_i
            linear_weights = self.v3_model.coef_[0]
            linear_shap_vals = linear_weights * v3_vec_scaled[0]
            primary_base_val = float(self.v3_model.intercept_[0])
            active_feature_cols = self.v3_feature_cols
            active_scaled_vec = v3_vec_scaled[0]
            primary_shap_raw = linear_shap_vals
            active_model_name = "Optimized Logistic Regression (v3, C=0.5, Balanced, RobustScaler)"
            active_version = "v3.0-Combined-Heliyon-DeepKinematic-LogisticRegression-RobustScaler"
            active_bacc = "92.58%"
            active_auc = "0.912"
        elif self.v2_available:
            v2_vec = np.array([raw_features.get(f, 0.0) for f in self.v2_feature_cols]).reshape(1, -1)
            v2_vec_scaled = self.v2_scaler.transform(v2_vec)
            v2_proba = self.v2_model.predict_proba(v2_vec_scaled)[0]
            v2_prob_pd = float(v2_proba[0])
            v2_prob_msa = float(v2_proba[1])
            v2_pred_idx = int(np.argmax(v2_proba))
            primary_pred_class = self.inv_label_mapping[v2_pred_idx]
            primary_confidence = v2_prob_msa if primary_pred_class == "MSA" else v2_prob_pd
            prob_msa = v2_prob_msa
            prob_pd = v2_prob_pd
            
            linear_weights = self.v2_model.coef_[0]
            linear_shap_vals = linear_weights * v2_vec_scaled[0]
            primary_base_val = float(self.v2_model.intercept_[0])
            active_feature_cols = self.v2_feature_cols
            active_scaled_vec = v2_vec_scaled[0]
            primary_shap_raw = linear_shap_vals
            active_model_name = "Optimized Logistic Regression (v2, C=0.5, RobustScaler)"
            active_version = "v2.0-Optimized-LogisticRegression-RobustScaler"
            active_bacc = "84.89%"
            active_auc = "0.896"
        else:
            primary_pred_class = "UNKNOWN"
            primary_confidence = 0.5
            prob_msa = 0.5
            prob_pd = 0.5
            primary_base_val = 0.0
            active_feature_cols = self.rf_feature_cols
            active_scaled_vec = np.zeros(len(self.rf_feature_cols))
            primary_shap_raw = np.zeros(len(self.rf_feature_cols))
            active_model_name = "Random Forest (Baseline)"
            active_version = "v1.0-RandomForest-Baseline"
            active_bacc = "72.83%"
            active_auc = "0.767"

        # 3. Secondary Benchmark Model Inference: Random Forest (45 features, StandardScaler)
        rf_vec = np.array([raw_features.get(f, 0.0) for f in self.rf_feature_cols]).reshape(1, -1)
        rf_vec_scaled = self.rf_scaler.transform(rf_vec)
        rf_proba = self.rf_model.predict_proba(rf_vec_scaled)[0]
        rf_prob_pd = float(rf_proba[0])
        rf_prob_msa = float(rf_proba[1])
        rf_pred_idx = int(np.argmax(rf_proba))
        rf_pred_class = self.inv_label_mapping[rf_pred_idx]

        # 4. Secondary Benchmark Model Inference: KNN Baseline
        knn_proba = self.knn_model.predict_proba(rf_vec_scaled)[0]
        knn_pred_idx = int(np.argmax(knn_proba))
        knn_pred_class = self.inv_label_mapping[knn_pred_idx]

        # If v2 wasn't available, fall back to RF for primary output
        if not self.v2_available:
            primary_pred_class = rf_pred_class
            primary_confidence = rf_prob_msa if rf_pred_class == "MSA" else rf_prob_pd
            prob_msa = rf_prob_msa
            prob_pd = rf_prob_pd
            rf_shap_vals = self.tree_explainer.shap_values(rf_vec_scaled)
            if isinstance(rf_shap_vals, list):
                primary_shap_raw = rf_shap_vals[1][0]
            elif isinstance(rf_shap_vals, np.ndarray) and rf_shap_vals.ndim == 3:
                primary_shap_raw = rf_shap_vals[0, :, 1]
            else:
                primary_shap_raw = rf_shap_vals[0]

        # 5. Build feature contributions list
        feature_contributions = []
        for i, f_name in enumerate(active_feature_cols):
            val = float(primary_shap_raw[i])
            feature_contributions.append({
                "feature": f_name,
                "shap_value": round(val, 4),
                "feature_value": round(float(raw_features.get(f_name, 0.0)), 4),
                "scaled_value": round(float(active_scaled_vec[i]), 4),
                "direction": "Pushes towards MSA" if val > 0 else "Pushes towards PD"
            })

        feature_contributions.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        top_positive = [c for c in feature_contributions if c["shap_value"] > 0][:6]
        top_negative = [c for c in feature_contributions if c["shap_value"] < 0][:6]

        # 6. Uncertainty & Quality Evaluation Policy
        is_uncertain = False
        uncertainty_reasons = []

        if 0.45 <= prob_msa <= 0.55:
            is_uncertain = True
            uncertainty_reasons.append("Score near decision boundary (45%-55%): Borderline differential separation between MSA and PD.")

        if primary_pred_class != rf_pred_class or primary_pred_class != knn_pred_class:
            uncertainty_reasons.append(
                f"Model consensus variance: Primary v2 predicts {primary_pred_class}, "
                f"Random Forest predicts {rf_pred_class}, and KNN predicts {knn_pred_class}."
            )
            if primary_confidence < 0.65:
                is_uncertain = True

        if parsed_data["duration_sec"] < 4.0:
            uncertainty_reasons.append(
                f"Short recording duration ({parsed_data['duration_sec']:.1f}s < 4.0s): "
                f"Tapping rhythm statistics and fatigue ratio exhibit higher sample variance."
            )
            is_uncertain = True

        # Downsample for frontend chart preview (~120 points per channel)
        step = max(1, parsed_data["num_samples"] // 120)
        time_axis = [round(i / fs, 3) for i in range(0, parsed_data["num_samples"], step)]
        downsampled_signals = {
            ch: [round(float(v), 3) for v in signals[ch][::step]]
            for ch in GYRO_CHANNELS
        }

        return {
            "prediction": {
                "predicted_class": primary_pred_class,
                "confidence_score": round(primary_confidence, 3),
                "probabilities": {
                    "MSA": round(prob_msa, 3),
                    "PD": round(prob_pd, 3)
                },
                "knn_baseline_class": knn_pred_class,
                "knn_probabilities": {
                    "MSA": round(float(knn_proba[1]), 3),
                    "PD": round(float(knn_proba[0]), 3)
                },
                "is_uncertain": is_uncertain,
                "uncertainty_reasons": uncertainty_reasons
            },
            "shap_explanation": {
                "base_value": round(primary_base_val, 4),
                "top_positive_features": top_positive,
                "top_negative_features": top_negative,
                "top_features": feature_contributions[:10]
            },
            "input_metadata": {
                "filename": parsed_data["filename"],
                "original_label": parsed_data["diagnosis"],
                "person_id": parsed_data["person_id"],
                "trial_id": parsed_data["trial_id"],
                "duration_sec": round(parsed_data["duration_sec"], 2),
                "sampling_rate_hz": fs,
                "sample_count": parsed_data["num_samples"]
            },
            "extracted_features": {k: round(v, 4) for k, v in raw_features.items()},
            "signal_preview": {
                "time": time_axis,
                "signals": downsampled_signals
            },
            "chart_data": {
                "time": time_axis,
                "signals": downsampled_signals
            },
            "model_metadata": {
                "primary_model_name": active_model_name,
                "model_version": active_version,
                "explainer_type": "LinearSHAP (Exact Closed-Form Log-Odds Contributions)" if (self.v3_available or self.v2_available) else "TreeSHAP",
                "balanced_accuracy": active_bacc,
                "roc_auc": active_auc,
                "random_forest": {
                    "predicted_class": rf_pred_class,
                    "probabilities": {
                        "MSA": round(rf_prob_msa, 3),
                        "PD": round(rf_prob_pd, 3)
                    }
                }
            }
        }
