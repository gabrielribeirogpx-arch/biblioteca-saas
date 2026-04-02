'use client';

import { usePathname } from 'next/navigation';

import { UserMenu } from '../components/UserMenu';
import { Providers } from './providers';

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isOpacRoute = pathname === '/opac' || pathname.startsWith('/opac/');

  if (isOpacRoute) {
    return <>{children}</>;
  }

  return (
    <Providers>
      <div className="absolute top-4 right-6">
        <UserMenu />
      </div>
      {children}
    </Providers>
  );
}
