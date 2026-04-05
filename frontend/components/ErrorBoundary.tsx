'use client'

import React, { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export default class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error('[ErrorBoundary]', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div style={{
          padding: '40px',
          textAlign: 'center',
          background: 'var(--bg-card, #FFFBF5)',
          borderRadius: '16px',
          margin: '20px',
          border: '1px solid var(--danger, #C44D4D)',
        }}>
          <h2 style={{ color: 'var(--danger, #C44D4D)', marginBottom: '12px' }}>
            Хатолик юз берди
          </h2>
          <p style={{ color: 'var(--text-secondary, #6B5744)', marginBottom: '16px' }}>
            {this.state.error?.message || 'Кутилмаган хатолик'}
          </p>
          <button
            onClick={() => this.setState({ hasError: false, error: null })}
            style={{
              padding: '10px 24px',
              background: 'var(--accent-primary, #B48C64)',
              color: '#fff',
              border: 'none',
              borderRadius: '8px',
              cursor: 'pointer',
              fontSize: '14px',
            }}
          >
            Қайта уриниш
          </button>
        </div>
      )
    }

    return this.props.children
  }
}
