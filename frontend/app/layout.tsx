import './globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import LoginGuard from '../components/LoginGuard'
import DashboardLayout from '../components/DashboardLayout'
import ErrorBoundary from '../components/ErrorBoundary'
import LanguageProvider from '../components/LanguageProvider'
import VersionPoller from '../components/VersionPoller'

// Rebuild triggered: 2026-04-05
const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Pharma Expert AI',
  description: 'Trilingual Document Aligner for Pharmaceutical Standards',
}

export const viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 5,
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="uz">
      <body className={inter.className}>
        <ErrorBoundary>
          <LanguageProvider>
            <LoginGuard>
              <DashboardLayout>
                {children}
              </DashboardLayout>
            </LoginGuard>
          </LanguageProvider>
        </ErrorBoundary>
        <VersionPoller />
        <script src="https://accounts.google.com/gsi/client" async defer></script>
      </body>
    </html>
  )
}
