export interface UserRegisterRequest {
  name: string;
  institution?: string;
  email: string;
  password: string;
  confirm_password: string;
}

export interface UserLoginRequest {
  email: string;
  password: string;
}

export interface UserResponse {
  id: number;
  name: string;
  institution: string;
  email: string;
  token: string;
}

export interface UserProfile {
  id?: number;
  name: string;
  institution: string;
  email: string;
  role?: string;
}

export interface PredictionResult {
  predicted_class: 'MSA' | 'PD' | string;
  confidence_score: number;
  probabilities: {
    MSA: number;
    PD: number;
  };
  logistic_regression?: {
    predicted_class: string;
    probabilities: {
      MSA: number;
      PD: number;
    };
  };
  knn_baseline_class: string;
  knn_probabilities: {
    MSA: number;
    PD: number;
  };
  is_uncertain: boolean;
  uncertainty_reasons: string[];
}

export interface FeatureContribution {
  feature: string;
  shap_value: number;
  feature_value: number;
  scaled_value: number;
  direction: string;
}

export interface SHAPExplanation {
  base_value: number;
  top_positive_features: FeatureContribution[];
  top_negative_features: FeatureContribution[];
  top_features: FeatureContribution[];
}

export interface InputMetadata {
  filename: string;
  original_label: string;
  person_id: string;
  trial_id: string;
  duration_sec: number;
  sampling_rate_hz: number;
  sample_count: number;
}

export interface SignalPreview {
  time: number[];
  channels: {
    gyroThumbX: number[];
    gyroThumbY: number[];
    gyroThumbZ: number[];
    gyroIndexX: number[];
    gyroIndexY: number[];
    gyroIndexZ: number[];
  };
}

export interface AnalysisResponse {
  id: number | null;
  prediction: PredictionResult;
  shap_explanation: SHAPExplanation;
  input_metadata: InputMetadata;
  extracted_features: Record<string, number>;
  signal_preview: SignalPreview;
  model_metadata: {
    model_name: string;
    model_version: string;
    dataset_source: string;
    validation_method: string;
    disclaimer: string;
  };
}

export interface AuthenticSample {
  sample_id: string;
  filename: string;
  rel_path?: string;
  person_id: string;
  trial_id: string;
  verified_diagnosis: string;
  display_name: string;
  code: string;
  duration_sec: number;
  sample_count?: number;
  sampling_rate_hz?: number;
  sampling_rate: string;
  file_size_kb?: number;
  description: string;
}

export interface ImportDatasetResponse {
  status: string;
  message: string;
  record: AuthenticSample;
  total_dataset_count: number;
}


export interface HistoryItem {
  id: number;
  created_at: string;
  filename: string;
  original_label: string;
  predicted_class: string;
  confidence_score: number;
  prob_msa: number;
  prob_pd: number;
  knn_baseline: string;
  is_uncertain: boolean;
  duration_sec: number;
}

export interface DatasetInfo {
  dataset_name: string;
  citation: string;
  sensor_type: string;
  sampling_rate_hz: number;
  classes_available: Record<string, number>;
  primary_differential_classes: string[];
  dataset_summary: {
    total_recordings: number;
    unique_subjects: number;
    class_distribution: Record<string, number>;
    participants_per_class: Record<string, number>;
    source: string;
    msa_subtype_note: string;
  };
  clinical_notes: {
    msa_subtype_limitation: string;
    study_protocol: string;
    data_use: string;
  };
}

export interface ModelEvaluation {
  evaluation_protocol: string;
  description: string;
  cohort: {
    total_recordings: number;
    unique_subjects: number;
    classes: Record<string, number>;
  };
  results: Record<string, {
    pooled: {
      accuracy: number;
      balanced_accuracy: number;
      sensitivity_msa: number;
      specificity_pd: number;
      f1_score: number;
      roc_auc: number;
      brier_score?: number;
      confusion_matrix: {
        tn: number;
        fp: number;
        fn: number;
        tp: number;
        matrix: number[][];
      };
    };
    per_fold?: {
      balanced_accuracy_mean: number;
      balanced_accuracy_std: number;
      roc_auc_mean: number;
      roc_auc_std: number;
      folds: any[];
    };
  }>;
  research_interpretation: string;
}
