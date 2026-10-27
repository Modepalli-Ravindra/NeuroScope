from pydantic import BaseModel, EmailStr
from typing import Dict, List, Any, Optional

class UserRegisterRequest(BaseModel):
    name: str
    institution: Optional[str] = "Independent Research"
    email: str
    password: str
    confirm_password: str

class UserLoginRequest(BaseModel):
    email: str
    password: str

class UserResponse(BaseModel):
    id: int
    name: str
    institution: str
    email: str
    token: str

class PredictionResult(BaseModel):
    predicted_class: str
    confidence_score: float
    probabilities: Dict[str, float]
    knn_baseline_class: str
    knn_probabilities: Dict[str, float]
    is_uncertain: bool
    uncertainty_reasons: List[str]

class FeatureContribution(BaseModel):
    feature: str
    shap_value: float
    feature_value: float
    scaled_value: float
    direction: str

class SHAPExplanation(BaseModel):
    base_value: float
    top_positive_features: List[FeatureContribution]
    top_negative_features: List[FeatureContribution]
    top_features: List[FeatureContribution]

class InputMetadata(BaseModel):
    filename: str
    original_label: str
    person_id: str
    trial_id: str
    duration_sec: float
    sampling_rate_hz: float
    sample_count: int

class AnalysisResponse(BaseModel):
    id: Optional[int] = None
    prediction: PredictionResult
    shap_explanation: SHAPExplanation
    input_metadata: InputMetadata
    extracted_features: Dict[str, float]
    signal_preview: Dict[str, Any]
    model_metadata: Dict[str, Any]

class HistoryItem(BaseModel):
    id: int
    user_id: Optional[int] = None
    created_at: str
    filename: str
    original_label: str
    predicted_class: str
    confidence_score: float
    prob_msa: float
    prob_pd: float
    knn_baseline: str
    is_uncertain: bool
    duration_sec: float

class AuthenticSample(BaseModel):
    sample_id: str
    filename: str
    rel_path: Optional[str] = None
    person_id: Optional[str] = None
    trial_id: Optional[str] = None
    verified_diagnosis: Optional[str] = None
    display_name: str
    code: str
    duration_sec: float
    sample_count: Optional[int] = None
    sampling_rate_hz: Optional[int] = 200
    sampling_rate: str
    file_size_kb: Optional[float] = None
    description: str

