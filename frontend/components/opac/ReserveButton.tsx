'use client';

import { useEffect, useState } from 'react';

import { Toast } from '../ui/Toast';
import { apiFetch } from '../../lib/api';

interface ReserveButtonProps {
  bookId: number;
  className?: string;
}

export function ReserveButton({ bookId, className }: ReserveButtonProps) {
  const [loading, setLoading] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!successMessage) return;
    const timeout = window.setTimeout(() => setSuccessMessage(null), 2500);
    return () => window.clearTimeout(timeout);
  }, [successMessage]);

  const reserve = async () => {
    setLoading(true);
    setErrorMessage(null);

    try {
      await apiFetch('/api/reservations/', {
        method: 'POST',
        body: JSON.stringify({ book_id: bookId })
      });
      setSuccessMessage('Reserva registrada com sucesso.');
    } catch {
      setErrorMessage('Não foi possível reservar este livro. Faça login para continuar.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {successMessage ? <Toast message={successMessage} /> : null}
      <button
        type="button"
        className={className ?? 'inline-flex rounded-md border border-slate-300 px-3 py-2 text-xs font-semibold text-slate-700'}
        onClick={() => void reserve()}
        disabled={loading}
      >
        {loading ? 'Reservando...' : 'Reservar'}
      </button>
      {errorMessage ? <p className="mt-1 text-xs font-medium text-rose-700">{errorMessage}</p> : null}
    </>
  );
}
