'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { api } from '@/lib/api'; // We might need to extend api.ts or use fetch directly

interface Agent {
  name: string;
  display_name: string;
  description: string;
  capabilities: string[];
}

interface AgentListResponse {
  agents: Agent[];
}

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch('/api/agents/')
      .then(res => {
        if (!res.ok) throw new Error('Failed to fetch agents');
        return res.json();
      })
      .then((data: AgentListResponse) => {
        setAgents(data.agents);
        setLoading(false);
      })
      .catch(err => {
        console.error(err);
        setError('Could not load agents system.');
        setLoading(false);
      });
  }, []);

  return (
    <div className="agents-page animate-fade-in">
      <header className="page-header">
        <h1 className="page-title">Agent Orchestration</h1>
        <p className="page-subtitle">Monitor and interact with specialized AI agents.</p>
      </header>

      {loading ? (
        <div className="loading-state">
          <div className="spinner"></div>
          <p>Connecting to Agent Swarm...</p>
        </div>
      ) : error ? (
        <div className="error-state">
          <p>{error}</p>
          <button className="btn btn-primary" onClick={() => window.location.reload()}>Retry</button>
        </div>
      ) : (
        <div className="agents-grid">
          {agents.map((agent) => (
            <Link href={`/chat?agent=${agent.name}`} key={agent.name} className="agent-card-link">
              <div className="agent-card glass-card">
                <div className="agent-header">
                  <div className={`agent-icon ${agent.name}`}>
                    {getAgentIcon(agent.name)}
                  </div>
                  <div className="agent-info">
                    <h2>{agent.display_name}</h2>
                    <span className="agent-status online">Active</span>
                  </div>
                </div>
                <p className="agent-desc">{agent.description}</p>
                <div className="agent-capabilities">
                  {agent.capabilities.map(cap => (
                    <span key={cap} className="tag">{cap}</span>
                  ))}
                </div>
              </div>
            </Link>
          ))}
        </div>
      )}

      <style jsx>{`
        .agents-page {
          padding: var(--spacing-lg);
          max-width: 1200px;
          margin: 0 auto;
        }

        .page-header {
          margin-bottom: var(--spacing-2xl);
          text-align: center;
        }

        .page-title {
          font-size: 2.5rem;
          background: var(--accent-gradient);
          -webkit-background-clip: text;
          -webkit-text-fill-color: transparent;
          margin-bottom: var(--spacing-xs);
        }

        .page-subtitle {
          color: var(--text-secondary);
          font-size: 1.1rem;
        }

        .loading-state, .error-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          min-height: 400px;
          gap: var(--spacing-md);
          color: var(--text-secondary);
        }

        .spinner {
          width: 40px;
          height: 40px;
          border: 3px solid var(--bg-tertiary);
          border-top-color: var(--accent-primary);
          border-radius: 50%;
          animation: spin 1s linear infinite;
        }

        .agents-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
          gap: var(--spacing-xl);
        }

        :global(.agent-card-link) {
            text-decoration: none;
            color: inherit;
            display: block;
            height: 100%;
        }

        .agent-card {
          padding: var(--spacing-xl);
          display: flex;
          flex-direction: column;
          gap: var(--spacing-md);
          transition: transform var(--transition-base);
          height: 100%;
        }

        .agent-card:hover {
          transform: translateY(-5px);
        }

        .agent-header {
          display: flex;
          align-items: center;
          gap: var(--spacing-md);
        }

        .agent-icon {
          width: 48px;
          height: 48px;
          border-radius: var(--radius-md);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 1.5rem;
          background: var(--bg-tertiary);
        }
        
        .agent-icon.supervisor { background: linear-gradient(135deg, #6366f1, #818cf8); color: white; }
        .agent-icon.research { background: linear-gradient(135deg, #f59e0b, #fbbf24); color: white; }
        .agent-icon.code { background: linear-gradient(135deg, #10b981, #34d399); color: white; }
        .agent-icon.content { background: linear-gradient(135deg, #ec4899, #f472b6); color: white; }

        .agent-info h2 {
          font-size: 1.25rem;
          margin: 0;
        }

        .agent-status {
          font-size: 0.75rem;
          color: var(--success);
          display: flex;
          align-items: center;
          gap: 4px;
        }

        .agent-status::before {
          content: '';
          display: block;
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: currentColor;
          box-shadow: 0 0 5px currentColor;
        }

        .agent-desc {
          color: var(--text-secondary);
          line-height: 1.5;
          flex: 1;
        }

        .agent-capabilities {
          display: flex;
          flex-wrap: wrap;
          gap: var(--spacing-xs);
          margin-top: auto;
        }

        .tag {
          font-size: 0.75rem;
          padding: 2px 8px;
          background: var(--bg-tertiary);
          border-radius: var(--radius-full);
          color: var(--text-secondary);
        }

        @keyframes spin {
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}

function getAgentIcon(name: string) {
  switch (name) {
    case 'supervisor': return '🧠';
    case 'research': return '🔍';
    case 'code': return '💻';
    case 'content': return '✍️';
    case 'memory': return '💾';
    default: return '🤖';
  }
}
