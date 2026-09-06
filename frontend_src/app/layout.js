

import { INTER_FONT, OUTFIT_FONT } from './fonts'
import './globals.css'
import '../lib/suppressErrors'

export const metadata = {
  title: 'Adaptive Exam AI - Intelligent Learning Platform',
  description: 'ML-powered adaptive learning platform with personalized quizzes and analytics',
}

export default function RootLayout({ children }) {
  return (
    <html lang="en" suppressHydrationWarning className={`${OUTFIT_FONT.variable} ${INTER_FONT.variable}`}>
      <head>
        {/* Theme script removed - Enforcing Dark Mode via CSS */}
      </head>
      <body suppressHydrationWarning={true} className={`${INTER_FONT.className} min-h-screen bg-background text-foreground antialiased selection:bg-primary/20`}>
        {children}
      </body>
    </html>
  )
}
