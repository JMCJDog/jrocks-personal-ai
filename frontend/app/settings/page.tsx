'use client';

import { useState, useEffect } from 'react';
import { api, AppSettings } from '@/lib/api';

export default function SettingsPage() {
    const [settings, setSettings] = useState<AppSettings | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);
    const [message, setMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

    useEffect(() => {
        loadSettings();
    }, []);

    const loadSettings = async () => {
        try {
            const data = await api.getSettings();
            setSettings(data);
        } catch (error) {
            console.error('Failed to load settings:', error);
            setMessage({ text: 'Failed to load settings', type: 'error' });
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        if (!settings) return;
        setSaving(true);
        setMessage(null);
        try {
            await api.updateSettings(settings);
            setMessage({ text: 'Settings saved successfully!', type: 'success' });
        } catch (error) {
            console.error('Failed to save settings:', error);
            setMessage({ text: 'Failed to save settings', type: 'error' });
        } finally {
            setSaving(false);
        }
    };

    const handleChange = (section: keyof AppSettings, field: string, value: any) => {
        if (!settings) return;
        setSettings({
            ...settings,
            [section]: typeof settings[section] === 'object' && settings[section] !== null
                ? { ...settings[section], [field]: value }
                : value
        });
    };

    const handleTraitChange = (index: number, field: string, value: any) => {
        if (!settings) return;
        const newTraits = [...settings.persona_traits];
        newTraits[index] = { ...newTraits[index], [field]: value };
        setSettings({ ...settings, persona_traits: newTraits });
    };

    if (loading) return <div className="p-8">Loading settings...</div>;
    if (!settings) return <div className="p-8">Error loading settings</div>;

    return (
        <div className="settings-page">
            <header className="page-header">
                <h1>Settings</h1>
                <p>Configure JRock's personality and intelligence.</p>
            </header>

            {message && (
                <div className={`message-banner ${message.type}`}>
                    {message.text}
                </div>
            )}

            <div className="settings-grid">
                {/* Persona Section */}
                <section className="card">
                    <h2>Persona Identity</h2>
                    <div className="form-group">
                        <label>Name</label>
                        <input
                            type="text"
                            value={settings.persona_name}
                            onChange={(e) => setSettings({ ...settings, persona_name: e.target.value })}
                        />
                    </div>
                </section>

                {/* Model Params Section */}
                <section className="card">
                    <h2>LLM Configuration</h2>
                    <div className="form-group">
                        <label>Provider</label>
                        <select
                            value={settings.default_model.provider}
                            onChange={(e) => handleChange('default_model', 'provider', e.target.value)}
                        >
                            <option value="ollama">Ollama (Local)</option>
                            <option value="gemini">Google Gemini</option>
                            <option value="claude">Anthropic Claude</option>
                            <option value="openai">OpenAI GPT-4</option>
                        </select>
                    </div>
                    <div className="form-group">
                        <label>Model Name</label>
                        <input
                            type="text"
                            value={settings.default_model.model_name}
                            onChange={(e) => handleChange('default_model', 'model_name', e.target.value)}
                        />
                    </div>
                    <div className="form-group">
                        <label>Temperature ({settings.default_model.temperature})</label>
                        <input
                            type="range"
                            min="0"
                            max="1"
                            step="0.1"
                            value={settings.default_model.temperature}
                            onChange={(e) => handleChange('default_model', 'temperature', parseFloat(e.target.value))}
                        />
                    </div>
                </section>

                {/* Traits Section */}
                <section className="card full-width">
                    <h2>Personality Traits</h2>
                    <div className="traits-list">
                        {settings.persona_traits.map((trait, idx) => (
                            <div key={idx} className="trait-item">
                                <div className="trait-header">
                                    <input
                                        type="text"
                                        className="trait-name"
                                        value={trait.name}
                                        onChange={(e) => handleTraitChange(idx, 'name', e.target.value)}
                                        placeholder="Trait Name"
                                    />
                                    <input
                                        type="number"
                                        className="trait-weight"
                                        min="0.1"
                                        max="3.0"
                                        step="0.1"
                                        value={trait.weight}
                                        onChange={(e) => handleTraitChange(idx, 'weight', parseFloat(e.target.value))}
                                        title="Weight"
                                    />
                                </div>
                                <textarea
                                    className="trait-desc"
                                    value={trait.description}
                                    onChange={(e) => handleTraitChange(idx, 'description', e.target.value)}
                                    placeholder="Description"
                                    rows={2}
                                />
                            </div>
                        ))}
                    </div>
                </section>

                {/* Writing Style Section */}
                <section className="card">
                    <h2>Writing Style</h2>
                    <div className="writing-grid">
                        <div className="form-group">
                            <label>Tone</label>
                            <input
                                type="text"
                                list="tones"
                                value={settings.writing_style.tone}
                                onChange={(e) => handleChange('writing_style', 'tone', e.target.value)}
                            />
                            <datalist id="tones">
                                <option value="conversational" />
                                <option value="sarcastic" />
                                <option value="professional" />
                                <option value="friendly" />
                            </datalist>
                        </div>
                        <div className="form-group">
                            <label>Formality</label>
                            <select
                                value={settings.writing_style.formality}
                                onChange={(e) => handleChange('writing_style', 'formality', e.target.value)}
                            >
                                <option value="casual">Casual</option>
                                <option value="informal">Informal</option>
                                <option value="neutral">Neutral</option>
                                <option value="formal">Formal</option>
                            </select>
                        </div>
                        <div className="form-group">
                            <label>Humor Level ({settings.writing_style.humor_level})</label>
                            <input
                                type="range"
                                min="0"
                                max="1"
                                step="0.1"
                                value={settings.writing_style.humor_level}
                                onChange={(e) => handleChange('writing_style', 'humor_level', parseFloat(e.target.value))}
                            />
                        </div>
                        <div className="form-group">
                            <label>Verbosity</label>
                            <select
                                value={settings.writing_style.verbosity}
                                onChange={(e) => handleChange('writing_style', 'verbosity', e.target.value)}
                            >
                                <option value="concise">Concise</option>
                                <option value="moderate">Moderate</option>
                                <option value="verbose">Verbose</option>
                            </select>
                        </div>
                        <div className="form-group checkbox">
                            <label>
                                <input
                                    type="checkbox"
                                    checked={settings.writing_style.emoji_usage}
                                    onChange={(e) => handleChange('writing_style', 'emoji_usage', e.target.checked)}
                                />
                                Use Emojis 🚀
                            </label>
                        </div>
                    </div>
                </section>

                {/* API Keys Section */}
                <section className="card full-width">
                    <h2>API Keys (Optional)</h2>
                    <div className="api-keys-grid">
                        <div className="form-group">
                            <label>Google API Key</label>
                            <input
                                type="password"
                                placeholder="env: GOOGLE_API_KEY"
                                value={settings.google_api_key || ''}
                                onChange={(e) => setSettings({ ...settings, google_api_key: e.target.value })}
                            />
                        </div>
                        <div className="form-group">
                            <label>Anthropic API Key</label>
                            <input
                                type="password"
                                placeholder="env: ANTHROPIC_API_KEY"
                                value={settings.anthropic_api_key || ''}
                                onChange={(e) => setSettings({ ...settings, anthropic_api_key: e.target.value })}
                            />
                        </div>
                    </div>
                </section>
            </div>

            <div className="actions">
                <button
                    onClick={handleSave}
                    disabled={saving}
                    className="btn btn-primary save-btn"
                >
                    {saving ? 'Saving...' : 'Save Settings'}
                </button>
            </div>

            <style jsx>{`
                .settings-page {
                    max-width: 1000px;
                    margin: 0 auto;
                    padding: var(--spacing-lg);
                }
                
                .page-header {
                    margin-bottom: var(--spacing-xl);
                }

                .settings-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
                    gap: var(--spacing-lg);
                    margin-bottom: var(--spacing-xl);
                }

                .card {
                    background: var(--bg-secondary);
                    padding: var(--spacing-lg);
                    border-radius: var(--radius-lg);
                    border: 1px solid var(--border-subtle);
                }

                .full-width {
                    grid-column: 1 / -1;
                }

                h2 {
                    font-size: 1.25rem;
                    margin-bottom: var(--spacing-md);
                    border-bottom: 1px solid var(--border-subtle);
                    padding-bottom: var(--spacing-sm);
                }

                .form-group {
                    margin-bottom: var(--spacing-md);
                }

                .form-group label {
                    display: block;
                    margin-bottom: var(--spacing-xs);
                    font-weight: 500;
                    color: var(--text-secondary);
                }

                input[type="text"],
                input[type="password"],
                input[type="number"],
                select,
                textarea {
                    width: 100%;
                    padding: 8px 12px;
                    background: var(--bg-tertiary);
                    border: 1px solid var(--border-subtle);
                    border-radius: var(--radius-md);
                    color: var(--text-primary);
                }

                .traits-list {
                    display: grid;
                    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
                    gap: var(--spacing-md);
                }

                .trait-item {
                    background: var(--bg-tertiary);
                    padding: var(--spacing-md);
                    border-radius: var(--radius-md);
                }

                .trait-header {
                    display: flex;
                    gap: var(--spacing-sm);
                    margin-bottom: var(--spacing-sm);
                }

                .trait-name {
                    flex: 1;
                    font-weight: bold;
                }

                .trait-weight {
                    width: 60px;
                }

                .trait-desc {
                    width: 100%;
                    resize: vertical;
                    font-size: 0.9em;
                }

                .api-keys-grid,
                .writing-grid {
                    display: grid;
                    grid-template-columns: 1fr 1fr;
                    gap: var(--spacing-lg);
                }
                
                .form-group.checkbox {
                    display: flex;
                    align-items: flex-end;
                    padding-bottom: 10px;
                }
                
                .form-group.checkbox label {
                    display: flex;
                    align-items: center;
                    gap: 8px;
                    cursor: pointer;
                    margin: 0;
                }
                
                .form-group.checkbox input {
                    width: auto;
                    margin: 0;
                }

                .actions {
                    position: sticky;
                    bottom: var(--spacing-lg);
                    display: flex;
                    justify-content: flex-end;
                    padding-top: var(--spacing-lg);
                }

                .save-btn {
                    padding: 12px 32px;
                    font-size: 1.1rem;
                    box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
                }

                .message-banner {
                    padding: var(--spacing-md);
                    border-radius: var(--radius-md);
                    margin-bottom: var(--spacing-lg);
                    text-align: center;
                    font-weight: 600;
                }

                .message-banner.success {
                    background: rgba(16, 185, 129, 0.1);
                    color: #10b981;
                    border: 1px solid rgba(16, 185, 129, 0.2);
                }

                .message-banner.error {
                    background: rgba(239, 68, 68, 0.1);
                    color: #ef4444;
                    border: 1px solid rgba(239, 68, 68, 0.2);
                }
            `}</style>
        </div>
    );
}
