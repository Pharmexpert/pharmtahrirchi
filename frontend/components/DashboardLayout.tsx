'use client'

import React, { useState } from 'react'
import { 
  LayoutDashboard, 
  PlusCircle, 
  Database, 
  Settings, 
  LogOut, 
  Menu, 
  X, 
  User,
  History,
  ShieldCheck,
  Bell
} from 'lucide-react'
import Link from 'next/link'
import { useAuth } from './LoginGuard'
import { usePathname } from 'next/navigation'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, isAdmin, logout } = useAuth()
  const [isSidebarOpen, setSidebarOpen] = useState(true)
  const pathname = usePathname()

  if (!user) return <>{children}</> // Don't show layout on login screen

  const navItems = [
    { name: 'Dashboard', icon: LayoutDashboard, href: '/' },
    { name: 'History', icon: History, href: '/history' },
    { name: 'Rules DB', icon: Database, href: '/rules', adminOnly: true },
    { name: 'Admin Panel', icon: ShieldCheck, href: '/admin', adminOnly: true },
  ]

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      {/* Sidebar */}
      <aside style={{ 
        width: isSidebarOpen ? 'var(--sidebar-width)' : '80px',
        background: 'var(--bg-secondary)',
        borderRight: '1px solid var(--border)',
        transition: 'all 0.3s ease',
        display: 'flex',
        flexDirection: 'column',
        zIndex: 100,
        position: 'fixed',
        height: '100vh',
        overflow: 'hidden'
      }}>
        {/* Logo Area */}
        <div style={{ 
          height: 'var(--header-height)', 
          padding: '0 24px', 
          display: 'flex', 
          alignItems: 'center', 
          gap: '12px',
          borderBottom: '1px solid var(--border)' 
        }}>
          <div style={{ 
            width: '40px', 
            height: '40px', 
            background: 'var(--accent-gradient)', 
            borderRadius: '10px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: 'var(--shadow-glow)',
            flexShrink: 0
          }}>
            <Database size={22} color="white" />
          </div>
          {isSidebarOpen && (
            <span style={{ 
              fontWeight: 800, 
              fontSize: '1.2rem', 
              background: 'var(--accent-gradient)', 
              WebkitBackgroundClip: 'text', 
              WebkitTextFillColor: 'transparent',
              letterSpacing: '-0.5px'
            }}>
              PharmaExpert
            </span>
          )}
        </div>

        {/* Navigation */}
        <nav style={{ flex: 1, padding: '24px 12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {navItems.map((item) => {
            if (item.adminOnly && !isAdmin) return null
            const isActive = pathname === item.href
            return (
              <Link key={item.name} href={item.href} style={{
                display: 'flex',
                alignItems: 'center',
                gap: '12px',
                padding: '12px 16px',
                borderRadius: 'var(--radius-md)',
                color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                background: isActive ? 'rgba(192, 120, 64, 0.1)' : 'transparent',
                transition: 'all 0.2s',
                textDecoration: 'none',
                fontWeight: isActive ? 600 : 500,
                fontSize: '0.92rem'
              }}>
                <item.icon size={20} />
                {isSidebarOpen && <span>{item.name}</span>}
              </Link>
            )
          })}
        </nav>

        {/* User Footer */}
        <div style={{ padding: '20px', borderTop: '1px solid var(--border)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
            <div style={{ 
              width: '38px', 
              height: '38px', 
              borderRadius: '50%', 
              background: 'var(--accent-gradient)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'white',
              fontWeight: 700,
              fontSize: '1rem',
              boxShadow: 'var(--shadow-glow)'
            }}>
              {user.name?.[0].toUpperCase() || 'U'}
            </div>
            {isSidebarOpen && (
              <div style={{ minWidth: 0 }}>
                <div style={{ fontSize: '0.9rem', fontWeight: 600, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                  {user.name}
                </div>
                <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', textTransform: 'capitalize' }}>
                  {user.role}
                </div>
              </div>
            )}
          </div>
          <button 
            onClick={logout}
            style={{ 
              width: '100%', 
              padding: '10px', 
              background: 'var(--bg-glass)', 
              border: '1px solid var(--border)', 
              borderRadius: 'var(--radius-sm)', 
              color: 'var(--text-secondary)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              cursor: 'pointer',
              fontSize: '0.85rem'
            }}
          >
            <LogOut size={16} />
            {isSidebarOpen && <span>Chiqish</span>}
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main style={{ 
        flex: 1, 
        marginLeft: isSidebarOpen ? 'var(--sidebar-width)' : '80px',
        transition: 'margin-left 0.3s ease',
        minHeight: '100vh'
      }}>
        {/* Header */}
        <header style={{ 
          height: 'var(--header-height)', 
          background: 'rgba(255, 248, 240, 0.85)', 
          backdropFilter: 'blur(20px)',
          WebkitBackdropFilter: 'blur(20px)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 32px',
          position: 'sticky',
          top: 0,
          zIndex: 50
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <button 
              onClick={() => setSidebarOpen(!isSidebarOpen)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-secondary)' }}
            >
              {isSidebarOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700 }}>
              {navItems.find(i => pathname === i.href)?.name || 'Editor'}
            </h2>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{ position: 'relative' }}>
              <Bell size={20} color="var(--text-muted)" style={{ cursor: 'pointer' }} />
              <span style={{ position: 'absolute', top: '-4px', right: '-4px', width: '8px', height: '8px', background: 'var(--danger)', borderRadius: '50%' }}></span>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', fontWeight: 500 }}>
              {new Date().toLocaleDateString('uz-UZ', { day: 'numeric', month: 'long', year: 'numeric' })}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <div style={{ padding: '32px' }}>
          {children}
        </div>
      </main>
    </div>
  )
}
