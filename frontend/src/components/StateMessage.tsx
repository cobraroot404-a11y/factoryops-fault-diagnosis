export function Loading({ label = "Loading..." }: { label?: string }) {
  return (
    <div className="state-msg" role="status" aria-live="polite">
      {label}
    </div>
  );
}

export function ErrorMessage({ message }: { message: string }) {
  return (
    <div className="state-msg error" role="alert">
      {message}
    </div>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <div className="state-msg" role="status">
      {message}
    </div>
  );
}
