import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Component } from 'react';
import type { ErrorInfo, ReactNode } from 'react';
import Layout from './components/Layout';
import Home from './pages/Home';
import Overview from './pages/Overview';
import Binding from './pages/Binding';
import Selectivity from './pages/Selectivity';
import EHR from './pages/EHR';
import Agent from './pages/Agent';
import About from './pages/About';
import Documentation from './pages/Documentation';

class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) { return { error }; }
  componentDidCatch(error: Error, info: ErrorInfo) { console.error('React error:', error, info); }
  render() {
    if (this.state.error) {
      return (
        <div style={{ padding: 40, fontFamily: 'Arial' }}>
          <h1 style={{ color: 'red' }}>Something went wrong</h1>
          <pre style={{ whiteSpace: 'pre-wrap', background: '#f5f5f5', padding: 16 }}>
            {this.state.error.message}{'\n\n'}{this.state.error.stack}
          </pre>
        </div>
      );
    }
    return this.props.children;
  }
}

export default function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<Home />} />
            <Route path="/overview" element={<Overview />} />
            <Route path="/binding" element={<Binding />} />
            <Route path="/selectivity" element={<Selectivity />} />
            <Route path="/ehr" element={<EHR />} />
            <Route path="/agent" element={<Agent />} />
            <Route path="/about" element={<About />} />
            <Route path="/documentation" element={<Documentation />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}
