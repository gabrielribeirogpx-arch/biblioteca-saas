import Link from 'next/link';
import type { Metadata } from 'next';

import { getPublicBooks } from '../../lib/opac';

type SearchParams = Record<string, string | string[] | undefined>;

export const metadata: Metadata = {
  title: 'OPAC | Biblioteca SaaS',
  description: 'Catálogo público online para pesquisa de acervo, disponibilidade e bibliotecas participantes.'
};

function asValue(value: string | string[] | undefined): string {
  if (Array.isArray(value)) {
    return value[0] ?? '';
  }
  return value ?? '';
}

export default async function OPACPage({ searchParams }: { searchParams: SearchParams }) {
  const page = Math.max(1, Number(asValue(searchParams.page) || 1));
  const pageSize = 12;

  const search = asValue(searchParams.search);
  const library = asValue(searchParams.library);
  const tenant = asValue(searchParams.tenant);
  const isbn = asValue(searchParams.isbn);
  const subject = asValue(searchParams.subject);

  const query = new URLSearchParams({
    page: String(page),
    page_size: String(pageSize),
    ...(search ? { search } : {}),
    ...(library ? { library } : {}),
    ...(tenant ? { tenant } : {}),
    ...(isbn ? { isbn } : {}),
    ...(subject ? { subject } : {})
  });

  const data = await getPublicBooks(query.toString());
  const totalPages = Math.max(1, Math.ceil(data.total / data.page_size));

  const buildPageHref = (nextPage: number) => {
    const params = new URLSearchParams(query);
    params.set('page', String(nextPage));
    return `/opac?${params.toString()}`;
  };

  return (
    <main className="min-h-screen bg-slate-50 px-4 py-8 sm:px-6 lg:px-10">
      <div className="mx-auto flex w-full max-w-7xl flex-col gap-6">
        <header className="rounded-2xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
          <h1 className="text-2xl font-bold text-slate-900">OPAC - Catálogo Público</h1>
          <p className="mt-2 text-sm text-slate-600">Pesquisa por título, autor, assunto, ISBN, tenant e biblioteca sem autenticação.</p>
        </header>

        <section className="grid gap-6 lg:grid-cols-[280px_1fr]">
          <aside className="rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
            <form className="space-y-4" method="GET" action="/opac">
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase text-slate-500">Busca</label>
                <input name="search" defaultValue={search} placeholder="Título ou autor" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase text-slate-500">Biblioteca</label>
                <input name="library" defaultValue={library} placeholder="Nome, código ou ID" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase text-slate-500">Tenant</label>
                <input name="tenant" defaultValue={tenant} placeholder="Slug, nome ou ID" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase text-slate-500">ISBN</label>
                <input name="isbn" defaultValue={isbn} placeholder="978..." className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <div>
                <label className="mb-1 block text-xs font-semibold uppercase text-slate-500">Assunto</label>
                <input name="subject" defaultValue={subject} placeholder="Ex.: catalogação" className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm" />
              </div>
              <button type="submit" className="w-full rounded-lg bg-slate-900 px-3 py-2 text-sm font-semibold text-white">Aplicar filtros</button>
            </form>
          </aside>

          <div className="space-y-4">
            <div className="rounded-2xl bg-white px-4 py-3 text-sm text-slate-600 shadow-sm ring-1 ring-slate-200">
              {data.total} resultado(s) encontrado(s)
            </div>

            <ul className="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
              {data.items.map((book) => (
                <li key={book.id} className="flex h-full flex-col rounded-2xl bg-white p-4 shadow-sm ring-1 ring-slate-200">
                  <div className="mb-3 flex items-start gap-3">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img
                      src={book.cover_url ?? 'https://placehold.co/120x180?text=Sem+Capa'}
                      alt={`Capa de ${book.title}`}
                      className="h-28 w-20 rounded-md object-cover ring-1 ring-slate-200"
                    />
                    <div>
                      <h2 className="line-clamp-2 text-base font-semibold text-slate-900">{book.title}</h2>
                      <p className="mt-1 text-sm text-slate-600">{book.author}</p>
                      <p className="mt-1 text-xs text-slate-500">ISBN: {book.isbn ?? 'N/A'}</p>
                    </div>
                  </div>

                  <div className="mt-auto space-y-2 text-xs text-slate-600">
                    <p>
                      <span className="font-semibold">Biblioteca:</span> {book.library.name} ({book.library.code})
                    </p>
                    <p>
                      <span className="font-semibold">Disponibilidade:</span> {book.available_copies}/{book.total_copies}
                    </p>
                    <p className={book.available ? 'font-semibold text-emerald-700' : 'font-semibold text-rose-700'}>
                      {book.available ? 'Disponível' : 'Indisponível'}
                    </p>
                    <Link href={`/opac/book/${book.id}`} className="inline-flex rounded-md bg-slate-900 px-3 py-2 text-xs font-semibold text-white">
                      Ver detalhes
                    </Link>
                  </div>
                </li>
              ))}
            </ul>

            <nav className="flex items-center justify-between rounded-2xl bg-white px-4 py-3 shadow-sm ring-1 ring-slate-200">
              <Link href={buildPageHref(Math.max(1, page - 1))} className="rounded-md border border-slate-300 px-3 py-1 text-sm text-slate-700">
                Anterior
              </Link>
              <span className="text-sm text-slate-600">Página {page} de {totalPages}</span>
              <Link href={buildPageHref(Math.min(totalPages, page + 1))} className="rounded-md border border-slate-300 px-3 py-1 text-sm text-slate-700">
                Próxima
              </Link>
            </nav>
          </div>
        </section>
      </div>
    </main>
  );
}
