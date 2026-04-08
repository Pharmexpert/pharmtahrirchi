'use client'

import React from 'react'

export function Skeleton({ width = '100%', height = 16, rounded = 6, style = {} }: {
  width?: string | number
  height?: string | number
  rounded?: number
  style?: React.CSSProperties
}) {
  return (
    <div
      style={{
        width, height,
        borderRadius: rounded,
        background: 'linear-gradient(90deg, #F1F5F9 0%, #E2E8F0 50%, #F1F5F9 100%)',
        backgroundSize: '200% 100%',
        animation: 'shimmer 1.4s ease-in-out infinite',
        ...style,
      }}
    />
  )
}

export function SkeletonTable({ rows = 5, cols = 4 }: { rows?: number; cols?: number }) {
  return (
    <div style={{ padding: 20 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 12 }}>
          {Array.from({ length: cols }).map((__, j) => (
            <Skeleton key={j} width={j === 0 ? 60 : j === cols - 1 ? 90 : '100%'} height={24} />
          ))}
        </div>
      ))}
    </div>
  )
}

export function SkeletonCards({ count = 6 }: { count?: number }) {
  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 12 }}>
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} style={{ padding: 16, borderRadius: 12, border: '1px solid #E2E8F0', background: '#FAFBFC' }}>
          <Skeleton width={100} height={10} style={{ marginBottom: 10 }} />
          <Skeleton width={60} height={22} />
        </div>
      ))}
    </div>
  )
}

/* Add keyframes to global.css or use jsx block */
export const SkeletonStyles = () => (
  <style jsx global>{`
    @keyframes shimmer {
      0% { background-position: 200% 0; }
      100% { background-position: -200% 0; }
    }
  `}</style>
)
