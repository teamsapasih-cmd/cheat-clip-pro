import { useEffect, useState } from 'react';
import { Cloud, FolderPlus, LogIn, LogOut, UploadCloud, X } from 'lucide-react';
import {
  putSignedUpload,
  workspaceApi,
  type AuthSession,
  type AnalysisJob,
  type WorkspaceProject,
  type WorkspaceUser,
} from '../services/workspaceApi';
import './CloudWorkspacePanel.css';

const SESSION_KEY = 'clip_intelligence_session';

function readSession(): AuthSession | null {
  try {
    const raw = sessionStorage.getItem(SESSION_KEY);
    return raw ? JSON.parse(raw) as AuthSession : null;
  } catch {
    return null;
  }
}

export function CloudWorkspacePanel() {
  const [open, setOpen] = useState(false);
  const [session, setSession] = useState<AuthSession | null>(readSession);
  const [user, setUser] = useState<WorkspaceUser | null>(null);
  const [projects, setProjects] = useState<WorkspaceProject[]>([]);
  const [projectName, setProjectName] = useState('');
  const [selectedProject, setSelectedProject] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [mode, setMode] = useState<'login' | 'register'>('register');
  const [busy, setBusy] = useState(false);
  const [progress, setProgress] = useState<number | null>(null);
  const [uploadedAssetId, setUploadedAssetId] = useState<string | null>(null);
  const [analysisJob, setAnalysisJob] = useState<AnalysisJob | null>(null);
  const [message, setMessage] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!session?.access_token) return;
    let active = true;
    void Promise.all([
      workspaceApi.me(session.access_token),
      workspaceApi.projects(session.access_token),
    ]).then(([currentUser, ownedProjects]) => {
      if (!active) return;
      setUser(currentUser);
      setProjects(ownedProjects);
      setSelectedProject((current) =>
        current && ownedProjects.some((project) => project.id === current)
          ? current
          : ownedProjects[0]?.id || '',
      );
    }).catch((reason: unknown) => {
      if (!active) return;
      const text = reason instanceof Error ? reason.message : 'Session expired';
      setError(text);
      setUser(null);
      setProjects([]);
      sessionStorage.removeItem(SESSION_KEY);
      setSession(null);
    });
    return () => { active = false; };
  }, [session]);


  useEffect(() => {
    const token = session?.access_token;
    const analysisId = analysisJob?.analysis_id;
    if (!token || !analysisId || ['completed', 'failed', 'cancelled'].includes(analysisJob?.status || '')) return;
    let active = true;
    let timer: number | undefined;
    const poll = async () => {
      try {
        const latest = await workspaceApi.analysisStatus(token, analysisId);
        if (!active) return;
        setAnalysisJob(latest);
        if (!['completed', 'failed', 'cancelled'].includes(latest.status)) timer = window.setTimeout(poll, 2000);
      } catch (reason) {
        if (!active) return;
        setError(reason instanceof Error ? reason.message : 'Could not refresh analysis status.');
        timer = window.setTimeout(poll, 5000);
      }
    };
    timer = window.setTimeout(poll, 1200);
    return () => { active = false; if (timer !== undefined) window.clearTimeout(timer); };
  }, [session?.access_token, analysisJob?.analysis_id, analysisJob?.status]);

  const saveSession = (next: AuthSession) => {
    sessionStorage.setItem(SESSION_KEY, JSON.stringify(next));
    setSession(next);
    setError('');
    setMessage('Signed in successfully.');
  };

  const submitAuth = async () => {
    setBusy(true);
    setError('');
    setMessage('');
    try {
      const next = mode === 'register'
        ? await workspaceApi.register(email.trim(), password, displayName.trim())
        : await workspaceApi.login(email.trim(), password);
      saveSession(next);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Authentication failed.');
    } finally {
      setBusy(false);
    }
  };

  const createProject = async () => {
    if (!session || !projectName.trim()) return;
    setBusy(true);
    setError('');
    try {
      const project = await workspaceApi.createProject(session.access_token, projectName.trim());
      const next = [...projects, project];
      setProjects(next);
      setSelectedProject(project.id);
      setProjectName('');
      setMessage('Project created.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not create project.');
    } finally {
      setBusy(false);
    }
  };

  const uploadFile = async (file?: File) => {
    if (!file || !session || !selectedProject) return;
    setBusy(true);
    setError('');
    setMessage('');
    setProgress(0);
    try {
      const intent = await workspaceApi.createUploadIntent(session.access_token, selectedProject, file);
      await putSignedUpload(intent.upload_url, file, intent.required_headers, setProgress);
      const completed = await workspaceApi.completeUpload(session.access_token, intent.media_asset_id);
      setProgress(100);
      setUploadedAssetId(completed.media_asset_id);
      setAnalysisJob(null);
      setMessage(`${file.name} uploaded and verified (${(completed.size_bytes / 1024 / 1024).toFixed(1)} MB).`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Upload failed.');
    } finally {
      setBusy(false);
    }
  };


  const startAnalysis = async () => {
    if (!session || !uploadedAssetId) return;
    setBusy(true); setError(''); setMessage('');
    try {
      const job = await workspaceApi.createAnalysisJob(session.access_token, uploadedAssetId);
      setAnalysisJob(job); setMessage('Video queued for AI analysis.');
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not start AI analysis.');
    } finally { setBusy(false); }
  };

  const signOut = () => {
    sessionStorage.removeItem(SESSION_KEY);
    setSession(null);
    setUser(null);
    setProjects([]);
    setSelectedProject('');
    setUploadedAssetId(null);
    setAnalysisJob(null);
    setMessage('Signed out.');
    setError('');
  };

  return (
    <>
      <button className="cloud-workspace-launcher" onClick={() => setOpen(true)} type="button">
        <Cloud size={17} /> Cloud Workspace
      </button>
      {open && (
        <div className="cloud-workspace-backdrop" role="presentation" onMouseDown={(event) => {
          if (event.target === event.currentTarget) setOpen(false);
        }}>
          <section className="cloud-workspace-panel" role="dialog" aria-modal="true" aria-labelledby="cloud-workspace-title">
            <header className="cloud-workspace-header">
              <div>
                <span className="cloud-workspace-eyebrow">CLIP INTELLIGENCE STUDIO</span>
                <h2 id="cloud-workspace-title">Cloud Workspace</h2>
              </div>
              <button className="cloud-workspace-icon-button" onClick={() => setOpen(false)} type="button" aria-label="Close">
                <X size={19} />
              </button>
            </header>

            {user ? (
              <div className="cloud-workspace-user">
                <div className="cloud-workspace-user-copy">
                  <strong>{user.display_name || user.email}</strong>
                  <span>{user.email}</span>
                </div>
                <button className="cloud-workspace-secondary" onClick={signOut} type="button">
                  <LogOut size={15} /> Sign out
                </button>
              </div>
            ) : (
              <div className="cloud-workspace-auth">
                <div className="cloud-workspace-tabs">
                  <button className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')} type="button">Create account</button>
                  <button className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')} type="button">Sign in</button>
                </div>
                {mode === 'register' && (
                  <label>Display name<input value={displayName} onChange={(event) => setDisplayName(event.target.value)} autoComplete="name" maxLength={160} /></label>
                )}
                <label>Email<input type="email" value={email} onChange={(event) => setEmail(event.target.value)} autoComplete="email" /></label>
                <label>Password<input type="password" value={password} onChange={(event) => setPassword(event.target.value)} autoComplete={mode === 'register' ? 'new-password' : 'current-password'} /></label>
                {mode === 'register' && <p className="cloud-workspace-hint">Use at least 12 characters. Your session is kept in this browser tab.</p>}
                <button className="cloud-workspace-primary" disabled={busy || !email.trim() || password.length < (mode === 'register' ? 12 : 1)} onClick={() => void submitAuth()} type="button">
                  <LogIn size={16} /> {busy ? 'Please wait…' : mode === 'register' ? 'Create account' : 'Sign in'}
                </button>
              </div>
            )}

            {user && (
              <div className="cloud-workspace-content">
                <div className="cloud-workspace-section-title">Your projects</div>
                <div className="cloud-workspace-create-row">
                  <input aria-label="New project name" placeholder="New project name" value={projectName} onChange={(event) => setProjectName(event.target.value)} maxLength={200} />
                  <button className="cloud-workspace-secondary" disabled={busy || !projectName.trim()} onClick={() => void createProject()} type="button">
                    <FolderPlus size={16} /> Add
                  </button>
                </div>
                <label className="cloud-workspace-project-label">
                  Active project
                  <select value={selectedProject} onChange={(event) => setSelectedProject(event.target.value)}>
                    <option value="">Select a project</option>
                    {projects.map((project) => <option key={project.id} value={project.id}>{project.name}</option>)}
                  </select>
                </label>
                <div className="cloud-workspace-upload">
                  <UploadCloud size={24} />
                  <strong>Upload source video</strong>
                  <span>MP4, MOV, WebM or MKV · maximum 2 GB</span>
                  <label className="cloud-workspace-file-button">
                    Choose video
                    <input type="file" accept="video/mp4,video/quicktime,video/webm,video/x-matroska" disabled={busy || !selectedProject} onChange={(event) => {
                      const file = event.target.files?.[0];
                      void uploadFile(file);
                      event.currentTarget.value = '';
                    }} />
                  </label>
                  {!selectedProject && <small>Create or select a project first.</small>}
                  {progress !== null && <div className="cloud-workspace-progress"><span style={{ width: String(progress) + '%' }} /></div>}
                  {uploadedAssetId && (
                    <div className="cloud-workspace-analysis">
                      <button className="cloud-workspace-primary" disabled={busy || Boolean(analysisJob && !['failed', 'cancelled'].includes(analysisJob.status))} onClick={() => void startAnalysis()} type="button">
                        {analysisJob && !['failed', 'cancelled'].includes(analysisJob.status) ? 'Analysis running…' : 'Start AI analysis'}
                      </button>
                      {analysisJob && (
                        <>
                          <strong>{analysisJob.status.replaceAll('_', ' ')}</strong>
                          <span>{analysisJob.detail || (analysisJob.status === 'completed' ? 'Analysis complete.' : 'Preparing analysis worker…')}</span>
                          <div className="cloud-workspace-progress"><span style={{ width: String(Math.max(0, Math.min(100, analysisJob.progress))) + '%' }} /></div>
                          {analysisJob.result?.clips && <small>{analysisJob.result.clips.length} clip candidates found.</small>}
                          {analysisJob.error && <small>{analysisJob.error}</small>}
                        </>
                      )}
                    </div>
                  )}
                </div>
              </div>
            )}

            {error && <div className="cloud-workspace-alert error" role="alert">{error}</div>}
            {message && <div className="cloud-workspace-alert success" role="status">{message}</div>}
            <footer className="cloud-workspace-footer">Cloud upload requires configured database, private object storage and bucket CORS settings.</footer>
          </section>
        </div>
      )}
    </>
  );
}
