import './globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import LoginGuard from '../components/LoginGuard'
import DashboardLayout from '../components/DashboardLayout'
import ErrorBoundary from '../components/ErrorBoundary'

// Rebuild triggered: 2026-04-05
const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Pharma Expert AI',
  description: 'Trilingual Document Aligner for Pharmaceutical Standards',
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
          <LoginGuard>
            <DashboardLayout>
              {children}
            </DashboardLayout>
          </LoginGuard>
        </ErrorBoundary>
        <script src="https://accounts.google.com/gsi/client" async defer></script>
      </body>
    </html>
  )
}
