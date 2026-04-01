'use client';

import { FormEvent, KeyboardEvent, useMemo, useState } from 'react';

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

export function AdvancedCatalogWorkspace() {
  const [form, setForm] = useState<FormState>(EMPTY_FORM);
  const [saving, setSaving] = useState(false);
  const [loadingLookup, setLoadingLookup] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  const preview = useMemo(() => {
    const title245 = form.subtitle.trim() ? `${form.title.trim()} : ${form.subtitle.trim()}` : form.title.trim();
    const publication = [form.publisher.trim(), form.publicationYear.trim()].filter(Boolean).join(', ');

    return {
      '001': 'pré-visualização',
      '100': form.authors[0] ?? '',
      '245': title245,
      '260': publication,
      '300': form.pages.trim(),
      '650': form.subjects,
      '020': form.isbn.trim(),
      ...(form.edition.trim() ? { '250': form.edition.trim() } : {}),
      ...(form.language.trim() ? { '041': form.language.trim() } : {}),
      ...(form.description.trim() ? { '520': form.description.trim() } : {})
    };
  }, [form]);

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
    description: form.description.trim() || undefined
  }), [form]);

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
