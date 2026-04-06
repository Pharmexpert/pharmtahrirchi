'use client'

import React, { useState } from 'react'
import { 
  Database, Menu, X, LayoutDashboard, FileText, Settings, 
  LogOut, User, Globe, ChevronLeft, ChevronRight, Search, 
  PlusCircle, History, Bell, ShieldCheck, Mail, Info, MessageSquare, BookOpen, FolderOpen, Repeat2, UserCog, Library, Layers
} from 'lucide-react'
import { useAuth } from './LoginGuard'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import LanguageSwitcher from './LanguageSwitcher'
import { useLang } from './LanguageProvider'

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const { user, logout, isAdmin } = useAuth()
  const { t } = useLang()
  const [isSidebarOpen, setIsSidebarOpen] = useState(true)
  const pathname = usePathname()

  const navItems = [
    { name: t('nav.dashboard'), icon: LayoutDashboard, path: '/dashboard' },
    { name: t('nav.paragraphs'), icon: FileText, path: '/paragraphs' },
    { name: t('nav.projects'), icon: History, path: '/projects' },
    { name: t('nav.files'), icon: FolderOpen, path: '/files' },
    { name: t('nav.rules'), icon: Database, path: '/rules' },
    { name: t('nav.annotated'), icon: BookOpen, path: '/linguistic/annotated' },
    { name: t('nav.disputed'), icon: MessageSquare, path: '/linguistic/disputed' },
    { name: t('nav.abbreviations'), icon: Info, path: '/linguistic/abbreviations' },
    { name: t('nav.synonyms'), icon: Repeat2, path: '/synonyms' },
    { name: 'Луғат', icon: Library, path: '/dictionary' },
    { name: 'Affix Flags', icon: Layers, path: '/affix-flags' },
  ]

  if (isAdmin) {
    navItems.push({ name: t('nav.admin'), icon: ShieldCheck, path: '/admin' })
  }

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      {/* Sidebar */}
      <aside style={{ 
        width: isSidebarOpen ? 'var(--sidebar-width)' : '80px',
        background: 'var(--bg-card)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        position: 'fixed',
        height: '100vh',
        zIndex: 100,
        boxShadow: 'var(--shadow-sm)'
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
            background: 'linear-gradient(135deg, #B48C64, #D4956B, #E8B78E)', 
            borderRadius: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            boxShadow: '0 4px 16px rgba(180, 140, 100, 0.25)',
            flexShrink: 0
          }}>
            <Database size={22} color="white" />
          </div>
          {isSidebarOpen && (
            <div style={{ display: 'flex', flexDirection: 'column' }}>
              <span style={{ 
                fontWeight: 800, 
                fontSize: '1.2rem', 
                background: 'linear-gradient(135deg, #B48C64, #D4956B)', 
                WebkitBackgroundClip: 'text', 
                WebkitTextFillColor: 'transparent',
                lineHeight: 1
              }}>
                Pharma Expert
              </span>
              <span style={{ fontSize: '0.6rem', fontWeight: 700, color: '#8B5E3C', marginTop: '2px' }}>V.4 SYSTEM</span>
            </div>
          )}
        </div>

        {/* Navigation */}
        <nav style={{ padding: '24px 12px', flex: 1, overflowY: 'auto' }}>
          {navItems.map((item) => {
            const isActive = pathname === item.path
            return (
              <Link key={item.path} href={item.path} style={{ textDecoration: 'none' }}>
                <div style={{ 
                  display: 'flex', 
                  alignItems: 'center', 
                  gap: '12px', 
                  padding: '12px 14px',
                  borderRadius: 'var(--radius-md)',
                  marginBottom: '6px',
                  color: isActive ? 'var(--accent-primary)' : 'var(--text-secondary)',
                  background: isActive ? 'var(--bg-glass-hover)' : 'transparent',
                  transition: 'all 0.2s',
                  cursor: 'pointer',
                  fontWeight: isActive ? 600 : 500,
                  fontSize: '0.95rem'
                }} className="nav-item">
                  <item.icon size={20} />
                  {isSidebarOpen && <span>{item.name}</span>}
                </div>
              </Link>
            )
          })}
        </nav>

        {/* User Profile / Logout */}
        <div style={{ padding: '20px 12px', borderTop: '1px solid var(--border)' }}>
          {isSidebarOpen && (
            <Link href="/profile" style={{ textDecoration: 'none', color: 'inherit' }}>
              <div style={{ 
                padding: '12px', 
                background: 'var(--bg-secondary)', 
                borderRadius: 'var(--radius-md)',
                marginBottom: '12px',
                display: 'flex',
                alignItems: 'center',
                gap: '10px',
                cursor: 'pointer',
                transition: 'background 0.2s'
              }} className="nav-item">
                <div style={{ 
                  width: '36px', height: '36px', borderRadius: '50%', 
                  background: 'var(--accent-gradient)', 
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  color: 'white', fontWeight: 600
                }}>
                  {user?.name?.charAt(0) || 'U'}
                </div>
                <div style={{ overflow: 'hidden' }}>
                  <div style={{ fontWeight: 600, fontSize: '0.85rem', whiteSpace: 'nowrap', textOverflow: 'ellipsis' }}>{user?.name}</div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{user?.role} • Профиль →</div>
                </div>
              </div>
            </Link>
          )}
          <button 
            onClick={logout}
            style={{ 
              width: '100%', 
              display: 'flex', 
              alignItems: 'center', 
              gap: '12px', 
              padding: '12px 14px',
              background: 'transparent',
              border: 'none',
              borderRadius: 'var(--radius-md)',
              color: 'var(--danger)',
              cursor: 'pointer',
              fontWeight: 600,
              fontSize: '0.9rem',
              transition: 'background 0.2s'
            }}
            className="logout-btn"
          >
            <LogOut size={20} />
            {isSidebarOpen && <span>{t('common.logout')}</span>}
          </button>
        </div>

        {/* Toggle Button */}
        <button 
          onClick={() => setIsSidebarOpen(!isSidebarOpen)}
          style={{ 
            position: 'absolute',
            bottom: '80px',
            right: '-16px',
            width: '32px',
            height: '32px',
            borderRadius: '50%',
            background: 'white',
            border: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            boxShadow: 'var(--shadow-sm)',
            zIndex: 101,
            color: 'var(--accent-primary)'
          }}
        >
          {isSidebarOpen ? <ChevronLeft size={18} /> : <ChevronRight size={18} />}
        </button>
      </aside>

      {/* Main Content Area */}
      <main style={{ 
        flex: 1, 
        marginLeft: isSidebarOpen ? 'var(--sidebar-width)' : '80px',
        transition: 'margin-left 0.3s ease',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header */}
        <header style={{ 
          height: 'var(--header-height)', 
          background: 'var(--bg-glass)', 
          backdropFilter: 'blur(12px)',
          borderBottom: '1px solid var(--border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 32px',
          position: 'sticky',
          top: 0,
          zIndex: 90
        }}>
          <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)' }}>
            {navItems.find(i => pathname.startsWith(i.path))?.name || 'Dashboard'}
          </h2>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <div style={{ position: 'relative' }}>
              <Search style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)', color: 'var(--text-muted)' }} size={18} />
              <input 
                type="text" 
                placeholder="Search..." 
                style={{ 
                  padding: '10px 16px 10px 40px', 
                  borderRadius: '20px', 
                  border: '1px solid var(--border)',
                  background: 'var(--bg-secondary)',
                  fontSize: '0.9rem',
                  outline: 'none',
                  width: '240px',
                  transition: 'all 0.2s'
                }}
                onFocus={(e) => e.target.style.borderColor = 'var(--accent-primary)'}
                onBlur={(e) => e.target.style.borderColor = 'var(--border)'}
              />
            </div>
            <button style={{ 
              background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer',
              position: 'relative'
            }}>
              <Bell size={22} />
              <div style={{ position: 'absolute', top: '0', right: '0', width: '8px', height: '8px', background: 'var(--danger)', borderRadius: '50%', border: '2px solid white' }}></div>
            </button>
            <LanguageSwitcher />
            <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--bg-glass-hover)', border: '1px solid var(--border)' }}></div>
          </div>
        </header>

        {/* Page Content */}
        <div style={{ padding: '32px', flex: 1 }}>
          {children}
        </div>

        {/* Informational Footer */}
        <footer style={{ 
          padding: '24px 32px', 
          borderTop: '1px solid var(--border)',
          background: 'rgba(255, 251, 245, 0.5)',
          textAlign: 'center'
        }}>
           <p style={{ fontSize: '0.75rem', fontWeight: 700, color: '#8B5E3C', letterSpacing: '1px', textTransform: 'uppercase', marginBottom: '8px' }}>
            {t('footer.copyright')}
          </p>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', lineHeight: '1.6' }}>
             <p style={{ fontWeight: 600 }}>{t('footer.description')}</p>
             <p>Саволлар ва таклифлар билан Акмалходжа Зайнидинов номига, қуйидаги почта манзилига мурожаат қилишингиз мумкин: <a href="mailto:texnopharm@gmail.com" style={{ color: 'var(--accent-primary)', fontWeight: 700 }}>texnopharm@gmail.com</a></p>
          </div>
        </footer>
      </main>
    </div>
  )
}
