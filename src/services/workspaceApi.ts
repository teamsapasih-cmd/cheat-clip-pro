/** Typed browser client for the authenticated cloud workspace APIs. */
export interface WorkspaceUser {
  id: string;
  email: string;
  display_name: string | null;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
}

export interface WorkspaceProject {
  id: string;
  name: string;
  description: string | null;
  status: string;
  created_at: string;
  updated_at: string;
}

export interface AuthSession {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: WorkspaceUser;
}

export interface UploadIntent {
  media_asset_id: string;
  upload_url: string;
  method: 'PUT';
  required_headers: Record<string, string>;
  expires_in: number;
  max_size_bytes: number;
}

async function request<T>(path: string, token?: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  if (init.body && !(init.body instanceof FormData) && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (token) headers.set('Authorization', `Bearer ${token}`);
  const response = await fetch(path, { ...init, headers });
  const payload = await response.json().catch(() => null) as { detail?: string } | null;
  if (!response.ok) {
    throw new Error(payload?.detail || `Request failed (HTTP ${response.status})`);
  }
  return payload as T;
}

export const workspaceApi = {
  register: (email: string, password: string, displayName: string) =>
    request<AuthSession>('/api/auth/register', undefined, {
      method: 'POST',
      body: JSON.stringify({ email, password, display_name: displayName }),
    }),
  login: (email: string, password: string) =>
    request<AuthSession>('/api/auth/login', undefined, {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),
  me: (token: string) => request<WorkspaceUser>('/api/auth/me', token),
  projects: (token: string) => request<WorkspaceProject[]>('/api/projects', token),
  createProject: (token: string, name: string) =>
    request<WorkspaceProject>('/api/projects', token, {
      method: 'POST',
      body: JSON.stringify({ name }),
    }),
  createUploadIntent: (token: string, projectId: string, file: File) =>
    request<UploadIntent>('/api/media/cloud/upload-intent', token, {
      method: 'POST',
      body: JSON.stringify({
        project_id: projectId,
        filename: file.name,
        content_type: file.type,
        size_bytes: file.size,
      }),
    }),
  completeUpload: (token: string, assetId: string) =>
    request<{ media_asset_id: string; status: string; size_bytes: number; content_type: string }>(
      `/api/media/cloud/${encodeURIComponent(assetId)}/complete`,
      token,
      { method: 'POST' },
    ),
  createAnalysisJob: (token: string, mediaAssetId: string) =>
    request<AnalysisJob>('/api/analyses', token, {
      method: 'POST',
      body: JSON.stringify({ media_asset_id: mediaAssetId, provider: 'gemini', duration: 'auto', transcript_language: 'id' }),
    }),
  analysisStatus: (token: string, analysisId: string) =>
    request<AnalysisJob>(`/api/analyses/${encodeURIComponent(analysisId)}`, token),
};

export async function putSignedUpload(
  url: string,
  file: File,
  headers: Record<string, string>,
  onProgress: (percent: number) => void,
): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('PUT', url);
    Object.entries(headers).forEach(([key, value]) => xhr.setRequestHeader(key, value));
    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable) onProgress(Math.round((event.loaded / event.total) * 100));
    };
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) resolve();
      else reject(new Error(`Cloud storage rejected the upload (HTTP ${xhr.status}). Check bucket CORS settings.`));
    };
    xhr.onerror = () => reject(new Error('Could not reach cloud storage. Check the bucket CORS configuration and network connection.'));
    xhr.onabort = () => reject(new Error('Upload was cancelled.'));
    xhr.send(file);
  });
}

export interface AnalysisJob {
  analysis_id: string;
  job_id: string | null;
  media_asset_id: string;
  status: string;
  progress: number;
  detail: string | null;
  error: string | null;
  result?: { summary?: string; clips?: Array<{ title: string; start_time: number; end_time: number; virality_score: number }> };
}
