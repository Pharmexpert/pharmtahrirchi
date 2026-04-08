'use client'

import React, { useEffect, useState } from 'react'
import { CheckCircle2, CreditCard, Star, Zap, Crown, Loader2 } from 'lucide-react'
import { useAuth } from '../../components/LoginGuard'
import api from '../../services/api'

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

interface Plan {
  name: string
  price: number
  currency: string
  limits: Record<string, any>
}

const PLAN_ICONS: Record<string, any> = {
  free: Star,
  starter: Zap,
  pro: CheckCircle2,
  enterprise: Crown,
}

const PLAN_COLORS: Record<string, string> = {
  free: '#9CA3AF',
  starter: '#0EA5E9',
  pro: '#7C3AED',
  enterprise: '#D97706',
}

export default function BillingPage() {
  const { token } = useAuth()
  const [plans, setPlans] = useState<Record<string, Plan>>({})
  const [current, setCurrent] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null)
  const [stripeConfigured, setStripeConfigured] = useState(false)

  useEffect(() => {
    if (!token) return
    Promise.all([api.billing.plans(), api.billing.subscription()])
      .then(([plansRes, subRes]: any[]) => {
        setPlans(plansRes.plans || {})
        setStripeConfigured(plansRes.stripe_configured || false)
        setCurrent(subRes)
      }).catch(() => {})
      .finally(() => setLoading(false))
  }, [token])

  const handleUpgrade = async (planKey: string) => {
    setCheckoutLoading(planKey)
    try {
      const data: any = await api.billing.checkout(planKey)
      if (data.checkout_url) {
        window.location.href = data.checkout_url
      } else {
        alert('Stripe настройкаланмаган ёки хатолик: ' + (data.detail || ''))
      }
    } catch (e: any) {
      alert('Хатолик: ' + (e?.message || e))
    } finally {
      setCheckoutLoading(null)
    }
  }

  if (loading) return <div style={{ textAlign: 'center', padding: 60 }}><Loader2 className="animate-spin" /></div>

  return (
    <div style={{ maxWidth: 1200, margin: '0 auto', padding: '20px 4px' }}>
      <div style={{ textAlign: 'center', marginBottom: 40 }}>
        <CreditCard size={48} color="#7C3AED" style={{ marginBottom: 12 }} />
        <h1 style={{ margin: 0, fontSize: '2rem', fontWeight: 800 }}>Тарифлар</h1>
        <p style={{ color: '#6B7280', fontSize: '0.95rem' }}>Ҳозирги тариф: <strong style={{ color: '#7C3AED' }}>{current?.plan_name || current?.plan || 'Free'}</strong></p>
        {!stripeConfigured && (
          <div style={{ marginTop: 10, padding: '8px 14px', background: '#FEF3C7', border: '1px solid #FCD34D', borderRadius: 8, display: 'inline-block', fontSize: '0.82rem', color: '#92400E' }}>
            ⚠ Stripe ҳали фаолланмаган — тарифлар демо режимда кўрсатиляпти
          </div>
        )}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(260px, 1fr))', gap: 16 }}>
        {Object.entries(plans).map(([key, plan]) => {
          const Icon = PLAN_ICONS[key] || Star
          const color = PLAN_COLORS[key] || '#9CA3AF'
          const isCurrent = current?.plan === key
          const isPaid = plan.price > 0

          return (
            <div key={key} style={{
              background: 'white', border: isCurrent ? `2px solid ${color}` : '1.5px solid #E5E7EB',
              borderRadius: 14, padding: 22, position: 'relative',
              boxShadow: isCurrent ? `0 8px 24px ${color}22` : '0 2px 6px rgba(0,0,0,0.04)',
            }}>
              {isCurrent && (
                <div style={{ position: 'absolute', top: -10, right: 12, background: color, color: 'white', padding: '3px 10px', borderRadius: 6, fontSize: '0.65rem', fontWeight: 800, textTransform: 'uppercase' }}>
                  Жорий тариф
                </div>
              )}
              <div style={{ width: 46, height: 46, borderRadius: 12, background: `${color}22`, color, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 12 }}>
                <Icon size={24} />
              </div>
              <h3 style={{ margin: '0 0 4px', fontSize: '1.1rem', fontWeight: 800 }}>{plan.name}</h3>
              <div style={{ fontSize: '1.6rem', fontWeight: 800, color: color, marginBottom: 4 }}>
                ${plan.price}<span style={{ fontSize: '0.72rem', color: '#6B7280', fontWeight: 500 }}>/ой</span>
              </div>

              <div style={{ marginTop: 14, borderTop: '1px solid #F1F5F9', paddingTop: 14, fontSize: '0.82rem' }}>
                <div style={{ marginBottom: 6 }}>
                  <CheckCircle2 size={12} style={{ display: 'inline', color, marginRight: 6, verticalAlign: 'middle' }} />
                  {plan.limits?.ai_calls_per_day === -1 ? 'Чексиз AI сўровлар' : `${plan.limits?.ai_calls_per_day || 5} AI сўров/кун`}
                </div>
                <div style={{ marginBottom: 6 }}>
                  <CheckCircle2 size={12} style={{ display: 'inline', color: plan.limits?.local_gguf ? color : '#D1D5DB', marginRight: 6, verticalAlign: 'middle' }} />
                  {plan.limits?.local_gguf ? 'Локал GGUF модел' : 'Фақат cloud AI'}
                </div>
                <div style={{ marginBottom: 6 }}>
                  <CheckCircle2 size={12} style={{ display: 'inline', color: plan.limits?.who_inn ? color : '#D1D5DB', marginRight: 6, verticalAlign: 'middle' }} />
                  {plan.limits?.who_inn ? 'WHO INN маълумотлар' : 'Базавий дорилар'}
                </div>
                <div style={{ marginBottom: 6 }}>
                  <CheckCircle2 size={12} style={{ display: 'inline', color, marginRight: 6, verticalAlign: 'middle' }} />
                  Ёрдам: {plan.limits?.support || 'none'}
                </div>
                {plan.limits?.multi_tenant && (
                  <div>
                    <CheckCircle2 size={12} style={{ display: 'inline', color, marginRight: 6, verticalAlign: 'middle' }} />
                    Multi-tenancy
                  </div>
                )}
              </div>

              {isPaid && !isCurrent && (
                <button
                  onClick={() => handleUpgrade(key)}
                  disabled={checkoutLoading === key || !stripeConfigured}
                  style={{
                    marginTop: 16, width: '100%', padding: '10px',
                    background: stripeConfigured ? `linear-gradient(135deg, ${color}, ${color}dd)` : '#F3F4F6',
                    color: stripeConfigured ? 'white' : '#9CA3AF',
                    border: 'none', borderRadius: 8, fontWeight: 700,
                    fontSize: '0.88rem', cursor: stripeConfigured ? 'pointer' : 'not-allowed',
                    display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 6,
                  }}
                >
                  {checkoutLoading === key ? <Loader2 size={14} className="animate-spin" /> : <CreditCard size={14} />}
                  {stripeConfigured ? 'Тарифни олиш' : 'Ҳали мумкин эмас'}
                </button>
              )}
              {isCurrent && (
                <div style={{ marginTop: 16, textAlign: 'center', fontSize: '0.78rem', color: '#16A34A', fontWeight: 700 }}>
                  ✓ Сиз ҳозир бу тарифдасиз
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
