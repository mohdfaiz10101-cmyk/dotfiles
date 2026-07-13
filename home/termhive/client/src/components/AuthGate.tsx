import { useEffect, useState } from 'react';
import App from '../App';
import Ic from './Icons';

interface AuthStatus {
  authenticated: boolean;
  enabled: boolean;
  username: string | null;
}

export default function AuthGate() {
  const [status, setStatus] = useState<AuthStatus | null>(null);
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const check = () => {
    fetch('/api/auth/status', { credentials: 'same-origin' })
      .then((r) => r.json())
      .then((data: AuthStatus) => setStatus(data))
      .catch(() => setStatus({ authenticated: false, enabled: true, username: null }));
  };

  useEffect(check, []);

  const login = async (event: React.FormEvent) => {
    event.preventDefault();
    setSubmitting(true);
    setError('');
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        credentials: 'same-origin',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(data.error || `Login failed (${response.status})`);
      setStatus(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setSubmitting(false);
    }
  };

  if (!status) {
    return (
      <div className="auth-page">
        <div className="auth-loading"><span className="cmd-dot" /><span className="cmd-dot" /><span className="cmd-dot" /></div>
      </div>
    );
  }

  if (status.authenticated || !status.enabled) return <App />;

  return (
    <div className="auth-page">
      <form className="auth-card" onSubmit={login}>
        <div className="auth-logo"><Ic.logo size={26} /></div>
        <h1>TermHive</h1>
        <p>Sign in to your remote terminal control plane.</p>
        <label htmlFor="termhive-user">Username</label>
        <input
          id="termhive-user"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          autoCapitalize="none"
          spellCheck={false}
          autoFocus
        />
        <label htmlFor="termhive-password">Password</label>
        <input
          id="termhive-password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
        />
        {error && <div className="auth-error">{error}</div>}
        <button className="auth-submit" type="submit" disabled={submitting || !username || !password}>
          {submitting ? 'Signing in…' : 'Sign in'}
        </button>
        <div className="auth-note">HTTPS + private Tailnet access</div>
      </form>
    </div>
  );
}
