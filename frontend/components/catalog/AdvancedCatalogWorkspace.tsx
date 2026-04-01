'use client';

import { FormEvent, KeyboardEvent, useEffect, useMemo, useRef, useState } from 'react';

import { ApiError, apiFetch, type Book } from '../../lib/api';

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

interface MarcPreviewField {
  ind1?: string;
  ind2?: string;
  subfields?: Record<string, string>;
}

interface MarcHumanToken {
  type: 'field' | 'subfield' | 'value';
  text: string;
}

interface MarcHumanLine {
  id: string;
  tokens: MarcHumanToken[];
}

interface MarcValidationResult {
  errors: string[];
  fieldErrors: Record<string, string[]>;
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

function formatMarcHuman(marc21Full: Record<string, unknown>): MarcHumanLine[] {
  const tags = Object.keys(marc21Full)
    .filter((tag) => /^\d{3}$/.test(tag))
    .sort((a, b) => Number(a) - Number(b));

  return tags.map((tag) => {
    const fieldValue = marc21Full[tag] as MarcPreviewField | undefined;
    const ind1 = (fieldValue?.ind1 ?? '#').toString().slice(0, 1) || '#';
    const ind2 = (fieldValue?.ind2 ?? '#').toString().slice(0, 1) || '#';
    const tokens: MarcHumanToken[] = [
      { type: 'field', text: `${tag} ${ind1}${ind2}` }
    ];

    const subfields = fieldValue?.subfields;
    if (subfields && typeof subfields === 'object') {
      Object.entries(subfields).forEach(([code, value]) => {
        const normalizedCode = code.trim().slice(0, 1).toLowerCase();
        if (!normalizedCode) {
          return;
        }
        tokens.push({ type: 'subfield', text: `$${normalizedCode}` });
        tokens.push({ type: 'value', text: String(value ?? '') });
      });
    }

    return { id: tag, tokens };
  });
}

function validateMarc(marc21_full: Record<string, unknown>): MarcValidationResult {
  const fieldErrors: Record<string, string[]> = {};
  const isbnRegex = /^(?:\d{9}[\dXx]|\d{13})$/;
  const pushError = (key: string, message: string) => {
    fieldErrors[key] = [...(fieldErrors[key] ?? []), message];
  };

  const getField = (tag: string): MarcPreviewField | null => {
    const raw = marc21_full[tag];
    if (!raw || typeof raw !== 'object') {
      return null;
    }
    return raw as MarcPreviewField;
  };

  const readSubfieldValue = (tag: string, code: string): string => {
    const field = getField(tag);
    const raw = field?.subfields?.[code];
    return typeof raw === 'string' ? raw.trim() : String(raw ?? '').trim();
  };

  const title = readSubfieldValue('245', 'a');
  if (!title) {
    pushError('245', 'Campo 245 (Título) é obrigatório');
  }

  const author = readSubfieldValue('100', 'a');
  if (!author) {
    pushError('100', 'Campo 100 deve conter autor');
  }

  const isbn = readSubfieldValue('020', 'a').replace(/[-\s]/g, '');
  if (isbn && !isbnRegex.test(isbn)) {
    pushError('020$a', 'ISBN inválido');
  }

  const yearValue = readSubfieldValue('260', 'c');
  if (yearValue && !/^\d{4}$/.test(yearValue)) {
    pushError('260$c', 'Ano deve ser número válido');
  }

  Object.entries(marc21_full).forEach(([tag, value]) => {
    if (!/^\d{3}$/.test(tag) || typeof value !== 'object' || value === null) {
      return;
    }
    const subfields = (value as MarcPreviewField).subfields;
    const validSubfields = subfields && typeof subfields === 'object'
      ? Object.entries(subfields).filter(([code]) => code.trim()).filter(([, subValue]) => String(subValue ?? '').trim())
      : [];
    if (validSubfields.length === 0) {
      pushError(tag, `Campo ${tag} deve conter pelo menos 1 subcampo`);
    }
  });

  return { errors: Object.values(fieldErrors).flat(), fieldErrors };
}

export function AdvancedCatalogWorkspace() {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [marcRows, setMarcRows] = useState<MarcRow[]>(() => buildRowsFromForm(EMPTY_FORM));
  const [saving, setSaving] = useState(false);
  const [loadingLookup, setLoadingLookup] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  const [validationErrors, setValidationErrors] = useState<Record<string, string[]>>({});
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

  const humanPreview = useMemo(() => formatMarcHuman(preview), [preview]);
  const humanPreviewText = useMemo(
    () => humanPreview.map((line) => line.tokens.map((token) => token.text).join(' ')).join('\n'),
    [humanPreview]
  );

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
    const validation = validateMarc(preview);
    setValidationErrors(validation.fieldErrors);
    if (validation.errors.length > 0) {
      setToast(`Erros de validação: ${validation.errors.join(' | ')}`);
      return;
    }

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
      if (error instanceof ApiError) {
        try {
          const parsed = JSON.parse(error.body) as { detail?: { errors?: string[] } | string };
          if (typeof parsed.detail === 'object' && parsed.detail?.errors?.length) {
            setToast(`Erros de validação: ${parsed.detail.errors.join(' | ')}`);
          } else {
            setToast('Falha ao salvar o livro.');
          }
        } catch {
          setToast(error.message);
        }
      } else {
        setToast(error instanceof Error ? error.message : 'Falha ao salvar o livro.');
      }
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

  const copyMarc = async () => {
    if (!humanPreviewText) {
      setToast('Não há MARC formatado para copiar.');
      return;
    }
    try {
      await navigator.clipboard.writeText(humanPreviewText);
      setToast('MARC formatado copiado.');
    } catch (error) {
      setToast(error instanceof Error ? error.message : 'Falha ao copiar MARC.');
    }
  };

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <form className="space-y-4 rounded-xl border bg-white p-5 shadow-sm" onSubmit={onSave}>
        <h3 className="text-lg font-semibold text-slate-900">Formulário bibliográfico avançado</h3>
        <div className="grid gap-4 md:grid-cols-2">
          <Field
            error={validationErrors['245']?.[0]}
            label="Título"
            required
            value={form.title}
            onChange={(value) => setForm((s) => ({ ...s, title: value }))}
          />
          <Field label="Subtítulo" value={form.subtitle} onChange={(value) => setForm((s) => ({ ...s, subtitle: value }))} />
          <TagField
            error={validationErrors['100']?.[0]}
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
          <Field error={validationErrors['020$a']?.[0]} label="ISBN" value={form.isbn} onChange={(value) => setForm((s) => ({ ...s, isbn: value }))} />
          <Field label="Editora" value={form.publisher} onChange={(value) => setForm((s) => ({ ...s, publisher: value }))} />
          <Field error={validationErrors['260$c']?.[0]} label="Ano" type="number" value={form.publicationYear} onChange={(value) => setForm((s) => ({ ...s, publicationYear: value }))} />
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
                  <th className="px-3 py-2">Ações</th>
                  <th className="px-3 py-2">Erros</th>
                </tr>
              </thead>
              <tbody>
                {marcRows.map((row) => (
                  <tr className={`border-t align-top ${validationErrors[row.tag.trim()] ? 'border-red-200 bg-red-50/40' : 'border-slate-100'}`} key={row.id}>
                    <td className="px-3 py-2">
                      <input
                        className={`w-20 rounded-md px-2 py-1 font-mono ${validationErrors[row.tag.trim()] ? 'border-red-300 bg-red-50 text-red-900' : 'border-emerald-200 bg-emerald-50 text-emerald-900'}`}
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
                    <td className="px-3 py-2 text-xs text-red-600">
                      {validationErrors[row.tag.trim()]?.join(' | ')}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </section>
      </form>

      <div className="rounded-xl border bg-white p-5 shadow-sm">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">MARC21 Preview</h3>
            <p className="mt-1 text-sm text-slate-500">Visual humano MARC21 em tempo real (principal) + JSON técnico (secundário).</p>
          </div>
          <button
            className="rounded-lg border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-xs font-semibold text-emerald-900"
            onClick={copyMarc}
            type="button"
          >
            Copiar MARC
          </button>
        </div>

        <div className="mt-4 space-y-2 rounded-lg bg-slate-950 p-4 font-mono text-sm">
          {humanPreview.map((line) => (
            <div className="flex flex-wrap gap-2" key={line.id}>
              {line.tokens.map((token, index) => {
                if (token.type === 'field') {
                  const isHighlight = MARC_HIGHLIGHT_TAGS.includes(line.id);
                  return (
                    <span className={isHighlight ? 'font-semibold text-emerald-300' : 'text-emerald-400'} key={`${line.id}-${token.type}-${index}`}>
                      {token.text}
                    </span>
                  );
                }

                if (token.type === 'subfield') {
                  return (
                    <span className="text-white" key={`${line.id}-${token.type}-${index}`}>
                      {token.text}
                    </span>
                  );
                }

                return (
                  <span className="text-slate-300" key={`${line.id}-${token.type}-${index}`}>
                    {token.text}
                  </span>
                );
              })}
            </div>
          ))}
        </div>

        <details className="mt-4 rounded-lg border border-slate-200">
          <summary className="cursor-pointer list-none px-3 py-2 text-xs font-semibold uppercase tracking-wide text-slate-600">
            JSON Preview (secundário)
          </summary>
          <pre className="max-h-[280px] overflow-auto border-t bg-slate-50 p-3 text-xs text-slate-700">
            {JSON.stringify(preview, null, 2)}
          </pre>
        </details>
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
  error?: string;
}

function Field({ label, value, onChange, required, type = 'text', error }: FieldProps) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <input
        className={`mt-1 w-full rounded-lg border px-3 py-2 text-sm shadow-sm focus:outline-none ${error ? 'border-red-300 focus:border-red-400' : 'border-slate-200 focus:border-brand-400'}`}
        onChange={(event) => onChange(event.target.value)}
        required={required}
        type={type}
        value={value}
      />
      {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
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
  error?: string;
}

function TagField({ label, tags, inputValue, onInputChange, onKeyDown, onAdd, onRemove, error }: TagFieldProps) {
  return (
    <label className="block text-sm font-medium text-slate-700">
      {label}
      <div className="mt-1 flex gap-2">
        <input
          className={`w-full rounded-lg border px-3 py-2 text-sm shadow-sm focus:outline-none ${error ? 'border-red-300 focus:border-red-400' : 'border-slate-200 focus:border-brand-400'}`}
          onChange={(event) => onInputChange(event.target.value)}
          onKeyDown={onKeyDown}
          value={inputValue}
        />
        <button className="rounded-lg border border-slate-300 px-3 text-sm" onClick={onAdd} type="button">+</button>
      </div>
      {error ? <span className="mt-1 block text-xs text-red-600">{error}</span> : null}
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
