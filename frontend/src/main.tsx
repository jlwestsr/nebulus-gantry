import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

// Apply stored theme (default: dark)
const storedTheme = localStorage.getItem('nebulus-theme') || 'dark';
document.documentElement.classList.toggle('dark', storedTheme === 'dark');

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
