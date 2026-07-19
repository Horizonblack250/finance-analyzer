import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// Self-hosted fonts (see index.css comment for why -- more reliable than
// a live Google Fonts CDN import, which can silently fail and fall back
// to a default system font, causing inconsistent typography across pages).
import '@fontsource/manrope/400.css'
import '@fontsource/manrope/500.css'
import '@fontsource/manrope/600.css'
import '@fontsource/manrope/700.css'
import '@fontsource/ibm-plex-mono/400.css'
import '@fontsource/ibm-plex-mono/500.css'

import './index.css'
import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
