'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';

interface SystemStatus {
  status: string;
  version: string;
}

export default function Dashboard() {
  const [systemStatus, setSystemStatus] = useState<SystemStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch('/api/health')
      .then(res => res.json())
      .then(data => {
        setSystemStatus({ status: data.status, version: '0.1.0' });
        setLoading(false);
      })
      .catch(() => {
        setSystemStatus({ status: 'offline', version: 'N/A' });
        setLoading(false);
      });
  }, []);

  const features = [
    {
      title: 'Chat',
      description: 'Have a conversation with your Personal AI',
      href: '/chat',
      icon: '💬',
      gradient: 'linear-gradient(135deg, #6366f1 0%, #818cf8 100%)',
    },
    {
      title: 'Agents',
      description: 'Manage and monitor AI agent activities',
      href: '/agents',
      icon: '🤖',
      gradient: 'linear-gradient(135deg, #a855f7 0%, #d946ef 100%)',
    },
    {
      title: 'Ingest',
      description: 'Upload documents and media for processing',
      href: '/ingest',
      icon: '📁',
      gradient: 'linear-gradient(135deg, #22c55e 0%, #4ade80 100%)',
    },
    {
      title: 'Webhooks',
      description: 'Configure event notifications',
      href: '/webhooks',
      icon: '🔔',
      gradient: 'linear-gradient(135deg, #f59e0b 0%, #fbbf24 100%)',
    },
  ];

  return (
    <div className="dashboard animate-fade-in">
      <section className="hero">
        <h1>Welcome to JRock's Personal AI</h1>
        <p>Your digital consciousness ecosystem powered by local SLMs</p>

        <div className="status-card glass-card">
          <div className="status-indicator">
            <span className={`dot ${loading ? 'loading' : systemStatus?.status === 'healthy' ? 'online' : 'offline'}`} />
            <span className="status-text">
              {loading ? 'Connecting...' : systemStatus?.status === 'healthy' ? 'System Online' : 'System Offline'}
            </span>
          </div>
          <span className="version">v{systemStatus?.version || '...'}</span>
        </div>
      </section>

      <section className="features-grid">
        {features.map((feature, index) => (
          <Link
            key={feature.title}
            href={feature.href}
            className="feature-card glass-card"
            style={{ animationDelay: `${index * 100}ms` }}
          >
            <div className="feature-icon" style={{ background: feature.gradient }}>
              {feature.icon}
            </div>
            <h3>{feature.title}</h3>
            <p>{feature.description}</p>
            <span className="arrow">→</span>
          </Link>
        ))}
      </section>

      <style jsx>{`
        .dashboard {
          max-width: 1200px;
          margin: 0 auto;
        }
        
        .hero {
          text-align: center;
          padding: var(--spacing-2xl) 0;
        }
        
        .hero h1 {
          font-size: 2.5rem;
          background: var(--accent-gradient);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          background-clip: text;
          margin-bottom: var(--spacing-md);
        }
        
        .hero p {
          font-size: 1.125rem;
          color: var(--text-secondary);
          margin-bottom: var(--spacing-xl);
        }
        
        .status-card {
          display: inline-flex;
          align-items: center;
          justify-content: space-between;
          gap: var(--spacing-xl);
          padding: var(--spacing-md) var(--spacing-lg);
        }
        
        .status-indicator {
          display: flex;
          align-items: center;
          gap: var(--spacing-sm);
        }
        
        .dot {
          width: 10px;
          height: 10px;
          border-radius: 50%;
          animation: pulse 2s ease-in-out infinite;
        }
        
        .dot.online { background: var(--success); }
        .dot.offline { background: var(--error); }
        .dot.loading { background: var(--warning); }
        
        .status-text {
          font-weight: 500;
        }
        
        .version {
          color: var(--text-muted);
          font-size: 0.875rem;
        }
        
        .features-grid {
          display: grid;
          grid-template-columns: repeat(4, 1fr);
          gap: var(--spacing-md);
          padding: var(--spacing-lg) 0;
        }
        
        .feature-card {
          padding: var(--spacing-md);
          display: flex;
          flex-direction: column;
          gap: var(--spacing-sm);
          animation: fadeIn var(--transition-base) backwards;
          cursor: pointer;
          text-decoration: none;
          color: inherit;
        }
        
        .feature-icon {
          width: 44px;
          height: 44px;
          border-radius: var(--radius-md);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.25rem;
        }
        
        .feature-card h3 {
          font-size: 1rem;
        }
        
        .feature-card p {
          flex: 1;
          font-size: 0.8rem;
          color: var(--text-secondary);
          line-height: 1.4;
        }
        
        .arrow {
          color: var(--accent-primary);
          font-size: 1rem;
          transition: transform var(--transition-fast);
        }
        
        .feature-card:hover .arrow {
          transform: translateX(4px);
        }

        @media (max-width: 900px) {
          .features-grid {
            grid-template-columns: repeat(2, 1fr);
          }
        }

        @media (max-width: 500px) {
          .features-grid {
            grid-template-columns: 1fr;
          }
        }
      `}</style>
    </div>
  );
}
