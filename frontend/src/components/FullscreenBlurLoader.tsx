import React, { useEffect, useState } from 'react';
import { Activity, ShieldCheck, LogOut, CheckCircle2 } from 'lucide-react';

export interface FullscreenBlurLoaderProps {
  type: 'analysis' | 'login' | 'logout';
  durationMs?: number;
  message?: string;
  onFinished?: () => void;
}

export const FullscreenBlurLoader: React.FC<FullscreenBlurLoaderProps> = ({
  type,
  durationMs = 10000,
  message,
  onFinished,
}) => {
  const [progress, setProgress] = useState(0);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);

  // Analysis specific 4-step sequence
  const analysisSteps = [
    {
      title: 'Sensor Channel Synchronization',
      desc: 'Acquiring continuous 200 Hz 6-axis gyroscope telemetry (Thumb & Index)',
      timeThreshold: 25,
    },
    {
      title: 'Biomechanical Feature Extraction',
      desc: 'Computing 59 kinematic indicators (velocity decay, rhythm, ataxia power)',
      timeThreshold: 55,
    },
    {
      title: 'Differential Model & SHAP Inference',
      desc: 'Evaluating leave-one-patient-out classifier & calculating LinearSHAP attributions',
      timeThreshold: 85,
    },
    {
      title: 'Diagnostic Synthesis & Reporting',
      desc: 'Synthesizing kinematic attributions and assembling research results viewport',
      timeThreshold: 100,
    },
  ];

  // Login specific sequence
  const loginSteps = [
    { title: 'Verifying Credentials', desc: 'Validating institutional researcher signature...' },
    { title: 'Authorizing Secure Session', desc: 'Loading verified research access tokens...' },
    { title: 'Opening Workspace', desc: 'Welcome to NeuroKinematix Lab' },
  ];

  // Logout specific sequence
  const logoutSteps = [
    { title: 'Securing Session', desc: 'Terminating active researcher authorization...' },
    { title: 'Purging Telemetry Cache', desc: 'Clearing ephemeral session tokens and workspace data...' },
    { title: 'Redirecting', desc: 'Returning to NeuroKinematix Public Portal' },
  ];

  useEffect(() => {
    const startTime = Date.now();
    const interval = setInterval(() => {
      const elapsed = Date.now() - startTime;
      const currentPct = Math.min(100, Math.floor((elapsed / durationMs) * 100));
      setProgress(currentPct);

      if (type === 'analysis') {
        if (currentPct < 25) setCurrentStepIndex(0);
        else if (currentPct < 55) setCurrentStepIndex(1);
        else if (currentPct < 85) setCurrentStepIndex(2);
        else setCurrentStepIndex(3);
      } else {
        if (currentPct < 40) setCurrentStepIndex(0);
        else if (currentPct < 80) setCurrentStepIndex(1);
        else setCurrentStepIndex(2);
      }

      if (elapsed >= durationMs) {
        clearInterval(interval);
        onFinished?.();
      }
    }, 40);

    return () => clearInterval(interval);
  }, [durationMs, type, onFinished]);

  const remainingSeconds = Math.max(0, ((durationMs * (100 - progress)) / 100 / 1000)).toFixed(1);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 select-none animate-in fade-in duration-300"
      style={{
        backgroundColor: 'rgba(14, 17, 20, 0.82)',
        backdropFilter: 'blur(24px)',
        WebkitBackdropFilter: 'blur(24px)',
      }}
    >
      {/* Background Ambient Glow */}
      <div className="absolute inset-0 pointer-events-none flex items-center justify-center overflow-hidden">
        <div className="w-[500px] h-[500px] rounded-full bg-[#343c46]/20 blur-[120px] animate-pulse" />
      </div>

      {/* Main Glass Center Card */}
      <div className="relative w-full max-w-xl bg-[#2a3139]/90 border border-[#3a434d] rounded-3xl p-6 sm:p-9 shadow-[0_25px_60px_-15px_rgba(0,0,0,0.85)] flex flex-col items-center text-center space-y-6">
        {/* Top Header Badge */}
        <div className="flex items-center gap-2 px-3 py-1 rounded-full bg-[#14181d] border border-[#3a434d] text-[11px] font-mono text-[#c4cbd5]">
          <span className="w-2 h-2 rounded-full bg-[#f0f4f8] animate-ping" />
          <span>
            {type === 'analysis'
              ? 'Kinematic Pipeline Processing'
              : type === 'login'
              ? 'Researcher Authentication'
              : 'Session Termination'}
          </span>
          {type === 'analysis' && (
            <>
              <span className="text-[#87919b]">•</span>
              <span className="text-[#f0f4f8] font-bold">{remainingSeconds}s</span>
            </>
          )}
        </div>

        {/* Central Visual Icon / Logo with Rotating Rings */}
        <div className="relative flex items-center justify-center my-2">
          {/* Outer Pulsing Glow */}
          <div className="absolute w-32 h-32 rounded-full bg-[#c4cbd5]/10 blur-xl animate-pulse" />

          {/* Rotating Dashed Orbit Ring */}
          <div className="absolute w-28 h-28 rounded-full border border-dashed border-[#c4cbd5]/30 animate-spin [animation-duration:12s]" />
          <div className="absolute w-24 h-24 rounded-full border border-[#3a434d] animate-pulse" />

          {/* Inner Icon Container */}
          <div className="relative w-18 h-18 sm:w-20 sm:h-20 rounded-2xl bg-[#14181d] border border-[#3a434d] flex items-center justify-center shadow-2xl p-3">
            {type === 'analysis' ? (
              <img
                src="/logo.png"
                alt="NeuroKinematix Mark"
                className="w-10 h-10 object-contain filter drop-shadow-[0_0_10px_rgba(196,203,213,0.4)] animate-pulse"
              />
            ) : type === 'login' ? (
              <ShieldCheck className="w-9 h-9 text-[#f0f4f8] animate-bounce" />
            ) : (
              <LogOut className="w-9 h-9 text-red-400 animate-pulse" />
            )}
          </div>
        </div>

        {/* Dynamic Titles */}
        <div className="space-y-1.5 max-w-md">
          <h2 className="font-serif text-xl sm:text-2xl font-bold text-[#f0f4f8] tracking-tight">
            {type === 'analysis'
              ? analysisSteps[currentStepIndex].title
              : type === 'login'
              ? loginSteps[currentStepIndex].title
              : logoutSteps[currentStepIndex].title}
          </h2>
          <p className="text-xs text-[#87919b] leading-relaxed">
            {message ||
              (type === 'analysis'
                ? analysisSteps[currentStepIndex].desc
                : type === 'login'
                ? loginSteps[currentStepIndex].desc
                : logoutSteps[currentStepIndex].desc)}
          </p>
        </div>

        {/* Dynamic Waveform Pulse (Analysis mode) */}
        {type === 'analysis' && (
          <div className="flex items-center justify-center gap-1.5 h-6">
            <span className="w-1 bg-[#c4cbd5] rounded-full animate-rhythm-1 h-3" />
            <span className="w-1 bg-[#c4cbd5] rounded-full animate-rhythm-2 h-5" />
            <span className="w-1 bg-[#f0f4f8] rounded-full animate-rhythm-3 h-6" />
            <span className="w-1 bg-[#c4cbd5] rounded-full animate-rhythm-4 h-4" />
            <span className="w-1 bg-[#87919b] rounded-full animate-rhythm-5 h-2" />
            <span className="w-1 bg-[#c4cbd5] rounded-full animate-rhythm-2 h-5" />
            <span className="w-1 bg-[#f0f4f8] rounded-full animate-rhythm-1 h-4" />
          </div>
        )}

        {/* Progress Bar & Percentage */}
        <div className="w-full space-y-2">
          <div className="flex justify-between items-center text-xs font-mono">
            <span className="text-[#87919b]">
              {type === 'analysis'
                ? `Stage ${currentStepIndex + 1} of 4`
                : type === 'login'
                ? 'Authentication in progress'
                : 'Signing out'}
            </span>
            <span className="font-bold text-[#f0f4f8] text-sm tabular-nums">{progress}%</span>
          </div>

          <div className="w-full h-2.5 bg-[#14181d] rounded-full overflow-hidden p-0.5 border border-[#3a434d]">
            <div
              className="h-full bg-gradient-to-r from-[#343c46] via-[#87919b] to-[#f0f4f8] transition-all duration-75 rounded-full shadow-[0_0_12px_rgba(240,244,248,0.5)]"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>

        {/* 4 Step Pills for Analysis */}
        {type === 'analysis' && (
          <div className="w-full grid grid-cols-2 sm:grid-cols-4 gap-2 pt-2 border-t border-[#3a434d]/60">
            {analysisSteps.map((step, idx) => {
              const isDone = progress >= step.timeThreshold;
              const isCurrent = currentStepIndex === idx && !isDone;
              return (
                <div
                  key={idx}
                  className={`p-2 rounded-xl text-[10px] font-mono flex flex-col items-center justify-center transition-all ${
                    isDone
                      ? 'bg-[#343c46] text-[#f0f4f8] border border-[#3a434d]'
                      : isCurrent
                      ? 'bg-[#14181d] text-[#f0f4f8] border border-[#c4cbd5] shadow-sm'
                      : 'bg-[#14181d]/50 text-[#87919b]/50 border border-transparent'
                  }`}
                >
                  <div className="flex items-center gap-1 mb-0.5">
                    {isDone ? (
                      <CheckCircle2 className="w-3 h-3 text-[#c4cbd5]" />
                    ) : isCurrent ? (
                      <Activity className="w-3 h-3 text-[#f0f4f8] animate-spin" />
                    ) : (
                      <span className="w-2.5 h-2.5 rounded-full bg-[#3a434d]" />
                    )}
                    <span className="font-semibold">Step {idx + 1}</span>
                  </div>
                  <span className="truncate max-w-[85px]">{step.title.split(' ')[0]}</span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
};
