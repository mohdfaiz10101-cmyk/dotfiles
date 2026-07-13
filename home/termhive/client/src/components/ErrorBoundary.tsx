import React from 'react';

interface State {
  error: Error | null;
}

export default class ErrorBoundary extends React.Component<React.PropsWithChildren, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    console.error('[termhive-ui]', error, info);
  }

  render() {
    if (!this.state.error) return this.props.children;
    return (
      <div className="auth-page">
        <div className="auth-card">
          <h1>TermHive hit a UI error</h1>
          <p>{this.state.error.message}</p>
          <button className="auth-submit" onClick={() => window.location.reload()}>Reload dashboard</button>
        </div>
      </div>
    );
  }
}
