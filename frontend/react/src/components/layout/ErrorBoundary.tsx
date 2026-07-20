import { Component, type ErrorInfo, type ReactNode } from 'react';

type Props = {
  children: ReactNode;
};

type State = {
  hasError: boolean;
};

class ErrorBoundary extends Component<Props, State> {
  state: State = {
    hasError: false,
  };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('Synapse UI error boundary:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <main className="flex min-h-screen items-center justify-center bg-ink px-6 text-text">
          <section className="max-w-md rounded-panel border border-danger/40 bg-ink-raised p-6 text-center shadow-glow-signal">
            <p className="font-mono text-[11px] uppercase tracking-[0.24em] text-danger">runtime fault</p>
            <h1 className="mt-2 font-display text-2xl text-parchment">The interface encountered an issue.</h1>
            <p className="mt-3 text-sm text-text-muted">
              The Synapse shell could not render cleanly. Please refresh and retry.
            </p>
          </section>
        </main>
      );
    }

    return this.props.children;
  }
}

export default ErrorBoundary;
