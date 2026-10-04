import { useRef, useState } from 'react';
import type { SubmissionTypeInfo } from '../api/types';
import { formatBytes } from '../lib/format';

interface Props {
  submissionTypes: SubmissionTypeInfo[];
  disabled?: boolean;
  disabledReason?: string;
  onUpload: (file: File) => Promise<void>;
}

export function UploadControl({ submissionTypes, disabled, disabledReason, onUpload }: Props) {
  const [file, setFile] = useState<File | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const accept = submissionTypes.flatMap((t) => t.accepted_extensions).join(',');

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file) return;
    setBusy(true);
    setError(null);
    try {
      await onUpload(file);
      setFile(null);
      if (inputRef.current) inputRef.current.value = '';
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed');
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="upload" onSubmit={submit}>
      <label className="file-label">
        <span>Choose your artifact ({accept})</span>
        <input ref={inputRef} type="file" accept={accept} disabled={disabled || busy} onChange={(e) => setFile(e.target.files?.[0] ?? null)} />
      </label>
      {file && (
        <p className="muted small">
          {file.name} · {formatBytes(file.size)}
        </p>
      )}
      <button type="submit" className="primary" disabled={!file || disabled || busy}>
        {busy ? 'Uploading…' : 'Submit'}
      </button>
      {disabled && disabledReason && <p className="muted small">{disabledReason}</p>}
      {error && <p className="error" role="alert">{error}</p>}
      <details className="small">
        <summary>Accepted submission types</summary>
        <ul>
          {submissionTypes.map((t) => (
            <li key={t.id}>
              <strong>{t.label}</strong> ({t.accepted_extensions.join(', ')}) — {t.description}
            </li>
          ))}
        </ul>
      </details>
    </form>
  );
}
