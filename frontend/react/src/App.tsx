import ErrorBoundary from './components/layout/ErrorBoundary';
import AppShell from './components/layout/AppShell';

function App() {
  return (
    <ErrorBoundary>
      <AppShell />
    </ErrorBoundary>
  );
}

export default App;
