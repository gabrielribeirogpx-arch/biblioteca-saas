import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'OPAC | Biblioteca SaaS',
  description: 'Catálogo público online isolado do contexto autenticado.'
};

export default function OpacLayout({ children }: { children: React.ReactNode }) {
  return <>{children}</>;
}
