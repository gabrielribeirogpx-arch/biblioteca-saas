import type { Metadata } from 'next';
import { UserMenu } from '../components/UserMenu';
import './globals.css';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'Biblioteca SaaS',
  description: 'Enterprise-grade library operations platform'
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="relative">
        <Providers>
          <div className="absolute top-4 right-6">
            <UserMenu />
          </div>
          {children}
        </Providers>
      </body>
    </html>
  );
}
