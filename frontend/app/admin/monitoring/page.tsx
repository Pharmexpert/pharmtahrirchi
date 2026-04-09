'use client'

import React, { useEffect, useState } from 'react'
import { BarChart3, Users, Database, Activity, Pill, Sparkles, TrendingUp, Calendar, BookOpen, Loader2 } from 'lucide-react'
import api from '../../../services/api'
import { useAuth } from '../../../components/LoginGuard'

type Period = 'daily' | 'weekly' | 'monthly'

export default function MonitoringPage() {
  const { token } = useAuth()
  const [period, setPeriod] = useState<Period>('daily')
  const [data, setData] = useState<any>(null)
  const [loading, setLoading] = useState(false)

  const load = async () => {
    if (!token) return
    setLoading(true)
    try {
      const r = await api.admin.monitoring(period)
      setData(r)
    } catch (_) {}
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [token, period])

  const StatCard = ({ icon: Icon, label, value, color, sub }: any) => (
    <div style={{
      background: 'white', border: '1.5px solid var(--border)', borderRadius: 14, padding: 18,
      display: 'flex', gap: 14, alignItems: 'center',
    }}>
      <div style={{ width: 50, height: 50, borderRadius: 12, background: `${color}22`, color, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon size={26} />
      </div>
      <div>
        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', textTransform: 'uppercase', fontWeight: 700 }}>{label}</div>
        <div style={{ fontSize: '1.6rem', fontWeight: 800, color: 'var(--text-primary)', lineHeight: 1.2 }}>{value}</div>
        {sub !== undefined && <div style={{ fontSize: '0.72rem', color, fontWeight: 600 }}>{sub}</div>}
      </div>
    </div>
  )

  // Enhanced SVG chart: area + line + gradient + grid + tooltip markers
  const BarChart = ({ data: chartData, color = '#7C3AED', label = 'Кунлик' }: { data: Array<{ date: string; count: number }>; color?: string; label?: string }) => {
    if (!chartData || chartData.length === 0) return (
      <div style={{ background: 'white', border: '1.5px solid var(--border)', borderRadius: 14, padding: 30, textAlign: 'center', color: '#9CA3AF' }}>
        📊 {label}: маълумот йўқ
      </div>
    )
    const max = Math.max(...chartData.map(d => d.count), 1)
    const total = chartData.reduce((a, b) => a + b.count, 0)
    const avg = Math.round(total / chartData.length)
    // Growth: compare last 3 days avg vs previous 3 days avg
    const lastN = chartData.slice(-3).reduce((a, b) => a + b.count, 0) / 3
    const prevN = chartData.slice(-6, -3).reduce((a, b) => a + b.count, 0) / 3
    const growth = prevN > 0 ? ((lastN - prevN) / prevN) * 100 : 0

    const W = 800
    const H = 220
    const padL = 40
    const padB = 30
    const padT = 20
    const innerW = W - padL - 10
    const innerH = H - padT - padB
    const stepX = innerW / Math.max(1, chartData.length - 1)

    // Area path
    const points = chartData.map((d, i) => ({
      x: padL + i * stepX,
      y: padT + innerH - (d.count / max) * innerH,
      v: d.count,
      date: d.date,
    }))
    const linePath = points.map((p, i) => `${i === 0 ? 'M' : 'L'}${p.x},${p.y}`).join(' ')
    const areaPath = linePath + ` L${points[points.length - 1].x},${padT + innerH} L${points[0].x},${padT + innerH} Z`

    // Grid lines (4 horizontal)
    const gridLines = [0.25, 0.5, 0.75, 1].map(p => ({
      y: padT + innerH - p * innerH,
      label: Math.round(p * max),
    }))

    return (
      <div style={{ background: 'white', border: '1.5px solid var(--border)', borderRadius: 14, padding: 18 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 }}>
          <h3 style={{ margin: 0, fontSize: '0.95rem', fontWeight: 700, display: 'flex', alignItems: 'center', gap: 6 }}>
            <BarChart3 size={16} color={color} /> {label}
          </h3>
          <div style={{ display: 'flex', gap: 10, fontSize: '0.72rem' }}>
            <span style={{ color: '#64748B' }}>Жами: <b style={{ color }}>{total.toLocaleString()}</b></span>
            <span style={{ color: '#64748B' }}>Ўрт: <b style={{ color }}>{avg}</b></span>
            {growth !== 0 && (
              <span style={{
                color: growth > 0 ? '#16A34A' : '#DC2626',
                fontWeight: 700,
                display: 'flex', alignItems: 'center', gap: 2
              }}>
                {growth > 0 ? '↗' : '↘'} {Math.abs(growth).toFixed(0)}%
              </span>
            )}
          </div>
        </div>
        <svg viewBox={`0 0 ${W} ${H}`} style={{ width: '100%', height: 220 }}>
          <defs>
            <linearGradient id={`grad-${label}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          {/* Grid lines */}
          {gridLines.map((g, i) => (
            <g key={i}>
              <line x1={padL} y1={g.y} x2={W - 10} y2={g.y} stroke="#F1F5F9" strokeWidth={1} strokeDasharray="3,3" />
              <text x={padL - 8} y={g.y + 3} fontSize="9" fill="#94A3B8" textAnchor="end">{g.label}</text>
            </g>
          ))}
          {/* Area fill */}
          <path d={areaPath} fill={`url(#grad-${label})`} />
          {/* Line */}
          <path d={linePath} fill="none" stroke={color} strokeWidth={2.2} strokeLinecap="round" strokeLinejoin="round" />
          {/* Points */}
          {points.map((p, i) => (
            <circle key={i} cx={p.x} cy={p.y} r={2.5} fill={color}>
              <title>{p.date}: {p.v}</title>
            </circle>
          ))}
          {/* X labels */}
          {points.map((p, i) => (
            i % Math.max(1, Math.floor(points.length / 8)) === 0 ? (
              <text key={i} x={p.x} y={H - 8} fontSize="9" fill="#94A3B8" textAnchor="middle">{p.date.slice(5)}</text>
            ) : null
          ))}
        </svg>
      </div>
    )
  }

  // Donut chart for AI usage breakdown
  const DonutChart = ({ data: d }: { data: Record<string, number> }) => {
    const entries = Object.entries(d).sort(([, a], [, b]) => b - a)
    const total = entries.reduce((a, [, v]) => a + v, 0)
    if (total === 0) return null
    const colors = ['#7C3AED', '#0EA5E9', '#16A34A', '#F59E0B', '#EC4899', '#0891B2', '#DC2626']
    const R = 70
    const cx = 100
    const cy = 100
    let cum = 0
    const slices = entries.map(([k, v], i) => {
      const pct = v / total
      const startAngle = cum * Math.PI * 2
      cum += pct
      const endAngle = cum * Math.PI * 2
      const x1 = cx + R * Math.sin(startAngle)
      const y1 = cy - R * Math.cos(startAngle)
      const x2 = cx + R * Math.sin(endAngle)
      const y2 = cy - R * Math.cos(endAngle)
      const large = pct > 0.5 ? 1 : 0
      return {
        key: k, v, pct,
        path: `M${cx},${cy} L${x1},${y1} A${R},${R} 0 ${large} 1 ${x2},${y2} Z`,
        color: colors[i % colors.length],
      }
    })
    return (
      <div style={{ display: 'flex', gap: 20, alignItems: 'center' }}>
        <svg viewBox="0 0 200 200" style={{ width: 180, height: 180, flexShrink: 0 }}>
          {slices.map(s => (
            <path key={s.key} d={s.path} fill={s.color} stroke="white" strokeWidth={2}>
              <title>{s.key}: {s.v}</title>
            </path>
          ))}
          <circle cx={cx} cy={cy} r={R * 0.55} fill="white" />
          <text x={cx} y={cy - 4} textAnchor="middle" fontSize="14" fontWeight="800" fill="#1E293B">{total}</text>
          <text x={cx} y={cy + 12} textAnchor="middle" fontSize="10" fill="#94A3B8">AI calls</text>
        </svg>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6, flex: 1 }}>
          {slices.map(s => (
            <div key={s.key} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: '0.82rem' }}>
              <div style={{ width: 10, height: 10, background: s.color, borderRadius: 2 }} />
              <span style={{ flex: 1, fontWeight: 600 }}>{s.key}</span>
              <span style={{ color: '#64748B', fontWeight: 700 }}>{s.v}</span>
              <span style={{ color: '#94A3B8', fontSize: '0.72rem', minWidth: 35, textAlign: 'right' }}>{(s.pct * 100).toFixed(0)}%</span>
            </div>
          ))}
        </div>
      </div>
    )
  }

  return (
    <div style={{ maxWidth: 1400, margin: '0 auto', padding: '0 4px', paddingBottom: 80 }}>
      {/* Hero */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 20 }}>
        <BarChart3 size={32} color="var(--accent-primary)" />
        <div style={{ flex: 1 }}>
          <h1 style={{ margin: 0, fontSize: '1.6rem', fontWeight: 800 }}>Мониторинг</h1>
          <p style={{ margin: 0, color: 'var(--text-muted)', fontSize: '0.85rem' }}>Платформа фаолияти, фойдаланувчилар, AI ишлатилиши</p>
        </div>
      </div>

      {/* Period tabs */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 18 }}>
        {(['daily', 'weekly', 'monthly'] as Period[]).map(p => (
          <button key={p} onClick={() => setPeriod(p)} style={{
            padding: '8px 18px', borderRadius: 10,
            background: period === p ? 'linear-gradient(135deg, #7C3AED, #6D28D9)' : 'white',
            color: period === p ? 'white' : 'var(--text-secondary)',
            border: period === p ? 'none' : '1.5px solid var(--border)',
            fontWeight: 700, fontSize: '0.85rem', cursor: 'pointer',
            display: 'flex', alignItems: 'center', gap: 6,
          }}>
            <Calendar size={14} /> {p === 'daily' ? 'Кунлик' : p === 'weekly' ? 'Ҳафталик' : 'Ойлик'}
          </button>
        ))}
      </div>

      {loading && (
        <div style={{ textAlign: 'center', padding: 40 }}>
          <Loader2 className="animate-spin" size={32} />
        </div>
      )}

      {data && (
        <>
          {/* Stat cards */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12, marginBottom: 18 }}>
            <StatCard icon={Users} label="Жами фойдаланувчи" value={data.users_total} color="#0EA5E9" sub={`${data.users_active} та фаол`} />
            <StatCard icon={Activity} label="Тахрирлар" value={data.edits_total} color="#16A34A" sub={`${period}`} />
            <StatCard icon={Sparkles} label="AI чақирувлар" value={data.ai_calls_total} color="#7C3AED" sub={`${period}`} />
            <StatCard icon={Database} label="Sayqallash жами" value={data.sayqallash_total} color="#D97706" sub={`+${data.sayqallash_new} янги`} />
            <StatCard icon={Pill} label="Дорилар DB" value={data.drugs_total} color="#DC2626" />
            <StatCard icon={BookOpen} label="Терминлар DB" value={data.terms_total} color="#059669" />
            <StatCard icon={TrendingUp} label="Лойиҳалар" value={data.projects_total} color="#DB2777" sub={`${data.alignments_total} жумла`} />
          </div>

          {/* Charts */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 18 }}>
            <BarChart data={data.daily_chart} color="#16A34A" label="Тахрирлар (30 кун)" />
            <BarChart data={data.ai_chart} color="#7C3AED" label="AI чақирувлар (30 кун)" />
          </div>

          {/* AI usage breakdown — donut chart */}
          {Object.keys(data.ai_usage || {}).length > 0 && (
            <div style={{ background: 'white', border: '1.5px solid var(--border)', borderRadius: 14, padding: 18, marginBottom: 18 }}>
              <h3 style={{ margin: '0 0 12px', fontSize: '0.95rem', fontWeight: 700 }}>🤖 AI ишлатилиши тури бўйича</h3>
              <DonutChart data={data.ai_usage as Record<string, number>} />
            </div>
          )}

          {/* Top users table */}
          <div style={{ background: 'white', border: '1.5px solid var(--border)', borderRadius: 14, padding: 18 }}>
            <h3 style={{ margin: '0 0 12px', fontSize: '0.95rem', fontWeight: 700 }}>🏆 Энг фаол фойдаланувчилар ({period})</h3>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '0.85rem' }}>
              <thead>
                <tr style={{ background: '#F8FAFC', borderBottom: '2px solid var(--border)', textAlign: 'left' }}>
                  <th style={{ padding: 10 }}>#</th>
                  <th style={{ padding: 10 }}>Фойдаланувчи</th>
                  <th style={{ padding: 10, textAlign: 'right' }}>Фаолият</th>
                  <th style={{ padding: 10 }}>Прогресс</th>
                </tr>
              </thead>
              <tbody>
                {data.top_users.length === 0 ? (
                  <tr><td colSpan={4} style={{ padding: 30, textAlign: 'center', color: '#9CA3AF' }}>Бу даврда фаолият йўқ</td></tr>
                ) : (
                  data.top_users.map((u: any, i: number) => {
                    const max = Math.max(...data.top_users.map((x: any) => x.count), 1)
                    const pct = (u.count / max) * 100
                    return (
                      <tr key={u.user_id} style={{ borderBottom: '1px solid #F1F5F9' }}>
                        <td style={{ padding: 10, fontWeight: 700, color: i < 3 ? '#D97706' : 'var(--text-muted)' }}>{i + 1}</td>
                        <td style={{ padding: 10, fontWeight: 600 }}>{u.user_name || u.user_id}</td>
                        <td style={{ padding: 10, textAlign: 'right', fontWeight: 700 }}>{u.count}</td>
                        <td style={{ padding: 10, width: 200 }}>
                          <div style={{ height: 8, background: '#F3F4F6', borderRadius: 4, overflow: 'hidden' }}>
                            <div style={{ height: '100%', width: `${pct}%`, background: 'linear-gradient(90deg, #7C3AED, #6D28D9)', borderRadius: 4 }} />
                          </div>
                        </td>
                      </tr>
                    )
                  })
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  )
}
