/**
 * API Client for JRock's Personal AI Backend
 * 
 * Provides typed methods for interacting with the FastAPI backend.
 * All requests go through Next.js rewrites to http://localhost:8000.
 */

const API_BASE = '/api';

interface ChatMessage {
    role: 'user' | 'assistant';
    content: string;
}

interface ChatResponse {
    response: string;
    conversation_id?: string;
}

interface AgentResponse {
    agent: string;
    response: string;
    execution_time: number;
}

interface WebhookConfig {
    id: string;
    name: string;
    url: string;
    events: string[];
    enabled: boolean;
    created_at: string;
}

interface HealthResponse {
    status: string;
}

class ApiClient {
    private async request<T>(
        endpoint: string,
        options: RequestInit = {}
    ): Promise<T> {
        const url = `${API_BASE}${endpoint}`;

        const response = await fetch(url, {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers,
            },
            ...options,
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({ detail: 'Request failed' }));
            throw new Error(error.detail || `Request failed: ${response.status}`);
        }

        return response.json();
    }

    // Health
    async getHealth(): Promise<HealthResponse> {
        return this.request<HealthResponse>('/health');
    }

    // Chat
    async sendChatMessage(message: string, conversationId?: string): Promise<ChatResponse> {
        return this.request<ChatResponse>('/chat/', {
            method: 'POST',
            body: JSON.stringify({ message, conversation_id: conversationId }),
        });
    }

    // Agents
    async chatWithAgent(message: string, agentType: string = 'general'): Promise<AgentResponse> {
        return this.request<AgentResponse>('/agents/chat', {
            method: 'POST',
            body: JSON.stringify({ message, agent_type: agentType }),
        });
    }

    async researchWithAgent(query: string): Promise<AgentResponse> {
        return this.request<AgentResponse>('/agents/research', {
            method: 'POST',
            body: JSON.stringify({ query }),
        });
    }

    // Webhooks
    async listWebhooks(): Promise<{ webhooks: WebhookConfig[]; total: number }> {
        return this.request('/webhooks/');
    }

    async registerWebhook(
        name: string,
        url: string,
        events: string[] = [],
        secret?: string
    ): Promise<WebhookConfig> {
        return this.request<WebhookConfig>('/webhooks/register', {
            method: 'POST',
            body: JSON.stringify({ name, url, events, secret }),
        });
    }

    async deleteWebhook(webhookId: string): Promise<void> {
        await this.request(`/webhooks/${webhookId}`, { method: 'DELETE' });
    }

    async testWebhook(webhookId: string): Promise<{ status: string; message: string }> {
        return this.request(`/webhooks/test/${webhookId}`, { method: 'POST' });
    }

    // Ingest
    async uploadFile(file: File): Promise<{ status: string; file_id: string }> {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${API_BASE}/ingest/`, {
            method: 'POST',
            body: formData,
        });

        if (!response.ok) {
            throw new Error('Upload failed');
        }

        return response.json();
    }
}

export const api = new ApiClient();
export type { ChatMessage, ChatResponse, AgentResponse, WebhookConfig, HealthResponse };
