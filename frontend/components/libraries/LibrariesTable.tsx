import type { LibraryOption } from '../../lib/api';

interface LibrariesTableProps {
  libraries: LibraryOption[];
  loading: boolean;
  onSelectLibrary: (libraryId: number) => void;
  selectedLibraryId?: string | null;
}

function statusClass(isActive: boolean): string {
  return isActive ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-100 text-slate-600';
}

export function LibrariesTable({ libraries, loading, onSelectLibrary, selectedLibraryId }: LibrariesTableProps) {
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
            <th className="px-4 py-3 text-left font-semibold text-slate-700">Código</th>
            <th className="px-4 py-3 text-left font-semibold text-slate-700">Status</th>
            <th className="px-4 py-3 text-right font-semibold text-slate-700">Ações</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100 bg-white">
          {libraries.map((library) => {
            const isSelected = selectedLibraryId === String(library.id);

            return (
              <tr key={library.id}>
                <td className="px-4 py-3 font-medium text-slate-900">{library.name}</td>
                <td className="px-4 py-3 text-slate-600">{library.code}</td>
                <td className="px-4 py-3">
                  <span className={`rounded px-2 py-1 text-xs ${statusClass(library.is_active)}`}>
                    {library.is_active ? 'Ativo' : 'Inativo'}
                  </span>
                </td>
                <td className="px-4 py-3 text-right">
                  <button
                    type="button"
                    onClick={() => onSelectLibrary(library.id)}
                    className="rounded-md border border-slate-300 px-3 py-1 text-xs font-semibold text-slate-700 hover:bg-slate-50"
                  >
                    {isSelected ? 'Selecionada' : 'Selecionar'}
                  </button>
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
