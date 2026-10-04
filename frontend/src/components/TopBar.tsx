import { Link } from 'react-router-dom';
import type { ReactNode } from 'react';

export function TopBar({ title, children }: { title?: ReactNode; children?: ReactNode }) {
  return (
    <header className="topbar">
      <Link to="/" className="brand">
        DNNLS Live Arena
      </Link>
      {title && <span className="topbar-title">{title}</span>}
      <div className="topbar-actions">{children}</div>
    </header>
  );
}
