'use client';

import { FormEvent, useMemo, useState } from 'react';

interface CreateLibraryModalProps {
  isOpen: boolean;
  isSubmitting: boolean;
  onClose: () => void;
  onSubmit: (payload: { name: string }) => Promise<void>;
}

export function CreateLibraryModal({ isOpen, isSubmitting, onClose, onSubmit }: CreateLibraryModalProps) {
  const [name, setName] = useState('');
  const [showValidation, setShowValidation] = useState(false);

  const normalizedName = name.trim();
  const canSubmit = useMemo(() => normalizedName.length > 0, [normalizedName]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setShowValidation(true);

    if (!canSubmit || isSubmitting) {
      return;
    }

    await onSubmit({ name: normalizedName });
    setName('');
    setShowValidation(false);
  }

  function handleClose() {
    setShowValidation(false);
    setName('');
    onClose();
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
              onChange={(event) => setName(event.target.value)}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm"
              placeholder="Biblioteca Central"
              required
              autoFocus
            />
            {showValidation && !canSubmit ? (
              <p className="mt-1 text-xs text-rose-700">O nome da biblioteca é obrigatório.</p>
            ) : null}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={handleClose}
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
