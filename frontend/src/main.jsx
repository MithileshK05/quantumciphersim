import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import './index.css'
import App from './App.jsx'
import { SimulationProvider } from './context/SimulationContext.jsx'

const queryClient = new QueryClient();

// ── Keep-alive ping ──────────────────────────────────────────────────────────
// Render free tier sleeps after 15 min of inactivity (cold start = 30-60s).
// This pings the backend immediately on load and every 10 min to keep it warm.
const API = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const pingBackend = () => fetch(`${API}/`).catch(() => {});
pingBackend(); // immediate wake-up on first page load
setInterval(pingBackend, 10 * 60 * 1000); // ping every 10 minutes
// ────────────────────────────────────────────────────────────────────────────

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <QueryClientProvider client={queryClient}>
      <SimulationProvider>
        <BrowserRouter>
          <App />
        </BrowserRouter>
      </SimulationProvider>
    </QueryClientProvider>
  </StrictMode>,
)
