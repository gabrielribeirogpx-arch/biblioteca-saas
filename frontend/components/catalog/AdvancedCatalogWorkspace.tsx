'use client';

import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react';

import { apiFetch, type Book } from '../../lib/api';

interface AdvancedCatalogPayload {
  title: string;
  subtitle?: string;
  authors: string[];
  subjects: string[];
  isbn?: string;
  publisher?: string;
  publication_year?: number;
  edition?: string;
  language?: string;
  pages?: number;
  description?: string;
  marc21_full?: Record<string, unknown>;
}

interface AdvancedCatalogResponse {
  book: Book;
  marc21_record: Record<string, unknown>;
}

interface LookupResponse extends AdvancedCatalogPayload {}

interface FormState {
  title: string;
  subtitle: string;
  authorInput: string;
  subjectInput: string;
  authors: string[];
  subjects: string[];
  isbn: string;
  publisher: string;
  publicationYear: string;
  edition: string;
  language: string;
  pages: string;
  description: string;
}

interface MarcSubfield {
  id: string;
  code: string;
  value: string;
}

interface MarcRow {
  id: string;
  tag: string;
  indicators: string;
  subfields: MarcSubfield[];
}

const EMPTY_FORM: FormState = {
  title: '',
  subtitle: '',
  authorInput: '',
  subjectInput: '',
  authors: [],
  subjects: [],
  isbn: '',
  publisher: '',
  publicationYear: '',
  edition: '',
  language: '',
  pages: '',
  description: ''
};

const MARC_HIGHLIGHT_TAGS = ['001', '100', '245', '260', '300', '650', '020'];

const createId = () => `${Date.now()}-${Math.random().toString(36).slice(2, 9)}`;

const createSubfield = (code = 'a', value = ''): MarcSubfield => ({ id: createId(), code, value });

const createRow = (tag = '', indicators = '##', subfields: MarcSubfield[] = [createSubfield()]): MarcRow => ({
  id: createId(),
  tag,
  indicators,
  subfields
});

const upsertRow = (rows: MarcRow[], tag: string, indicators: string, subfields: Array<{ code: string; value: string }>): MarcRow[] => {
  const existing = rows.find((row) => row.tag === tag);
  const normalizedSubfields = subfields.map((item) => createSubfield(item.code, item.value));
  if (existing) {
    return rows.map((row) => (
      row.id === existing.id
        ? {
          ...row,
          indicators,
          subfields: normalizedSubfields
        }
        : row
    ));
  }

  return [...rows, createRow(tag, indicators, normalizedSubfields)];
};

const buildRowsFromForm = (form: FormState): MarcRow[] => {
  let rows: MarcRow[] = [];
  rows = upsertRow(rows, '100', '1#', [{ code: 'a', value: form.authors[0] ?? '' }]);
  rows = upsertRow(rows, '245', '10', [
    { code: 'a', value: form.title.trim() },
    { code: 'b', value: form.subtitle.trim() }
  ]);
  rows = upsertRow(rows, '260', '##', [
    { code: 'b', value: form.publisher.trim() },
    { code: 'c', value: form.publicationYear.trim() }
  ]);
  rows = upsertRow(rows, '300', '##', [{ code: 'a', value: form.pages.trim() }]);
  rows = upsertRow(rows, '650', '#0', [{ code: 'a', value: form.subjects.join(' | ') }]);
  rows = upsertRow(rows, '020', '##', [{ code: 'a', value: form.isbn.trim() }]);
  if (form.edition.trim()) {
    rows = upsertRow(rows, '250', '##', [{ code: 'a', value: form.edition.trim() }]);
  }
  if (form.language.trim()) {
    rows = upsertRow(rows, '041', '##', [{ code: 'a', value: form.language.trim() }]);
  }
  if (form.description.trim()) {
    rows = upsertRow(rows, '520', '##', [{ code: 'a', value: form.description.trim() }]);
  }
  return rows;
};

const readSubfield = (row: MarcRow | undefined, code: string): string => row?.subfields.find((item) => item.code === code)?.value.trim() ?? '';

const rowToJson = (row: MarcRow) => {
  const indicators = `${row.indicators || '##'}##`.slice(0, 2);
  const subfields: Record<string, string> = {};
  row.subfields.forEach((item) => {
    const code = item.code.trim().slice(0, 1).toLowerCase();
    if (!code) {
      return;
    }
    subfields[code] = item.value.trim();
  });

  return {
    [row.tag.trim()]: {
      ind1: indicators[0],
      ind2: indicators[1],
      subfields
    }
  };
};

export function AdvancedCatalogWorkspace() {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [marcRows, setMarcRows] = useState<MarcRow[]>(() => buildRowsFromForm(EMPTY_FORM));
  const [saving, setSaving] = useState(false);
  const [loadingLookup, setLoadingLookup] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const syncingFromRowsRef = useRef(false);

  useEffect(() => {
    if (syncingFromRowsRef.current) {
      syncingFromRowsRef.current = false;
      return;
    }
    setMarcRows((current) => {
      const rebuilt = buildRowsFromForm(form);
      const merged = current.filter((row) => !['100', '245', '260', '300', '650', '020', '250', '041', '520'].includes(row.tag.trim()));
      return [...merged, ...rebuilt];
    });
  }, [form]);

  const preview = useMemo(() => {
    const record = marcRows
      .filter((row) => row.tag.trim())
      .map((row) => [row.tag.trim(), rowToJson(row)[row.tag.trim()]]);
    return Object.fromEntries(record);
  }, [marcRows]);

  const payload = useMemo<AdvancedCatalogPayload>(() => ({
    title: form.title.trim(),
    subtitle: form.subtitle.trim() || undefined,
    authors: form.authors,
    subjects: form.subjects,
    isbn: form.isbn.trim() || undefined,
    publisher: form.publisher.trim() || undefined,
    publication_year: form.publicationYear ? Number(form.publicationYear) : undefined,
    edition: form.edition.trim() || undefined,
    language: form.language.trim() || undefined,
    pages: form.pages ? Number(form.pages) : undefined,
    description: form.description.trim() || undefined,
    marc21_full: preview
  }), [form, preview]);

  const syncFormFromRows = (rows: MarcRow[]) => {
    const field100 = rows.find((row) => row.tag.trim() === '100');
    const field245 = rows.find((row) => row.tag.trim() === '245');
    const field260 = rows.find((row) => row.tag.trim() === '260');
    const field300 = rows.find((row) => row.tag.trim() === '300');
    const field650 = rows.find((row) => row.tag.trim() === '650');
    const field020 = rows.find((row) => row.tag.trim() === '020');
    const field250 = rows.find((row) => row.tag.trim() === '250');
    const field041 = rows.find((row) => row.tag.trim() === '041');
    const field520 = rows.find((row) => row.tag.trim() === '520');

    syncingFromRowsRef.current = true;
    setForm((current) => ({
      ...current,
      title: readSubfield(field245, 'a'),
      subtitle: readSubfield(field245, 'b'),
      authors: readSubfield(field100, 'a') ? [readSubfield(field100, 'a')] : [],
      subjects: readSubfield(field650, 'a').split('|').map((item) => item.trim()).filter(Boolean),
      isbn: readSubfield(field020, 'a'),
      publisher: readSubfield(field260, 'b'),
      publicationYear: readSubfield(field260, 'c'),
      edition: readSubfield(field250, 'a'),
      language: readSubfield(field041, 'a'),
      pages: readSubfield(field300, 'a'),
      description: readSubfield(field520, 'a')
    }));
  };

  const addTag = (kind: 'authors' | 'subjects', value: string) => {
    const normalized = value.trim();
    if (!normalized) {
      return;
    }

    setForm((current) => ({
      ...current,
      [kind]: current[kind].includes(normalized) ? current[kind] : [...current[kind], normalized],
      ...(kind === 'authors' ? { authorInput: '' } : { subjectInput: '' })
    }));
  };

  const removeTag = (kind: 'authors' | 'subjects', value: string) => {
    setForm((current) => ({
      ...current,
      [kind]: current[kind].filter((item) => item !== value)
    }));
  };

  const onTagKeyDown = (
    event: KeyboardEvent<HTMLInputElement>,
    kind: 'authors' | 'subjects',
    currentValue: string
  ) => {
    if (event.key === 'Enter' || event.key === ',') {
      event.preventDefault();
      addTag(kind, currentValue);
    }
  };

  const onSave = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSaving(true);
    setToast(null);

    try {
      const response = await apiFetch<AdvancedCatalogResponse>('/api/v1/catalog/advanced', {
        method: 'POST',
        body: JSON.stringify(payload)
      });

      if (!response) {
        throw new Error('Sem resposta da API. Verifique autenticação.');
      }

      setToast(`Livro salvo com sucesso! Registro #${response.book.id}.`);
      setForm(EMPTY_FORM);
    } catch (error) {
      setToast(error instanceof Error ? error.message : 'Falha ao salvar o livro.');
    } finally {
      setSaving(false);
    }
  };

  const importByIsbn = async () => {
    const isbn = form.isbn.trim();
    if (!isbn) {
      setToast('Informe um ISBN para importar.');
      return;
    }

    setLoadingLookup(true);
    setToast(null);

    try {
      const data = await apiFetch<LookupResponse>(`/api/v1/books/lookup?isbn=${encodeURIComponent(isbn)}`);
      if (!data) {
        throw new Error('Não foi possível importar via ISBN.');
      }

      setForm((current) => ({
        ...current,
        title: data.title ?? current.title,
        subtitle: data.subtitle ?? current.subtitle,
        authors: data.authors ?? current.authors,
        subjects: data.subjects ?? current.subjects,
        publisher: data.publisher ?? current.publisher,
        publicationYear: data.publication_year ? String(data.publication_year) : current.publicationYear,
        edition: data.edition ?? current.edition,
        language: data.language ?? current.language,
        pages: data.pages ? String(data.pages) : current.pages,
        description: data.description ?? current.description
      }));
      setToast('Importação via ISBN concluída.');
    } catch (error) {
      setToast(error instanceof Error ? error.message : 'Falha na importação por ISBN.');
    } finally {
      setLoadingLookup(false);
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <form className="space-y-4 rounded-xl border bg-white p-5 shadow-sm" onSubmit={onSave}>
        <h3 className="text-lg font-semibold text-slate-900">Formulário bibliográfico avançado</h3>
        <div className="grid gap-4 md:grid-cols-2">
          <Field label="Título" required value={form.title} onChange={(value) => setForm((s) => ({ ...s, title: value }))} />
          <Field label="Subtítulo" value={form.subtitle} onChange={(value) => setForm((s) => ({ ...s, subtitle: value }))} />
          <TagField
            label="Autor(es)"
            inputValue={form.authorInput}
            tags={form.authors}
            onInputChange={(value) => setForm((s) => ({ ...s, authorInput: value }))}
            onKeyDown={(event) => onTagKeyDown(event, 'authors', form.authorInput)}
            onAdd={() => addTag('authors', form.authorInput)}
            onRemove={(value) => removeTag('authors', value)}
          />
          <TagField
            label="Assuntos"
            inputValue={form.subjectInput}
            tags={form.subjects}
            onInputChange={(value) => setForm((s) => ({ ...s, subjectInput: value }))}
            onKeyDown={(event) => onTagKeyDown(event, 'subjects', form.subjectInput)}
            onAdd={() => addTag('subjects', form.subjectInput)}
            onRemove={(value) => removeTag('subjects', value)}
          />
          <Field label="ISBN" value={form.isbn} onChange={(value) => setForm((s) => ({ ...s, isbn: value }))} />
          <Field label="Editora" value={form.publisher} onChange={(value) => setForm((s) => ({ ...s, publisher: value }))} />
          <Field label="Ano" type="number" value={form.publicationYear} onChange={(value) => setForm((s) => ({ ...s, publicationYear: value }))} />
          <Field label="Edição" value={form.edition} onChange={(value) => setForm((s) => ({ ...s, edition: value }))} />
          <Field label="Idioma" value={form.language} onChange={(value) => setForm((s) => ({ ...s, language: value }))} />
          <Field label="Número de páginas" type="number" value={form.pages} onChange={(value) => setForm((s) => ({ ...s, pages: value }))} />
        </div>

        <label className="block text-sm font-medium text-slate-700">
          Descrição
          <textarea
            className="mt-1 h-24 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-brand-400 focus:outline-none"
            value={form.description}
            onChange={(event) => setForm((state) => ({ ...state, description: event.target.value }))}
          />
        </label>

        <div className="flex flex-wrap gap-3 pt-2">
          <button className="rounded-lg bg-brand-700 px-4 py-2 text-sm font-semibold text-white shadow-sm" disabled={saving} type="submit">
            {saving ? 'Salvando...' : 'Salvar livro'}
          </button>
          <button className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-slate-700" type="button">
            Gerar MARC21
          </button>
          <button className="rounded-lg border border-brand-200 bg-brand-50 px-4 py-2 text-sm font-semibold text-brand-800" disabled={loadingLookup} onClick={importByIsbn} type="button">
            {loadingLookup ? 'Importando...' : 'Importar via ISBN'}
          </button>
        </div>

        {toast ? <p className="rounded-md bg-slate-100 px-3 py-2 text-sm text-slate-700">{toast}</p> : null}

        <section className="pt-4">
          <div className="flex items-center justify-between gap-3">
            <h4 className="text-base font-semibold text-slate-900">Editor MARC21 Avançado</h4>
            <button
              className="rounded-lg border border-slate-300 px-3 py-1.5 text-xs font-semibold text-slate-700"
              onClick={() => setMarcRows((current) => [...current, createRow('', '##', [createSubfield('a', '')])])}
              type="button"
            >
              + Campo
            </button>
          </div>

          <div className="mt-3 overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full min-w-[680px] text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-3 py-2">Campo</th>
                  <th className="px-3 py-2">Indicadores</th>
                  <th className="px-3 py-2">Subcampos</th>
                  <th className="px-3 py-2" />
                </tr>
              </thead>
              <tbody>
                {marcRows.map((row) => (
                  <tr className="border-t border-slate-100 align-top" key={row.id}>
                    <td className="px-3 py-2">
                      <input
                        className="w-20 rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 font-mono text-emerald-900"
                        maxLength={3}
                        onChange={(event) => setMarcRows((current) => current.map((item) => item.id === row.id ? { ...item, tag: event.target.value } : item))}
                        value={row.tag}
                      />
                    </td>
                    <td className="px-3 py-2">
                      <input
                        className="w-16 rounded-md border border-slate-200 px-2 py-1 font-mono"
                        maxLength={2}
                        onChange={(event) => setMarcRows((current) => current.map((item) => item.id === row.id ? { ...item, indicators: event.target.value } : item))}
                        value={row.indicators}
                      />
                    </td>
                    <td className="space-y-2 px-3 py-2">
                      {row.subfields.map((subfield) => (
                        <div className="grid grid-cols-[4.5rem_1fr_auto] gap-2" key={subfield.id}>
                          <input
                            className="rounded-md border border-slate-200 px-2 py-1 font-mono"
                            maxLength={1}
                            onChange={(event) => setMarcRows((current) => current.map((item) => item.id === row.id ? {
                              ...item,
                              subfields: item.subfields.map((entry) => entry.id === subfield.id ? { ...entry, code: event.target.value } : entry)
                            } : item))}
                            value={subfield.code}
                          />
                          <input
                            className="rounded-md border border-slate-200 px-2 py-1"
                            onChange={(event) => setMarcRows((current) => current.map((item) => item.id === row.id ? {
                              ...item,
                              subfields: item.subfields.map((entry) => entry.id === subfield.id ? { ...entry, value: event.target.value } : entry)
                            } : item))}
                            value={subfield.value}
                          />
                          <button
                            className="rounded-md border border-slate-200 px-2 py-1 text-xs"
                            onClick={() => setMarcRows((current) => current.map((item) => item.id === row.id ? {
                              ...item,
                              subfields: item.subfields.filter((entry) => entry.id !== subfield.id)
                            } : item))}
                            type="button"
                          >
                            remover
                          </button>
                        </div>
                      ))}
                      <button
                        className="rounded-md border border-brand-200 bg-brand-50 px-2 py-1 text-xs font-semibold text-brand-800"
                        onClick={() => setMarcRows((current) => current.map((item) => item.id === row.id ? {
                          ...item,
                          subfields: [...item.subfields, createSubfield('a', '')]
                        } : item))}
                        type="button"
                      >
                        + Subcampo
                      </button>
                    </td>
                    <td className="px-3 py-2">
                      <div className="flex flex-col gap-2">
                        <button
                          className="rounded-md border border-slate-200 px-2 py-1 text-xs"
                          onClick={() => setMarcRows((current) => current.filter((item) => item.id !== row.id))}
                          type="button"
                        >
                          excluir
                        </button>
                        <button
                          className="rounded-md border border-emerald-200 bg-emerald-50 px-2 py-1 text-xs font-semibold text-emerald-800"
                          onClick={() => syncFormFromRows(marcRows)}
                          type="button"
                        >
                          sincronizar
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </form>

      <div className="rounded-xl border bg-white p-5 shadow-sm">
        <h3 className="text-lg font-semibold text-slate-900">MARC21 Preview</h3>
        <p className="mt-1 text-sm text-slate-500">Atualização em tempo real com campos bibliográficos estratégicos.</p>

        <div className="mt-4 space-y-2 rounded-lg bg-slate-950 p-4 text-sm text-slate-100">
          {Object.entries(preview).map(([tag, value]) => (
            <div className="grid grid-cols-[3rem_1fr] gap-2" key={tag}>
              <span className={MARC_HIGHLIGHT_TAGS.includes(tag) ? 'font-semibold text-emerald-300' : 'text-slate-400'}>{tag}:</span>
              <span>{Array.isArray(value) ? value.join(' | ') : String(value || '—')}</span>
            </div>
          ))}
        </div>

        <pre className="mt-4 max-h-[380px] overflow-auto rounded-lg border bg-slate-50 p-3 text-xs text-slate-700">
          {JSON.stringify(preview, null, 2)}
        </pre>
      </div>
    </div>
  );
}

interface FieldProps {
  label: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  type?: 'text' | 'number';
}

function Field({ label, value, onChange, required, type = 'text' }: FieldProps) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <input
        className="mt-1 w-full rounded-lg border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-brand-400 focus:outline-none"
        onChange={(event) => onChange(event.target.value)}
        required={required}
        type={type}
        value={value}
      />
    </label>
  );
}

interface TagFieldProps {
  label: string;
  tags: string[];
  inputValue: string;
  onInputChange: (value: string) => void;
  onKeyDown: (event: KeyboardEvent<HTMLInputElement>) => void;
  onAdd: () => void;
  onRemove: (value: string) => void;
}

function TagField({ label, tags, inputValue, onInputChange, onKeyDown, onAdd, onRemove }: TagFieldProps) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <div className="mt-1 flex gap-2">
        <input
          className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm shadow-sm focus:border-brand-400 focus:outline-none"
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={onKeyDown}
          value={inputValue}
        />
        <button className="rounded-lg border border-slate-300 px-3 text-sm" onClick={onAdd} type="button">+</button>
      </div>
      <div className="mt-2 flex flex-wrap gap-2">
        {tags.map((tag) => (
          <button className="rounded-full bg-brand-50 px-3 py-1 text-xs text-brand-800" key={tag} onClick={() => onRemove(tag)} type="button">
            {tag} ×
          </button>
        ))}
      </div>
    </label>
  );
}
