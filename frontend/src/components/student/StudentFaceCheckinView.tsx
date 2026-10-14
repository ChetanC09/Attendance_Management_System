import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Camera,
  CameraOff,
  CheckCircle2,
  Clock,
  RefreshCw,
  ShieldAlert,
  ShieldCheck,
  ScanFace,
  Wifi,
  AlertTriangle,
  BookOpen,
  UserCheck,
  Loader2,
} from 'lucide-react';
import { api, ApiError } from '../../services/api';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ActiveSession {
  id: string;
  lecture_id: string;
  course_name: string;
  course_code: string;
  starts_at: string;
  ends_at: string;
}

interface NetworkVerification {
  client_ip: string;
  allowed: boolean;
  reason: string;
  enforced: boolean;
  bound_subnet: string;
}

interface ActiveSessionResponse {
  session: ActiveSession | null;
  already_marked: boolean;
  existing_status: string | null;
  message: string;
  network_verification?: NetworkVerification;
}

interface FaceProfile {
  enrolled: boolean;
  consented_at: string | null;
  revoked_at: string | null;
}

type CheckinState =
  | 'idle'
  | 'loading-session'
  | 'no-session'
  | 'already-marked'
  | 'session-found'
  | 'requesting-camera'
  | 'camera-active'
  | 'capturing'
  | 'submitting'
  | 'success'
  | 'error'
  | 'subnet-blocked';

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(iso: string): string {
  return new Date(iso).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
}

// ─── Sub-components ───────────────────────────────────────────────────────────

const StatusBadge: React.FC<{ children: React.ReactNode; color: string }> = ({
  children,
  color,
}) => (
  <span
    style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: '0.375rem',
      padding: '0.25rem 0.75rem',
      borderRadius: '9999px',
      fontSize: '0.75rem',
      fontWeight: 600,
      background: color,
    }}
  >
    {children}
  </span>
);

// ─── Main Component ───────────────────────────────────────────────────────────

export const StudentFaceCheckinView: React.FC = () => {
  const videoRef = useRef<HTMLVideoElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const streamRef = useRef<MediaStream | null>(null);

  const [state, setState] = useState<CheckinState>('idle');
  const [session, setSession] = useState<ActiveSession | null>(null);
  const [profile, setProfile] = useState<FaceProfile | null>(null);
  const [errorMsg, setErrorMsg] = useState('');
  const [successData, setSuccessData] = useState<{
    course_name: string;
    course_code: string;
    confidence: number;
  } | null>(null);
  const [cameraFacingMode, setCameraFacingMode] = useState<'user' | 'environment'>('user');
  const [networkVerif, setNetworkVerif] = useState<NetworkVerification | null>(null);

  // ── Face profile ────────────────────────────────────────────────────────────
  useEffect(() => {
    api<FaceProfile>('/student/face-profile').then(setProfile).catch(() => {});
  }, []);

  // ── Load active session ─────────────────────────────────────────────────────
  const loadSession = useCallback(async () => {
    setState('loading-session');
    setErrorMsg('');
    try {
      const data = await api<ActiveSessionResponse>('/student/checkin/active-session');
      if (data.network_verification) {
        setNetworkVerif(data.network_verification);
      }
      if (!data.session) {
        setState('no-session');
        setErrorMsg(data.message);
        return;
      }
      if (data.already_marked) {
        setState('already-marked');
        setSession(data.session);
        return;
      }
      setSession(data.session);
      setState('session-found');
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        setState('subnet-blocked');
        setErrorMsg(err.message);
      } else {
        setState('error');
        setErrorMsg(err instanceof ApiError ? err.message : 'Failed to load session');
      }
    }
  }, []);

  useEffect(() => {
    void loadSession();
  }, [loadSession]);

  // ── Camera ──────────────────────────────────────────────────────────────────
  const stopCamera = useCallback(() => {
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop());
      streamRef.current = null;
    }
  }, []);

  const startCamera = useCallback(async () => {
    setState('requesting-camera');
    stopCamera();
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: cameraFacingMode, width: { ideal: 1280 }, height: { ideal: 720 } },
      });
      streamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
        await videoRef.current.play();
      }
      setState('camera-active');
    } catch {
      setState('error');
      setErrorMsg('Camera permission denied or unavailable. Please allow camera access and retry.');
    }
  }, [cameraFacingMode, stopCamera]);

  // Clean up camera on unmount
  useEffect(() => () => stopCamera(), [stopCamera]);

  // ── Capture & submit ────────────────────────────────────────────────────────
  const captureAndSubmit = useCallback(async () => {
    if (!videoRef.current || !canvasRef.current || !session) return;
    setState('capturing');

    const video = videoRef.current;
    const canvas = canvasRef.current;
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    ctx.drawImage(video, 0, 0);

    canvas.toBlob(
      async (blob) => {
        if (!blob) {
          setState('error');
          setErrorMsg('Could not capture image from camera');
          return;
        }
        setState('submitting');
        const form = new FormData();
        form.append('image', blob, 'checkin.jpg');
        try {
          const result = await api<{
            course_name: string;
            course_code: string;
            confidence: number;
          }>('/student/checkin', { method: 'POST', body: form });
          stopCamera();
          setSuccessData(result);
          setState('success');
        } catch (err) {
          if (err instanceof ApiError && err.status === 403) {
            setState('subnet-blocked');
            setErrorMsg(err.message);
          } else {
            setState('error');
            setErrorMsg(
              err instanceof ApiError ? err.message : 'Check-in failed. Please try again.',
            );
          }
        }
      },
      'image/jpeg',
      0.92,
    );
  }, [session, stopCamera]);

  const switchCamera = useCallback(async () => {
    setCameraFacingMode((prev) => (prev === 'user' ? 'environment' : 'user'));
    stopCamera();
    await startCamera();
  }, [startCamera, stopCamera]);

  // ─── Render ─────────────────────────────────────────────────────────────────
  return (
    <div className="checkin-page">
      <canvas ref={canvasRef} style={{ display: 'none' }} />

      {/* Header */}
      <div className="checkin-header">
        <div className="checkin-header-icon">
          <ScanFace size={28} />
        </div>
        <div>
          <h1 className="checkin-title">Face Check-In</h1>
          <p className="checkin-subtitle">Mark your attendance by scanning your face</p>
        </div>
      </div>

      {/* Face profile warning */}
      {profile && !profile.enrolled && (
        <div className="checkin-alert checkin-alert-warn">
          <AlertTriangle size={18} />
          <span>
            Your face is not enrolled. Go to{' '}
            <strong>Profile &amp; settings</strong> to enrol your face before using check-in.
          </span>
        </div>
      )}

      {/* Main card */}
      <div className="checkin-card">
        {/* ── Loading session ─────────────────────────────── */}
        {state === 'loading-session' && (
          <div className="checkin-center">
            <Loader2 size={36} className="checkin-spin" />
            <p className="checkin-hint">Looking for an active lecture…</p>
          </div>
        )}

        {/* ── Subnet blocked ──────────────────────────────── */}
        {state === 'subnet-blocked' && (
          <div className="checkin-center">
            <div className="checkin-status-icon checkin-status-error">
              <Wifi size={32} />
            </div>
            <h2 className="checkin-status-title">Not on Campus Network</h2>
            <p className="checkin-hint">{errorMsg}</p>
            <div className="checkin-instructions">
              <p>
                <strong>What to do:</strong>
              </p>
              <ul>
                <li>Connect to the college Wi-Fi</li>
                <li>Make sure you are physically in the classroom</li>
                <li>Tap Retry once connected</li>
              </ul>
            </div>
            <button className="checkin-btn checkin-btn-primary" onClick={() => void loadSession()}>
              <RefreshCw size={16} /> Retry
            </button>
          </div>
        )}

        {/* ── No session ──────────────────────────────────── */}
        {state === 'no-session' && (
          <div className="checkin-center">
            <div className="checkin-status-icon checkin-status-neutral">
              <Clock size={32} />
            </div>
            <h2 className="checkin-status-title">No Active Session</h2>
            <p className="checkin-hint">{errorMsg}</p>
            <p className="checkin-hint" style={{ fontSize: '0.8rem', opacity: 0.7 }}>
              Your faculty must open an attendance session first.
            </p>
            <button className="checkin-btn checkin-btn-outline" onClick={() => void loadSession()}>
              <RefreshCw size={16} /> Refresh
            </button>
          </div>
        )}

        {/* ── Already marked ──────────────────────────────── */}
        {state === 'already-marked' && session && (
          <div className="checkin-center">
            <div className="checkin-status-icon checkin-status-success">
              <CheckCircle2 size={32} />
            </div>
            <h2 className="checkin-status-title">Already Marked</h2>
            <div className="checkin-session-info">
              <BookOpen size={15} />
              <span>
                {session.course_code} — {session.course_name}
              </span>
            </div>
            <p className="checkin-hint">
              Your attendance is already recorded for this lecture ({fmt(session.starts_at)} –{' '}
              {fmt(session.ends_at)}).
            </p>
          </div>
        )}

        {/* ── Session found, prompt to start ──────────────── */}
        {state === 'session-found' && session && (
          <div className="checkin-center">
            <div className="checkin-status-icon checkin-status-active">
              <UserCheck size={32} />
            </div>
            <h2 className="checkin-status-title">Session Open</h2>
            <div className="checkin-session-card">
              <div className="checkin-session-info">
                <BookOpen size={15} />
                <span>
                  <strong>{session.course_code}</strong> — {session.course_name}
                </span>
              </div>
              <p className="checkin-session-time">
                {fmt(session.starts_at)} – {fmt(session.ends_at)}
              </p>
            </div>

            {networkVerif && (
              <div
                style={{
                  width: '100%',
                  marginTop: '0.75rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  gap: '0.5rem',
                  padding: '0.625rem 0.875rem',
                  borderRadius: '0.75rem',
                  fontSize: '0.75rem',
                  border: networkVerif.allowed ? '1px solid #a7f3d0' : '1px solid #fecdd3',
                  background: networkVerif.allowed ? '#ecfdf5' : '#fff1f2',
                  color: networkVerif.allowed ? '#065f46' : '#9f1239',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <Wifi size={15} />
                  <div>
                    <span style={{ fontWeight: 600 }}>
                      {networkVerif.allowed ? 'Classroom Wi-Fi: Verified' : 'Outside Classroom Network'}
                    </span>
                    <span style={{ marginLeft: '0.25rem', opacity: 0.85 }}>({networkVerif.client_ip})</span>
                  </div>
                </div>
                <span style={{ fontWeight: 600, fontSize: '0.7rem' }}>
                  {networkVerif.enforced ? '🔒 Geofenced' : '⚡ Demo Mode'}
                </span>
              </div>
            )}

            {networkVerif && !networkVerif.allowed && (
              <p style={{ color: '#e11d48', fontSize: '0.75rem', marginTop: '0.5rem', fontWeight: 500 }}>
                ⚠️ Your device IP does not match the classroom network ({networkVerif.bound_subnet}). Connect to the classroom Wi-Fi to check in.
              </p>
            )}

            <p className="checkin-hint">
              Tap <strong>Start Camera</strong> and look directly at the camera.
            </p>
            <button
              className="checkin-btn checkin-btn-primary"
              onClick={() => void startCamera()}
              disabled={profile ? !profile.enrolled || (networkVerif ? !networkVerif.allowed : false) : false}
            >
              <Camera size={18} /> Start Camera
            </button>
          </div>
        )}

        {/* ── Requesting camera ───────────────────────────── */}
        {state === 'requesting-camera' && (
          <div className="checkin-center">
            <Loader2 size={36} className="checkin-spin" />
            <p className="checkin-hint">Requesting camera access…</p>
          </div>
        )}

        {/* ── Camera active ───────────────────────────────── */}
        {(state === 'camera-active' || state === 'capturing' || state === 'submitting') && (
          <div className="checkin-camera-container">
            <div className="checkin-camera-wrapper">
              <video
                ref={videoRef}
                className="checkin-video"
                playsInline
                muted
                autoPlay
              />
              {/* Overlay face guide */}
              <div className="checkin-face-guide">
                <div className="checkin-face-oval" />
              </div>
              {/* Processing overlay */}
              {(state === 'capturing' || state === 'submitting') && (
                <div className="checkin-camera-overlay">
                  <Loader2 size={40} className="checkin-spin checkin-spin-white" />
                  <p className="checkin-overlay-text">
                    {state === 'capturing' ? 'Capturing…' : 'Verifying…'}
                  </p>
                </div>
              )}
            </div>

            {/* Camera instructions */}
            <p className="checkin-camera-hint">
              Centre your face in the oval and ensure good lighting.
            </p>

            <div className="checkin-camera-actions">
              {state === 'camera-active' && (
                <>
                  <button
                    className="checkin-btn checkin-btn-capture"
                    onClick={() => void captureAndSubmit()}
                  >
                    <ScanFace size={20} /> Scan Face
                  </button>
                  <button
                    className="checkin-btn checkin-btn-ghost"
                    onClick={() => void switchCamera()}
                    title="Switch camera"
                  >
                    <RefreshCw size={16} />
                  </button>
                  <button
                    className="checkin-btn checkin-btn-ghost"
                    onClick={() => {
                      stopCamera();
                      setState('session-found');
                    }}
                    title="Stop camera"
                  >
                    <CameraOff size={16} />
                  </button>
                </>
              )}
            </div>
          </div>
        )}

        {/* ── Error ───────────────────────────────────────── */}
        {state === 'error' && (
          <div className="checkin-center">
            <div className="checkin-status-icon checkin-status-error">
              <ShieldAlert size={32} />
            </div>
            <h2 className="checkin-status-title">Check-In Failed</h2>
            <p className="checkin-hint">{errorMsg}</p>
            <div className="checkin-camera-actions">
              <button
                className="checkin-btn checkin-btn-primary"
                onClick={() => {
                  if (session) setState('session-found');
                  else void loadSession();
                }}
              >
                <RefreshCw size={16} /> Try Again
              </button>
            </div>
          </div>
        )}

        {/* ── Success ─────────────────────────────────────── */}
        {state === 'success' && successData && (
          <div className="checkin-center checkin-success-center">
            <div className="checkin-success-anim">
              <ShieldCheck size={48} />
            </div>
            <h2 className="checkin-status-title checkin-success-title">
              Attendance Recorded!
            </h2>
            <div className="checkin-session-card checkin-session-card-success">
              <div className="checkin-session-info">
                <BookOpen size={15} />
                <span>
                  <strong>{successData.course_code}</strong> — {successData.course_name}
                </span>
              </div>
              <p className="checkin-session-time">
                Confidence:{' '}
                <StatusBadge color="rgba(16,185,129,0.15)">
                  {Math.round((successData.confidence ?? 0) * 100)}%
                </StatusBadge>
              </p>
            </div>
            <p className="checkin-hint" style={{ color: 'var(--c-success)' }}>
              ✓ You are marked <strong>Present</strong>
            </p>
          </div>
        )}
      </div>

      {/* Footer hint about network requirement */}
      <div className="checkin-footer">
        <Wifi size={13} />
        <span>Check-in requires you to be on the campus Wi-Fi network</span>
      </div>
    </div>
  );
};
