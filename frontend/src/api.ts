import type {
  AnalysisResponse,
  AuthenticSample,
  DatasetInfo,
  HistoryItem,
  ImportDatasetResponse,
  ModelEvaluation,
  UserRegisterRequest,
  UserLoginRequest,
  UserResponse,
  UserProfile
} from './types';


const API_BASE = '/api';

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem('neuroscope_token');
  const headers: Record<string, string> = {};
  if (token) {
    headers['Authorization'] = `Bearer ${token}`;
  }
  return headers;
}

export async function registerResearcher(payload: UserRegisterRequest): Promise<UserResponse> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Registration failed');
  }
  return res.json();
}

export async function loginResearcher(payload: UserLoginRequest): Promise<UserResponse> {
  const res = await fetch(`${API_BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload)
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Invalid email or password');
  }
  return res.json();
}

export async function fetchMe(): Promise<UserProfile> {
  const res = await fetch(`${API_BASE}/auth/me`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch user profile');
  return res.json();
}

export async function fetchHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/health`);
  if (!res.ok) throw new Error('Failed to fetch health status');
  return res.json();
}

export async function fetchDatasetInfo(): Promise<DatasetInfo> {
  const res = await fetch(`${API_BASE}/dataset/info`);
  if (!res.ok) throw new Error('Failed to fetch dataset info');
  return res.json();
}

export async function fetchSamples(cohort?: string, search?: string): Promise<AuthenticSample[]> {
  const params = new URLSearchParams();
  if (cohort && cohort.toLowerCase() !== 'all') params.append('cohort', cohort);
  if (search && search.trim()) params.append('search', search.trim());
  const queryStr = params.toString();
  const url = `${API_BASE}/dataset/samples${queryStr ? `?${queryStr}` : ''}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error('Failed to fetch authentic dataset samples');
  return res.json();
}

export async function importDataset(file: File): Promise<ImportDatasetResponse> {
  const formData = new FormData();
  formData.append('file', file);
  const res = await fetch(`${API_BASE}/dataset/import`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
  });
  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Failed to import dataset file');
  }
  return res.json();
}


export async function fetchModelEvaluation(): Promise<ModelEvaluation> {
  const res = await fetch(`${API_BASE}/model/evaluation`);
  if (!res.ok) throw new Error('Failed to fetch model evaluation');
  return res.json();
}

export async function fetchModelInfo(): Promise<any> {
  const res = await fetch(`${API_BASE}/model/info`);
  if (!res.ok) throw new Error('Failed to fetch model info');
  return res.json();
}

export async function runAnalysis(
  file?: File,
  sampleId?: string,
  notes?: string
): Promise<AnalysisResponse> {
  const formData = new FormData();
  if (file) {
    formData.append('file', file);
  }
  if (sampleId) {
    formData.append('sample_id', sampleId);
  }
  if (notes) {
    formData.append('notes', notes);
  }

  const res = await fetch(`${API_BASE}/analyze`, {
    method: 'POST',
    headers: getAuthHeaders(),
    body: formData,
  });

  if (!res.ok) {
    const errorData = await res.json().catch(() => ({}));
    throw new Error(errorData.detail || 'Analysis execution failed');
  }

  return res.json();
}

export async function fetchHistory(): Promise<HistoryItem[]> {
  const res = await fetch(`${API_BASE}/history`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch analysis history');
  return res.json();
}

export async function fetchHistoryDetail(id: number): Promise<any> {
  const res = await fetch(`${API_BASE}/history/${id}`, {
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error('Failed to fetch history detail');
  return res.json();
}

export async function deleteHistoryItem(id: number): Promise<void> {
  const res = await fetch(`${API_BASE}/history/${id}`, {
    method: 'DELETE',
    headers: getAuthHeaders()
  });
  if (!res.ok) throw new Error('Failed to delete history item');
}

export function getPdfReportUrl(analysisId: number): string {
  return `${API_BASE}/reports/${analysisId}/pdf`;
}

