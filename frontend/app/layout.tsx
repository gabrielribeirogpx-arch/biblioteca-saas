import type { Metadata } from 'next';

import './globals.css';
import { AppShell } from './AppShell';

export const metadata: Metadata = {
  title: 'Biblioteca SaaS',
  description: 'Enterprise-grade library operations platform'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="relative">
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
