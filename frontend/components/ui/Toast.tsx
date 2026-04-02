interface ToastProps {
  message: string;
}

export function Toast({ message }: ToastProps) {
  return (
    <div className="fixed bottom-4 right-4 z-50 rounded-md bg-emerald-600 px-4 py-3 text-sm font-semibold text-white shadow-lg">
      {message}
    </div>
  );
}
