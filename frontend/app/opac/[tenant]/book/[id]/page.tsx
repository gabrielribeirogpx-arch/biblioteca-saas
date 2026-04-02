import Link from 'next/link';
import type { Metadata } from 'next';

import { ReserveButton } from '../../../../../components/opac/ReserveButton';
import { getPublicBook } from '../../../../../lib/opac';

export async function generateMetadata({ params }: { params: { tenant: string; id: string } }): Promise<Metadata> {
  const bookId = Number(params.id);
  if (!Number.isInteger(bookId) || bookId <= 0) {
    return { title: 'Livro não encontrado | OPAC' };
  }

  const book = await getPublicBook(bookId, params.tenant);
  if (!book) {
    return { title: 'Livro não encontrado | OPAC' };
  }

  return {
    title: `${book.title} | OPAC`,
    description: `Disponibilidade de ${book.title} nas bibliotecas participantes.`
  };
}

export default async function OPACTenantBookPage({ params }: { params: { tenant: string; id: string } }) {
  const bookId = Number(params.id);
  const tenant = params.tenant;
  const book = Number.isInteger(bookId) && bookId > 0 ? await getPublicBook(bookId, tenant) : null;

  if (!book) {
    return (
      <main className="min-h-screen bg-slate-50 px-4 py-10">
        <div className="mx-auto max-w-3xl rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h1 className="text-xl font-bold text-slate-900">Livro não encontrado</h1>
          <Link href={`/opac/${tenant}`} className="mt-4 inline-flex rounded-md bg-slate-900 px-3 py-2 text-sm font-semibold text-white">Voltar ao catálogo</Link>
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-10">
      <div className="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[280px_1fr]">
        <section className="rounded-2xl bg-white p-5 shadow-sm ring-1 ring-slate-200">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={book.cover_url ?? 'https://placehold.co/240x360?text=Sem+Capa'}
            alt={`Capa de ${book.title}`}
            className="mx-auto h-72 w-48 rounded-lg object-cover ring-1 ring-slate-200"
          />
          <p className="mt-4 text-center text-xs text-slate-500">ISBN: {book.isbn ?? 'N/A'}</p>
        </section>

        <section className="space-y-4 rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <Link href={`/opac/${tenant}`} className="inline-flex rounded-md border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700">← Voltar</Link>
          <h1 className="text-2xl font-bold text-slate-900">{book.title}</h1>
          {book.subtitle ? <p className="text-slate-600">{book.subtitle}</p> : null}

          <dl className="grid gap-2 text-sm text-slate-700 sm:grid-cols-2">
            <div><dt className="font-semibold">Autor</dt><dd>{book.author}</dd></div>
            <div><dt className="font-semibold">Assunto</dt><dd>{book.subject ?? 'N/A'}</dd></div>
            <div><dt className="font-semibold">Edição</dt><dd>{book.edition ?? 'N/A'}</dd></div>
            <div><dt className="font-semibold">Ano</dt><dd>{book.publication_year ?? 'N/A'}</dd></div>
            <div><dt className="font-semibold">Biblioteca de origem</dt><dd>{book.library.name} ({book.library.code})</dd></div>
            <div><dt className="font-semibold">Exemplares</dt><dd>{book.available_copies}/{book.total_copies}</dd></div>
            <div><dt className="font-semibold">Status</dt><dd className={book.status === 'available' ? 'text-emerald-700 font-semibold' : 'text-rose-700 font-semibold'}>{book.status === 'available' ? 'Disponível' : 'Indisponível'}</dd></div>
          </dl>

          <div className="flex flex-wrap gap-2">
            <ReserveButton bookId={book.id} className="inline-flex rounded-md bg-slate-900 px-3 py-2 text-xs font-semibold text-white" />
          </div>

          <div>
            <h2 className="text-lg font-semibold text-slate-900">Assuntos</h2>
            <div className="mt-2 flex flex-wrap gap-2">
              {book.subjects.length > 0 ? book.subjects.map((item) => (
                <span key={item} className="rounded-full bg-slate-100 px-3 py-1 text-xs text-slate-700">{item}</span>
              )) : <span className="text-sm text-slate-500">Sem assuntos informados</span>}
            </div>
          </div>

          <div>
            <h2 className="text-lg font-semibold text-slate-900">Disponibilidade por biblioteca</h2>
            <ul className="mt-3 space-y-2">
              {book.libraries.map((holding) => (
                <li key={`${holding.library.tenant_slug}-${holding.library.id}`} className="rounded-lg border border-slate-200 p-3 text-sm">
                  <p className="font-semibold text-slate-800">{holding.library.name} ({holding.library.code})</p>
                  <p className="text-slate-600">Tenant: {holding.library.tenant_name} ({holding.library.tenant_slug})</p>
                  <p className={holding.status === 'available' ? 'font-semibold text-emerald-700' : 'font-semibold text-rose-700'}>
                    {holding.available_copies}/{holding.total_copies} disponível(is) - {holding.status === 'available' ? 'Disponível' : 'Indisponível'}
                  </p>
                </li>
              ))}
            </ul>
          </div>
        </section>
      </div>
    </main>
  );
}
