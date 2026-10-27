import React from 'react';
import { AuthProvider, useAuth } from './context/AuthContext';
import { AuthModal } from './components/AuthModal';
import { PublicNavbar } from './components/PublicNavbar';
import { LandingPage } from './pages/LandingPage';
import { DashboardPage } from './pages/DashboardPage';
import { FullscreenBlurLoader } from './components/FullscreenBlurLoader';

const MainAppContent: React.FC = () => {
  const { isAuthenticated, openRegister, authOverlay } = useAuth();
  const [activeTab, setActiveTab] = React.useState<'screening' | 'prediction' | 'history'>('screening');

  const handleNavigateSection = (sectionId: string) => {
    const el = document.getElementById(sectionId);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth' });
    }
  };

  return (
    <div
      className={`bg-[#14181d] text-[#f0f4f8] font-sans selection:bg-[#c4cbd5] selection:text-[#14181d] ${
        isAuthenticated
          ? 'h-screen overflow-hidden flex flex-col'
          : 'min-h-screen flex flex-col overflow-x-clip'
      }`}
    >
      {/* Floating Instrument Navbar */}
      <PublicNavbar
        onNavigateSection={handleNavigateSection}
        activeTab={activeTab}
        onSelectTab={setActiveTab}
      />

      {/* Main Viewport */}
      {!isAuthenticated ? (
        <>
          {/* 1. Public Landing Page with normal page scrolling & standard responsive margins (+10px width) */}
          <main className="flex-1 w-full max-w-[1290px] mx-auto px-4 sm:px-6 lg:px-8 py-6">
            <LandingPage onStartAnalysis={openRegister} />
          </main>

          {/* Minimalist Editorial Footer on Landing Page Only */}
          <footer className="border-t border-[#3a434d] bg-[#0e1114] py-8 text-xs text-[#87919b] mt-20">
            <div className="w-full max-w-[1290px] mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4 text-[11px]">
              <div className="flex items-center gap-2">
                <span className="font-bold text-sm text-[#f0f4f8]">NeuroScope</span>
                <span className="text-[#87919b]">— Explainable Movement Disorders Research Platform</span>
              </div>
              <div className="text-[#87919b] font-mono text-[10px]">
                University of Belgrade 200 Hz Cohort
              </div>
            </div>
          </footer>
        </>
      ) : (
        /* 2. Authenticated Application: Full-width research workspace with generous navbar clearance */
        <main className="flex-1 w-[99%] max-w-[1920px] mx-auto pt-[114px] sm:pt-[124px] pb-3 px-2 sm:px-4 overflow-hidden flex flex-col min-h-0">
          <DashboardPage activeTab={activeTab} onSelectTab={setActiveTab} />
        </main>
      )}

      {/* Real Researcher Login & Registration Modal */}
      <AuthModal />

      {/* Fullscreen Blur Loader on Researcher Login and Sign Out */}
      {authOverlay && (
        <FullscreenBlurLoader
          type={authOverlay.type}
          durationMs={authOverlay.durationMs}
          message={authOverlay.message}
        />
      )}
    </div>
  );
};

export const App: React.FC = () => {
  return (
    <AuthProvider>
      <MainAppContent />
    </AuthProvider>
  );
};

export default App;
