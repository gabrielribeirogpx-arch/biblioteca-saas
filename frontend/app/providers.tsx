'use client';

import { AuthProvider } from '../context/AuthContext';
import { LibraryProvider } from '../context/LibraryContext';

export function Providers({ children }: { children: React.ReactNode }) {
  return (
    <LibraryProvider>
      <AuthProvider>{children}</AuthProvider>
    </LibraryProvider>
  );
}
