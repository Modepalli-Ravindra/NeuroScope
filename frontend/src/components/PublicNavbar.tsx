import React, { useState, useEffect } from 'react';
import { Menu, X, ArrowRight, User, LogOut, Activity, FileText, Layers } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

interface PublicNavbarProps {
  onNavigateSection?: (sectionId: string) => void;
  activeTab?: 'screening' | 'prediction' | 'history';
  onSelectTab?: (tab: 'screening' | 'prediction' | 'history') => void;
}

export const PublicNavbar: React.FC<PublicNavbarProps> = ({
  onNavigateSection,
  activeTab = 'screening',
  onSelectTab,
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [activeSection, setActiveSection] = useState<string>('home');
  const [isScrolled, setIsScrolled] = useState(false);
  const { user, isAuthenticated, openLogin, openRegister, logout } = useAuth();

  // Scroll detection to adjust glass intensity & track active section
  useEffect(() => {
    const handleScroll = () => {
      setIsScrolled(window.scrollY > 20);

      const homeEl = document.getElementById('home');
      const whyEl = document.getElementById('why');
      const howEl = document.getElementById('how');

      const scrollPosition = window.scrollY + 200;

      if (howEl && scrollPosition >= howEl.offsetTop) {
        setActiveSection('how');
      } else if (whyEl && scrollPosition >= whyEl.offsetTop) {
        setActiveSection('why');
      } else if (homeEl) {
        setActiveSection('home');
      }
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, []);

  const handleNavClick = (id: string) => {
    setActiveSection(id);
    onNavigateSection?.(id);
    setMobileMenuOpen(false);
  };

  const handleTabClick = (tab: 'screening' | 'prediction' | 'history') => {
    onSelectTab?.(tab);
    setMobileMenuOpen(false);
  };

  return (
    <header
      className={`fixed top-3 sm:top-4 inset-x-0 z-40 mx-auto transition-all duration-300 ${
        isAuthenticated
          ? 'w-[99%] max-w-[1920px] px-2 sm:px-4'
          : 'w-full max-w-[1410px] px-4 sm:px-6 lg:px-8'
      }`}
    >
      {/* Exquisite Floating Instrument Navbar */}
      <div
        className={`relative rounded-2xl sm:rounded-3xl transition-all duration-300 flex items-center justify-between border ${
          isAuthenticated
            ? 'px-5 sm:px-7 py-2.5 sm:py-3'
            : 'px-4 sm:px-6 py-2 sm:py-2.5'
        } ${
          isScrolled
            ? 'bg-[#14181d]/95 backdrop-blur-2xl border-[#3a434d] shadow-[0_16px_40px_-8px_rgba(0,0,0,0.8)]'
            : 'bg-[#2a3139]/90 backdrop-blur-xl border-[#3a434d]/80 shadow-[0_12px_36px_-10px_rgba(0,0,0,0.7)]'
        }`}
      >
        {/* Luminous Top Accent Sheen */}
        <div className="absolute inset-x-12 top-0 h-[1px] bg-gradient-to-r from-transparent via-[#c4cbd5]/40 via-cyan-400/20 to-transparent pointer-events-none" />

        {/* 1. BRAND MARK & HIGH-TECH STATUS BADGE */}
        <div
          onClick={() => (!isAuthenticated ? handleNavClick('home') : handleTabClick('screening'))}
          className="flex items-center gap-2.5 sm:gap-3 cursor-pointer group"
        >
          <div className="relative w-8 h-8 rounded-xl bg-[#14181d] border border-[#3a434d] flex items-center justify-center overflow-hidden transition-all duration-300 group-hover:border-[#c4cbd5] group-hover:shadow-[0_0_15px_rgba(196,203,213,0.25)]">
            <img
              src="/logo.png"
              alt="NeuroScope Mark"
              className="w-5 h-5 object-contain filter drop-shadow-[0_0_6px_rgba(196,203,213,0.3)] transition-transform duration-300 group-hover:scale-105"
            />
            <div className="absolute inset-0 bg-[#c4cbd5]/10 rounded-full blur-md pointer-events-none group-hover:bg-[#c4cbd5]/20 transition-colors" />
          </div>

          <div className="flex items-center gap-2">
            <span className="font-serif font-bold text-base sm:text-lg tracking-tight text-[#f0f4f8] group-hover:text-[#c4cbd5] transition-colors">
              NeuroScope
            </span>
          </div>
        </div>

        {/* 2. CENTER NAVIGATION DOCK */}
        {!isAuthenticated ? (
          /* Public Landing Navigation */
          <nav className="hidden md:flex items-center gap-1 p-1 rounded-full bg-[#14181d]/90 border border-[#3a434d]/80 shadow-inner">
            <button
              onClick={() => handleNavClick('home')}
              className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-200 cursor-pointer ${
                activeSection === 'home'
                  ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#c4cbd5]/40 shadow-sm'
                  : 'text-[#87919b] hover:text-[#f0f4f8] hover:bg-[#343c46]/40'
              }`}
            >
              Home
            </button>
            <button
              onClick={() => handleNavClick('why')}
              className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-200 cursor-pointer flex items-center gap-1.5 ${
                activeSection === 'why'
                  ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#c4cbd5]/40 shadow-sm'
                  : 'text-[#87919b] hover:text-[#f0f4f8] hover:bg-[#343c46]/40'
              }`}
            >
              <Activity className="w-3 h-3 text-[#c4cbd5]" />
              <span>Why NeuroScope</span>
            </button>
            <button
              onClick={() => handleNavClick('how')}
              className={`px-3.5 py-1.5 rounded-full text-xs font-medium transition-all duration-200 cursor-pointer flex items-center gap-1.5 ${
                activeSection === 'how'
                  ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#c4cbd5]/40 shadow-sm'
                  : 'text-[#87919b] hover:text-[#f0f4f8] hover:bg-[#343c46]/40'
              }`}
            >
              <span>How to Use</span>
            </button>
          </nav>
        ) : (
          /* Authenticated Application Navigation Dock: New Analysis -> Prediction -> History */
          <nav className="hidden md:flex items-center gap-2 p-1.5 rounded-full bg-[#14181d]/85 border border-[#3a434d]/80 shadow-inner">
            <button
              onClick={() => handleTabClick('screening')}
              className={`px-5 py-2 rounded-full text-xs sm:text-[13px] font-medium transition-all duration-200 cursor-pointer flex items-center gap-2 ${
                activeTab === 'screening'
                  ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#c4cbd5]/40 shadow-sm'
                  : 'text-[#87919b] hover:text-[#f0f4f8] hover:bg-[#343c46]/40'
              }`}
            >
              <Activity className="w-3.5 h-3.5 text-[#c4cbd5]" />
              <span>New Analysis</span>
            </button>
            <button
              onClick={() => handleTabClick('prediction')}
              className={`px-5 py-2 rounded-full text-xs sm:text-[13px] font-medium transition-all duration-200 cursor-pointer flex items-center gap-2 ${
                activeTab === 'prediction'
                  ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#c4cbd5]/40 shadow-sm'
                  : 'text-[#87919b] hover:text-[#f0f4f8] hover:bg-[#343c46]/40'
              }`}
            >
              <Layers className="w-3.5 h-3.5 text-[#c4cbd5]" />
              <span>Prediction & Explanation</span>
            </button>
            <button
              onClick={() => handleTabClick('history')}
              className={`px-5 py-2 rounded-full text-xs sm:text-[13px] font-medium transition-all duration-200 cursor-pointer flex items-center gap-2 ${
                activeTab === 'history'
                  ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#c4cbd5]/40 shadow-sm'
                  : 'text-[#87919b] hover:text-[#f0f4f8] hover:bg-[#343c46]/40'
              }`}
            >
              <FileText className="w-3.5 h-3.5 text-[#87919b]" />
              <span>Analysis History</span>
            </button>
          </nav>
        )}

        {/* 3. RIGHT AUTH ACTION / USER PROFILE */}
        {!isAuthenticated ? (
          <div className="hidden md:flex items-center gap-2.5">
            <button
              onClick={openLogin}
              className="text-xs font-medium text-[#c4cbd5] hover:text-[#f0f4f8] px-3.5 py-1.5 rounded-xl transition-all cursor-pointer hover:bg-[#343c46]/50 border border-transparent hover:border-[#3a434d]"
            >
              Login
            </button>

            <button
              onClick={openRegister}
              className="relative group overflow-hidden px-4 py-1.5 rounded-xl bg-gradient-to-b from-[#f0f4f8] to-[#c4cbd5] text-[#14181d] font-bold text-xs cursor-pointer shadow-[0_0_15px_rgba(196,203,213,0.2)] hover:shadow-[0_0_25px_rgba(196,203,213,0.4)] transition-all transform hover:-translate-y-0.5 flex items-center gap-1.5"
            >
              <span className="relative z-10 flex items-center gap-1">
                <span>Get Started</span>
                <ArrowRight className="w-3.5 h-3.5 transition-transform duration-200 group-hover:translate-x-0.5" />
              </span>
              <div className="absolute inset-0 -translate-x-full group-hover:translate-x-full bg-gradient-to-r from-transparent via-white/40 to-transparent transition-transform duration-700 ease-in-out pointer-events-none" />
            </button>
          </div>
        ) : (
          <div className="hidden md:flex items-center gap-3">
            {/* User Profile Info Card */}
            <div className="flex items-center gap-2.5 px-3 py-1.5 rounded-xl bg-[#14181d] border border-[#3a434d]">
              <div className="w-6 h-6 rounded-lg bg-[#2a3139] border border-[#3a434d] flex items-center justify-center text-[#f0f4f8]">
                <User className="w-3.5 h-3.5 text-[#c4cbd5]" />
              </div>
              <div className="text-left">
                <div className="text-xs font-semibold text-[#f0f4f8] leading-tight">
                  {user?.name || 'Researcher'}
                </div>
                <div className="text-[10px] text-[#87919b] leading-tight truncate max-w-[130px]">
                  {user?.institution || 'Movement Lab'}
                </div>
              </div>
            </div>

            {/* Prominent Sign Out Button */}
            <button
              onClick={logout}
              className="px-3.5 py-2 rounded-xl text-xs font-medium text-[#c4cbd5] hover:text-[#f0f4f8] hover:bg-[#2a3139] border border-[#3a434d] transition-all cursor-pointer flex items-center gap-1.5"
              title="Sign Out"
            >
              <LogOut className="w-3.5 h-3.5 text-red-400" />
              <span>Sign Out</span>
            </button>
          </div>
        )}

        {/* Mobile Hamburger Button */}
        <button
          onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
          className="md:hidden p-2.5 rounded-xl bg-[#14181d] border border-[#3a434d] text-[#87919b] hover:text-[#f0f4f8] focus:outline-none transition-colors"
          aria-label="Toggle navigation menu"
        >
          {mobileMenuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
        </button>
      </div>

      {/* Mobile Drawer */}
      {mobileMenuOpen && (
        <div className="md:hidden mt-2 bg-[#1a2026]/95 backdrop-blur-2xl border border-[#3a434d] rounded-2xl p-5 shadow-2xl space-y-4 animate-in fade-in slide-in-from-top-2 duration-200">
          {!isAuthenticated ? (
            <>
              <nav className="flex flex-col space-y-1 text-sm text-[#87919b]">
                <button
                  onClick={() => handleNavClick('home')}
                  className={`text-left px-4 py-2.5 rounded-xl transition-colors ${
                    activeSection === 'home'
                      ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#3a434d]'
                      : 'hover:bg-[#343c46]/50 hover:text-[#f0f4f8]'
                  }`}
                >
                  Home
                </button>
                <button
                  onClick={() => handleNavClick('why')}
                  className={`text-left px-4 py-2.5 rounded-xl transition-colors ${
                    activeSection === 'why'
                      ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#3a434d]'
                      : 'hover:bg-[#343c46]/50 hover:text-[#f0f4f8]'
                  }`}
                >
                  Why NeuroScope
                </button>
                <button
                  onClick={() => handleNavClick('how')}
                  className={`text-left px-4 py-2.5 rounded-xl transition-colors ${
                    activeSection === 'how'
                      ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#3a434d]'
                      : 'hover:bg-[#343c46]/50 hover:text-[#f0f4f8]'
                  }`}
                >
                  How to Use
                </button>
              </nav>

              <div className="pt-3 border-t border-[#3a434d] flex flex-col gap-2.5">
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    openLogin();
                  }}
                  className="w-full py-2.5 px-3 rounded-xl text-xs font-medium text-[#c4cbd5] hover:bg-[#343c46] hover:text-[#f0f4f8] text-center border border-[#3a434d]"
                >
                  Login
                </button>
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    openRegister();
                  }}
                  className="w-full py-2.5 rounded-xl bg-gradient-to-b from-[#f0f4f8] to-[#c4cbd5] text-[#14181d] text-xs font-bold text-center flex items-center justify-center gap-1.5 shadow-md"
                >
                  <span>Get Started</span>
                  <ArrowRight className="w-3.5 h-3.5" />
                </button>
              </div>
            </>
          ) : (
            <>
              <div className="flex items-center gap-3 p-3 rounded-xl bg-[#14181d] border border-[#3a434d]">
                <div className="w-8 h-8 rounded-lg bg-[#2a3139] border border-[#3a434d] flex items-center justify-center text-[#f0f4f8]">
                  <User className="w-4 h-4 text-[#c4cbd5]" />
                </div>
                <div>
                  <div className="text-xs font-semibold text-[#f0f4f8]">{user?.name}</div>
                  <div className="text-[10px] text-[#87919b]">{user?.email}</div>
                </div>
              </div>

              <nav className="flex flex-col space-y-1 text-sm text-[#87919b]">
                <button
                  onClick={() => handleTabClick('screening')}
                  className={`text-left px-4 py-2.5 rounded-xl transition-colors flex items-center gap-2 ${
                    activeTab === 'screening'
                      ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#c4cbd5]/40'
                      : 'hover:bg-[#343c46]/40 hover:text-[#f0f4f8]'
                  }`}
                >
                  <Activity className="w-4 h-4 text-[#c4cbd5]" />
                  <span>New Analysis</span>
                </button>
                <button
                  onClick={() => handleTabClick('prediction')}
                  className={`text-left px-4 py-2.5 rounded-xl transition-colors flex items-center gap-2 ${
                    activeTab === 'prediction'
                      ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#c4cbd5]/40'
                      : 'hover:bg-[#343c46]/40 hover:text-[#f0f4f8]'
                  }`}
                >
                  <Layers className="w-4 h-4 text-[#c4cbd5]" />
                  <span>Prediction & Explanation</span>
                </button>
                <button
                  onClick={() => handleTabClick('history')}
                  className={`text-left px-4 py-2.5 rounded-xl transition-colors flex items-center gap-2 ${
                    activeTab === 'history'
                      ? 'bg-[#343c46] text-[#f0f4f8] font-semibold border border-[#c4cbd5]/40'
                      : 'hover:bg-[#343c46]/40 hover:text-[#f0f4f8]'
                  }`}
                >
                  <FileText className="w-4 h-4 text-[#87919b]" />
                  <span>Analysis History</span>
                </button>
              </nav>

              <div className="pt-3 border-t border-[#3a434d]">
                <button
                  onClick={() => {
                    setMobileMenuOpen(false);
                    logout();
                  }}
                  className="w-full py-2.5 px-3 rounded-xl text-xs font-medium text-red-400 hover:bg-[#14181d] text-center border border-[#3a434d] flex items-center justify-center gap-1.5 cursor-pointer"
                >
                  <LogOut className="w-4 h-4" />
                  <span>Sign Out</span>
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </header>
  );
};
