# Model Card: NeuroScope Scientific Optimization (v3.0)

## 1. Model Summary
* **Model Name:** NeuroScope Combined Table-2 & Deep Kinematic Classifier (v3.0)
* **Version:** 3.0.0 (Advanced MSA Detection Release)
* **Date:** 2026-10-26
* **Model Architecture:** Regularized Logistic Regression (`LogisticRegression(C=0.5, class_weight='balanced')` + `RobustScaler`)
* **Retained Baselines:** 
  * Heliyon 2023 Paper Baseline (`kNN(k=5, weights='distance')` on Table-2 six features)
  * Optimized Logistic Regression v2 (53 deep kinematic features)
  * Random Forest Classifier (100 trees, depth 6, `StandardScaler`)
* **Explainability Framework:** Exact LinearSHAP (`shap.LinearExplainer` computing closed-form additive log-odds Shapley values: $\phi_i = w_i \cdot x_i$) for Primary Model + Native TreeSHAP for Random Forest
* **Task:** Binary differential screening between Multiple System Atrophy (MSA-P) and Parkinson's Disease (PD) from continuous 6-axis gyroscope finger-tapping signals.

---

## 2. Intended Use & Boundaries
* **Primary Intended Use:** Educational research and interactive explainability exploration for biomedical engineering and clinical neurology research.
* **Out-of-Scope Uses:** 
  * Standalone clinical diagnostic decision-making without neurologist evaluation.
  * Prescribing or altering levodopa / dopaminergic therapy.
  * Screening uncharacterized tremors (e.g. Essential Tremor, Dystonic Tremor).
  * Extrapolating to MSA-C (cerebellar ataxia subtype) without full cerebellar battery.

---

## 3. Training & Validation Data
* **Data Source:** Finger Tapping Parkinsonisms Database (Heliyon 2023, University of Belgrade, *Belić et al.*).
* **Sample Size:** 140 continuous movement recordings across 27 independent human participants.
* **Class Balance:**
  * MSA: 72 recordings (13 unique participants)
  * PD: 68 recordings (14 unique participants)
* **Validation Strategy:** **Leave-One-Patient-Out Cross-Validation (LOPO-CV: 27 Folds)** and 5-Fold Stratified Group CV grouped strictly by participant identifier (`person_id`).
* **Leakage Barrier:** Scalers, tap segmentation, and feature transformations are fitted strictly inside training folds. Zero participant overlap exists between train and test splits.

---

## 4. Comprehensive Model Comparison Benchmark (LOPO-CV: 27 Folds)

Evaluated under strict Leave-One-Patient-Out cross-validation across all 27 independent participants:

| Architecture | Features | Patient Balanced Acc | Patient MSA Sens | Patient PD Spec | Overall Pt Acc | Patient ROC-AUC | Brier Loss | Explainability |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Optimized Logistic Regression v3 (Selected)** | **59 (6 Paper + 53 Deep)** | **92.58%** | **92.31% (12/13)** | **92.86% (13/14)** | **92.59% (25/27)** | **0.912** | **0.156** | **Exact LinearSHAP** |
| Heliyon 2023 Paper Baseline | 6 (Table 2) | 89.29% | 100.00% (13/13) | 78.57% (11/14) | 88.89% (24/27) | 0.909 | 0.123 | Distance Metric |
| Optimized Logistic Regression v2 | 53 | 84.89% | 76.92% (10/13) | 92.86% (13/14) | 85.19% (23/27) | 0.896 | 0.162 | LinearSHAP |
| Linear SVM ($C=0.5$, Balanced) | 53 | 81.59% | 84.62% (11/13) | 78.57% (11/14) | 81.48% (22/27) | 0.890 | 0.175 | Margin Hyperplane |
| Baseline Random Forest | 45 | 70.05% | 69.23% (9/13) | 71.43% (10/14) | 70.37% (19/27) | 0.758 | 0.217 | TreeSHAP |
| Baseline KNN ($k=5$) | 45 | 63.19% | 76.92% (10/13) | 50.00% (7/14) | 62.96% (17/27) | 0.720 | 0.245 | Distance Metric |

### Patient-Level Confusion Matrix (v3.0, LOPO-CV)
* **True Negative (PD correctly identified):** 13 / 14 (92.86%)
* **False Positive (PD misclassified as MSA):** 1 / 14 (7.14%)
* **False Negative (MSA misclassified as PD):** 1 / 13 (7.69% - `MSABM23`)
* **True Positive (MSA correctly identified):** 12 / 13 (92.31%)

---

## 5. Feature Engineering Architecture (59 Features)
1. **Heliyon 2023 Table-2 Six Replicated Features:**
   - `paper_feat1_index_x_rms`: Index finger lateral excursion RMS
   - `paper_feat2_index_y_tap_max_mean`: Sustained finger opening amplitude
   - `paper_feat3_index_y_acc_rms`: Index finger opening angular acceleration RMS ($d\omega / dt$)
   - `paper_feat4_index_vec_spec_centroid`: Frequency centroid of index vector intensity
   - `paper_feat5_thumb_x_max`: Maximal thumb lateral rotation
   - `paper_feat6_thumb_z_acc_tap_max_std`: Variability of thumb angular acceleration across tap cycles
2. **Deep Kinematic & Spectral Features (53 Features):**
   - 6-axis jerk RMS, vector magnitudes, asymmetry ratios
   - Phase cross-correlation peak and timing lag (`phase_lag_ms`)
   - Sequence fatigue and amplitude decay (`tap_amplitude_decay`)
   - Multi-band Welch PSD (1–4 Hz voluntary, 4–8 Hz tremor, 8–14 Hz cerebellar ataxia band)
