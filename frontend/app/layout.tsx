import './globals.css'
import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import LoginGuard from '../components/LoginGuard'
import DashboardLayout from '../components/DashboardLayout'

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
    <html lang="en">
      <body className={inter.className}>
        <LoginGuard>
          <DashboardLayout>
            {children}
          </DashboardLayout>
        </LoginGuard>
        <script src="https://accounts.google.com/gsi/client" async defer></script>
      </body>
    </html>
  )
}

