import React, { createContext, useContext, useState, useEffect } from 'react';
import type { UserProfile, UserLoginRequest, UserRegisterRequest } from '../types';
import { loginResearcher, registerResearcher, fetchMe } from '../api';

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: UserProfile | null;
  authMode: 'login' | 'register';
  isAuthModalOpen: boolean;
  authOverlay: { type: 'login' | 'logout'; message?: string; durationMs: number } | null;
  openLogin: () => void;
  openRegister: () => void;
  closeAuth: () => void;
  login: (credentials: UserLoginRequest) => Promise<void>;
  register: (payload: UserRegisterRequest) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType>({
  isAuthenticated: false,
  isLoading: false,
  user: null,
  authMode: 'login',
  isAuthModalOpen: false,
  authOverlay: null,
  openLogin: () => {},
  openRegister: () => {},
  closeAuth: () => {},
  login: async () => {},
  register: async () => {},
  logout: () => {},
});

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserProfile | null>(() => {
    try {
      const stored = localStorage.getItem('neuroscope_user');
      return stored ? JSON.parse(stored) : null;
    } catch {
      return null;
    }
  });

  const [isAuthenticated, setIsAuthenticated] = useState<boolean>(() => {
    const token = localStorage.getItem('neuroscope_token');
    return Boolean(token);
  });

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isAuthModalOpen, setIsAuthModalOpen] = useState<boolean>(false);
  const [authMode, setAuthMode] = useState<'login' | 'register'>('login');
  const [authOverlay, setAuthOverlay] = useState<{ type: 'login' | 'logout'; message?: string; durationMs: number } | null>(null);

  // Verify session on mount if token is present
  useEffect(() => {
    const token = localStorage.getItem('neuroscope_token');
    if (token) {
      fetchMe()
        .then((profile) => {
          setUser(profile);
          setIsAuthenticated(true);
          localStorage.setItem('neuroscope_user', JSON.stringify(profile));
        })
        .catch(() => {
          // Token expired or invalid
          localStorage.removeItem('neuroscope_token');
          localStorage.removeItem('neuroscope_user');
          setUser(null);
          setIsAuthenticated(false);
        });
    }
  }, []);

  const login = async (credentials: UserLoginRequest) => {
    setIsLoading(true);
    try {
      const res = await loginResearcher(credentials);
      localStorage.setItem('neuroscope_token', res.token);
      const profile: UserProfile = {
        id: res.id,
        name: res.name,
        institution: res.institution,
        email: res.email
      };
      localStorage.setItem('neuroscope_user', JSON.stringify(profile));

      // Close modal and show background-blurred loader
      setIsAuthModalOpen(false);
      setAuthOverlay({
        type: 'login',
        durationMs: 2200,
        message: 'Validating researcher signature & initializing workspace...',
      });

      await new Promise((resolve) => setTimeout(resolve, 2200));

      setUser(profile);
      setIsAuthenticated(true);
      setAuthOverlay(null);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (payload: UserRegisterRequest) => {
    setIsLoading(true);
    try {
      const res = await registerResearcher(payload);
      localStorage.setItem('neuroscope_token', res.token);
      const profile: UserProfile = {
        id: res.id,
        name: res.name,
        institution: res.institution,
        email: res.email
      };
      localStorage.setItem('neuroscope_user', JSON.stringify(profile));

      // Close modal and show background-blurred loader
      setIsAuthModalOpen(false);
      setAuthOverlay({
        type: 'login',
        durationMs: 2200,
        message: 'Creating institutional researcher profile & setting up workspace...',
      });

      await new Promise((resolve) => setTimeout(resolve, 2200));

      setUser(profile);
      setIsAuthenticated(true);
      setAuthOverlay(null);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setAuthOverlay({
      type: 'logout',
      durationMs: 1800,
      message: 'Terminating active researcher authorization & clearing cache...',
    });

    await new Promise((resolve) => setTimeout(resolve, 1800));

    localStorage.removeItem('neuroscope_token');
    localStorage.removeItem('neuroscope_user');
    setUser(null);
    setIsAuthenticated(false);
    setAuthOverlay(null);
  };

  const openLogin = () => {
    setAuthMode('login');
    setIsAuthModalOpen(true);
  };

  const openRegister = () => {
    setAuthMode('register');
    setIsAuthModalOpen(true);
  };

  const closeAuth = () => {
    setIsAuthModalOpen(false);
  };

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        user,
        authMode,
        isAuthModalOpen,
        authOverlay,
        openLogin,
        openRegister,
        closeAuth,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
