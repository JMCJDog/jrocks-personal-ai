'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';

const navItems = [
  { href: '/', label: 'Home', icon: '🏠' },
  { href: '/dashboard', label: 'Monitor', icon: '📊' },
  { href: '/chat', label: 'Chat', icon: '💬' },
  { href: '/agents', label: 'Agents', icon: '🤖' },
  { href: '/ingest', label: 'Ingest', icon: '📁' },
  { href: '/analytics', label: 'Heatmap', icon: '🗺️' },
  { href: '/webhooks', label: 'Webhooks', icon: '🔔' },
  { href: '/settings', label: 'Settings', icon: '⚙️' },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="sidebar">
      <Link href="/" className="logo">
        <span className="logo-icon">🧠</span>
        <span className="logo-text">JRock's AI</span>
      </Link>

      <nav className="nav">
        {navItems.map((item) => (
          <Link
            key={item.href}
            href={item.href}
            className={`nav-item ${pathname === item.href ? 'active' : ''}`}
          >
            <span className="nav-icon">{item.icon}</span>
            <span className="nav-label">{item.label}</span>
          </Link>
        ))}
      </nav>

      <div className="sidebar-footer">
        <div className="footer-item">
          <span>Powered by Ollama</span>
        </div>
      </div>

      <style jsx>{`
        .sidebar {
          position: fixed;
          left: 0;
          top: 0;
          width: 260px;
          height: 100vh;
          background: var(--bg-secondary);
          border-right: 1px solid var(--border-subtle);
          display: flex;
          flex-direction: column;
          padding: var(--spacing-lg);
          z-index: 100;
        }

        .logo {
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
          padding: var(--spacing-md);
          margin-bottom: var(--spacing-xl);
        }

        .logo-icon {
          font-size: 2rem;
        }

        .logo-text {
          font-size: 1.25rem;
          font-weight: 700;
          background: var(--accent-gradient);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
        }

        .nav {
          flex: 1;
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xs);
        }

        .nav-item {
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
          padding: var(--spacing-sm) var(--spacing-md);
          border-radius: var(--radius-md);
          color: var(--text-secondary);
          text-decoration: none;
          transition: all var(--transition-fast);
        }

        .nav-item:hover {
          background: var(--bg-card-hover);
          color: var(--text-primary);
        }

        .nav-item.active {
          background: var(--accent-primary);
          color: white;
        }

        .nav-icon {
          font-size: 1.125rem;
        }

        .nav-label {
          font-weight: 500;
        }

        .sidebar-footer {
          padding-top: var(--spacing-lg);
          border-top: 1px solid var(--border-subtle);
        }

        .footer-item {
          font-size: 0.75rem;
          color: var(--text-muted);
          text-align: center;
        }

        @media (max-width: 768px) {
          .sidebar {
            transform: translateX(-100%);
          }
        }
      `}</style>
    </aside>
  );
}
