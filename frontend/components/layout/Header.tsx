'use client';

import { usePathname } from 'next/navigation';
import Image from 'next/image';

const pageTitles: Record<string, string> = {
  '/': 'Dashboard',
  '/chat': 'Chat',
  '/agents': 'Agents',
  '/ingest': 'Ingest',
  '/webhooks': 'Webhooks',
  '/settings': 'Settings',
};

export function Header() {
  const pathname = usePathname();
  const title = pageTitles[pathname] || 'JRock AI';

  return (
    <header className="header">
      <h2 className="page-title">{title}</h2>

      <div className="header-actions">
        <button className="header-btn" title="Notifications">
          🔔
        </button>
        <Image
          src="/profile.jpg"
          alt="JRock"
          width={40}
          height={40}
          className="user-avatar"
        />
      </div>

      <style jsx>{`
        .header {
          display: flex;
          align-items: center;
          justify-content: space-between;
          padding: var(--spacing-lg) var(--spacing-xl);
          background: var(--bg-secondary);
          border-bottom: 1px solid var(--border-subtle);
        }

        .page-title {
          font-size: 1.5rem;
          font-weight: 600;
        }

        .header-actions {
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
        }

        .header-btn {
          width: 40px;
          height: 40px;
          border-radius: var(--radius-md);
          background: var(--bg-tertiary);
          border: 1px solid var(--border-subtle);
          cursor: pointer;
          font-size: 1rem;
          transition: all var(--transition-fast);
        }

        .header-btn:hover {
          background: var(--bg-card-hover);
          border-color: var(--border-focus);
        }

        .user-avatar {
          width: 40px;
          height: 40px;
          border-radius: var(--radius-full);
          object-fit: cover;
          border: 2px solid var(--border-subtle);
          transition: border-color var(--transition-fast);
        }

        .user-avatar:hover {
          border-color: var(--accent-primary);
        }
      `}</style>
    </header>
  );
}
