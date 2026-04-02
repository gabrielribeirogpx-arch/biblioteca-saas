'use client';

import { createContext, useContext, useEffect, useMemo, useState } from 'react';

import { getStoredLibraryId, setStoredLibraryId } from '../lib/api';

interface LibraryContextValue {
  libraryId: string | null;
  setLibraryId: (libraryId: string | null) => void;
}

const LibraryContext = createContext<LibraryContextValue | undefined>(undefined);

export function LibraryProvider({ children }: { children: React.ReactNode }) {
  const [libraryId, setLibraryIdState] = useState<string | null>(null);

  useEffect(() => {
    setLibraryIdState(getStoredLibraryId());
  }, []);

  const setLibraryId = (nextLibraryId: string | null) => {
    const normalized = nextLibraryId?.trim() ?? '';
    if (!normalized) {
      setLibraryIdState(null);
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem('library_id');
      }
      return;
    }

    setStoredLibraryId(normalized);
    setLibraryIdState(normalized);
  };

  const value = useMemo(() => ({ libraryId, setLibraryId }), [libraryId]);

  return <LibraryContext.Provider value={value}>{children}</LibraryContext.Provider>;
}

export function useLibrary() {
  const context = useContext(LibraryContext);
  if (!context) {
    throw new Error('useLibrary deve ser usado dentro de LibraryProvider');
  }
  return context;
}
