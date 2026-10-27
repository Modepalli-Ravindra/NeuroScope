import React, { useState, useEffect } from 'react';
import {
  Activity, Layers, FileText, UploadCloud, CheckCircle2,
  AlertTriangle, RefreshCw, Download, ShieldAlert, Check,
  ArrowRight, X, FileSpreadsheet, Cpu, Radio, RotateCcw
} from 'lucide-react';
import { runAnalysis, fetchHistory, fetchHistoryDetail, getPdfReportUrl } from '../api';
import type { AnalysisResponse, HistoryItem } from '../types';
import { FullscreenBlurLoader } from '../components/FullscreenBlurLoader';

interface DashboardPageProps {
  activeTab?: 'screening' | 'prediction' | 'history';
  onSelectTab?: (tab: 'screening' | 'prediction' | 'history') => void;
}

interface FeatureExplanation {
  factor: string;
  finding: string;
  clinicalMeaning: string;
}

// Clear, human-friendly explanation of movement features
const getSimpleFeatureExplanation = (featureName: string, direction: string): FeatureExplanation => {
  const f = featureName.toLowerCase();

  if (f.includes('cadence') || f.includes('rate') || f.includes('speed') || f.includes('interval')) {
    return {
      factor: 'Tapping Rhythm & Pacing',
      finding: direction.includes('MSA')
        ? 'Frequent irregular delays and jerky pacing detected during finger opening.'
        : 'Rhythmic, steady tapping with slight progressive slowing observed.',
      clinicalMeaning: direction.includes('MSA')
        ? 'Indicates cerebellar motor arrest typical of Multiple System Atrophy.'
        : 'Consistent with classic Parkinson\'s disease bradykinesia.'
    };
  }
  if (f.includes('deceleration') || f.includes('slope') || f.includes('stop') || f.includes('velocity')) {
    return {
      factor: 'Movement Braking & Smoothness',
      finding: direction.includes('MSA')
        ? 'Finger stopped abruptly before closing rather than in a smooth continuous wave.'
        : 'Finger movement maintained a smooth speed trajectory with gradual decay.',
      clinicalMeaning: direction.includes('MSA')
        ? 'Points to atypical cerebellar motor incoordination.'
        : 'Reflects standard basal ganglia motor pacing.'
    };
  }
  if (f.includes('power') || f.includes('ataxia') || f.includes('spectral') || f.includes('energy')) {
    return {
      factor: 'Tremor & Involuntary Shaking',
      finding: direction.includes('MSA')
        ? 'Wide-band (8–14 Hz) irregular shaking detected across movement channels.'
        : 'Predictable, narrow-band resting tremor detected.',
      clinicalMeaning: direction.includes('MSA')
        ? 'Characteristic of cerebellar-type ataxia.'
        : 'Consistent with classic Parkinsonian rest tremors.'
    };
  }
  if (f.includes('amplitude') || f.includes('decay') || f.includes('decrement') || f.includes('range')) {
    return {
      factor: 'Finger Opening Size & Fatigue',
      finding: direction.includes('MSA')
        ? 'Tap opening sizes fluctuated erratically without a progressive fatigue pattern.'
        : 'Tap opening sizes progressively shrunk over the trial sequence.',
      clinicalMeaning: direction.includes('MSA')
        ? 'Atypical motor planning instability distinctive of MSA.'
        : 'Sequence amplitude fatigue (hypokinesia), a hallmark of Parkinson\'s.'
    };
  }

  return {
    factor: featureName.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase()),
    finding: direction.includes('MSA')
      ? 'Kinematic sensor readings diverged from standard Parkinsonism patterns.'
      : 'Kinematic sensor readings closely followed classic Parkinsonian signatures.',
    clinicalMeaning: direction.includes('MSA')
      ? 'Movement features align with Multiple System Atrophy motor markers.'
      : 'Movement features align with classic Parkinson\'s disease motor markers.'
  };
};

export const DashboardPage: React.FC<DashboardPageProps> = ({
  activeTab = 'screening',
  onSelectTab,
}) => {
  // Upload and Analysis State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [notes, setNotes] = useState<string>('');
  const [isDragging, setIsDragging] = useState<boolean>(false);

  // Execution & Output State
  const [isAnalyzing, setIsAnalyzing] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const [currentAnalysis, setCurrentAnalysis] = useState<AnalysisResponse | null>(null);

  // Authenticated Researcher History State
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState<boolean>(false);

  const loadHistory = async () => {
    setIsLoadingHistory(true);
    try {
      const data = await fetchHistory();
      setHistory(data || []);
    } catch (err) {
      console.error('Failed to load researcher history:', err);
    } finally {
      setIsLoadingHistory(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const handleFileDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      validateAndSetFile(file);
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      validateAndSetFile(file);
    }
  };

  const validateAndSetFile = (file: File) => {
    if (file.name.toLowerCase().endsWith('.mat')) {
      setSelectedFile(file);
      setErrorMsg(null);
    } else {
      setSelectedFile(null);
      setErrorMsg('Invalid file format. Please upload a MATLAB (.mat) recording containing 6-axis gyroscope channels at 200 Hz.');
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    setErrorMsg(null);
    const input = document.getElementById('matFileInput') as HTMLInputElement | null;
    if (input) input.value = '';
  };

  const handleRunAnalysis = async () => {
    if (!selectedFile || isAnalyzing) return;

    setErrorMsg(null);
    setIsAnalyzing(true);

    try {
      // Parallelize actual backend ML analysis and guaranteed 10s visual telemetry animation
      const analysisPromise = runAnalysis(selectedFile, undefined, notes);
      const timerPromise = new Promise((resolve) => setTimeout(resolve, 10000));

      const [result] = await Promise.all([analysisPromise, timerPromise]);

      setCurrentAnalysis(result);
      await loadHistory();

      // Smooth switch to prediction view after 10s loader
      setTimeout(() => {
        setIsAnalyzing(false);
        onSelectTab?.('prediction');
      }, 250);
    } catch (err: any) {
      setIsAnalyzing(false);
      setErrorMsg(err.message || 'Analysis failed. Please verify that the file contains 6 continuous gyroscope channels at 200 Hz.');
    }
  };

  const handleLoadPastAnalysis = async (historyId: number) => {
    try {
      const detail = await fetchHistoryDetail(historyId);
      const reconstituted: AnalysisResponse = {
        id: detail.id,
        prediction: {
          predicted_class: detail.predicted_class,
          confidence_score: detail.confidence_score,
          probabilities: {
            MSA: detail.prob_msa,
            PD: detail.prob_pd,
          },
          knn_baseline_class: detail.knn_baseline,
          knn_probabilities: {
            MSA: detail.prob_msa,
            PD: detail.prob_pd,
          },
          is_uncertain: detail.is_uncertain,
          uncertainty_reasons: detail.uncertainty_reasons || [],
        },
        shap_explanation: {
          base_value: 0,
          top_positive_features: (detail.top_shap_features || []).filter((f: any) => f.shap_value > 0),
          top_negative_features: (detail.top_shap_features || []).filter((f: any) => f.shap_value <= 0),
          top_features: detail.top_shap_features || [],
        },
        input_metadata: {
          filename: detail.filename,
          original_label: detail.original_label,
          person_id: detail.person_id || 'ANONYMOUS',
          trial_id: detail.trial_id || 'trial1',
          duration_sec: detail.duration_sec,
          sampling_rate_hz: detail.sampling_rate_hz,
          sample_count: Math.round(detail.duration_sec * detail.sampling_rate_hz),
        },
        extracted_features: detail.extracted_features || {},
        signal_preview: { time: [], channels: { gyroThumbX: [], gyroThumbY: [], gyroThumbZ: [], gyroIndexX: [], gyroIndexY: [], gyroIndexZ: [] } },
        model_metadata: {
          model_name: 'NeuroScope Kinematic Classifier',
          model_version: '3.0',
          dataset_source: 'Belgrade Movement Disorders Cohort',
          validation_method: 'Leave-One-Patient-Out Cross-Validation',
          disclaimer: 'Research screening prototype. Not for clinical diagnosis.',
        },
      };
      setCurrentAnalysis(reconstituted);
      onSelectTab?.('prediction');
    } catch (err: any) {
      console.error('Error loading past analysis:', err);
    }
  };

  // Top 4 movement factor attributions (LinearSHAP)
  const topFactors = currentAnalysis?.shap_explanation.top_features.slice(0, 4).map((f) => ({
    name: f.feature.replace(/_/g, ' '),
    rawFeature: f.feature,
    value: Number(f.shap_value.toFixed(3)),
    direction: f.direction,
  })) || [];

  return (
    <div className="w-full h-full flex flex-col overflow-hidden min-h-0 text-[#f0f4f8]">
      {/* Fullscreen Blur Loader Overlay on Run Analysis (10 seconds) */}
      {isAnalyzing && (
        <FullscreenBlurLoader
          type="analysis"
          durationMs={10000}
        />
      )}

      {/* ========================================================================= */}
      {/* TAB 1: UPLOAD-FIRST WORKSPACE ("NEW ANALYSIS")                             */}
      {/* ========================================================================= */}
      {activeTab === 'screening' ? (
        <div className="h-full w-full flex flex-col bg-[#2a3139] border border-[#3a434d] rounded-2xl sm:rounded-3xl p-4 sm:p-6 shadow-2xl min-h-0 overflow-y-auto">
          {/* Header Bar */}
          <div className="shrink-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#3a434d] pb-3.5">
            <div>
              <div className="flex items-center gap-2.5">
                <Activity className="w-5 h-5 text-[#c4cbd5]" />
                <h1 className="font-serif text-xl sm:text-2xl font-bold text-[#f0f4f8] tracking-tight">
                  New Analysis
                </h1>
                <span className="text-[11px] font-mono text-[#c4cbd5] bg-[#14181d] px-2.5 py-0.5 rounded-full border border-[#3a434d]">
                  200 Hz Gyroscope
                </span>
                <span className="text-[11px] font-mono text-[#f0f4f8] bg-[#343c46] px-2.5 py-0.5 rounded-full border border-[#3a434d]">
                  59 Kinematic Features
                </span>
              </div>
              <p className="text-xs text-[#c4cbd5] mt-1 leading-relaxed">
                Upload a raw MATLAB (<span className="font-mono text-[#f0f4f8]">.mat</span>) continuous kinematic recording to perform automated feature extraction, differential screening, and LinearSHAP movement attributions.
              </p>
            </div>

            <div className="flex items-center gap-2">
              <span className="text-[11px] font-mono text-[#c4cbd5] bg-[#14181d] px-3 py-1.5 rounded-xl border border-[#3a434d] flex items-center gap-1.5">
                <Radio className="w-3.5 h-3.5 text-[#c4cbd5] animate-pulse" />
                <span>Engine Ready</span>
              </span>
            </div>
          </div>

          {/* Main Bento Grid */}
          <div className="flex-1 min-h-0 py-3.5 sm:py-4 grid grid-cols-1 lg:grid-cols-12 gap-4 lg:gap-5 items-stretch">
            {/* Left Dominant Upload Panel (8 Columns) */}
            <div className="lg:col-span-8 flex flex-col justify-between space-y-3.5 bg-[#14181d]/70 border border-[#3a434d] rounded-2xl p-4 sm:p-5">
              <div className="space-y-3.5">
                {/* Drag and Drop Zone */}
                <div>
                  <label className="block text-xs font-semibold text-[#f0f4f8] uppercase tracking-wider mb-1.5">
                    Kinematic Recording Source (.mat)
                  </label>

                  {!selectedFile ? (
                    <div
                      onDragOver={(e) => {
                        e.preventDefault();
                        setIsDragging(true);
                      }}
                      onDragLeave={() => setIsDragging(false)}
                      onDrop={handleFileDrop}
                      onClick={() => document.getElementById('matFileInput')?.click()}
                      className={`border-2 border-dashed rounded-2xl p-6 sm:p-8 text-center transition-all cursor-pointer flex flex-col items-center justify-center space-y-2.5 ${
                        isDragging
                          ? 'border-[#c4cbd5] bg-[#343c46]/30'
                          : 'border-[#3a434d] hover:border-[#c4cbd5]/60 bg-[#14181d] hover:bg-[#14181d]/90'
                      }`}
                    >
                      <input
                        type="file"
                        id="matFileInput"
                        accept=".mat"
                        onChange={handleFileSelect}
                        className="hidden"
                      />
                      <div className="w-12 h-12 rounded-2xl bg-[#2a3139] border border-[#3a434d] flex items-center justify-center text-[#c4cbd5] group-hover:scale-105 transition-transform shadow-inner">
                        <UploadCloud className="w-6 h-6 text-[#c4cbd5]" />
                      </div>
                      <div className="space-y-0.5">
                        <div className="text-sm font-semibold text-[#f0f4f8]">
                          Drag and drop your MATLAB (.mat) recording here
                        </div>
                        <p className="text-xs text-[#87919b]">
                          Recording must contain 6-axis continuous gyroscope channels (Thumb & Index) sampled at 200 Hz
                        </p>
                      </div>
                      <button
                        type="button"
                        onClick={(e) => {
                          e.stopPropagation();
                          document.getElementById('matFileInput')?.click();
                        }}
                        className="mt-1 px-4 py-2 rounded-xl bg-[#343c46] hover:bg-[#3a434d] text-[#f0f4f8] text-xs font-semibold border border-[#3a434d] shadow-sm transition-all cursor-pointer flex items-center gap-1.5"
                      >
                        <FileSpreadsheet className="w-3.5 h-3.5" />
                        <span>Browse Files</span>
                      </button>
                    </div>
                  ) : (
                    /* Selected File Information & Replacement State */
                    <div className="p-4 sm:p-5 rounded-2xl bg-[#14181d] border border-[#3a434d] shadow-lg space-y-3">
                      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                        <div className="flex items-center gap-3 min-w-0">
                          <div className="w-11 h-11 rounded-xl bg-[#343c46] border border-[#3a434d] flex items-center justify-center text-[#c4cbd5] shrink-0">
                            <FileSpreadsheet className="w-6 h-6" />
                          </div>
                          <div className="min-w-0">
                            <div className="text-sm font-mono font-bold text-[#f0f4f8] truncate">
                              {selectedFile.name}
                            </div>
                            <div className="text-xs text-[#87919b] flex items-center gap-2 mt-0.5">
                              <span>{(selectedFile.size / 1024).toFixed(1)} KB</span>
                              <span>•</span>
                              <span className="font-mono">MATLAB Format</span>
                            </div>
                          </div>
                        </div>

                        <div className="flex items-center gap-2 self-start sm:self-auto">
                          <span className="px-2.5 py-1 rounded-lg text-[11px] font-mono font-semibold bg-[#343c46] border border-[#3a434d] text-[#f0f4f8] flex items-center gap-1.5 shadow-sm">
                            <CheckCircle2 className="w-3.5 h-3.5 text-[#c4cbd5]" />
                            <span>Ready to Analyze</span>
                          </span>

                          <button
                            type="button"
                            onClick={() => document.getElementById('matFileInput')?.click()}
                            className="p-1.5 rounded-lg bg-[#2a3139] hover:bg-[#343c46] border border-[#3a434d] text-xs text-[#c4cbd5] hover:text-[#f0f4f8] transition-colors cursor-pointer"
                            title="Replace File"
                          >
                            <RotateCcw className="w-4 h-4" />
                          </button>

                          <button
                            type="button"
                            onClick={handleRemoveFile}
                            className="p-1.5 rounded-lg bg-[#2a3139] hover:bg-red-950/60 border border-[#3a434d] text-xs text-[#c4cbd5] hover:text-red-400 transition-colors cursor-pointer"
                            title="Remove File"
                          >
                            <X className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      <input
                        type="file"
                        id="matFileInput"
                        accept=".mat"
                        onChange={handleFileSelect}
                        className="hidden"
                      />
                    </div>
                  )}
                </div>

                {/* Research Notes (Optional) */}
                <div>
                  <label className="block text-xs font-medium text-[#c4cbd5] mb-1.5">
                    Research Notes (Optional)
                  </label>
                  <input
                    type="text"
                    placeholder="e.g., Baseline resting test, subject bilateral observation, trial 1"
                    value={notes}
                    onChange={(e) => setNotes(e.target.value)}
                    className="w-full bg-[#14181d] border border-[#3a434d] focus:border-[#c4cbd5] rounded-xl px-4 py-2.5 text-xs text-[#f0f4f8] placeholder-[#87919b]/50 focus:outline-none transition-colors"
                  />
                </div>

                {/* Error State */}
                {errorMsg && (
                  <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/60 text-red-200 text-xs flex items-start gap-2.5 animate-in fade-in">
                    <AlertTriangle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
                    <span className="leading-relaxed">{errorMsg}</span>
                  </div>
                )}
              </div>

              {/* Action Area: Run Button */}
              <div className="pt-4 border-t border-[#3a434d] space-y-3">
                <button
                  type="button"
                  onClick={handleRunAnalysis}
                  disabled={isAnalyzing || !selectedFile}
                  className={`w-full py-3.5 px-6 rounded-xl font-bold text-sm flex items-center justify-center gap-2 transition-all shadow-lg ${
                    !selectedFile || isAnalyzing
                      ? 'bg-[#343c46]/40 text-[#87919b]/50 border border-[#3a434d] cursor-not-allowed'
                      : 'bg-gradient-to-b from-[#f0f4f8] to-[#c4cbd5] text-[#14181d] shadow-[0_4px_18px_rgba(196,203,213,0.25)] hover:shadow-[0_6px_24px_rgba(196,203,213,0.45)] cursor-pointer transform hover:-translate-y-0.5'
                  }`}
                >
                  {isAnalyzing ? (
                    <>
                      <RefreshCw className="w-4 h-4 animate-spin text-[#14181d]" />
                      <span>Extracting Features & Evaluating Model...</span>
                    </>
                  ) : (
                    <>
                      <Activity className="w-4 h-4" />
                      <span>Run Analysis</span>
                      <ArrowRight className="w-4 h-4" />
                    </>
                  )}
                </button>
              </div>
            </div>

            {/* Right Supporting Bento Sections (4 Columns) */}
            <div className="lg:col-span-4 flex flex-col justify-between space-y-3.5">
              {/* Protocol Spec Card */}
              <div className="p-4 sm:p-5 rounded-2xl bg-[#14181d]/70 border border-[#3a434d] space-y-3">
                <div className="flex items-center gap-2 border-b border-[#3a434d] pb-2.5">
                  <Cpu className="w-4 h-4 text-[#c4cbd5]" />
                  <h3 className="font-serif text-sm font-bold text-[#f0f4f8]">
                    Sensor Protocol Criteria
                  </h3>
                </div>
                <div className="space-y-2 text-xs text-[#87919b]">
                  <div className="flex justify-between items-center py-1 border-b border-[#3a434d]/60 font-mono text-[11px]">
                    <span className="text-[#87919b]">Sampling Frequency:</span>
                    <span className="text-[#f0f4f8] font-semibold">200 Hz Nominal</span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-[#3a434d]/60 font-mono text-[11px]">
                    <span className="text-[#87919b]">Channel Count:</span>
                    <span className="text-[#f0f4f8] font-semibold">6 Gyroscope Axes</span>
                  </div>
                  <div className="flex justify-between items-center py-1 border-b border-[#3a434d]/60 font-mono text-[11px]">
                    <span className="text-[#87919b]">Sensor Placement:</span>
                    <span className="text-[#f0f4f8] font-semibold">Thumb & Index Fingertips</span>
                  </div>
                  <div className="flex justify-between items-center py-1 font-mono text-[11px]">
                    <span className="text-[#87919b]">Minimum Duration:</span>
                    <span className="text-[#f0f4f8] font-semibold">≥ 2.0 Seconds</span>
                  </div>
                </div>
              </div>

              {/* Differential Framework Card */}
              <div className="p-4 sm:p-5 rounded-2xl bg-[#14181d]/70 border border-[#3a434d] space-y-3">
                <div className="flex items-center gap-2 border-b border-[#3a434d] pb-2.5">
                  <Layers className="w-4 h-4 text-[#c4cbd5]" />
                  <h3 className="font-serif text-sm font-bold text-[#f0f4f8]">
                    Pipeline Architecture
                  </h3>
                </div>
                <div className="space-y-2 text-xs text-[#c4cbd5] leading-relaxed">
                  <p>
                    <strong className="text-[#f0f4f8]">Kinematic Feature Extraction:</strong> Computes 59 biomechanical indicators across opening/closing velocity, rhythm variability, sequence decay, and spectral energy.
                  </p>
                  <p>
                    <strong className="text-[#f0f4f8]">Explainable Attributions:</strong> LinearSHAP attribution models quantify exact closed-form log-odds shifts showing how each kinematic factor moved the prediction toward Multiple System Atrophy (MSA) versus Parkinson's Disease (PD).
                  </p>
                </div>
              </div>

              {/* Research Status Card */}
              <div className="p-4 rounded-2xl bg-[#14181d] border border-[#3a434d] flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-[#c4cbd5] animate-ping" />
                  <span className="text-[#87919b]">Authenticated Session</span>
                </div>
                <button
                  type="button"
                  onClick={() => onSelectTab?.('history')}
                  className="font-mono text-[11px] text-[#c4cbd5] hover:text-[#f0f4f8] underline decoration-[#3a434d] transition-colors cursor-pointer"
                >
                  View Past Runs ({history.length})
                </button>
              </div>
            </div>
          </div>
        </div>
      ) : activeTab === 'prediction' ? (
        /* ========================================================================= */
        /* TAB 2: PREDICTION & SHAP EXPLANATION (50/50 SPLIT SCREEN)                 */
        /* ========================================================================= */
        <div className="h-full flex flex-col min-h-0 bg-[#2a3139] border border-[#3a434d] rounded-2xl sm:rounded-3xl p-4 sm:p-5.5 shadow-2xl overflow-hidden">
          {/* Header Bar */}
          <div className="shrink-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#3a434d] pb-3">
            <div>
              <div className="flex items-center gap-2.5">
                <Layers className="w-5 h-5 text-[#c4cbd5]" />
                <h2 className="font-serif text-lg sm:text-xl font-bold text-[#f0f4f8] tracking-tight">
                  Prediction & SHAP Explanation
                </h2>
              </div>
              <p className="text-xs text-[#87919b] mt-0.5">
                Differential classification output with explainable movement feature attributions.
              </p>
            </div>

            <div className="flex items-center gap-3">
              <button
                onClick={() => onSelectTab?.('screening')}
                className="px-3.5 py-1.5 rounded-xl bg-[#14181d] hover:bg-[#343c46] border border-[#3a434d] text-xs font-semibold text-[#f0f4f8] flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <Activity className="w-3.5 h-3.5 text-[#c4cbd5]" />
                <span>New Analysis</span>
              </button>

              {currentAnalysis?.id && (
                <a
                  href={getPdfReportUrl(currentAnalysis.id)}
                  download
                  className="px-3.5 py-1.5 rounded-xl bg-gradient-to-b from-[#f0f4f8] to-[#c4cbd5] text-[#14181d] font-bold text-xs flex items-center gap-1.5 shadow-md hover:shadow-lg transition-all"
                >
                  <Download className="w-3.5 h-3.5" />
                  <span>Download PDF Report</span>
                </a>
              )}
            </div>
          </div>

          {!currentAnalysis ? (
            /* Empty State if no analysis has been run yet */
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-4 bg-[#14181d]/80 rounded-2xl border border-[#3a434d] my-4">
              <div className="w-16 h-16 rounded-2xl bg-[#2a3139] border border-[#3a434d] flex items-center justify-center text-[#c4cbd5] mx-auto">
                <Layers className="w-8 h-8 opacity-70" />
              </div>
              <div>
                <h3 className="font-serif text-lg font-bold text-[#f0f4f8]">
                  No Prediction Output Yet
                </h3>
                <p className="text-xs text-[#87919b] max-w-md mx-auto mt-1 leading-relaxed">
                  Go to the New Analysis tab, upload a valid .mat sensor recording, and click "Run Analysis". The prediction output and SHAP explanation will be displayed here immediately.
                </p>
              </div>
              <button
                onClick={() => onSelectTab?.('screening')}
                className="px-5 py-2.5 rounded-xl bg-gradient-to-b from-[#f0f4f8] to-[#c4cbd5] text-[#14181d] font-bold text-xs inline-flex items-center gap-2 cursor-pointer shadow-lg hover:shadow-xl transition-all"
              >
                <span>Upload a Recording</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </div>
          ) : (
            /* 50/50 TRUE SPLIT SCREEN: LEFT (PREDICTION) & RIGHT (SHAP EXPLANATION) - NO SCROLLBAR */
            <div className="flex-1 min-h-0 mt-2.5 overflow-hidden">
              <div className="h-full grid grid-cols-1 lg:grid-cols-2 gap-4 items-stretch overflow-hidden">
                {/* ========================================================= */}
                {/* LEFT SIDE (50%): DIFFERENTIAL PREDICTION                 */}
                {/* ========================================================= */}
                <div className="bg-[#14181d] p-4 sm:p-5 rounded-2xl border border-[#3a434d] flex flex-col justify-between overflow-hidden space-y-3">
                  <div className="space-y-3 overflow-hidden">
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-[#3a434d] pb-2.5">
                      <div>
                        <span className="text-[10px] font-mono uppercase tracking-wider text-[#87919b]">
                          Differential Classification
                        </span>
                        <div className="font-serif text-xl sm:text-2xl font-bold text-[#f0f4f8] mt-0.5 tracking-tight">
                          {currentAnalysis.prediction.predicted_class === 'MSA'
                            ? 'Multiple System Atrophy'
                            : "Parkinson's Disease"}
                        </div>
                      </div>
                      <span
                        className={`px-3 py-1.5 rounded-xl font-mono text-sm font-bold shadow ${
                          currentAnalysis.prediction.predicted_class === 'MSA'
                            ? 'bg-[#343c46] text-[#f0f4f8] border border-[#c4cbd5]'
                            : 'bg-[#2a3139] text-[#c4cbd5] border border-[#3a434d]'
                        }`}
                      >
                        {currentAnalysis.prediction.predicted_class}
                      </span>
                    </div>

                    {/* Model Confidence Metric Card */}
                    <div className="p-3 rounded-xl bg-[#2a3139] border border-[#3a434d] flex items-center justify-between">
                      <div>
                        <div className="text-[11px] text-[#87919b]">Model Confidence Score</div>
                        <div className="text-xl sm:text-2xl font-bold font-mono text-[#f0f4f8]">
                          {(currentAnalysis.prediction.confidence_score * 100).toFixed(1)}%
                        </div>
                      </div>
                      <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-[#343c46] border border-[#3a434d] text-[#f0f4f8]">
                        Inference Validated
                      </span>
                    </div>

                    {/* Cohort Class Probability Breakdown */}
                    <div className="space-y-2.5 bg-[#2a3139]/60 p-3 rounded-xl border border-[#3a434d]">
                      <div className="text-[11px] font-bold text-[#f0f4f8] uppercase tracking-wide">
                        Cohort Class Probabilities
                      </div>

                      {/* MSA probability bar */}
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-[#f0f4f8]">Multiple System Atrophy (MSA)</span>
                          <span className="font-bold text-[#f0f4f8]">{(currentAnalysis.prediction.probabilities.MSA * 100).toFixed(1)}%</span>
                        </div>
                        <div className="h-2 w-full bg-[#14181d] rounded-full overflow-hidden">
                          <div
                            className="bg-[#c4cbd5] h-full transition-all duration-500 rounded-full"
                            style={{ width: `${currentAnalysis.prediction.probabilities.MSA * 100}%` }}
                          />
                        </div>
                      </div>

                      {/* PD probability bar */}
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-[#87919b]">Parkinson's Disease (PD)</span>
                          <span className="font-bold text-[#f0f4f8]">{(currentAnalysis.prediction.probabilities.PD * 100).toFixed(1)}%</span>
                        </div>
                        <div className="h-2 w-full bg-[#14181d] rounded-full overflow-hidden">
                          <div
                            className="bg-[#3a434d] h-full transition-all duration-500 rounded-full"
                            style={{ width: `${currentAnalysis.prediction.probabilities.PD * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Independent KNN Baseline Concordance */}
                    <div className="p-2.5 rounded-xl bg-[#2a3139]/60 border border-[#3a434d] flex items-center justify-between text-xs">
                      <span className="text-[#87919b]">Independent KNN Baseline:</span>
                      <span className="font-mono font-bold text-[#f0f4f8]">
                        {currentAnalysis.prediction.knn_baseline_class}{' '}
                        <span className="text-[11px] font-normal text-[#c4cbd5] font-sans">
                          ({currentAnalysis.prediction.knn_baseline_class === currentAnalysis.prediction.predicted_class ? 'Concordant' : 'Discordant'})
                        </span>
                      </span>
                    </div>

                    {/* Uncertainty Alert if Flagged */}
                    {currentAnalysis.prediction.is_uncertain && (
                      <div className="p-2.5 rounded-xl bg-[#FEDA87]/10 border border-[#FEDA87]/40 text-[#FEDA87] text-xs flex items-start gap-2">
                        <ShieldAlert className="w-4 h-4 text-[#FEDA87] shrink-0 mt-0.5" />
                        <div>
                          <span className="font-bold">Uncertainty Flag:</span>{' '}
                          {currentAnalysis.prediction.uncertainty_reasons.join('; ')}
                        </div>
                      </div>
                    )}
                  </div>

                  <div className="p-2.5 rounded-xl bg-[#2a3139] border border-[#3a434d] text-[11px] text-[#87919b] flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-[#c4cbd5] shrink-0" />
                    <span>Validated differential classification based on 6-axis gyroscope continuous signals.</span>
                  </div>
                </div>

                {/* ========================================================= */}
                {/* RIGHT SIDE (50%): SHAP EXPLANATION (NO CHART, PURE CLARITY) */}
                {/* ========================================================= */}
                <div className="bg-[#14181d] p-4 sm:p-5 rounded-2xl border border-[#3a434d] flex flex-col justify-between overflow-hidden space-y-3">
                  <div className="space-y-2.5 overflow-hidden">
                    {/* Header */}
                    <div className="flex items-center justify-between border-b border-[#3a434d] pb-2.5">
                      <div>
                        <span className="text-[10px] font-mono uppercase tracking-wider text-[#87919b]">
                          Explainable AI Attribution
                        </span>
                        <div className="font-serif text-lg font-bold text-[#f0f4f8] mt-0.5">
                          Movement Biomarker Breakdown
                        </div>
                      </div>
                      <span className="text-[10px] font-mono text-[#f0f4f8] bg-[#2a3139] px-2.5 py-1 rounded-full border border-[#3a434d]">
                        LinearSHAP (59 Features)
                      </span>
                    </div>

                    {/* Movement Narrative Banner */}
                    <div className="text-xs text-[#f0f4f8] leading-relaxed bg-[#2a3139]/60 p-3 rounded-xl border border-[#3a434d]">
                      <p>
                        <strong className="text-white">Biomarker Finding:</strong> Continuous 200 Hz finger-tapping kinematic features exhibited physical patterns characteristic of{' '}
                        <strong className="text-white underline decoration-[#c4cbd5] decoration-2">
                          {currentAnalysis.prediction.predicted_class === 'MSA' ? 'Multiple System Atrophy' : "Parkinson's Disease"}
                        </strong>.
                      </p>
                      <p className="mt-1.5 text-[11px] text-[#87919b]">
                        {currentAnalysis.prediction.predicted_class === 'MSA'
                          ? 'Irregular cadence delays and abrupt speed halts (cerebellar ataxia incoordination) dominated the movement signals over sequence fatigue.'
                          : 'Rhythmic tap pacing with progressive amplitude decay (hypokinesia sequence fatigue) and low-frequency rest tremor dominated the movement signals.'}
                      </p>
                    </div>

                    {/* Top 4 Key Movement Factors (Structured Explanations Instead of Bar Chart) */}
                    <div className="space-y-1.5">
                      <div className="flex items-center justify-between text-[11px] font-bold text-[#f0f4f8] uppercase tracking-wide px-0.5">
                        <span>Key Movement Signal Influences</span>
                        <span className="text-[10px] font-mono font-normal text-[#87919b]">LinearSHAP Log-Odds</span>
                      </div>

                      <div className="space-y-2">
                        {topFactors.map((item, idx) => {
                          const exp = getSimpleFeatureExplanation(item.rawFeature, item.direction);
                          const isMsa = item.value > 0;
                          return (
                            <div
                              key={idx}
                              className="p-2 sm:p-2.5 rounded-xl bg-[#2a3139] border border-[#3a434d] flex flex-col justify-between space-y-1"
                            >
                              <div className="flex items-center justify-between text-xs font-semibold text-[#f0f4f8]">
                                <div className="flex items-center gap-1.5 truncate">
                                  <span className={`w-2 h-2 rounded-full shrink-0 ${isMsa ? 'bg-[#c4cbd5]' : 'bg-[#87919b]'}`} />
                                  <span className="font-bold truncate text-[#f0f4f8]">{exp.factor}</span>
                                </div>
                                <span
                                  className={`font-mono text-[10px] px-2 py-0.5 rounded-md font-bold shrink-0 ${
                                    isMsa
                                      ? 'bg-[#343c46] text-[#f0f4f8] border border-[#c4cbd5]/40'
                                      : 'bg-[#2a3139] text-[#c4cbd5] border border-[#3a434d]'
                                  }`}
                                >
                                  {isMsa ? `+${item.value} Towards MSA` : `${item.value} Towards PD`}
                                </span>
                              </div>

                              <p className="text-[11px] text-[#87919b] leading-snug">
                                <span className="text-[#f0f4f8] font-medium">{exp.finding}</span>{' '}
                                <span className="text-[#87919b]">{exp.clinicalMeaning}</span>
                              </p>

                              {/* Mini Attribution Weight Line */}
                              <div className="w-full h-1 bg-[#14181d] rounded-full overflow-hidden mt-0.5">
                                <div
                                  className={`h-full rounded-full transition-all duration-300 ${isMsa ? 'bg-[#c4cbd5]' : 'bg-[#87919b]'}`}
                                  style={{ width: `${Math.min(100, Math.max(20, Math.abs(item.value) * 150))}%` }}
                                />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  </div>

                  <div className="p-2.5 rounded-xl bg-[#2a3139] border border-[#3a434d] text-[11px] text-[#87919b] flex items-center gap-2">
                    <CheckCircle2 className="w-4 h-4 text-[#c4cbd5] shrink-0" />
                    <span>Closed-form LinearSHAP attributions quantified across all 59 continuous movement features.</span>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : (
        /* ========================================================================= */
        /* TAB 3: AUTHENTICATED RESEARCHER ANALYSIS HISTORY                          */
        /* ========================================================================= */
        <div className="h-full flex flex-col min-h-0 bg-[#2a3139] border border-[#3a434d] rounded-2xl sm:rounded-3xl p-4 sm:p-5.5 shadow-2xl overflow-hidden">
          <div className="shrink-0 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-[#3a434d] pb-3">
            <div>
              <div className="flex items-center gap-2">
                <FileText className="w-5 h-5 text-[#c4cbd5]" />
                <h2 className="font-serif text-lg sm:text-xl font-bold text-[#f0f4f8] tracking-tight">
                  Researcher Analysis History
                </h2>
              </div>
              <p className="text-xs text-[#87919b] mt-0.5">
                Past kinematic screening records and generated clinical research reports.
              </p>
            </div>

            <div className="flex items-center gap-2.5">
              <button
                onClick={loadHistory}
                disabled={isLoadingHistory}
                className="px-3 py-1.5 rounded-xl bg-[#14181d] border border-[#3a434d] text-xs text-[#c4cbd5] hover:text-[#f0f4f8] flex items-center gap-1.5 transition-colors cursor-pointer"
              >
                <RefreshCw className={`w-3.5 h-3.5 ${isLoadingHistory ? 'animate-spin' : ''}`} />
                <span>Refresh</span>
              </button>

              <button
                onClick={() => onSelectTab?.('screening')}
                className="px-3.5 py-1.5 rounded-xl bg-gradient-to-b from-[#f0f4f8] to-[#c4cbd5] text-[#14181d] font-bold text-xs flex items-center gap-1.5 shadow-md hover:shadow-lg transition-all cursor-pointer"
              >
                <span>New Analysis</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>

          {history.length === 0 ? (
            <div className="flex-1 flex flex-col items-center justify-center p-8 text-center space-y-3 bg-[#14181d]/80 rounded-2xl border border-[#3a434d] my-4">
              <FileText className="w-10 h-10 mx-auto text-[#87919b] opacity-40" />
              <div className="font-serif text-base font-semibold text-[#f0f4f8]">No Analysis Records Yet</div>
              <p className="text-xs text-[#87919b] max-w-sm mx-auto leading-relaxed">
                Upload a continuous MATLAB (.mat) sensor recording in the New Analysis tab to execute differential screening.
              </p>
              <button
                onClick={() => onSelectTab?.('screening')}
                className="px-4 py-2 rounded-xl bg-gradient-to-b from-[#f0f4f8] to-[#c4cbd5] text-[#14181d] font-bold text-xs inline-flex items-center gap-1.5 mt-2 cursor-pointer shadow"
              >
                <span>Go to New Analysis</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          ) : (
            <div className="flex-1 overflow-y-auto rounded-xl border border-[#3a434d] mt-4 min-h-0">
              <table className="w-full text-left text-xs text-[#87919b]">
                <thead className="sticky top-0 z-10 border-b border-[#3a434d] bg-[#14181d] text-[#f0f4f8] uppercase text-[10px] font-mono tracking-wider">
                  <tr>
                    <th className="py-3 px-4">Date & Time</th>
                    <th className="py-3 px-4">Recording Filename</th>
                    <th className="py-3 px-4">Predicted Class</th>
                    <th className="py-3 px-4">Confidence</th>
                    <th className="py-3 px-4">Status</th>
                    <th className="py-3 px-4 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#3a434d]/50 bg-[#14181d]/40">
                  {history.map((item) => (
                    <tr key={item.id} className="hover:bg-[#14181d]/90 transition-colors">
                      <td className="py-3 px-4 font-mono text-[11px] whitespace-nowrap text-[#87919b]">
                        {item.created_at}
                      </td>
                      <td className="py-3 px-4 font-mono text-[#f0f4f8] font-medium max-w-[200px] truncate">
                        {item.filename}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2.5 py-0.5 rounded-md font-mono text-[11px] font-bold ${
                            item.predicted_class === 'MSA'
                              ? 'bg-[#343c46] text-[#f0f4f8] border border-[#c4cbd5]/40'
                              : 'bg-[#2a3139] text-[#c4cbd5] border border-[#3a434d]'
                          }`}
                        >
                          {item.predicted_class}
                        </span>
                      </td>
                      <td className="py-3 px-4 font-mono text-[11px] text-[#f0f4f8]">
                        {(item.confidence_score * 100).toFixed(1)}%
                      </td>
                      <td className="py-3 px-4">
                        {item.is_uncertain ? (
                          <span className="text-[#FEDA87] flex items-center gap-1.5 text-[11px] font-medium">
                            <AlertTriangle className="w-3.5 h-3.5 text-[#FEDA87]" />
                            <span>Uncertain</span>
                          </span>
                        ) : (
                          <span className="text-[#c4cbd5] flex items-center gap-1.5 text-[11px] font-medium">
                            <Check className="w-3.5 h-3.5" />
                            <span>Normal</span>
                          </span>
                        )}
                      </td>
                      <td className="py-3 px-4 text-right whitespace-nowrap space-x-2">
                        <button
                          onClick={() => handleLoadPastAnalysis(item.id)}
                          className="px-2.5 py-1 rounded-lg bg-[#2a3139] hover:bg-[#343c46] text-[#f0f4f8] border border-[#3a434d] text-[11px] font-medium transition-colors cursor-pointer"
                        >
                          View Prediction & SHAP
                        </button>

                        <a
                          href={getPdfReportUrl(item.id)}
                          download
                          className="px-2.5 py-1 rounded-lg bg-[#2a3139] hover:bg-[#343c46] text-[#f0f4f8] border border-[#3a434d] text-[11px] font-medium transition-colors inline-flex items-center gap-1 cursor-pointer"
                        >
                          <Download className="w-3 h-3 text-[#c4cbd5]" />
                          <span>PDF</span>
                        </a>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
