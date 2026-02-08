'use client';

import { useState, useEffect } from 'react';
import { api, WebhookConfig } from '@/lib/api';

export default function WebhooksPage() {
    const [webhooks, setWebhooks] = useState<WebhookConfig[]>([]);
    const [loading, setLoading] = useState(true);
    const [showForm, setShowForm] = useState(false);
    const [formData, setFormData] = useState({ name: '', url: '', events: '' });

    const loadWebhooks = async () => {
        try {
            const response = await api.listWebhooks();
            setWebhooks(response.webhooks);
        } catch (error) {
            console.error('Failed to load webhooks:', error);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        loadWebhooks();
    }, []);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            const events = formData.events
                .split(',')
                .map(e => e.trim())
                .filter(Boolean);

            await api.registerWebhook(formData.name, formData.url, events);
            setFormData({ name: '', url: '', events: '' });
            setShowForm(false);
            loadWebhooks();
        } catch (error) {
            console.error('Failed to register webhook:', error);
        }
    };

    const handleDelete = async (webhookId: string) => {
        if (!confirm('Are you sure you want to delete this webhook?')) return;
        try {
            await api.deleteWebhook(webhookId);
            loadWebhooks();
        } catch (error) {
            console.error('Failed to delete webhook:', error);
        }
    };

    const handleTest = async (webhookId: string) => {
        try {
            const result = await api.testWebhook(webhookId);
            alert(result.message);
        } catch (error) {
            alert('Test failed: ' + (error as Error).message);
        }
    };

    return (
        <div className="webhooks-page animate-fade-in">
            <div className="page-header">
                <div>
                    <h1>Webhooks</h1>
                    <p>Configure event notifications to external services</p>
                </div>
                <button
                    className="btn btn-primary"
                    onClick={() => setShowForm(!showForm)}
                >
                    {showForm ? 'Cancel' : '+ Add Webhook'}
                </button>
            </div>

            {showForm && (
                <form className="webhook-form glass-card" onSubmit={handleSubmit}>
                    <div className="form-group">
                        <label>Name</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="My Webhook"
                            value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>URL</label>
                        <input
                            type="url"
                            className="input"
                            placeholder="https://example.com/webhook"
                            value={formData.url}
                            onChange={(e) => setFormData({ ...formData, url: e.target.value })}
                            required
                        />
                    </div>
                    <div className="form-group">
                        <label>Events (comma-separated, leave empty for all)</label>
                        <input
                            type="text"
                            className="input"
                            placeholder="agent.completed, chat.message.sent"
                            value={formData.events}
                            onChange={(e) => setFormData({ ...formData, events: e.target.value })}
                        />
                    </div>
                    <button type="submit" className="btn btn-primary">
                        Register Webhook
                    </button>
                </form>
            )}

            {loading ? (
                <div className="loading">Loading webhooks...</div>
            ) : webhooks.length === 0 ? (
                <div className="empty-state glass-card">
                    <span className="empty-icon">🔔</span>
                    <h3>No webhooks configured</h3>
                    <p>Add a webhook to receive event notifications</p>
                </div>
            ) : (
                <div className="webhooks-list">
                    {webhooks.map((webhook) => (
                        <div key={webhook.id} className="webhook-card glass-card">
                            <div className="webhook-header">
                                <div className="webhook-info">
                                    <h3>{webhook.name}</h3>
                                    <code className="webhook-url">{webhook.url}</code>
                                </div>
                                <span className={`badge ${webhook.enabled ? 'badge-success' : 'badge-error'}`}>
                                    {webhook.enabled ? 'Enabled' : 'Disabled'}
                                </span>
                            </div>

                            <div className="webhook-events">
                                {webhook.events.length > 0 ? (
                                    webhook.events.map((event) => (
                                        <span key={event} className="event-tag">{event}</span>
                                    ))
                                ) : (
                                    <span className="event-tag all">All Events</span>
                                )}
                            </div>

                            <div className="webhook-actions">
                                <button
                                    className="btn btn-secondary"
                                    onClick={() => handleTest(webhook.id)}
                                >
                                    Test
                                </button>
                                <button
                                    className="btn btn-secondary delete"
                                    onClick={() => handleDelete(webhook.id)}
                                >
                                    Delete
                                </button>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            <style jsx>{`
        .webhooks-page {
          max-width: 900px;
          margin: 0 auto;
        }

        .page-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: var(--spacing-xl);
        }

        .page-header h1 {
          margin-bottom: var(--spacing-xs);
        }

        .page-header p {
          color: var(--text-secondary);
        }

        .webhook-form {
          padding: var(--spacing-xl);
          margin-bottom: var(--spacing-xl);
          display: flex;
          flex-direction: column;
          gap: var(--spacing-lg);
        }

        .form-group {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-sm);
        }

        .form-group label {
          font-weight: 500;
          font-size: 0.875rem;
        }

        .loading {
          text-align: center;
          color: var(--text-muted);
          padding: var(--spacing-2xl);
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          padding: var(--spacing-2xl);
          text-align: center;
        }

        .empty-icon {
          font-size: 3rem;
          margin-bottom: var(--spacing-lg);
        }

        .webhooks-list {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-md);
        }

        .webhook-card {
          padding: var(--spacing-lg);
        }

        .webhook-header {
          display: flex;
          justify-content: space-between;
          align-items: flex-start;
          margin-bottom: var(--spacing-md);
        }

        .webhook-info h3 {
          margin-bottom: var(--spacing-xs);
          font-size: 1.125rem;
        }

        .webhook-url {
          font-size: 0.75rem;
          color: var(--text-muted);
          background: var(--bg-secondary);
          padding: var(--spacing-xs) var(--spacing-sm);
          border-radius: var(--radius-sm);
        }

        .webhook-events {
          display: flex;
          flex-wrap: wrap;
          gap: var(--spacing-xs);
          margin-bottom: var(--spacing-lg);
        }

        .event-tag {
          font-size: 0.75rem;
          padding: var(--spacing-xs) var(--spacing-sm);
          background: var(--bg-tertiary);
          border-radius: var(--radius-sm);
          color: var(--text-secondary);
        }

        .event-tag.all {
          background: rgba(99, 102, 241, 0.15);
          color: var(--accent-primary);
        }

        .webhook-actions {
          display: flex;
          gap: var(--spacing-sm);
        }

        .webhook-actions .delete {
          color: var(--error);
        }
      `}</style>
        </div>
    );
}
