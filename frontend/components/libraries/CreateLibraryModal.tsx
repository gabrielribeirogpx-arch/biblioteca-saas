'use client';

import { FormEvent, useMemo, useState } from 'react';

interface CreateLibraryModalProps {
  isOpen: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (payload: { name: string; code: string }) => Promise<void>;
}

function toSlug(rawValue: string): string {
  return rawValue
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '');
}

export function CreateLibraryModal({ isOpen, isSubmitting, onClose, onSubmit }: CreateLibraryModalProps) {
  const [name, setName] = useState('');
  const [code, setCode] = useState('');

  const canSubmit = useMemo(() => name.trim().length > 1 && code.trim().length > 1, [name, code]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!canSubmit || isSubmitting) {
      return;
    }

    await onSubmit({ name: name.trim(), code: code.trim() });
    setName('');
    setCode('');
  }

  if (!isOpen) {
    return null;
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4">
      <div className="w-full max-w-md rounded-xl border bg-white p-5 shadow-xl">
        <h4 className="text-lg font-semibold text-slate-900">Nova Biblioteca</h4>

        <form className="mt-4 space-y-3" onSubmit={(event) => void handleSubmit(event)}>
          <div>
            <label className="text-sm text-slate-600">Nome da biblioteca</label>
            <input
              value={name}
              onChange={(event) => {
                const nextName = event.target.value;
                setName(nextName);

                if (!code.trim()) {
                  setCode(toSlug(nextName));
                }
              }}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="Biblioteca Central"
              required
            />
          </div>

          <div>
            <label className="text-sm text-slate-600">Código (slug)</label>
            <input
              value={code}
              onChange={(event) => setCode(toSlug(event.target.value))}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="biblioteca-central"
              required
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm"
              disabled={isSubmitting}
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={!canSubmit || isSubmitting}
              className="rounded-md bg-brand-700 px-4 py-2 text-sm font-semibold text-white hover:bg-brand-800 disabled:opacity-60"
            >
              {isSubmitting ? 'Criando...' : 'Criar Biblioteca'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
