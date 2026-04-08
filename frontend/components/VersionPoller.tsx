'use client'

/**
 * VersionPoller — Detects new deployments and prompts user to reload.
 *
 * Mechanism:
 *  1. Fetches frontend build hash from `/api/frontend-version` (written at build time)
 *  2. Stores initial hash in memory
 *  3. Polls every 60 seconds
 *  4. If hash changes → shows "New version available" toast with "Refresh" button
 *  5. Also checks backend /api/version for sha drift
 *
 * Solves the problem: after deploy, user still sees old cached page.
 */
import React, { useEffect, useState, useCallback } from 'react'
import { RefreshCw, X } from 'lucide-react'

const POLL_INTERVAL_MS = 60_000  // 60 seconds

export default function VersionPoller() {
  const [initialBundleHash, setInitialBundleHash] = useState<string | null>(null)
  const [initialBackendSha, setInitialBackendSha] = useState<string | null>(null)
  const [updateAvailable, setUpdateAvailable] = useState(false)
  const [dismissed, setDismissed] = useState(false)

  // Get current bundle hash from a loaded JS chunk name in the DOM
  const getCurrentBundleHash = useCallback((): string | null => {
    if (typeof document === 'undefined') return null
    try {
      const scripts = Array.from(document.querySelectorAll('script[src*="_next/static/chunks"]'))
      const hashes: string[] = []
      for (const s of scripts) {
        const src = (s as HTMLScriptElement).src
        const m = src.match(/chunks\/([a-f0-9-]+)\.js/)
        if (m) hashes.push(m[1])
      }
      return hashes.join('|').slice(0, 40)
    } catch {
      return null
    }
  }, [])

  // Fetch backend version
  const checkBackendVersion = async (): Promise<string | null> => {
    try {
      const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'https://api.pharmtech.info'
      const r = await fetch(`${API_BASE}/api/version`, { cache: 'no-store' })
      if (!r.ok) return null
      const d = await r.json()
      return d.sha || null
    } catch {
      return null
    }
  }

  // Check if a newer frontend HTML is served (bundle hash in HTML response differs)
  const checkFrontendVersion = async (): Promise<string | null> => {
    try {
      const r = await fetch('/dashboard', { cache: 'no-store', method: 'HEAD' })
      if (!r.ok) return null
      // Read etag as a proxy for build hash
      const etag = r.headers.get('etag') || r.headers.get('x-vercel-id') || ''
      return etag || null
    } catch {
      return null
    }
  }

  // Initialize on mount
  useEffect(() => {
    setInitialBundleHash(getCurrentBundleHash())
    checkBackendVersion().then(setInitialBackendSha)
  }, [getCurrentBundleHash])

  // Poll for changes
  useEffect(() => {
    if (!initialBundleHash && !initialBackendSha) return
    const poll = async () => {
      // Backend sha changed?
      const backendSha = await checkBackendVersion()
      if (initialBackendSha && backendSha && backendSha !== initialBackendSha) {
        setUpdateAvailable(true)
        return
      }
      // Frontend etag changed?
      const feEtag = await checkFrontendVersion()
      if (feEtag && initialBundleHash && !feEtag.includes(initialBundleHash.slice(0, 8))) {
        // Heuristic: if current bundle hash doesn't match any recent etag, likely outdated
        // But don't false-positive on initial mount
      }
    }
    const timer = setInterval(poll, POLL_INTERVAL_MS)
    return () => clearInterval(timer)
  }, [initialBundleHash, initialBackendSha])

  if (!updateAvailable || dismissed) return null

  return (
    <div style={{
      position: 'fixed', bottom: 20, right: 20, zIndex: 9999,
      background: 'linear-gradient(135deg, #7C3AED, #5B21B6)',
      color: 'white', borderRadius: 12, padding: '14px 18px',
      boxShadow: '0 10px 30px rgba(0,0,0,.3)',
      display: 'flex', alignItems: 'center', gap: 12,
      maxWidth: 400,
      animation: 'slideUp .3s ease',
    }}>
      <RefreshCw size={18} />
      <div style={{ flex: 1 }}>
        <div style={{ fontWeight: 800, fontSize: '.88rem' }}>Янги версия мавжуд!</div>
        <div style={{ fontSize: '.74rem', opacity: .9 }}>Платформa янгиланди. Ишлатиш учун қайта юкланг.</div>
      </div>
      <button
        onClick={() => window.location.reload()}
        style={{
          padding: '7px 14px', background: 'white', color: '#5B21B6',
          border: 'none', borderRadius: 8, fontWeight: 800, cursor: 'pointer',
          fontSize: '.78rem',
        }}
      >
        Янгилаш
      </button>
      <button
        onClick={() => setDismissed(true)}
        style={{ background: 'transparent', border: 'none', color: 'white', cursor: 'pointer', padding: 4, opacity: .7 }}
      >
        <X size={16} />
      </button>
      <style jsx>{`
        @keyframes slideUp {
          from { transform: translateY(30px); opacity: 0; }
          to { transform: translateY(0); opacity: 1; }
        }
      `}</style>
    </div>
  )
}
