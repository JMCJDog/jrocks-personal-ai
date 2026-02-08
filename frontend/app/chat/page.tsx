'use client';

import { useState, useRef, useEffect } from 'react';
import { api, ChatMessage } from '@/lib/api';

export default function ChatPage() {
    const [messages, setMessages] = useState<ChatMessage[]>([]);
    const [input, setInput] = useState('');
    const [loading, setLoading] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    };

    useEffect(() => {
        scrollToBottom();
    }, [messages]);

    const handleSend = async () => {
        if (!input.trim() || loading) return;

        const userMessage: ChatMessage = { role: 'user', content: input };
        setMessages(prev => [...prev, userMessage]);
        setInput('');
        setLoading(true);

        try {
            const response = await api.chatWithAgent(input);
            const assistantMessage: ChatMessage = {
                role: 'assistant',
                content: response.response,
            };
            setMessages(prev => [...prev, assistantMessage]);
        } catch (error) {
            const errorMessage: ChatMessage = {
                role: 'assistant',
                content: 'Sorry, I encountered an error. Please try again.',
            };
            setMessages(prev => [...prev, errorMessage]);
        } finally {
            setLoading(false);
        }
    };

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    return (
        <div className="chat-page">
            <div className="messages-container">
                {messages.length === 0 ? (
                    <div className="empty-state">
                        <span className="empty-icon">💬</span>
                        <h3>Start a conversation</h3>
                        <p>Ask me anything about your data, or just have a chat!</p>
                    </div>
                ) : (
                    <div className="messages">
                        {messages.map((msg, idx) => (
                            <div
                                key={idx}
                                className={`message ${msg.role}`}
                            >
                                <div className="message-avatar">
                                    {msg.role === 'user' ? 'You' : '🧠'}
                                </div>
                                <div className="message-content">
                                    {msg.content}
                                </div>
                            </div>
                        ))}
                        {loading && (
                            <div className="message assistant">
                                <div className="message-avatar">🧠</div>
                                <div className="message-content typing">
                                    <span className="dot" />
                                    <span className="dot" />
                                    <span className="dot" />
                                </div>
                            </div>
                        )}
                        <div ref={messagesEndRef} />
                    </div>
                )}
            </div>

            <div className="input-area glass-card">
                <textarea
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyPress={handleKeyPress}
                    placeholder="Type your message..."
                    className="input chat-input"
                    rows={1}
                    disabled={loading}
                />
                <button
                    onClick={handleSend}
                    disabled={loading || !input.trim()}
                    className="btn btn-primary send-btn"
                >
                    {loading ? '...' : 'Send'}
                </button>
            </div>

            <style jsx>{`
        .chat-page {
          display: flex;
          flex-direction: column;
          height: calc(100vh - 140px);
          max-width: 900px;
          margin: 0 auto;
        }

        .messages-container {
          flex: 1;
          overflow-y: auto;
          padding: var(--spacing-lg) 0;
        }

        .empty-state {
          display: flex;
          flex-direction: column;
          align-items: center;
          justify-content: center;
          height: 100%;
          text-align: center;
          color: var(--text-secondary);
        }

        .empty-icon {
          font-size: 4rem;
          margin-bottom: var(--spacing-lg);
        }

        .empty-state h3 {
          margin-bottom: var(--spacing-sm);
        }

        .messages {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-lg);
        }

        .message {
          display: flex;
          gap: var(--spacing-md);
          animation: fadeIn var(--transition-base) forwards;
        }

        .message.user {
          flex-direction: row-reverse;
        }

        .message-avatar {
          width: 40px;
          height: 40px;
          border-radius: var(--radius-full);
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 0.875rem;
          font-weight: 600;
          flex-shrink: 0;
        }

        .message.user .message-avatar {
          background: var(--accent-gradient);
          color: white;
        }

        .message.assistant .message-avatar {
          background: var(--bg-tertiary);
          font-size: 1.25rem;
        }

        .message-content {
          max-width: 70%;
          padding: var(--spacing-md) var(--spacing-lg);
          border-radius: var(--radius-lg);
          line-height: 1.5;
        }

        .message.user .message-content {
          background: var(--accent-primary);
          color: white;
          border-bottom-right-radius: var(--spacing-xs);
        }

        .message.assistant .message-content {
          background: var(--bg-tertiary);
          color: var(--text-primary);
          border-bottom-left-radius: var(--spacing-xs);
        }

        .typing {
          display: flex;
          gap: 4px;
          padding: var(--spacing-md) var(--spacing-lg);
        }

        .typing .dot {
          width: 8px;
          height: 8px;
          background: var(--text-muted);
          border-radius: 50%;
          animation: pulse 1.4s infinite ease-in-out both;
        }

        .typing .dot:nth-child(1) { animation-delay: -0.32s; }
        .typing .dot:nth-child(2) { animation-delay: -0.16s; }

        .input-area {
          display: flex;
          gap: var(--spacing-md);
          padding: var(--spacing-md);
          margin-top: var(--spacing-md);
        }

        .chat-input {
          flex: 1;
          resize: none;
          min-height: 48px;
          max-height: 120px;
        }

        .send-btn {
          min-width: 80px;
        }
      `}</style>
        </div>
    );
}
