import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { ThemeProvider } from './context/ThemeContext.tsx'

// Apply theme to <html> before React mounts to prevent flash-of-wrong-theme.
// ThemeContext will call this again on mount (idempotent).
;(function applyStoredTheme() {
  try {
    const stored = localStorage.getItem('mf-theme');
    const theme =
      stored === 'light' || stored === 'dark'
        ? stored
        : window.matchMedia?.('(prefers-color-scheme: light)').matches
        ? 'light'
        : 'dark';
    document.documentElement.setAttribute('data-theme', theme);
    document.documentElement.style.colorScheme = theme;
  } catch {}
})();

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ThemeProvider>
      <App />
    </ThemeProvider>
  </StrictMode>,
)
