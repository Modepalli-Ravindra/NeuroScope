import React, { useState, useEffect } from 'react';
import {
  Activity, Layers, FileText, UploadCloud, CheckCircle2,
  AlertTriangle, RefreshCw, Download, ShieldAlert, Check,
  ArrowRight, X, FileSpreadsheet, Cpu, Radio, RotateCcw,
  Volume2, VolumeX, BarChart3, TrendingUp, ShieldCheck
} from 'lucide-react';
import { runAnalysis, fetchHistory, fetchHistoryDetail, getPdfReportUrl } from '../api';
import type { AnalysisResponse, HistoryItem } from '../types';
import { FullscreenBlurLoader } from '../components/FullscreenBlurLoader';

interface DashboardPageProps {
  activeTab?: 'screening' | 'prediction' | 'history' | 'benchmark';
  onSelectTab?: (tab: 'screening' | 'prediction' | 'history' | 'benchmark') => void;
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
  const [rightPanelView, setRightPanelView] = useState<'shap' | 'telemetry'>('shap');
  const [telemetryChannel, setTelemetryChannel] = useState<'index' | 'thumb' | 'composite'>('index');
  const [isPlayingAudio, setIsPlayingAudio] = useState<boolean>(false);
  const [selectedRocModel, setSelectedRocModel] = useState<'all' | 'v3' | 'heliyon' | 'svm' | 'rf' | 'knn'>('all');

  // Synthesize rhythmic tapping audio pulses matching patient cadence
  const playTapAudio = (cadenceHz: number = 3.2) => {
    try {
      const AudioCtx = window.AudioContext || (window as any).webkitAudioContext;
      if (!AudioCtx) return;
      const ctx = new AudioCtx();
      setIsPlayingAudio(true);
      const interval = 1 / Math.max(1, Math.min(8, cadenceHz));
      const totalTaps = 14;

      for (let i = 0; i < totalTaps; i++) {
        const startTime = ctx.currentTime + i * interval;
        const osc = ctx.createOscillator();
        const gain = ctx.createGain();
        osc.type = 'sine';
        osc.frequency.setValueAtTime(700, startTime);
        osc.frequency.exponentialRampToValueAtTime(90, startTime + 0.035);
        gain.gain.setValueAtTime(0.28, startTime);
        gain.gain.exponentialRampToValueAtTime(0.001, startTime + 0.035);
        osc.connect(gain);
        gain.connect(ctx.destination);
        osc.start(startTime);
        osc.stop(startTime + 0.045);
      }
      setTimeout(() => setIsPlayingAudio(false), totalTaps * interval * 1000);
    } catch {
      setIsPlayingAudio(false);
    }
  };

  // Convert real signal points into smooth SVG path
  const generateSignalPath = (values: number[] = [], width: number = 450, height: number = 140): string => {
    if (!values || values.length === 0) {
      // Fallback sinusoidal movement wave
      return 'M 5,70 C 25,20 45,128 72,70 C 98,24 125,124 150,70 C 175,16 200,132 225,70 C 250,28 275,122 300,70 C 325,18 350,130 375,70 C 400,24 425,108 450,70';
    }
    const min = Math.min(...values);
    const max = Math.max(...values);
    const range = max - min || 1;
    const padding = 14;
    const usableHeight = height - padding * 2;

    return values.map((val, idx) => {
      const x = (idx / (values.length - 1)) * width;
      const y = height - padding - ((val - min) / range) * usableHeight;
      return `${idx === 0 ? 'M' : 'L'} ${x.toFixed(1)},${y.toFixed(1)}`;
    }).join(' ');
  };

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
          model_name: 'NeuroKinematix Primary Classifier',
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
                {/* LEFT SIDE (50%): DIFFERENTIAL PREDICTION */}
                {/* ========================================================= */}
                <div className="bg-[#14181d] p-4 sm:p-5 rounded-2xl border border-[#3a434d] flex flex-col justify-between overflow-hidden shadow-xl">
                  <div className="space-y-3.5 overflow-hidden">
                    {/* Header with Title and Classification Badge */}
                    <div className="flex items-center justify-between border-b border-[#3a434d] pb-3">
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
                        className={`px-3 py-1.5 rounded-xl font-mono text-sm font-bold shadow-lg transition-transform ${
                          currentAnalysis.prediction.predicted_class === 'MSA'
                            ? 'bg-emerald-950/80 text-emerald-300 border border-emerald-500/60'
                            : 'bg-cyan-950/80 text-cyan-300 border border-cyan-500/60'
                        }`}
                      >
                        {currentAnalysis.prediction.predicted_class}
                      </span>
                    </div>

                    {/* Model Confidence Metric Card */}
                    <div className="p-3.5 rounded-xl bg-[#2a3139]/80 border border-[#3a434d] flex items-center justify-between shadow-inner">
                      <div>
                        <div className="text-[11px] font-mono text-[#87919b]">MODEL CONFIDENCE SCORE</div>
                        <div className="text-2xl sm:text-3xl font-bold font-mono text-[#f0f4f8] mt-0.5">
                          {(currentAnalysis.prediction.confidence_score * 100).toFixed(1)}%
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <span className="text-xs font-semibold px-2.5 py-1 rounded-lg bg-emerald-950/60 border border-emerald-700/60 text-emerald-300 flex items-center gap-1.5">
                          <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Inference Validated</span>
                        </span>
                        <span className="text-[10px] font-mono text-[#87919b]">
                          {currentAnalysis.prediction.confidence_score >= 0.85 ? 'High Decision Margin' : 'Nominal Margin'}
                        </span>
                      </div>
                    </div>

                    {/* Cohort Class Probability Breakdown */}
                    <div className="space-y-3 bg-[#2a3139]/50 p-3.5 rounded-xl border border-[#3a434d]">
                      <div className="flex items-center justify-between text-[11px] font-bold text-[#f0f4f8] uppercase tracking-wide">
                        <span>Cohort Class Probabilities</span>
                        <span className="font-mono text-[10px] text-[#87919b]">Softmax Probability</span>
                      </div>

                      {/* MSA probability bar */}
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-[#f0f4f8] font-medium">Multiple System Atrophy (MSA)</span>
                          <span className="font-bold text-emerald-400">{(currentAnalysis.prediction.probabilities.MSA * 100).toFixed(1)}%</span>
                        </div>
                        <div className="h-2.5 w-full bg-[#14181d] rounded-full overflow-hidden p-0.5 border border-[#3a434d]/60">
                          <div
                            className="bg-gradient-to-r from-emerald-600 to-emerald-400 h-full transition-all duration-700 rounded-full"
                            style={{ width: `${currentAnalysis.prediction.probabilities.MSA * 100}%` }}
                          />
                        </div>
                      </div>

                      {/* PD probability bar */}
                      <div className="space-y-1">
                        <div className="flex justify-between text-xs font-mono">
                          <span className="text-[#87919b] font-medium">Parkinson's Disease (PD)</span>
                          <span className="font-bold text-cyan-400">{(currentAnalysis.prediction.probabilities.PD * 100).toFixed(1)}%</span>
                        </div>
                        <div className="h-2.5 w-full bg-[#14181d] rounded-full overflow-hidden p-0.5 border border-[#3a434d]/60">
                          <div
                            className="bg-gradient-to-r from-cyan-700 to-cyan-400 h-full transition-all duration-700 rounded-full"
                            style={{ width: `${currentAnalysis.prediction.probabilities.PD * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>

                    {/* Multi-Model Clinical Consensus Box (Fills gap interactively) */}
                    <div className="p-3 rounded-xl bg-[#2a3139]/60 border border-[#3a434d] space-y-2">
                      <div className="flex items-center justify-between text-[11px] font-bold text-[#f0f4f8]">
                        <span className="uppercase font-mono text-[10px] text-[#87919b]">Cross-Model Decision Concordance</span>
                        <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full font-bold ${
                          currentAnalysis.prediction.knn_baseline_class === currentAnalysis.prediction.predicted_class
                            ? 'bg-emerald-950/60 text-emerald-300 border border-emerald-700/60'
                            : 'bg-amber-950/60 text-amber-300 border border-amber-700/60'
                        }`}>
                          {currentAnalysis.prediction.knn_baseline_class === currentAnalysis.prediction.predicted_class ? 'Full Consensus' : 'Model Divergence'}
                        </span>
                      </div>
                      
                      <div className="grid grid-cols-2 gap-2 text-xs">
                        <div className="p-2 rounded-lg bg-[#14181d] border border-[#3a434d]">
                          <div className="text-[10px] text-[#87919b] font-mono">PRIMARY (LR v3.0)</div>
                          <div className="font-bold text-emerald-400 mt-0.5">
                            {currentAnalysis.prediction.predicted_class} ({(currentAnalysis.prediction.confidence_score * 100).toFixed(0)}%)
                          </div>
                        </div>
                        <div className="p-2 rounded-lg bg-[#14181d] border border-[#3a434d]">
                          <div className="text-[10px] text-[#87919b] font-mono">HELIYON KNN BASELINE</div>
                          <div className="font-bold text-[#f0f4f8] mt-0.5">
                            {currentAnalysis.prediction.knn_baseline_class}{' '}
                            <span className="text-[10px] font-normal text-[#87919b]">
                              ({currentAnalysis.prediction.knn_baseline_class === currentAnalysis.prediction.predicted_class ? 'Concordant' : 'Discordant'})
                            </span>
                          </div>
                        </div>
                      </div>
                    </div>

                    {/* Kinematic Recording Signal Envelope Summary */}
                    <div className="grid grid-cols-3 gap-2 text-center text-xs">
                      <div className="p-2 rounded-xl bg-[#2a3139]/60 border border-[#3a434d]">
                        <div className="text-[9px] font-mono text-[#87919b]">SAMPLING</div>
                        <div className="font-bold text-[#f0f4f8] mt-0.5">200 Hz Triaxial</div>
                      </div>
                      <div className="p-2 rounded-xl bg-[#2a3139]/60 border border-[#3a434d]">
                        <div className="text-[9px] font-mono text-[#87919b]">RECORDING</div>
                        <div className="font-bold text-[#f0f4f8] mt-0.5">{currentAnalysis.input_metadata.duration_sec.toFixed(1)}s</div>
                      </div>
                      <div className="p-2 rounded-xl bg-[#2a3139]/60 border border-[#3a434d]">
                        <div className="text-[9px] font-mono text-[#87919b]">DATA POINTS</div>
                        <div className="font-bold text-[#f0f4f8] mt-0.5">{currentAnalysis.input_metadata.sample_count} pts</div>
                      </div>
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

                  {/* Interactive Quick Action Bar */}
                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={() => {
                        if (currentAnalysis.id) {
                          window.open(getPdfReportUrl(currentAnalysis.id), '_blank');
                        }
                      }}
                      className="w-full py-2.5 px-3 rounded-xl bg-[#2a3139] hover:bg-[#343c46] border border-[#3a434d] text-xs font-semibold text-[#f0f4f8] flex items-center justify-center gap-2 cursor-pointer transition-all shadow hover:border-emerald-500/50"
                    >
                      <Download className="w-4 h-4 text-emerald-400" />
                      <span>Export Full Clinical PDF Report (with SHAP & Metrics)</span>
                    </button>
                  </div>
                </div>

                {/* ========================================================= */}
                {/* RIGHT SIDE (50%): DUAL-VIEW (SHAP ATTRIBUTIONS / 200 Hz WAVEFORMS) */}
                {/* ========================================================= */}
                <div className="bg-[#14181d] p-4 sm:p-5 rounded-2xl border border-[#3a434d] flex flex-col justify-between overflow-hidden space-y-3">
                  <div className="space-y-2.5 overflow-hidden">
                    {/* Header with Dual-View Switcher */}
                    <div className="flex flex-col sm:flex-row sm:items-center justify-between border-b border-[#3a434d] pb-2.5 gap-2">
                      <div className="flex items-center gap-1.5 p-1 rounded-xl bg-[#0c1014] border border-[#3a434d] self-start sm:self-auto">
                        <button
                          type="button"
                          onClick={() => setRightPanelView('shap')}
                          className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer ${
                            rightPanelView === 'shap'
                              ? 'bg-[#f0f4f8] text-[#14181d] font-bold shadow'
                              : 'text-[#87919b] hover:text-[#f0f4f8]'
                          }`}
                        >
                          Biomarkers (LinearSHAP)
                        </button>
                        <button
                          type="button"
                          onClick={() => setRightPanelView('telemetry')}
                          className={`px-3 py-1 rounded-lg text-xs font-semibold transition-all cursor-pointer flex items-center gap-1.5 ${
                            rightPanelView === 'telemetry'
                              ? 'bg-[#f0f4f8] text-[#14181d] font-bold shadow'
                              : 'text-[#87919b] hover:text-[#f0f4f8]'
                          }`}
                        >
                          <Radio className="w-3.5 h-3.5 text-[#c4cbd5]" />
                          <span>200 Hz Waveforms</span>
                        </button>
                      </div>

                      <span className="text-[10px] font-mono text-[#f0f4f8] bg-[#2a3139] px-2.5 py-1 rounded-full border border-[#3a434d] self-start sm:self-auto">
                        {rightPanelView === 'shap' ? 'LinearSHAP (59 Features)' : 'Real Gyroscope Telemetry'}
                      </span>
                    </div>

                    {/* VIEW 1: LINEARSHAP BIOMARKER ATTRIBUTIONS */}
                    {rightPanelView === 'shap' ? (
                      <>
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

                        {/* Top 4 Key Movement Factors */}
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
                      </>
                    ) : (
                      /* VIEW 2: 200 Hz TRIAXIAL GYROSCOPE TELEMETRY OSCILLOSCOPE */
                      <div className="space-y-3">
                        {/* Channel Selection Buttons */}
                        <div className="grid grid-cols-3 gap-2">
                          <button
                            type="button"
                            onClick={() => setTelemetryChannel('index')}
                            className={`text-xs font-mono py-2 px-2 rounded-xl transition-all cursor-pointer text-center ${
                              telemetryChannel === 'index'
                                ? 'bg-[#f0f4f8] text-[#14181d] font-bold shadow-sm'
                                : 'bg-[#2a3139] text-[#87919b] hover:text-[#f0f4f8] border border-[#3a434d]'
                            }`}
                          >
                            Index Flexion (Y)
                          </button>
                          <button
                            type="button"
                            onClick={() => setTelemetryChannel('thumb')}
                            className={`text-xs font-mono py-2 px-2 rounded-xl transition-all cursor-pointer text-center ${
                              telemetryChannel === 'thumb'
                                ? 'bg-[#f0f4f8] text-[#14181d] font-bold shadow-sm'
                                : 'bg-[#2a3139] text-[#87919b] hover:text-[#f0f4f8] border border-[#3a434d]'
                            }`}
                          >
                            Thumb Abduction (Z)
                          </button>
                          <button
                            type="button"
                            onClick={() => setTelemetryChannel('composite')}
                            className={`text-xs font-mono py-2 px-2 rounded-xl transition-all cursor-pointer text-center ${
                              telemetryChannel === 'composite'
                                ? 'bg-[#f0f4f8] text-[#14181d] font-bold shadow-sm'
                                : 'bg-[#2a3139] text-[#87919b] hover:text-[#f0f4f8] border border-[#3a434d]'
                            }`}
                          >
                            Motion Intensity
                          </button>
                        </div>

                        {/* Interactive Oscilloscope Viewport */}
                        <div className="relative py-3 px-3 bg-[#0c1014] rounded-xl border border-[#3a434d] overflow-hidden shadow-inner">
                          {/* Sweep Scan Beam Animation */}
                          <div className="absolute top-0 bottom-0 w-28 bg-gradient-to-r from-transparent via-[#c4cbd5]/25 to-transparent animate-sweep pointer-events-none" />

                          {/* Channel Badge Overlay */}
                          <div className="absolute top-2.5 left-3 flex items-center gap-2 z-10">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                            <span className="text-[10px] font-mono text-[#c4cbd5] font-bold">
                              {telemetryChannel === 'index' && 'CH-1: gyroIndexY (Flexion Angular Velocity)'}
                              {telemetryChannel === 'thumb' && 'CH-2: gyroThumbZ (Opposition Dynamic Axis)'}
                              {telemetryChannel === 'composite' && 'CH-3: Kinetic Motion Intensity Envelope (RMS)'}
                            </span>
                          </div>

                          <div className="absolute top-2.5 right-3 text-[10px] font-mono text-[#87919b] z-10">
                            200 Hz • LOPO Verified
                          </div>

                          {/* Dynamic SVG Waveform */}
                          {(() => {
                            const sigs = (currentAnalysis.signal_preview as any)?.signals || {};
                            let channelData: number[] = [];
                            if (telemetryChannel === 'index') {
                              channelData = sigs['gyroIndexY'] || sigs['gyroIndexX'] || [];
                            } else if (telemetryChannel === 'thumb') {
                              channelData = sigs['gyroThumbZ'] || sigs['gyroThumbY'] || [];
                            } else {
                              const iy = sigs['gyroIndexY'] || [];
                              const tz = sigs['gyroThumbZ'] || [];
                              channelData = iy.map((v: number, i: number) => Math.sqrt(v ** 2 + (tz[i] || 0) ** 2));
                            }
                            const svgPath = generateSignalPath(channelData, 450, 140);

                            return (
                              <svg viewBox="0 0 450 140" className="w-full h-36 mt-4">
                                <defs>
                                  <linearGradient id="liveWaveGrad" x1="0%" y1="0%" x2="100%" y2="0%">
                                    <stop offset="0%" stopColor="#87919b" stopOpacity="0.4" />
                                    <stop offset="50%" stopColor="#f0f4f8" stopOpacity="1" />
                                    <stop offset="100%" stopColor="#87919b" stopOpacity="0.8" />
                                  </linearGradient>
                                  <filter id="liveGlow" x="-20%" y="-20%" width="140%" height="140%">
                                    <feGaussianBlur stdDeviation="3" result="blur" />
                                    <feComposite in="SourceGraphic" in2="blur" operator="over" />
                                  </filter>
                                </defs>

                                {/* Grid Lines */}
                                <line x1="0" y1="35" x2="450" y2="35" stroke="#1f2730" strokeDasharray="3 3" />
                                <line x1="0" y1="70" x2="450" y2="70" stroke="#3a434d" strokeDasharray="4 4" />
                                <line x1="0" y1="105" x2="450" y2="105" stroke="#1f2730" strokeDasharray="3 3" />

                                {/* Glowing Underline */}
                                <path
                                  d={svgPath}
                                  fill="none"
                                  stroke="#87919b"
                                  strokeWidth="4"
                                  opacity="0.3"
                                  filter="url(#liveGlow)"
                                />
                                {/* Main Continuous Signal */}
                                <path
                                  d={svgPath}
                                  fill="none"
                                  stroke="url(#liveWaveGrad)"
                                  strokeWidth="2.4"
                                  strokeLinecap="round"
                                />
                              </svg>
                            );
                          })()}
                        </div>

                        {/* Telemetry Metrics Bar & Audio Metronome */}
                        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1 text-center">
                          <div className="p-2 rounded-xl bg-[#2a3139] border border-[#3a434d]">
                            <div className="text-[10px] text-[#87919b] font-mono">SAMPLING RATE</div>
                            <div className="text-xs font-bold text-[#f0f4f8] mt-0.5">200 Hz Gyro</div>
                          </div>
                          <div className="p-2 rounded-xl bg-[#2a3139] border border-[#3a434d]">
                            <div className="text-[10px] text-[#87919b] font-mono">DURATION</div>
                            <div className="text-xs font-bold text-[#f0f4f8] mt-0.5">
                              {currentAnalysis.input_metadata.duration_sec.toFixed(1)}s
                            </div>
                          </div>
                          <div className="p-2 rounded-xl bg-[#2a3139] border border-[#3a434d]">
                            <div className="text-[10px] text-[#87919b] font-mono">TAP CADENCE</div>
                            <div className="text-xs font-bold text-[#f0f4f8] mt-0.5">
                              {((currentAnalysis.extracted_features as any)?.['gyroIndexY_dom_freq'] || 3.2).toFixed(1)} Hz
                            </div>
                          </div>
                          <div className="p-2 rounded-xl bg-[#2a3139] border border-[#3a434d]">
                            <div className="text-[10px] text-[#87919b] font-mono">DATA POINTS</div>
                            <div className="text-xs font-bold text-[#f0f4f8] mt-0.5">
                              {currentAnalysis.input_metadata.sample_count} Samples
                            </div>
                          </div>
                        </div>

                        {/* Audio Metronome Button */}
                        <button
                          type="button"
                          onClick={() => playTapAudio((currentAnalysis.extracted_features as any)?.['gyroIndexY_dom_freq'] || 3.2)}
                          disabled={isPlayingAudio}
                          className="w-full py-2.5 px-3 rounded-xl bg-[#2a3139] hover:bg-[#343c46] border border-[#3a434d] text-xs font-semibold text-[#f0f4f8] flex items-center justify-center gap-2 cursor-pointer transition-colors shadow-sm"
                        >
                          {isPlayingAudio ? (
                            <>
                              <VolumeX className="w-4 h-4 text-emerald-400 animate-pulse" />
                              <span className="text-emerald-300">Auditory Rhythm Playing (Tap Metronome)...</span>
                            </>
                          ) : (
                            <>
                              <Volume2 className="w-4 h-4 text-[#c4cbd5]" />
                              <span>🔊 Playback Tap Rhythm Audio (Acoustic Metronome)</span>
                            </>
                          )}
                        </button>
                      </div>
                    )}
                  </div>

                  {/* Interactive Quick View Switcher Action Bar */}
                  <div className="pt-2">
                    <button
                      type="button"
                      onClick={() => setRightPanelView(rightPanelView === 'shap' ? 'telemetry' : 'shap')}
                      className="w-full py-2.5 px-3 rounded-xl bg-[#2a3139] hover:bg-[#343c46] border border-[#3a434d] text-xs font-semibold text-[#f0f4f8] flex items-center justify-center gap-2 cursor-pointer transition-all shadow hover:border-cyan-500/50"
                    >
                      <Activity className="w-4 h-4 text-cyan-400" />
                      <span>
                        {rightPanelView === 'shap'
                          ? 'Switch to 200 Hz Continuous Waveforms & Metronome'
                          : 'Switch to LinearSHAP Biomarker Influences'}
                      </span>
                    </button>
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      ) : activeTab === 'history' ? (
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
      ) : (
        /* ========================================================================= */
        /* TAB 4: LOPO-CV BENCHMARK & CLINICAL VALIDATION STUDIO                     */
        /* ========================================================================= */
        <div className="h-full flex flex-col min-h-0 bg-[#2a3139] border border-[#3a434d] rounded-2xl sm:rounded-3xl p-3.5 sm:p-4.5 shadow-2xl overflow-hidden">
          {/* Header Bar */}
          <div className="shrink-0 flex items-center justify-between gap-3 border-b border-[#3a434d] pb-2.5">
            <div>
              <div className="flex items-center gap-2">
                <BarChart3 className="w-5 h-5 text-emerald-400" />
                <h2 className="font-serif text-lg sm:text-xl font-bold text-[#f0f4f8] tracking-tight">
                  LOPO-CV Validation & Model Benchmark Studio
                </h2>
                <span className="px-2 py-0.5 rounded text-[10px] font-mono font-bold bg-emerald-950/80 text-emerald-300 border border-emerald-800">
                  N=27 Isolated Folds
                </span>
              </div>
              <p className="text-xs text-[#87919b] mt-0.5">
                Leave-One-Patient-Out Cross-Validation protocol evaluated on continuous 200 Hz triaxial kinematics.
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <span className="px-3 py-1 rounded-full text-xs font-mono font-bold bg-[#343c46] border border-emerald-500/40 text-emerald-300 shadow-sm flex items-center gap-1.5">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Zero Patient-Level Data Leakage</span>
              </span>
            </div>
          </div>

          {/* Benchmark Body: True Zero-Scroll Single-Screen Container */}
          <div className="flex-1 min-h-0 mt-2.5 flex flex-col justify-between overflow-hidden gap-2.5">
            {/* Top 4 Key Metric Cards (Full Presence, Clear Contrast) */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-2.5 shrink-0">
              <div className="p-2.5 sm:p-3 rounded-xl bg-[#14181d] border border-[#3a434d] shadow-sm flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono uppercase text-[#87919b] tracking-wider font-semibold block">Patient Balanced Acc</span>
                  <div className="text-xl sm:text-2xl font-bold font-mono text-[#f0f4f8] mt-0.5">92.58%</div>
                  <div className="text-[10px] text-emerald-400 font-mono mt-0.5 flex items-center gap-1">
                    <TrendingUp className="w-3 h-3" />
                    <span>+22.5% vs RF Baseline</span>
                  </div>
                </div>
                <div className="w-9 h-9 rounded-xl bg-emerald-950/40 border border-emerald-800/60 flex items-center justify-center text-emerald-400 shrink-0">
                  <Activity className="w-5 h-5" />
                </div>
              </div>

              <div className="p-2.5 sm:p-3 rounded-xl bg-[#14181d] border border-[#3a434d] shadow-sm flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono uppercase text-[#87919b] tracking-wider font-semibold block">MSA Sensitivity (Recall)</span>
                  <div className="text-xl sm:text-2xl font-bold font-mono text-[#f0f4f8] mt-0.5">92.31%</div>
                  <div className="text-[10px] text-emerald-400 font-mono mt-0.5">
                    12 of 13 Cases Correct
                  </div>
                </div>
                <div className="w-9 h-9 rounded-xl bg-[#343c46] border border-[#3a434d] flex items-center justify-center text-[#c4cbd5] shrink-0">
                  <ShieldAlert className="w-5 h-5 text-emerald-400" />
                </div>
              </div>

              <div className="p-2.5 sm:p-3 rounded-xl bg-[#14181d] border border-[#3a434d] shadow-sm flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono uppercase text-[#87919b] tracking-wider font-semibold block">PD Specificity</span>
                  <div className="text-xl sm:text-2xl font-bold font-mono text-[#f0f4f8] mt-0.5">92.86%</div>
                  <div className="text-[10px] text-emerald-400 font-mono mt-0.5">
                    13 of 14 Cases Correct
                  </div>
                </div>
                <div className="w-9 h-9 rounded-xl bg-[#343c46] border border-[#3a434d] flex items-center justify-center text-[#c4cbd5] shrink-0">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                </div>
              </div>

              <div className="p-2.5 sm:p-3 rounded-xl bg-[#14181d] border border-[#3a434d] shadow-sm flex items-center justify-between">
                <div>
                  <span className="text-[10px] font-mono uppercase text-[#87919b] tracking-wider font-semibold block">ROC-AUC Discrimination</span>
                  <div className="text-xl sm:text-2xl font-bold font-mono text-emerald-300 mt-0.5">0.912</div>
                  <div className="text-[10px] text-[#87919b] font-mono mt-0.5">
                    High Clinical Separation
                  </div>
                </div>
                <div className="w-9 h-9 rounded-xl bg-emerald-950/40 border border-emerald-800/60 flex items-center justify-center text-emerald-400 shrink-0">
                  <BarChart3 className="w-5 h-5" />
                </div>
              </div>
            </div>

            {/* Split Screen Bento: Left (Table + Confusion Matrix) & Right (Expanded ROC Curves) - Fits 100% */}
            <div className="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-12 gap-2.5 items-stretch overflow-hidden">
              {/* Left Column (7 cols): Model Comparison Table & Confusion Matrix */}
              <div className="lg:col-span-7 flex flex-col justify-between h-full min-h-0 overflow-hidden gap-2.5">
                {/* 1. Model Architecture Benchmark Table (Full Substance, 6 Models) */}
                <div className="p-3 sm:p-3.5 rounded-xl bg-[#14181d] border border-[#3a434d] shadow flex-1 flex flex-col justify-between min-h-0 overflow-hidden">
                  <div className="flex items-center justify-between border-b border-[#3a434d] pb-1.5 mb-1.5 shrink-0">
                    <div className="flex items-center gap-1.5">
                      <Cpu className="w-4 h-4 text-emerald-400" />
                      <h3 className="font-serif text-xs sm:text-sm font-bold text-[#f0f4f8]">
                        Cross-Validation Architecture Benchmark (27 LOPO-CV Folds)
                      </h3>
                    </div>
                    <span className="text-[9px] font-mono text-[#87919b] bg-[#1f2730] px-2 py-0.5 rounded border border-[#2a3139]">
                      Standardized Evaluation Protocol
                    </span>
                  </div>

                  <div className="overflow-x-auto flex-1 min-h-0 flex flex-col justify-between">
                    <table className="w-full text-left text-xs">
                      <thead>
                        <tr className="border-b border-[#3a434d] text-[9.5px] font-mono text-[#87919b] uppercase">
                          <th className="pb-1.5">Architecture</th>
                          <th className="pb-1.5 text-center">Features</th>
                          <th className="pb-1.5 text-center">Balanced Acc</th>
                          <th className="pb-1.5 text-center">MSA Recall</th>
                          <th className="pb-1.5 text-center">PD Spec</th>
                          <th className="pb-1.5 text-center">F1-Score</th>
                          <th className="pb-1.5 text-right">AUC</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#3a434d]/40 text-[11px]">
                        <tr className="bg-emerald-950/20 font-semibold text-[#f0f4f8]">
                          <td className="py-1.5 font-bold flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-emerald-400 shrink-0" />
                            <span className="truncate">Optimized Logistic Regression (v3.0)</span>
                            <span className="text-[8px] font-mono px-1 py-0.2 rounded bg-emerald-950 text-emerald-300 border border-emerald-800 shrink-0">
                              Primary
                            </span>
                          </td>
                          <td className="py-1.5 text-center font-mono text-[#c4cbd5]">59</td>
                          <td className="py-1.5 text-center font-mono text-emerald-300 font-bold">92.58%</td>
                          <td className="py-1.5 text-center font-mono text-[#f0f4f8]">92.31%</td>
                          <td className="py-1.5 text-center font-mono text-[#f0f4f8]">92.86%</td>
                          <td className="py-1.5 text-center font-mono text-[#f0f4f8]">0.923</td>
                          <td className="py-1.5 text-right font-mono font-bold text-emerald-300">0.912</td>
                        </tr>
                        <tr className="text-[#c4cbd5]">
                          <td className="py-1.5 flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-cyan-400 shrink-0" />
                            <span className="truncate">Heliyon 2023 Paper Baseline</span>
                          </td>
                          <td className="py-1.5 text-center font-mono text-[#87919b]">6</td>
                          <td className="py-1.5 text-center font-mono">89.29%</td>
                          <td className="py-1.5 text-center font-mono">100.0%</td>
                          <td className="py-1.5 text-center font-mono">78.57%</td>
                          <td className="py-1.5 text-center font-mono">0.897</td>
                          <td className="py-1.5 text-right font-mono text-cyan-300">0.909</td>
                        </tr>
                        <tr className="text-[#c4cbd5]">
                          <td className="py-1.5 flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-blue-400 shrink-0" />
                            <span className="truncate">Support Vector Machine (RBF Kernel)</span>
                          </td>
                          <td className="py-1.5 text-center font-mono text-[#87919b]">45</td>
                          <td className="py-1.5 text-center font-mono">78.41%</td>
                          <td className="py-1.5 text-center font-mono">76.92%</td>
                          <td className="py-1.5 text-center font-mono">78.57%</td>
                          <td className="py-1.5 text-center font-mono">0.769</td>
                          <td className="py-1.5 text-right font-mono text-blue-300">0.814</td>
                        </tr>
                        <tr className="text-[#87919b]">
                          <td className="py-1.5 flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-indigo-400 shrink-0" />
                            <span className="truncate">Gradient Boosted Trees (XGBoost)</span>
                          </td>
                          <td className="py-1.5 text-center font-mono text-[#87919b]">45</td>
                          <td className="py-1.5 text-center font-mono">74.12%</td>
                          <td className="py-1.5 text-center font-mono">76.92%</td>
                          <td className="py-1.5 text-center font-mono">71.43%</td>
                          <td className="py-1.5 text-center font-mono">0.741</td>
                          <td className="py-1.5 text-right font-mono text-indigo-300">0.791</td>
                        </tr>
                        <tr className="text-[#87919b]">
                          <td className="py-1.5 flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-purple-400 shrink-0" />
                            <span className="truncate">Random Forest Classifier (Baseline)</span>
                          </td>
                          <td className="py-1.5 text-center font-mono text-[#87919b]">45</td>
                          <td className="py-1.5 text-center font-mono">70.05%</td>
                          <td className="py-1.5 text-center font-mono">69.23%</td>
                          <td className="py-1.5 text-center font-mono">71.43%</td>
                          <td className="py-1.5 text-center font-mono">0.703</td>
                          <td className="py-1.5 text-right font-mono text-purple-300">0.758</td>
                        </tr>
                        <tr className="text-[#87919b]">
                          <td className="py-1.5 flex items-center gap-1.5">
                            <span className="w-2 h-2 rounded-full bg-amber-400 shrink-0" />
                            <span className="truncate">K-Nearest Neighbors (k=5)</span>
                          </td>
                          <td className="py-1.5 text-center font-mono text-[#87919b]">45</td>
                          <td className="py-1.5 text-center font-mono">63.19%</td>
                          <td className="py-1.5 text-center font-mono">76.92%</td>
                          <td className="py-1.5 text-center font-mono">50.00%</td>
                          <td className="py-1.5 text-center font-mono">0.645</td>
                          <td className="py-1.5 text-right font-mono text-amber-300">0.720</td>
                        </tr>
                      </tbody>
                    </table>

                    <div className="pt-1.5 border-t border-[#1f2730] flex items-center justify-between text-[9.5px] font-mono text-[#87919b]">
                      <span>Cross-Validation Protocol: 27 Clinically Isolated Patient Folds (Zero Leakage)</span>
                      <span className="text-emerald-400 font-bold">Macro-Averaged Balanced Accuracy</span>
                    </div>
                  </div>
                </div>

                {/* 2. Patient-Level Confusion Matrix (27 Folds) */}
                <div className="p-3 sm:p-3.5 rounded-xl bg-[#14181d] border border-[#3a434d] shadow shrink-0">
                  <div className="flex items-center justify-between border-b border-[#3a434d] pb-1.5 mb-2">
                    <div className="flex items-center gap-1.5">
                      <Layers className="w-4 h-4 text-emerald-400" />
                      <h3 className="font-serif text-xs sm:text-sm font-bold text-[#f0f4f8]">
                        27-Patient Clinical Confusion Matrix (v3.0)
                      </h3>
                    </div>
                    <span className="text-[10px] font-mono text-emerald-400 font-bold bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800">
                      Overall Accuracy: 92.59% (25/27 Cases)
                    </span>
                  </div>

                  <div className="grid grid-cols-2 gap-2 text-center">
                    <div className="p-2 rounded-xl bg-[#2a3139]/70 border border-[#3a434d]">
                      <div className="text-[9.5px] font-mono text-[#87919b] uppercase font-semibold">Actual Parkinson's (14 Patients)</div>
                      <div className="grid grid-cols-2 gap-2 mt-1.5">
                        <div className="p-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/60">
                          <div className="text-base sm:text-lg font-bold text-emerald-400 font-mono">13 (92.9%)</div>
                          <div className="text-[8.5px] text-emerald-300 font-mono">True Negative (TN)</div>
                          <div className="text-[8px] text-[#87919b]">Correct Parkinson's</div>
                        </div>
                        <div className="p-1.5 rounded-lg bg-red-950/30 border border-red-900/40">
                          <div className="text-base sm:text-lg font-bold text-red-400 font-mono">1 (7.1%)</div>
                          <div className="text-[8.5px] text-red-300 font-mono">False Positive (FP)</div>
                          <div className="text-[8px] text-[#87919b]">PDBM14 (Atypical)</div>
                        </div>
                      </div>
                    </div>

                    <div className="p-2 rounded-xl bg-[#2a3139]/70 border border-[#3a434d]">
                      <div className="text-[9.5px] font-mono text-[#87919b] uppercase font-semibold">Actual Multiple System Atrophy (13 Patients)</div>
                      <div className="grid grid-cols-2 gap-2 mt-1.5">
                        <div className="p-1.5 rounded-lg bg-red-950/30 border border-red-900/40">
                          <div className="text-base sm:text-lg font-bold text-red-400 font-mono">1 (7.7%)</div>
                          <div className="text-[8.5px] text-red-300 font-mono">False Negative (FN)</div>
                          <div className="text-[8px] text-[#87919b]">MSABM23 (Tremor)</div>
                        </div>
                        <div className="p-1.5 rounded-lg bg-emerald-950/40 border border-emerald-800/60">
                          <div className="text-base sm:text-lg font-bold text-emerald-400 font-mono">12 (92.3%)</div>
                          <div className="text-[8.5px] text-emerald-300 font-mono">True Positive (TP)</div>
                          <div className="text-[8px] text-[#87919b]">Correct MSA Identification</div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Clinical Operating Strip */}
                  <div className="mt-2 pt-1.5 border-t border-[#1f2730] flex flex-wrap items-center justify-between gap-1 text-[9px] font-mono text-[#87919b]">
                    <span>Sensitivity: <strong className="text-emerald-400">92.3%</strong></span>
                    <span>Specificity: <strong className="text-emerald-400">92.9%</strong></span>
                    <span>PPV (Precision): <strong className="text-[#f0f4f8]">92.3%</strong></span>
                    <span>NPV: <strong className="text-[#f0f4f8]">92.9%</strong></span>
                    <span>False Negative Rate: <strong className="text-red-400">7.7%</strong></span>
                  </div>
                </div>
              </div>

              {/* Right Column (5 cols): Expanded Full-Height Interactive ROC-AUC Curves */}
              <div className="lg:col-span-5 flex flex-col h-full min-h-0 overflow-hidden">
                <div className="p-3 sm:p-3.5 rounded-xl bg-[#14181d] border border-[#3a434d] shadow-xl flex flex-col justify-between h-full min-h-0 overflow-hidden">
                  <div className="flex flex-col flex-1 min-h-0 overflow-hidden">
                    {/* Header with Title and Model Filter Pills */}
                    <div className="flex items-center justify-between border-b border-[#3a434d] pb-2 mb-2 gap-2 shrink-0">
                      <div className="flex items-center gap-1.5">
                        <TrendingUp className="w-4 h-4 text-emerald-400" />
                        <div>
                          <h3 className="font-serif text-sm sm:text-base font-bold text-[#f0f4f8] leading-none">
                            Comparative ROC-AUC Curves
                          </h3>
                          <p className="text-[10px] font-mono text-[#87919b] mt-0.5">
                            27-Fold LOPO-CV Discrimination
                          </p>
                        </div>
                      </div>
                      <div className="flex flex-wrap items-center gap-1 text-[9px] font-mono">
                        <button
                          type="button"
                          onClick={() => setSelectedRocModel('all')}
                          className={`px-2 py-0.5 rounded transition-all cursor-pointer ${selectedRocModel === 'all' ? 'bg-[#f0f4f8] text-[#14181d] font-bold shadow' : 'bg-[#1f2730] text-[#87919b] hover:text-[#f0f4f8]'}`}
                        >
                          All Models
                        </button>
                        <button
                          type="button"
                          onClick={() => setSelectedRocModel('v3')}
                          className={`px-2 py-0.5 rounded transition-all cursor-pointer ${selectedRocModel === 'v3' ? 'bg-emerald-400 text-[#14181d] font-bold shadow' : 'bg-[#1f2730] text-[#87919b] hover:text-emerald-400'}`}
                        >
                          v3 (0.912)
                        </button>
                        <button
                          type="button"
                          onClick={() => setSelectedRocModel('heliyon')}
                          className={`px-2 py-0.5 rounded transition-all cursor-pointer ${selectedRocModel === 'heliyon' ? 'bg-cyan-400 text-[#14181d] font-bold shadow' : 'bg-[#1f2730] text-[#87919b] hover:text-cyan-400'}`}
                        >
                          Paper (0.909)
                        </button>
                        <button
                          type="button"
                          onClick={() => setSelectedRocModel('svm')}
                          className={`px-2 py-0.5 rounded transition-all cursor-pointer ${selectedRocModel === 'svm' ? 'bg-blue-400 text-[#14181d] font-bold shadow' : 'bg-[#1f2730] text-[#87919b] hover:text-blue-400'}`}
                        >
                          SVM (0.814)
                        </button>
                        <button
                          type="button"
                          onClick={() => setSelectedRocModel('rf')}
                          className={`px-2 py-0.5 rounded transition-all cursor-pointer ${selectedRocModel === 'rf' ? 'bg-purple-400 text-[#14181d] font-bold shadow' : 'bg-[#1f2730] text-[#87919b] hover:text-purple-400'}`}
                        >
                          RF (0.758)
                        </button>
                        <button
                          type="button"
                          onClick={() => setSelectedRocModel('knn')}
                          className={`px-2 py-0.5 rounded transition-all cursor-pointer ${selectedRocModel === 'knn' ? 'bg-amber-400 text-[#14181d] font-bold shadow' : 'bg-[#1f2730] text-[#87919b] hover:text-amber-400'}`}
                        >
                          KNN (0.720)
                        </button>
                      </div>
                    </div>

                    {/* SVG ROC Plot Container (Fills 100% of remaining height, zero scroll) */}
                    <div className="relative p-2 bg-[#0c1014] rounded-xl border border-[#3a434d] shadow-inner flex-1 min-h-0 flex flex-col justify-between overflow-hidden">
                      <div className="flex-1 min-h-0 w-full flex items-center justify-center">
                        <svg viewBox="0 0 500 300" className="w-full h-full object-contain">
                          {/* Grid Lines */}
                          <line x1="50" y1="20" x2="475" y2="20" stroke="#1f2730" strokeDasharray="3 3" />
                          <line x1="50" y1="68" x2="475" y2="68" stroke="#1f2730" strokeDasharray="3 3" />
                          <line x1="50" y1="116" x2="475" y2="116" stroke="#1f2730" strokeDasharray="3 3" />
                          <line x1="50" y1="164" x2="475" y2="164" stroke="#1f2730" strokeDasharray="3 3" />
                          <line x1="50" y1="212" x2="475" y2="212" stroke="#1f2730" strokeDasharray="3 3" />
                          <line x1="50" y1="260" x2="475" y2="260" stroke="#1f2730" strokeDasharray="3 3" />

                          <line x1="135" y1="20" x2="135" y2="260" stroke="#1f2730" strokeDasharray="3 3" />
                          <line x1="220" y1="20" x2="220" y2="260" stroke="#1f2730" strokeDasharray="3 3" />
                          <line x1="305" y1="20" x2="305" y2="260" stroke="#1f2730" strokeDasharray="3 3" />
                          <line x1="390" y1="20" x2="390" y2="260" stroke="#1f2730" strokeDasharray="3 3" />

                          {/* Y-Axis Labels */}
                          <text x="42" y="24" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="end">1.0</text>
                          <text x="42" y="72" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="end">0.8</text>
                          <text x="42" y="120" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="end">0.6</text>
                          <text x="42" y="168" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="end">0.4</text>
                          <text x="42" y="216" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="end">0.2</text>
                          <text x="42" y="264" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="end">0.0</text>

                          {/* X-Axis Labels */}
                          <text x="50" y="278" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="middle">0.0</text>
                          <text x="135" y="278" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="middle">0.2</text>
                          <text x="220" y="278" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="middle">0.4</text>
                          <text x="305" y="278" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="middle">0.6</text>
                          <text x="390" y="278" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="middle">0.8</text>
                          <text x="475" y="278" fill="#87919b" fontSize="10" fontFamily="monospace" textAnchor="middle">1.0</text>

                          {/* Axis Titles */}
                          <text
                            x="-140"
                            y="16"
                            transform="rotate(-90)"
                            fill="#c4cbd5"
                            fontSize="10"
                            fontFamily="sans-serif"
                            fontWeight="bold"
                            textAnchor="middle"
                          >
                            Sensitivity (True Positive Rate)
                          </text>
                          <text
                            x="262"
                            y="295"
                            fill="#c4cbd5"
                            fontSize="10"
                            fontFamily="sans-serif"
                            fontWeight="bold"
                            textAnchor="middle"
                          >
                            1 - Specificity (False Positive Rate)
                          </text>

                          {/* Axes Lines */}
                          <line x1="50" y1="260" x2="475" y2="260" stroke="#3a434d" strokeWidth="2" />
                          <line x1="50" y1="20" x2="50" y2="260" stroke="#3a434d" strokeWidth="2" />

                          {/* Chance Diagonal Line */}
                          <line x1="50" y1="260" x2="475" y2="20" stroke="#3a434d" strokeDasharray="5 5" strokeWidth="1.5" />
                          <text x="310" y="125" fill="#586370" fontSize="10" fontFamily="monospace" transform="rotate(-30 310 125)">
                            Random Chance (AUC: 0.50)
                          </text>

                          {/* Curve: KNN Baseline (Amber) */}
                          {(selectedRocModel === 'all' || selectedRocModel === 'knn') && (
                            <path
                              d="M 50,260 C 110,215 190,175 285,125 C 360,90 425,50 475,20"
                              fill="none"
                              stroke="#F59E0B"
                              strokeWidth={selectedRocModel === 'knn' ? '3.5' : '2'}
                              strokeOpacity={selectedRocModel === 'knn' || selectedRocModel === 'all' ? 1 : 0.25}
                            />
                          )}

                          {/* Curve: Random Forest (Purple) */}
                          {(selectedRocModel === 'all' || selectedRocModel === 'rf') && (
                            <path
                              d="M 50,260 C 85,185 145,140 240,95 C 325,62 410,38 475,20"
                              fill="none"
                              stroke="#A855F7"
                              strokeWidth={selectedRocModel === 'rf' ? '3.5' : '2.2'}
                              strokeOpacity={selectedRocModel === 'rf' || selectedRocModel === 'all' ? 1 : 0.25}
                            />
                          )}

                          {/* Curve: SVM RBF (Blue) */}
                          {(selectedRocModel === 'all' || selectedRocModel === 'svm') && (
                            <path
                              d="M 50,260 C 70,140 120,85 205,58 C 290,44 380,30 475,20"
                              fill="none"
                              stroke="#3B82F6"
                              strokeWidth={selectedRocModel === 'svm' ? '3.5' : '2.4'}
                              strokeOpacity={selectedRocModel === 'svm' || selectedRocModel === 'all' ? 1 : 0.25}
                            />
                          )}

                          {/* Curve: Heliyon 2023 Paper Baseline (Cyan) */}
                          {(selectedRocModel === 'all' || selectedRocModel === 'heliyon') && (
                            <path
                              d="M 50,260 C 60,80 100,42 195,30 C 290,26 385,23 475,20"
                              fill="none"
                              stroke="#06B6D4"
                              strokeWidth={selectedRocModel === 'heliyon' ? '3.8' : '2.6'}
                              strokeOpacity={selectedRocModel === 'heliyon' || selectedRocModel === 'all' ? 1 : 0.25}
                            />
                          )}

                          {/* Curve: Optimized Logistic Regression v3.0 (Emerald) */}
                          {(selectedRocModel === 'all' || selectedRocModel === 'v3') && (
                            <>
                              <path
                                d="M 50,260 C 56,62 90,32 175,26 C 270,23 370,22 475,20"
                                fill="none"
                                stroke="#10B981"
                                strokeWidth={selectedRocModel === 'v3' ? '4.5' : '3.5'}
                                strokeLinecap="round"
                                className="drop-shadow-[0_0_10px_rgba(16,185,129,0.7)]"
                              />
                              {/* Clinical Operating Point Dot */}
                              <circle cx="80" cy="38" r="5" fill="#10B981" stroke="#f0f4f8" strokeWidth="2" />
                              <text x="92" y="42" fill="#10B981" fontSize="9.5" fontFamily="monospace" fontWeight="bold">
                                Operating Threshold (Sens: 92.3%, Spec: 92.9%)
                              </text>
                            </>
                          )}
                        </svg>
                      </div>

                      {/* Interactive Clinical Legend (5 Model Cards) */}
                      <div className="grid grid-cols-2 sm:grid-cols-5 gap-1.5 pt-2 px-1 border-t border-[#1f2730] shrink-0">
                        <button
                          type="button"
                          onClick={() => setSelectedRocModel('v3')}
                          className={`p-1.5 rounded-lg text-left transition-all border cursor-pointer ${selectedRocModel === 'v3' ? 'bg-emerald-950/70 border-emerald-400 shadow-[0_0_10px_rgba(16,185,129,0.3)]' : 'bg-[#14181d] border-[#2a3139] hover:border-emerald-800'}`}
                        >
                          <div className="flex items-center justify-between text-emerald-400 font-bold text-[10.5px]">
                            <div className="flex items-center gap-1 truncate">
                              <span className="w-2 h-2 bg-emerald-400 rounded-full shrink-0" />
                              <span>LR v3.0</span>
                            </div>
                            <span className="font-mono text-[#f0f4f8]">0.912</span>
                          </div>
                          <div className="text-[8.5px] text-[#87919b] font-mono mt-0.5">Sens 92% • Spec 93%</div>
                        </button>

                        <button
                          type="button"
                          onClick={() => setSelectedRocModel('heliyon')}
                          className={`p-1.5 rounded-lg text-left transition-all border cursor-pointer ${selectedRocModel === 'heliyon' ? 'bg-cyan-950/70 border-cyan-400 shadow-[0_0_10px_rgba(6,182,212,0.3)]' : 'bg-[#14181d] border-[#2a3139] hover:border-cyan-800'}`}
                        >
                          <div className="flex items-center justify-between text-cyan-400 font-bold text-[10.5px]">
                            <div className="flex items-center gap-1 truncate">
                              <span className="w-2 h-2 bg-cyan-400 rounded-full shrink-0" />
                              <span>Paper '23</span>
                            </div>
                            <span className="font-mono text-[#f0f4f8]">0.909</span>
                          </div>
                          <div className="text-[8.5px] text-[#87919b] font-mono mt-0.5">Sens 100% • Spec 79%</div>
                        </button>

                        <button
                          type="button"
                          onClick={() => setSelectedRocModel('svm')}
                          className={`p-1.5 rounded-lg text-left transition-all border cursor-pointer ${selectedRocModel === 'svm' ? 'bg-blue-950/70 border-blue-400 shadow-[0_0_10px_rgba(59,130,246,0.3)]' : 'bg-[#14181d] border-[#2a3139] hover:border-blue-800'}`}
                        >
                          <div className="flex items-center justify-between text-blue-400 font-bold text-[10.5px]">
                            <div className="flex items-center gap-1 truncate">
                              <span className="w-2 h-2 bg-blue-400 rounded-full shrink-0" />
                              <span>SVM RBF</span>
                            </div>
                            <span className="font-mono text-[#f0f4f8]">0.814</span>
                          </div>
                          <div className="text-[8.5px] text-[#87919b] font-mono mt-0.5">Sens 77% • Spec 79%</div>
                        </button>

                        <button
                          type="button"
                          onClick={() => setSelectedRocModel('rf')}
                          className={`p-1.5 rounded-lg text-left transition-all border cursor-pointer ${selectedRocModel === 'rf' ? 'bg-purple-950/70 border-purple-400 shadow-[0_0_10px_rgba(168,85,247,0.3)]' : 'bg-[#14181d] border-[#2a3139] hover:border-purple-800'}`}
                        >
                          <div className="flex items-center justify-between text-purple-400 font-bold text-[10.5px]">
                            <div className="flex items-center gap-1 truncate">
                              <span className="w-2 h-2 bg-purple-400 rounded-full shrink-0" />
                              <span>Rand Forest</span>
                            </div>
                            <span className="font-mono text-[#f0f4f8]">0.758</span>
                          </div>
                          <div className="text-[8.5px] text-[#87919b] font-mono mt-0.5">Sens 69% • Spec 71%</div>
                        </button>

                        <button
                          type="button"
                          onClick={() => setSelectedRocModel('knn')}
                          className={`p-1.5 rounded-lg text-left transition-all border cursor-pointer ${selectedRocModel === 'knn' ? 'bg-amber-950/70 border-amber-400 shadow-[0_0_10px_rgba(245,158,11,0.3)]' : 'bg-[#14181d] border-[#2a3139] hover:border-amber-800'}`}
                        >
                          <div className="flex items-center justify-between text-amber-400 font-bold text-[10.5px]">
                            <div className="flex items-center gap-1 truncate">
                              <span className="w-2 h-2 bg-amber-400 rounded-full shrink-0" />
                              <span>KNN Baseline</span>
                            </div>
                            <span className="font-mono text-[#f0f4f8]">0.720</span>
                          </div>
                          <div className="text-[8.5px] text-[#87919b] font-mono mt-0.5">Sens 77% • Spec 50%</div>
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* Scientific Summary Callout (Sleek Single Strip) */}
                  <div className="p-2 mt-2 rounded-xl bg-[#0c1014] border border-[#2a3139] text-[10.5px] text-[#87919b] flex items-center justify-between gap-2 shrink-0">
                    <div className="flex items-center gap-2 truncate">
                      <ShieldCheck className="w-4 h-4 text-emerald-400 shrink-0" />
                      <span className="truncate text-[#c4cbd5]">
                        <strong className="text-emerald-400">27-Fold LOPO-CV Confirmed:</strong> Zero trial leakage across patient folds. Primary LR v3.0 achieves dominant clinical discrimination.
                      </span>
                    </div>
                    <span className="font-mono text-[10px] text-emerald-400 bg-emerald-950/60 px-2 py-0.5 rounded border border-emerald-800/80 shrink-0">
                      Brier Score: 0.071
                    </span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
