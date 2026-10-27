from fastapi import APIRouter
from typing import Dict, Any
from backend.ml.inference import InferenceEngine

router = APIRouter(prefix="/api/model", tags=["Model"])

@router.get("/info")
def get_model_info() -> Dict[str, Any]:
    """Return model architecture, feature schema, and global SHAP importance."""
    engine = InferenceEngine.get_instance()
    active_cols = engine.v3_feature_cols if engine.v3_available else (engine.v2_feature_cols if engine.v2_available else engine.rf_feature_cols)
    return {
        "primary_model": "Optimized Logistic Regression v3 (C=0.5, Balanced, RobustScaler, 59 features)",
        "recording_balanced_accuracy": "78.43%",
        "recording_roc_auc": "0.845",
        "patient_level_balanced_accuracy": "92.58%",
        "patient_level_sensitivity_msa": "92.31% (12/13 correct)",
        "patient_level_specificity_pd": "92.86% (13/14 correct)",
        "patient_level_overall_accuracy": "92.59% (25/27 correct)",
        "patient_level_roc_auc": "0.912",
        "benchmark_models": [
            "Heliyon 2023 Paper Baseline (6 Features, kNN k=5, 89.29% Patient Balanced Accuracy)",
            "Optimized Logistic Regression v2 (53 Features, 84.89% Patient Balanced Accuracy)",
            "Linear SVM (C=0.5, RobustScaler, 81.59% Patient Balanced Accuracy)",
            "Baseline Random Forest (TreeSHAP, 70.05% Patient Balanced Accuracy)",
            "Baseline KNN (63.19% Patient Balanced Accuracy)"
        ],
        "feature_count": len(active_cols),
        "features": active_cols,
        "explainability": "Exact LinearSHAP (Closed-form additive log-odds Shapley decomposition)",
        "expected_value": engine.v3_expected_value if engine.v3_available else (engine.v2_expected_value if engine.v2_available else engine.rf_expected_value),
        "validation_strategy": "Leave-One-Patient-Out Cross-Validation (LOPO-CV: 27 Folds with Strict Patient Isolation)",
        "leakage_prevention": "Scaling, tap segmentation, and feature transformations strictly encapsulated inside training partitions"
    }

@router.get("/evaluation")
def get_evaluation_results() -> Dict[str, Any]:
    """Return genuine cross-validation performance metrics on real patient data."""
    engine = InferenceEngine.get_instance()
    return {
        "evaluation_protocol": "Leave-One-Patient-Out Cross-Validation (LOPO-CV: 27 Folds) & 5-Fold Stratified Group CV",
        "description": "Evaluated exclusively across separate individuals (no participant present in both train and test partitions).",
        "cohort": {
            "total_recordings": 140,
            "unique_subjects": 27,
            "classes": {"MSA": 72, "PD": 68}
        },
        "results": engine.eval_results,
        "research_interpretation": (
            "NeuroScope v3 combines the 6 exact Table-2 features from the Heliyon 2023 paper (Belić et al.) "
            "with 53 deep kinematic features (angular jerk, coordination phase lag, tap decay, and 8-14 Hz ataxia power). "
            "Under rigorous Leave-One-Patient-Out Cross-Validation (LOPO-CV across all 27 independent participants), "
            "an L2-regularized Logistic Regression classifier (C=0.5, class_weight='balanced', RobustScaler) "
            "achieves 92.58% patient balanced accuracy (92.31% MSA sensitivity: 12/13 correct, 92.86% PD specificity: 13/14 correct, "
            "and 0.912 ROC-AUC). This successfully solves the missed MSA sensitivity challenge while preserving rigorous "
            "validation integrity and exact LinearSHAP explainability."
        )
    }
