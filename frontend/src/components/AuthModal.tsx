import React, { useState } from 'react';
import { X, Lock, Mail, User, Eye, EyeOff, Check, AlertCircle, ArrowRight } from 'lucide-react';
import { useAuth } from '../context/AuthContext';

export const AuthModal: React.FC = () => {
  const { isAuthModalOpen, closeAuth, authMode, openLogin, openRegister, login, register, isLoading } = useAuth();

  // Form states
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');

  // Password visibility
  const [showPassword, setShowPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

  // Error & touched state
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  if (!isAuthModalOpen) return null;

  // Real password validation rules
  const hasMinLength = password.length >= 9;
  const hasUppercase = /[A-Z]/.test(password);
  const hasLowercase = /[a-z]/.test(password);
  const hasNumber = /\d/.test(password);
  const hasSpecial = /[!@#$%^&*(),.?":{}|<>_\-+=[\]\\/`~;]/.test(password);
  const passwordsMatch = password.length > 0 && password === confirmPassword;

  const isPasswordValid = hasMinLength && hasUppercase && hasLowercase && hasNumber && hasSpecial;

  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);
    if (!email.trim() || !password) {
      setErrorMessage('Please enter both your email address and password.');
      return;
    }

    try {
      await login({ email: email.trim(), password });
      resetForm();
    } catch (err: any) {
      setErrorMessage(err.message || 'Authentication failed. Please verify your credentials.');
    }
  };

  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrorMessage(null);

    if (!name.trim()) {
      setErrorMessage('Researcher Name is required.');
      return;
    }
    if (!email.trim()) {
      setErrorMessage('Institutional Email Address is required.');
      return;
    }
    if (!isPasswordValid) {
      setErrorMessage('Password must meet all complexity requirements.');
      return;
    }
    if (!passwordsMatch) {
      setErrorMessage('Passwords do not match.');
      return;
    }

    try {
      await register({
        name: name.trim(),
        institution: 'Independent Research',
        email: email.trim(),
        password,
        confirm_password: confirmPassword,
      });
      resetForm();
    } catch (err: any) {
      setErrorMessage(err.message || 'Registration failed. Please check your credentials.');
    }
  };

  const resetForm = () => {
    setName('');
    setEmail('');
    setPassword('');
    setConfirmPassword('');
    setErrorMessage(null);
  };

  const isSignUp = authMode === 'register';

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-md animate-in fade-in duration-200">
      {/* Sleek, proportional dialog with max-w-[450px] and balanced height */}
      <div
        className="w-full max-w-[450px] bg-[#2a3139] border border-[#3a434d] rounded-3xl shadow-[0_25px_60px_-15px_rgba(0,0,0,0.85)] overflow-hidden text-[#f0f4f8] transition-all transform"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header with generous vertical padding */}
        <div className="px-7 py-6 border-b border-[#3a434d] flex items-center justify-between bg-[#14181d]">
          <div className="flex items-center gap-3.5">
            <img
              src="/logo.png"
              alt="NeuroKinematix"
              className="w-9 h-9 object-contain filter drop-shadow-[0_0_10px_rgba(196,203,213,0.35)]"
            />
            <div>
              <h3 className="font-semibold text-base sm:text-lg text-[#f0f4f8] tracking-tight">
                {isSignUp ? 'Create Researcher Account' : 'Sign In to NeuroKinematix'}
              </h3>
              <p className="text-[11px] text-[#87919b] mt-0.5">
                {isSignUp
                  ? 'Access differential screening & explainability'
                  : 'Authorized movement disorders research workspace'}
              </p>
            </div>
          </div>
          <button
            onClick={() => {
              resetForm();
              closeAuth();
            }}
            className="p-2 rounded-xl text-[#87919b] hover:text-[#f0f4f8] hover:bg-[#343c46] transition-colors cursor-pointer"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Body with tall, well-proportioned inputs and comfortable height */}
        <div className="p-7 max-h-[82vh] overflow-y-auto space-y-5">
          {errorMessage && (
            <div className="p-3.5 rounded-xl bg-red-950/40 border border-red-800/60 text-red-200 text-xs flex items-start gap-2.5">
              <AlertCircle className="w-4 h-4 shrink-0 text-red-400 mt-0.5" />
              <span>{errorMessage}</span>
            </div>
          )}

          {isSignUp ? (
            /* Register Form: Balanced vertical flow with tall comfortable inputs */
            <form onSubmit={handleRegisterSubmit} className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-[#c4cbd5] mb-1.5">
                  Researcher Name <span className="text-[#f0f4f8]">*</span>
                </label>
                <div className="relative">
                  <User className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#87919b]" />
                  <input
                    type="text"
                    required
                    placeholder="e.g. Dr. Alex Mercer, MD"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    className="w-full bg-[#14181d] border border-[#3a434d] focus:border-[#c4cbd5] rounded-xl pl-10 pr-4 py-3 text-xs sm:text-sm text-[#f0f4f8] placeholder-[#87919b]/60 focus:outline-none transition-all shadow-inner"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#c4cbd5] mb-1.5">
                  Institutional Email Address <span className="text-[#f0f4f8]">*</span>
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#87919b]" />
                  <input
                    type="email"
                    required
                    placeholder="researcher@university-hospital.edu"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-[#14181d] border border-[#3a434d] focus:border-[#c4cbd5] rounded-xl pl-10 pr-4 py-3 text-xs sm:text-sm text-[#f0f4f8] placeholder-[#87919b]/60 focus:outline-none transition-all shadow-inner"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#c4cbd5] mb-1.5">
                  Password <span className="text-[#f0f4f8]">*</span>
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#87919b]" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="Minimum 9 characters"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-[#14181d] border border-[#3a434d] focus:border-[#c4cbd5] rounded-xl pl-10 pr-10 py-3 text-xs sm:text-sm text-[#f0f4f8] placeholder-[#87919b]/60 focus:outline-none transition-all shadow-inner"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#87919b] hover:text-[#f0f4f8]"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#c4cbd5] mb-1.5">
                  Confirm Password <span className="text-[#f0f4f8]">*</span>
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#87919b]" />
                  <input
                    type={showConfirmPassword ? 'text' : 'password'}
                    required
                    placeholder="Re-enter password"
                    value={confirmPassword}
                    onChange={(e) => setConfirmPassword(e.target.value)}
                    className="w-full bg-[#14181d] border border-[#3a434d] focus:border-[#c4cbd5] rounded-xl pl-10 pr-10 py-3 text-xs sm:text-sm text-[#f0f4f8] placeholder-[#87919b]/60 focus:outline-none transition-all shadow-inner"
                  />
                  <button
                    type="button"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#87919b] hover:text-[#f0f4f8]"
                  >
                    {showConfirmPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              {/* Password Requirements Checklist */}
              <div className="bg-[#14181d] p-3.5 rounded-2xl border border-[#3a434d] space-y-2 text-[11px] mt-1">
                <div className="text-[11px] font-semibold text-[#f0f4f8] uppercase tracking-wide">
                  Password Requirements:
                </div>
                <div className="grid grid-cols-2 gap-2 text-[#87919b]">
                  <div className={`flex items-center gap-1.5 ${hasMinLength ? 'text-[#c4cbd5]' : ''}`}>
                    <Check className={`w-3.5 h-3.5 ${hasMinLength ? 'text-[#c4cbd5]' : 'text-[#3a434d]'}`} />
                    <span>9+ characters</span>
                  </div>
                  <div className={`flex items-center gap-1.5 ${hasUppercase ? 'text-[#c4cbd5]' : ''}`}>
                    <Check className={`w-3.5 h-3.5 ${hasUppercase ? 'text-[#c4cbd5]' : 'text-[#3a434d]'}`} />
                    <span>Uppercase letter</span>
                  </div>
                  <div className={`flex items-center gap-1.5 ${hasLowercase ? 'text-[#c4cbd5]' : ''}`}>
                    <Check className={`w-3.5 h-3.5 ${hasLowercase ? 'text-[#c4cbd5]' : 'text-[#3a434d]'}`} />
                    <span>Lowercase letter</span>
                  </div>
                  <div className={`flex items-center gap-1.5 ${hasNumber ? 'text-[#c4cbd5]' : ''}`}>
                    <Check className={`w-3.5 h-3.5 ${hasNumber ? 'text-[#c4cbd5]' : 'text-[#3a434d]'}`} />
                    <span>Numeric digit</span>
                  </div>
                  <div className={`flex items-center gap-1.5 ${hasSpecial ? 'text-[#c4cbd5]' : ''}`}>
                    <Check className={`w-3.5 h-3.5 ${hasSpecial ? 'text-[#c4cbd5]' : 'text-[#3a434d]'}`} />
                    <span>Special character</span>
                  </div>
                  <div className={`flex items-center gap-1.5 ${passwordsMatch ? 'text-[#c4cbd5]' : ''}`}>
                    <Check className={`w-3.5 h-3.5 ${passwordsMatch ? 'text-[#c4cbd5]' : 'text-[#3a434d]'}`} />
                    <span>Passwords match</span>
                  </div>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-3 py-3.5 px-5 rounded-xl btn-yellow-primary text-xs sm:text-sm font-bold flex items-center justify-center gap-2 cursor-pointer shadow-lg disabled:opacity-50"
              >
                {isLoading ? (
                  <span>Creating Researcher Account...</span>
                ) : (
                  <>
                    <span>Create Researcher Account</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          ) : (
            /* Login Form: Sleek, tall, spacious layout */
            <form onSubmit={handleLoginSubmit} className="space-y-5 py-2">
              <div>
                <label className="block text-xs font-medium text-[#c4cbd5] mb-2">
                  Institutional Email Address
                </label>
                <div className="relative">
                  <Mail className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#87919b]" />
                  <input
                    type="email"
                    required
                    placeholder="researcher@university-hospital.edu"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    className="w-full bg-[#14181d] border border-[#3a434d] focus:border-[#c4cbd5] rounded-xl pl-10 pr-4 py-3.5 text-xs sm:text-sm text-[#f0f4f8] placeholder-[#87919b]/60 focus:outline-none transition-all shadow-inner"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-medium text-[#c4cbd5] mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[#87919b]" />
                  <input
                    type={showPassword ? 'text' : 'password'}
                    required
                    placeholder="Enter account password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-[#14181d] border border-[#3a434d] focus:border-[#c4cbd5] rounded-xl pl-10 pr-10 py-3.5 text-xs sm:text-sm text-[#f0f4f8] placeholder-[#87919b]/60 focus:outline-none transition-all shadow-inner"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-[#87919b] hover:text-[#f0f4f8]"
                  >
                    {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                  </button>
                </div>
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full mt-3 py-3.5 px-5 rounded-xl btn-yellow-primary text-xs sm:text-sm font-bold flex items-center justify-center gap-2 cursor-pointer shadow-lg disabled:opacity-50"
              >
                {isLoading ? (
                  <span>Signing In...</span>
                ) : (
                  <>
                    <span>Sign In</span>
                    <ArrowRight className="w-4 h-4" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* Toggle between Login and Register */}
          <div className="pt-4 text-center text-xs text-[#87919b] border-t border-[#3a434d]">
            {isSignUp ? (
              <span>
                Already registered?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setErrorMessage(null);
                    openLogin();
                  }}
                  className="text-[#f0f4f8] hover:text-[#c4cbd5] hover:underline font-bold ml-1"
                >
                  Sign In
                </button>
              </span>
            ) : (
              <span>
                New investigator?{' '}
                <button
                  type="button"
                  onClick={() => {
                    setErrorMessage(null);
                    openRegister();
                  }}
                  className="text-[#f0f4f8] hover:text-[#c4cbd5] hover:underline font-bold ml-1"
                >
                  Create a Researcher Account
                </button>
              </span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
