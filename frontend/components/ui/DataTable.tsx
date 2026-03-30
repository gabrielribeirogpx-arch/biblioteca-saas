'use client';

import { useMemo, useState } from 'react';

interface DataTableProps<T> {
  title: string;
  description?: string;
  columns: Array<{ key: keyof T; label: string }>;
  rows: T[];
  searchableFields?: Array<keyof T>;
}

export function DataTable<T extends Record<string, string | number | null | undefined>>({
  title,
  description,
  columns,
  rows,
  searchableFields = []
}: DataTableProps<T>) {
  const [query, setQuery] = useState('');

  const filteredRows = useMemo(() => {
    if (!query.trim()) {
      return rows;
    }

    const lowered = query.toLowerCase();
    return rows.filter((row) =>
      searchableFields.some((field) => String(row[field] ?? '').toLowerCase().includes(lowered))
    );
  }, [query, rows, searchableFields]);

  return (
    <article className="rounded-xl border bg-white p-4 shadow-sm md:p-6">
      <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-end md:justify-between">
        <div>
          <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
          {description ? <p className="text-sm text-slate-500">{description}</p> : null}
        </div>
        <input
          className="w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none ring-brand-200 transition focus:ring md:w-72"
          onChange={(event) => setQuery(event.target.value)}
          placeholder="Search records"
          value={query}
        />
      </div>

      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-slate-200 text-sm">
          <thead>
            <tr>
              {columns.map((column) => (
                <th className="px-3 py-2 text-left font-semibold text-slate-700" key={String(column.key)}>
                  {column.label}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {filteredRows.map((row, index) => (
              <tr className="hover:bg-slate-50" key={index}>
                {columns.map((column) => (
                  <td className="px-3 py-2 text-slate-700" key={String(column.key)}>
                    {String(row[column.key] ?? '—')}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </article>
  );
}
