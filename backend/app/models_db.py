import datetime
from sqlalchemy import Column, Integer, String, Float, Boolean, Text, DateTime, ForeignKey
from backend.app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    name = Column(String(255), nullable=False)
    institution = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)

class AnalysisHistory(Base):
    __tablename__ = "analysis_history"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow, index=True)
    filename = Column(String(255), nullable=False)
    original_label = Column(String(50), default="UNKNOWN")
    person_id = Column(String(100), default="ANONYMOUS")
    trial_id = Column(String(50), default="trial1")
    duration_sec = Column(Float, default=0.0)
    sampling_rate_hz = Column(Float, default=200.0)

    predicted_class = Column(String(50), nullable=False)
    confidence_score = Column(Float, nullable=False)
    prob_msa = Column(Float, nullable=False)
    prob_pd = Column(Float, nullable=False)
    knn_baseline = Column(String(50), default="UNKNOWN")
    
    is_uncertain = Column(Boolean, default=False)
    uncertainty_reasons_json = Column(Text, default="[]")
    
    top_shap_json = Column(Text, default="[]")
    extracted_features_json = Column(Text, default="{}")
    model_version = Column(String(50), default="1.0.0")
    notes = Column(Text, default="")
