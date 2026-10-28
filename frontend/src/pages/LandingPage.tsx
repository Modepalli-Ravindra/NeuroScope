import React, { useState, useEffect } from 'react';
import {
  Activity, ArrowRight, UploadCloud, Cpu,
  FileCheck, Play, Radio, Search, ShieldCheck
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface LandingPageProps {
  onStartAnalysis: () => void;
}

export const LandingPage: React.FC<LandingPageProps> = ({ onStartAnalysis }) => {
  const { isAuthenticated, openRegister, openLogin } = useAuth();
  const [activeSignalView, setActiveSignalView] = useState<'index' | 'thumb' | 'spectrum'>('index');

  // Auto-switch telemetry tabs (Index Flexion -> Thumb Opposition -> Frequency Spectrum) every 3 seconds
  useEffect(() => {
    const tabs: ('index' | 'thumb' | 'spectrum')[] = ['index', 'thumb', 'spectrum'];
    const timer = setInterval(() => {
      setActiveSignalView((prev) => {
        const nextIndex = (tabs.indexOf(prev) + 1) % tabs.length;
        return tabs[nextIndex];
      });
    }, 3000);

    return () => clearInterval(timer);
  }, []);

  const handleStart = () => {
    if (isAuthenticated) {
      onStartAnalysis();
    } else {
      openRegister();
    }
  };

  const scrollToSection = (id: string) => {
    const el = document.getElementById(id);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div className="space-y-28 sm:space-y-36 pt-16 pb-20 w-full text-[#f0f4f8]">
      {/* 1. DYNAMIC & EDITORIAL HERO SECTION (id="home") */}
      <section id="home" className="relative isolate min-h-[calc(100vh-140px)] flex flex-col justify-center pt-6 pb-12 scroll-mt-28">
        {/* Full-coverage Seamless Neural Brain & Waveform Background spanning from top of window with brain below navbar */}
        <div className="absolute -top-[120px] -bottom-[10px] left-1/2 -translate-x-1/2 w-screen h-[calc(100%+130px)] pointer-events-none z-0 select-none overflow-hidden">
          <img
            src="/hero-bg.png"
            alt="Neural Kinematic Telemetry Background"
            className="w-full h-full object-cover object-top opacity-90 filter contrast-110 brightness-105"
          />
          {/* Single Ultra-Smooth Radial Vignette - Crisp & Zero Banding Lines */}
          <div
            className="absolute inset-0 pointer-events-none"
            style={{
              background: 'radial-gradient(ellipse 100% 85% at 50% 35%, transparent 45%, rgba(20, 24, 29, 0.45) 80%, rgba(20, 24, 29, 0.9) 100%)'
            }}
          />
          {/* Smooth bottom edge blend into page background */}
          <div className="absolute inset-x-0 bottom-0 h-48 bg-gradient-to-b from-transparent via-[#14181d]/50 to-[#14181d] pointer-events-none" />
        </div>

        {/* Ambient Subtle Accent Glows */}
        <div className="absolute -top-20 left-1/4 w-80 h-80 bg-[#87919b]/15 rounded-full blur-3xl pointer-events-none z-0" />
        <div className="absolute top-1/3 right-10 w-80 h-80 bg-[#3a434d]/30 rounded-full blur-3xl pointer-events-none z-0" />

        <div className="relative z-10 grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-center">
          {/* Left: Editorial Content (Enhanced Proportions) */}
          <div className="lg:col-span-6 space-y-7">
            {/* Live Indicator Pill */}
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-[#2a3139]/90 backdrop-blur-md border border-[#87919b]/30 text-xs font-mono text-[#f0f4f8]">
              <span className="relative flex h-2 w-2">
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-400" />
              </span>
              <span>Explainable Medical AI • Movement Screening</span>
            </div>

            {/* Striking Editorial Headline (Enlarged Size) */}
            <h1 className="text-6xl sm:text-7xl lg:text-[80px] xl:text-[86px] text-[#f0f4f8] font-bold tracking-tight leading-[1.04]">
              Every Signal <br />
              <span className="text-[#87919b] font-normal italic drop-shadow-[0_0_30px_rgba(196,203,213,0.35)]">
                Holds an Insight.
              </span>
            </h1>

            {/* Supporting Research Subtitle (Enlarged Size) */}
            <p className="text-base sm:text-lg text-[#87919b] max-w-xl font-normal leading-relaxed">
              Explore movement patterns associated with Multiple System Atrophy and Parkinson's disease using sensor data and explainable machine learning.
            </p>

            {/* Action Buttons (Enlarged Size) */}
            <div className="flex flex-wrap items-center gap-4 pt-1">
              <button
                onClick={handleStart}
                className="px-7 py-3.5 rounded-xl btn-yellow-primary text-sm sm:text-base font-bold flex items-center gap-2.5 cursor-pointer shadow-[0_0_20px_rgba(196,203,213,0.25)] hover:shadow-[0_0_30px_rgba(196,203,213,0.45)] transition-all transform hover:-translate-y-0.5"
              >
                <span>Start Analysis</span>
                <ArrowRight className="w-4 h-4" />
              </button>

              <button
                onClick={() => scrollToSection('how')}
                className="px-7 py-3.5 rounded-xl btn-charcoal-outline text-sm sm:text-base font-medium cursor-pointer hover:border-[#87919b] hover:text-[#f0f4f8] transition-all flex items-center gap-2"
              >
                <Play className="w-4 h-4" />
                <span>How It Works</span>
              </button>
            </div>
          </div>

          {/* Right: COMPACT 200 Hz OSCILLOSCOPE CONSOLE (Enlarged Proportions & Increased Width) */}
          <div className="lg:col-span-6 mt-6 lg:mt-0 w-full">
            <div className="bg-[#2a3139]/85 backdrop-blur-xl border border-[#3a434d] hover:border-[#87919b]/40 rounded-2xl sm:rounded-3xl p-6 sm:p-7 shadow-[0_16px_44px_-10px_rgba(14,17,20,0.75)] relative overflow-hidden transition-all group space-y-4">
              {/* Clean Console Top Header */}
              <div className="flex items-center justify-between pb-3.5 border-b border-[#3a434d]">
                <div className="flex items-center gap-2.5">
                  <span className="relative flex h-2.5 w-2.5">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75" />
                    <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-emerald-400" />
                  </span>
                  <span className="text-xs sm:text-sm font-mono font-semibold text-[#f0f4f8]">
                    200 Hz Triaxial Telemetry
                  </span>
                </div>
                <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-[#14181d] border border-[#3a434d] text-[10px] font-mono text-[#87919b]">
                  <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
                  <span>LIVE SENSOR</span>
                </div>
              </div>

              {/* Clean Channel Tabs (Single Row - Increased Width) */}
              <div className="grid grid-cols-3 gap-2 sm:gap-2.5">
                <button
                  type="button"
                  onClick={() => setActiveSignalView('index')}
                  className={`text-xs font-mono py-2.5 px-2 rounded-xl transition-all cursor-pointer text-center flex items-center justify-center whitespace-nowrap ${
                    activeSignalView === 'index'
                      ? 'bg-[#f0f4f8] text-[#14181d] font-bold shadow-sm'
                      : 'bg-[#14181d] text-[#87919b] hover:text-[#f0f4f8] border border-[#3a434d]'
                  }`}
                >
                  Index Flexion
                </button>
                <button
                  type="button"
                  onClick={() => setActiveSignalView('thumb')}
                  className={`text-xs font-mono py-2.5 px-2 rounded-xl transition-all cursor-pointer text-center flex items-center justify-center whitespace-nowrap ${
                    activeSignalView === 'thumb'
                      ? 'bg-[#f0f4f8] text-[#14181d] font-bold shadow-sm'
                      : 'bg-[#14181d] text-[#87919b] hover:text-[#f0f4f8] border border-[#3a434d]'
                  }`}
                >
                  Thumb Opposition
                </button>
                <button
                  type="button"
                  onClick={() => setActiveSignalView('spectrum')}
                  className={`text-xs font-mono py-2.5 px-2 rounded-xl transition-all cursor-pointer text-center flex items-center justify-center whitespace-nowrap ${
                    activeSignalView === 'spectrum'
                      ? 'bg-[#f0f4f8] text-[#14181d] font-bold shadow-sm'
                      : 'bg-[#14181d] text-[#87919b] hover:text-[#f0f4f8] border border-[#3a434d]'
                  }`}
                >
                  Frequency Spectrum
                </button>
              </div>

              {/* Oscilloscope Viewport (Heightened & Enlarged proportions) */}
              <div className="relative py-4 px-2.5 bg-[#0c1014] rounded-xl border border-[#3a434d] overflow-hidden shadow-inner">
                {/* Sweep Scan Beam */}
                <div className="absolute top-0 bottom-0 w-24 bg-gradient-to-r from-transparent via-[#c4cbd5]/20 to-transparent animate-sweep pointer-events-none" />

                <svg viewBox="0 0 450 140" className="w-full h-auto">
                  <defs>
                    <linearGradient id="silverGradient" x1="0%" y1="0%" x2="100%" y2="0%">
                      <stop offset="0%" stopColor="#87919b" stopOpacity="0.5" />
                      <stop offset="50%" stopColor="#f0f4f8" stopOpacity="1" />
                      <stop offset="100%" stopColor="#87919b" stopOpacity="0.85" />
                    </linearGradient>
                    <filter id="waveGlow" x="-20%" y="-20%" width="140%" height="140%">
                      <feGaussianBlur stdDeviation="3.5" result="blur" />
                      <feComposite in="SourceGraphic" in2="blur" operator="over" />
                    </filter>
                  </defs>

                  {/* Grid Lines */}
                  <line x1="0" y1="35" x2="450" y2="35" stroke="#1f2730" strokeDasharray="3 3" />
                  <line x1="0" y1="70" x2="450" y2="70" stroke="#3a434d" strokeDasharray="4 4" />
                  <line x1="0" y1="105" x2="450" y2="105" stroke="#1f2730" strokeDasharray="3 3" />

                  {activeSignalView === 'index' && (
                    <>
                      {/* Secondary glowing shadow */}
                      <path
                        d="M 5,70 C 25,20 45,128 72,70 C 98,24 125,124 150,70 C 175,16 200,132 225,70 C 250,28 275,122 300,70 C 325,18 350,130 375,70 C 400,24 425,108 450,70"
                        fill="none"
                        stroke="#87919b"
                        strokeWidth="4"
                        opacity="0.3"
                        filter="url(#waveGlow)"
                      />
                      {/* Primary Finger Flexion Waveform */}
                      <path
                        d="M 5,70 C 25,20 45,128 72,70 C 98,24 125,124 150,70 C 175,16 200,132 225,70 C 250,28 275,122 300,70 C 325,18 350,130 375,70 C 400,24 425,108 450,70"
                        fill="none"
                        stroke="url(#silverGradient)"
                        strokeWidth="2.6"
                        strokeLinecap="round"
                      />
                    </>
                  )}

                  {activeSignalView === 'thumb' && (
                    <>
                      <path
                        d="M 5,70 C 30,102 55,42 82,70 C 108,102 135,44 160,70 C 185,110 210,34 235,70 C 260,102 285,46 310,70 C 335,104 360,42 385,70 C 410,98 430,50 450,70"
                        fill="none"
                        stroke="#87919b"
                        strokeWidth="4"
                        opacity="0.3"
                        filter="url(#waveGlow)"
                      />
                      <path
                        d="M 5,70 C 30,102 55,42 82,70 C 108,102 135,44 160,70 C 185,110 210,34 235,70 C 260,102 285,46 310,70 C 335,104 360,42 385,70 C 410,98 430,50 450,70"
                        fill="none"
                        stroke="url(#silverGradient)"
                        strokeWidth="2.6"
                        strokeLinecap="round"
                      />
                    </>
                  )}

                  {activeSignalView === 'spectrum' && (
                    <>
                      <path
                        d="M 5,125 C 40,125 70,118 100,106 C 130,95 150,18 165,18 C 180,18 195,90 220,102 C 250,114 310,122 450,125"
                        fill="none"
                        stroke="#87919b"
                        strokeWidth="4"
                        opacity="0.3"
                        filter="url(#waveGlow)"
                      />
                      <path
                        d="M 5,125 C 40,125 70,118 100,106 C 130,95 150,18 165,18 C 180,18 195,90 220,102 C 250,114 310,122 450,125"
                        fill="none"
                        stroke="url(#silverGradient)"
                        strokeWidth="2.6"
                        strokeLinecap="round"
                      />
                      <circle cx="165" cy="18" r="4" fill="#f0f4f8" />
                      <text x="178" y="24" fill="#f0f4f8" fontSize="10" fontFamily="monospace">
                        Peak: 3.45 Hz (Movement Cadence)
                      </text>
                    </>
                  )}
                </svg>
              </div>

              {/* 3 Essential Metric Cards (Enlarged typography & numbers) */}
              <div className="grid grid-cols-3 gap-3 pt-1 text-center font-mono">
                <div className="bg-[#14181d] p-3 rounded-xl border border-[#3a434d] transition-all">
                  <div className="text-[11px] text-[#87919b] uppercase flex items-center justify-center gap-1">
                    <span>{activeSignalView === 'spectrum' ? 'Peak Freq' : 'Cadence'}</span>
                    <span className="flex items-center gap-0.5 h-2.5">
                      <span className="w-0.5 h-2.5 bg-[#f0f4f8] animate-rhythm-1 rounded-full" />
                      <span className="w-0.5 h-2.5 bg-[#f0f4f8] animate-rhythm-2 rounded-full" />
                      <span className="w-0.5 h-2.5 bg-[#f0f4f8] animate-rhythm-3 rounded-full" />
                    </span>
                  </div>
                  <div className="text-lg font-bold text-[#f0f4f8] mt-1">
                    {activeSignalView === 'index' ? '3.45 Hz' : activeSignalView === 'thumb' ? '3.12 Hz' : '3.45 Hz'}
                  </div>
                </div>

                <div className="bg-[#14181d] p-3 rounded-xl border border-[#3a434d] transition-all">
                  <div className="text-[11px] text-[#87919b] uppercase">
                    {activeSignalView === 'spectrum' ? 'Band Energy' : 'Ataxia Power'}
                  </div>
                  <div className="text-lg font-bold text-[#f0f4f8] mt-1">
                    {activeSignalView === 'index' ? '0.118' : activeSignalView === 'thumb' ? '0.094' : '84.2%'}
                  </div>
                </div>

                <div className="bg-[#14181d] p-3 rounded-xl border border-[#3a434d] transition-all">
                  <div className="text-[11px] text-[#87919b] uppercase">
                    {activeSignalView === 'spectrum' ? 'Signal SNR' : 'LOPO BAcc'}
                  </div>
                  <div className="text-lg font-bold text-[#87919b] mt-1">
                    {activeSignalView === 'spectrum' ? '28.4 dB' : '92.58%'}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* 2. WHY NEUROSCOPE (id="why") — CENTERED HEADER & EQUAL CARDS */}
      <section id="why" className="space-y-10 scroll-mt-32">
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#2a3139] border border-[#3a434d] text-[11px] font-mono uppercase tracking-widest text-[#f0f4f8]">
            Differential Screening
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-[#f0f4f8] tracking-tight">
            Why NeuroScope
          </h2>
          <p className="text-xs sm:text-sm text-[#87919b] leading-relaxed">
            Validated biomechanical intelligence to discriminate movement disorders with clinical explainability.
          </p>
        </div>

        {/* 3 EQUAL CARDS: Identical 1/3 width, matching flex heights, unified structure */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
          {/* Card 1: Movement Analysis */}
          <div className="bg-[#2a3139]/80 backdrop-blur-md border border-[#3a434d] rounded-2xl p-7 flex flex-col justify-between hover:border-[#87919b]/40 transition-all shadow-lg group">
            <div className="space-y-4">
              <div className="w-11 h-11 rounded-xl bg-[#14181d] border border-[#3a434d] flex items-center justify-center text-[#f0f4f8] group-hover:scale-105 transition-transform">
                <Activity className="w-5 h-5" />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold text-[#f0f4f8]">
                  Movement Analysis
                </h3>
                <p className="text-sm text-[#87919b] leading-relaxed">
                  Examine finger-tapping sensor patterns. Capture subtle kinetic differences, frequency irregularities, and deceleration dynamics between MSA and Parkinson's disease.
                </p>
              </div>
            </div>
            <div className="pt-6 border-t border-[#3a434d]/60 flex items-center justify-between text-[11px] font-mono text-[#f0f4f8]">
              <span>Kinematic Biomarkers</span>
              <span className="text-[#87919b]">6-Axis Gyro</span>
            </div>
          </div>

          {/* Card 2: Explainable Results */}
          <div className="bg-[#2a3139]/80 backdrop-blur-md border border-[#3a434d] rounded-2xl p-7 flex flex-col justify-between hover:border-[#87919b]/40 transition-all shadow-lg group">
            <div className="space-y-4">
              <div className="w-11 h-11 rounded-xl bg-[#14181d] border border-[#3a434d] flex items-center justify-center text-[#f0f4f8] group-hover:scale-105 transition-transform">
                <Search className="w-5 h-5" />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold text-[#f0f4f8]">
                  Explainable Results
                </h3>
                <p className="text-sm text-[#87919b] leading-relaxed">
                  Explore the features contributing to a model prediction. Transparent SHAP attribution quantifies exact log-odds shifts without black-box opacity.
                </p>
              </div>
            </div>
            <div className="pt-6 border-t border-[#3a434d]/60 flex items-center justify-between text-[11px] font-mono text-[#f0f4f8]">
              <span>LinearSHAP</span>
              <span className="text-[#87919b]">Exact Log-Odds</span>
            </div>
          </div>

          {/* Card 3: Transparent Evaluation */}
          <div className="bg-[#2a3139]/80 backdrop-blur-md border border-[#3a434d] rounded-2xl p-7 flex flex-col justify-between hover:border-[#87919b]/40 transition-all shadow-lg group">
            <div className="space-y-4">
              <div className="w-11 h-11 rounded-xl bg-[#14181d] border border-[#3a434d] flex items-center justify-center text-[#f0f4f8] group-hover:scale-105 transition-transform">
                <ShieldCheck className="w-5 h-5" />
              </div>
              <div className="space-y-2">
                <h3 className="text-xl font-bold text-[#f0f4f8]">
                  Transparent Evaluation
                </h3>
                <p className="text-sm text-[#87919b] leading-relaxed">
                  Understand how the model was evaluated. Validated with rigorous leave-one-patient-out cross-validation to prevent participant data leakage.
                </p>
              </div>
            </div>
            <div className="pt-6 border-t border-[#3a434d]/60 flex items-center justify-between text-[11px] font-mono text-[#f0f4f8]">
              <span>LOPO Validation</span>
              <span className="text-[#87919b]">Zero Leakage</span>
            </div>
          </div>
        </div>
      </section>

      {/* 3. HOW TO USE (id="how") — CENTERED HEADER & EQUAL CARDS */}
      <section id="how" className="space-y-10 scroll-mt-32">
        <div className="text-center max-w-2xl mx-auto space-y-3">
          <div className="inline-flex items-center gap-2 px-3.5 py-1 rounded-full bg-[#2a3139] border border-[#3a434d] text-[11px] font-mono uppercase tracking-widest text-[#f0f4f8]">
            Workflow
          </div>
          <h2 className="text-3xl sm:text-4xl font-bold text-[#f0f4f8] tracking-tight">
            How to Use
          </h2>
          <p className="text-xs sm:text-sm text-[#87919b] leading-relaxed">
            Three simple steps from raw gyroscope sensor data to deep diagnostic explainability.
          </p>
        </div>

        {/* 3 Simple Equal Steps */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
          {/* Step 1 */}
          <div className="bg-[#2a3139]/80 backdrop-blur-md border border-[#3a434d] rounded-2xl p-7 flex flex-col justify-between space-y-4 shadow-lg">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-[#14181d] border border-[#3a434d] flex items-center justify-center text-[#f0f4f8]">
                  <UploadCloud className="w-5 h-5" />
                </div>
                <span className="text-xs font-mono font-bold text-[#f0f4f8]">01</span>
              </div>
              <h4 className="text-base font-semibold text-[#f0f4f8]">Upload or Select Sample</h4>
              <p className="text-xs sm:text-sm text-[#87919b] leading-relaxed">
                Upload a supported sensor recording or choose an available real dataset sample from the authentic cohort.
              </p>
            </div>
          </div>

          {/* Step 2 */}
          <div className="bg-[#2a3139]/80 backdrop-blur-md border border-[#3a434d] rounded-2xl p-7 flex flex-col justify-between space-y-4 shadow-lg">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-[#14181d] border border-[#3a434d] flex items-center justify-center text-[#f0f4f8]">
                  <Cpu className="w-5 h-5" />
                </div>
                <span className="text-xs font-mono font-bold text-[#f0f4f8]">02</span>
              </div>
              <h4 className="text-base font-semibold text-[#f0f4f8]">Run Model Analysis</h4>
              <p className="text-xs sm:text-sm text-[#87919b] leading-relaxed">
                Run the MSA-versus-PD model analysis to extract 59 biomechanical features and compute differential predictions.
              </p>
            </div>
          </div>

          {/* Step 3 */}
          <div className="bg-[#2a3139]/80 backdrop-blur-md border border-[#3a434d] rounded-2xl p-7 flex flex-col justify-between space-y-4 shadow-lg">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div className="w-10 h-10 rounded-xl bg-[#14181d] border border-[#3a434d] flex items-center justify-center text-[#f0f4f8]">
                  <FileCheck className="w-5 h-5" />
                </div>
                <span className="text-xs font-mono font-bold text-[#f0f4f8]">03</span>
              </div>
              <h4 className="text-base font-semibold text-[#f0f4f8]">Review & Export Report</h4>
              <p className="text-xs sm:text-sm text-[#87919b] leading-relaxed">
                Review the predicted class, relevant feature contributions, SHAP waterfall chart, and download the clinical report.
              </p>
            </div>
          </div>
        </div>

        {/* Clear Get Started Action */}
        <div className="bg-[#2a3139]/80 backdrop-blur-md border border-[#3a434d] rounded-2xl p-10 text-center space-y-4 shadow-xl">
          <h3 className="text-2xl sm:text-3xl font-bold text-[#f0f4f8]">
            Begin Differential Screening
          </h3>
          <p className="text-xs sm:text-sm text-[#87919b] max-w-lg mx-auto leading-relaxed">
            Create a researcher account or sign in with your institutional credentials to access the differential screening workspace.
          </p>
          <div className="pt-3 flex flex-wrap justify-center gap-4">
            <button
              onClick={handleStart}
              className="px-7 py-3.5 rounded-xl btn-yellow-primary text-xs sm:text-sm font-bold inline-flex items-center gap-2 cursor-pointer shadow-md hover:shadow-lg transition-all"
            >
              <span>Get Started</span>
              <ArrowRight className="w-4 h-4" />
            </button>
            {!isAuthenticated && (
              <button
                onClick={openLogin}
                className="px-7 py-3.5 rounded-xl btn-charcoal-outline text-xs sm:text-sm font-medium cursor-pointer hover:border-[#87919b] hover:text-[#f0f4f8] transition-all"
              >
                <span>Existing Researcher Login</span>
              </button>
            )}
          </div>
        </div>
      </section>
    </div>
  );
};
