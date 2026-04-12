'use client'

import React, { useState } from 'react'
import { 
  Database, Menu, X, LayoutDashboard, FileText, Settings, 
  LogOut, User, Globe, ChevronLeft, ChevronRight, Search, 
  PlusCircle, History, Bell, ShieldCheck, Mail, Info, MessageSquare, BookOpen, FolderOpen, Repeat2, UserCog, Library, Layers, Languages
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
  const [isMobileOpen, setIsMobileOpen] = useState(false)
  const pathname = usePathname()

  // Close mobile sidebar on route change
  React.useEffect(() => {
    setIsMobileOpen(false)
  }, [pathname])

  const navItems = [
    { name: t('nav.dashboard'), icon: LayoutDashboard, path: '/dashboard' },
    { name: 'Фармацевт ёрдамчиси', icon: ShieldCheck, path: '/assistant' },
    { name: 'AI Ассистент', icon: Languages, path: '/assistant2' },
    { name: t('nav.tilshunos'), icon: Globe, path: '/tilshunos' },
    { name: t('nav.paragraphs'), icon: FileText, path: '/paragraphs' },
    { name: t('nav.projects'), icon: History, path: '/projects' },
    { name: t('nav.files'), icon: FolderOpen, path: '/files' },
    { name: t('nav.rules'), icon: Database, path: '/rules' },
    { name: t('nav.annotated'), icon: BookOpen, path: '/linguistic/annotated' },
    { name: t('nav.disputed'), icon: MessageSquare, path: '/linguistic/disputed' },
    { name: t('nav.abbreviations'), icon: Info, path: '/linguistic/abbreviations' },
    { name: t('nav.synonyms'), icon: Repeat2, path: '/synonyms' },
    { name: t('nav.dictionary'), icon: Library, path: '/dictionary' },
    { name: t('nav.affixFlags'), icon: Layers, path: '/affix-flags' },
    { name: t('nav.morphology'), icon: Layers, path: '/morphology' },
    { name: t('nav.syntax'), icon: Layers, path: '/syntax' },
    { name: 'Workbench', icon: Layers, path: '/workbench' },
    { name: 'QA Lab', icon: ShieldCheck, path: '/qa' },
  ]

  if (isAdmin) {
    navItems.push({ name: t('nav.admin'), icon: ShieldCheck, path: '/admin' })
    navItems.push({ name: 'Мониторинг', icon: BookOpen, path: '/admin/monitoring' })
    navItems.push({ name: 'Pharma DB', icon: Database, path: '/admin/pharma' })
    navItems.push({ name: 'Style Guide', icon: FileText, path: '/admin/style-guide' })
    navItems.push({ name: 'Она тилини бойитиш', icon: Database, path: '/admin/language-resources' })
  }

  // Filter by visible_pages (from admin settings). null = show all.
  let visiblePages: string[] | null = null
  try {
    const vp = user?.visible_pages
    if (typeof vp === 'string') visiblePages = JSON.parse(vp)
    else if (Array.isArray(vp)) visiblePages = vp
  } catch {}

  const filteredNavItems = visiblePages
    ? navItems.filter(item => visiblePages!.includes(item.path) || item.path.startsWith('/admin'))
    : navItems

  const displayNavItems = filteredNavItems

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: 'var(--bg-primary)' }}>
      <style jsx global>{`
        .dl-hamburger { display: none; background: transparent; border: none; cursor: pointer; color: var(--text-secondary); padding: 8px; margin-right: 8px; }
        .dl-backdrop { display: none; }
        .dl-header-pad { padding: 0 32px; }
        .dl-search { width: 240px; }
        .dl-main { margin-left: var(--sidebar-width); }
        .dl-sidebar-toggle { display: flex; }
        @media (max-width: 768px) {
          .dl-hamburger { display: inline-flex; align-items: center; justify-content: center; min-height: 40px; min-width: 40px; }
          .dl-sidebar { transform: translateX(-100%); width: 280px !important; transition: transform 0.3s ease !important; }
          .dl-sidebar.open { transform: translateX(0); }
          .dl-backdrop.open { display: block; position: fixed; inset: 0; background: rgba(0,0,0,0.4); z-index: 150; }
          .dl-sidebar { z-index: 200 !important; }
          .dl-main { margin-left: 0 !important; }
          .dl-header-pad { padding: 0 16px !important; }
          .dl-header-right { gap: 8px !important; }
          .dl-search { display: none !important; }
          .dl-search-mobile-btn { display: inline-flex !important; }
          .dl-page-pad { padding: 16px !important; }
          .dl-footer-pad { padding: 16px !important; }
          .dl-sidebar-toggle { display: none !important; }
          .dl-avatar { display: none !important; }
        }
        .dl-search-mobile-btn { display: none; background: transparent; border: none; cursor: pointer; color: var(--text-secondary); min-height: 40px; min-width: 40px; align-items: center; justify-content: center; }
      `}</style>

      {/* Mobile backdrop */}
      <div
        className={`dl-backdrop${isMobileOpen ? ' open' : ''}`}
        onClick={() => setIsMobileOpen(false)}
      />

      {/* Sidebar */}
      <aside
        className={`dl-sidebar${isMobileOpen ? ' open' : ''}`}
        style={{
        width: isSidebarOpen ? 'var(--sidebar-width)' : '80px',
        background: 'var(--bg-card)',
        borderRight: '1px solid var(--border)',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.3s cubic-bezier(0.4, 0, 0.2, 1)',
        position: 'fixed',
        top: 0,
        left: 0,
        height: '100vh',
        zIndex: 100,
        boxShadow: 'var(--shadow-sm)',
        overflow: 'hidden',
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
          {displayNavItems.map((item) => {
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
          className="dl-sidebar-toggle"
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
      <main
        className="dl-main"
        style={{
        flex: 1,
        marginLeft: isSidebarOpen ? 'var(--sidebar-width)' : '80px',
        transition: 'margin-left 0.3s ease',
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column'
      }}>
        {/* Header */}
        <header
          className="dl-header-pad"
          style={{
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
          <div style={{ display: 'flex', alignItems: 'center', minWidth: 0, flex: 1 }}>
            <button
              className="dl-hamburger"
              aria-label="Toggle menu"
              onClick={() => setIsMobileOpen(v => !v)}
            >
              {isMobileOpen ? <X size={22} /> : <Menu size={22} />}
            </button>
            <h2 style={{ fontSize: '1.25rem', fontWeight: 700, color: 'var(--text-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
              {displayNavItems.find(i => pathname.startsWith(i.path))?.name || 'Dashboard'}
            </h2>
          </div>

          <div className="dl-header-right" style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
            <button className="dl-search-mobile-btn" aria-label="Search">
              <Search size={20} />
            </button>
            <div className="dl-search" style={{ position: 'relative' }}>
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
            <div className="dl-avatar" style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--bg-glass-hover)', border: '1px solid var(--border)' }}></div>
          </div>
        </header>

        {/* Page Content */}
        <div className="dl-page-pad" style={{ padding: '32px', flex: 1 }}>
          {children}
        </div>

        {/* Informational Footer */}
        <footer className="dl-footer-pad" style={{
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
