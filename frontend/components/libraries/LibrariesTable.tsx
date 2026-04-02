import type { LibraryOption } from '../../lib/api';

interface LibrariesTableProps {
  libraries: LibraryOption[];
  loading: boolean;
}

function statusClass(isActive: boolean): string {
  return isActive ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600';
}

function formatDate(dateValue: string): string {
  const parsed = new Date(dateValue);
  if (Number.isNaN(parsed.getTime())) {
    return '-';
  }

  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  }).format(parsed);
}

export function LibrariesTable({ libraries, loading }: LibrariesTableProps) {
  if (loading) {
    return <p className="text-sm text-slate-500">Carregando bibliotecas...</p>;
  }

  if (libraries.length === 0) {
    return (
      <div className="rounded-lg border border-dashed px-4 py-10 text-center text-sm text-slate-500">
        Nenhuma biblioteca cadastrada.
      </div>
    );
  }

  return (
    <div className="overflow-x-auto rounded-lg border">
      <table className="min-w-full divide-y divide-slate-200 text-sm">
        <thead className="bg-slate-50">
          <tr>
            <th className="px-4 py-3 text-left font-semibold text-slate-700">Nome</th>
            <th className="px-4 py-3 text-left font-semibold text-slate-700">Status</th>
            <th className="px-4 py-3 text-left font-semibold text-slate-700">Data de criação</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {libraries.map((library) => (
            <tr key={library.id}>
              <td className="px-4 py-3 font-medium text-slate-900">{library.name}</td>
              <td className="px-4 py-3">
                <span className={`rounded px-2 py-1 text-xs ${statusClass(library.is_active)}`}>
                  {library.is_active ? 'Ativo' : 'Inativo'}
                </span>
              </td>
              <td className="px-4 py-3 text-slate-600">{formatDate(library.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
