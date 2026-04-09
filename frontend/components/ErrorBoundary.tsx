'use client'

import React, { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
  name?: string  // Component name for logging
  onReset?: () => void  // Optional reset hook
  compact?: boolean  // Smaller display for inline boundaries
}

interface State {
  hasError: boolean
  error: Error | null
  errorCount: number  // Track repeated errors
}

export default class ErrorBoundary extends Component<Props, State> {
  private resetTimer: any = null

  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, errorCount: 0 }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    const name = this.props.name || 'anonymous'
    console.error(`[ErrorBoundary:${name}]`, error, errorInfo)
    this.setState(prev => ({ errorCount: prev.errorCount + 1 }))

    // Auto-reset after 5 seconds if it's a transient DOM error (e.g. removeChild)
    if (error.message?.includes('removeChild') || error.message?.includes('Node')) {
      if (this.resetTimer) clearTimeout(this.resetTimer)
      this.resetTimer = setTimeout(() => {
        this.handleReset()
      }, 800)
    }
  }

  componentWillUnmount() {
    if (this.resetTimer) clearTimeout(this.resetTimer)
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null })
    this.props.onReset?.()
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      const compact = this.props.compact
      const pad = compact ? '16px' : '40px'
      const margin = compact ? '10px 0' : '20px'

      return (
        <div style={{
          padding: pad,
          textAlign: 'center',
          background: 'var(--bg-card, #FFFBF5)',
          borderRadius: '12px',
          margin,
          border: '1px solid var(--danger, #C44D4D)',
          fontSize: compact ? '.85rem' : '1rem',
        }}>
          <div style={{ fontSize: compact ? '1.3rem' : '2rem', marginBottom: compact ? 4 : 10 }}>⚠️</div>
          <h3 style={{ color: 'var(--danger, #C44D4D)', marginBottom: 8, fontSize: compact ? '.95rem' : '1.2rem' }}>
            {this.props.name ? `${this.props.name} — хатолик` : 'Хатолик юз берди'}
          </h3>
          <p style={{ color: 'var(--text-secondary, #6B5744)', marginBottom: 12, fontSize: compact ? '.75rem' : '.9rem' }}>
            {this.state.error?.message?.slice(0, 200) || 'Кутилмаган хатолик'}
          </p>
          <button
            onClick={this.handleReset}
            style={{
              padding: compact ? '6px 16px' : '10px 24px',
              background: 'var(--accent-primary, #B48C64)',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: compact ? '.78rem' : '14px',
              fontWeight: 700,
            }}
          >
            🔄 Қайта уриниш
          </button>
          {this.state.errorCount > 3 && (
            <div style={{ marginTop: 8, fontSize: '.7rem', color: '#94A3B8' }}>
              Такрор хато ({this.state.errorCount}×) — саҳифани refresh қилинг
            </div>
          )}
        </div>
      )
    }

    return this.props.children
  }
}
