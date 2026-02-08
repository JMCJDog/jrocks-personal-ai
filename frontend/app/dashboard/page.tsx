'use client';

import React, { useEffect, useState } from 'react';
import { api } from '@/lib/api';
import { MetricCard, TableCard, StatusBadge } from '@/components/DashboardCards';

export default function DashboardPage() {
    const [health, setHealth] = useState<any>(null);
    const [usage, setUsage] = useState<any>(null);
    const [freshness, setFreshness] = useState<any[]>([]);
    const [codeStats, setCodeStats] = useState<any>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        async function fetchData() {
            try {
                const [h, u, f, c] = await Promise.all([
                    api.getAnalyticsHealth().catch(() => null),
                    api.getAnalyticsUsage().catch(() => null),
                    api.getAnalyticsFreshness().catch(() => []),
                    api.getAnalyticsCodeStats().catch(() => null)
                ]);

                setHealth(h);
                setUsage(u);
                setFreshness(f || []);
                setCodeStats(c);
            } catch (error) {
                console.error("Error fetching dashboard data:", error);
            } finally {
                setLoading(false);
            }
        }

        fetchData();
    }, []);

    if (loading) {
        return (
            <div className="flex items-center justify-center min-h-screen bg-gray-50">
                <div className="flex flex-col items-center gap-4">
                    <div className="w-12 h-12 border-4 border-indigo-600 border-t-transparent rounded-full animate-spin"></div>
                    <div className="text-gray-500 font-medium">Loading System Metrics...</div>
                </div>
            </div>
        );
    }

    // Calculate some derived metrics
    const uptimeHours = health?.uptime ? Math.floor(health.uptime / 3600) : 0;
    const uptimeDays = Math.floor(uptimeHours / 24);
    const uptimeRestHours = uptimeHours % 24;

    const costTrend = usage?.estimated_cost > 10 ? 'up' : 'neutral'; // Mock trend logic

    return (
        <div className="min-h-screen bg-gray-50/50 p-6 md:p-10 space-y-10">

            {/* Header */}
            <header className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h1 className="text-3xl font-bold text-gray-900 tracking-tight">System Monitor</h1>
                    <p className="text-gray-500 mt-1">Real-time telemetry for JRock's Personal AI Ecosystem</p>
                </div>
                <div className="flex items-center gap-3">
                    <div className="flex items-center gap-2 px-3 py-1.5 bg-white rounded-full border border-gray-200 shadow-sm">
                        <div className={`w-2.5 h-2.5 rounded-full ${health?.status === 'healthy' ? 'bg-green-500 animate-pulse' : 'bg-red-500'}`}></div>
                        <span className="text-sm font-medium text-gray-700">
                            {health?.status === 'healthy' ? 'System Operational' : 'System Issues'}
                        </span>
                    </div>
                    <button
                        onClick={() => window.location.reload()}
                        className="p-2 text-gray-500 hover:text-indigo-600 hover:bg-white rounded-full transition-all"
                        title="Refresh Data"
                    >
                        <span className="text-xl">↻</span>
                    </button>
                </div>
            </header>

            {/* Grid Layout */}
            <div className="grid grid-cols-1 xl:grid-cols-12 gap-6">

                {/* LEFT COLUMN - Main Metrics */}
                <div className="xl:col-span-8 space-y-6">

                    {/* Section: Infrastructure */}
                    <section>
                        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 px-1">Infrastructure Health</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <MetricCard
                                title="CPU Usage"
                                value={`${health?.cpu_percent || 0}%`}
                                status={health?.cpu_percent > 80 ? 'warning' : 'healthy'}
                                icon={<span>🖥️</span>}
                                trend={health?.cpu_percent > 50 ? 'up' : 'down'}
                                trendValue="2%"
                            />
                            <MetricCard
                                title="Memory"
                                value={`${health?.memory_percent || 0}%`}
                                status={health?.memory_percent > 85 ? 'warning' : 'healthy'}
                                icon={<span>🧠</span>}
                                subtitle={`${100 - (health?.memory_percent || 0)}% Free`}
                            />
                            <MetricCard
                                title="Database"
                                value={health?.database || 'Unknown'}
                                status={health?.database === 'connected' ? 'healthy' : 'critical'}
                                icon={<span>💾</span>}
                            />
                            <MetricCard
                                title="MCP Server"
                                value={health?.mcp_server || 'Unknown'}
                                status={health?.mcp_server === 'operational' ? 'healthy' : 'warning'}
                                icon={<span>🔌</span>}
                            />
                        </div>
                    </section>

                    {/* Section: Intelligence Cost & Usage */}
                    <section>
                        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 px-1 mt-8">Intelligence & Costs</h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <MetricCard
                                title="Est. Cost (MTD)"
                                value={`$${usage?.estimated_cost?.toFixed(2) || '0.00'}`}
                                icon={<span>💳</span>}
                                trend={costTrend}
                                trendValue="vs last month"
                                className="bg-indigo-50 border-indigo-100"
                            />
                            <MetricCard
                                title="Daily Tokens"
                                value={usage?.daily_tokens?.toLocaleString() || 0}
                                icon={<span>📝</span>}
                            />
                            <MetricCard
                                title="Total Tokens (MTD)"
                                value={usage?.monthly_tokens?.toLocaleString() || 0}
                                icon={<span>📚</span>}
                            />
                        </div>
                    </section>

                    {/* Table: Model Usage */}
                    {usage?.top_models && (
                        <section className="mt-8">
                            <TableCard
                                title="Model Utilization"
                                icon={<span>🤖</span>}
                                headers={['Model Name', 'Request Volume', 'Share']}
                                rows={usage.top_models.map((m: any) => [
                                    <span key={m.name} className="font-mono text-xs">{m.name}</span>,
                                    m.count.toLocaleString(),
                                    <div className="w-24 bg-gray-100 rounded-full h-2 overflow-hidden" key={`${m.name}-bar`}>
                                        <div
                                            className="bg-indigo-500 h-2 rounded-full"
                                            style={{ width: `${Math.min((m.count / (usage?.monthly_tokens / 10)) * 100, 100)}%` }}
                                        ></div>
                                    </div>
                                ])}
                            />
                        </section>
                    )}

                </div>

                {/* RIGHT COLUMN - Status & Code */}
                <div className="xl:col-span-4 space-y-6">

                    {/* Uptime Card */}
                    <div className="bg-gradient-to-br from-gray-900 to-gray-800 rounded-xl p-6 text-white shadow-lg">
                        <div className="flex items-center gap-3 mb-4">
                            <span className="text-2xl">⏱️</span>
                            <h3 className="font-medium text-gray-300 uppercase tracking-wide text-sm">System Uptime</h3>
                        </div>
                        <div className="text-4xl font-bold mb-2">
                            {uptimeDays}d <span className="text-gray-400">{uptimeRestHours}h</span>
                        </div>
                        <div className="text-sm text-gray-400">
                            Running smoothly. No interruptions detected.
                        </div>
                    </div>

                    {/* Section: Data Freshness */}
                    <section>
                        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 px-1">Pipeline Status</h2>
                        <TableCard
                            title="Data Freshness"
                            headers={['Source', 'Status', 'Age']}
                            rows={freshness.map((f: any) => [
                                f.name,
                                <StatusBadge key={f.name} status={f.status} />,
                                <span key={`${f.name}-age`} className="text-xs text-gray-500">
                                    {f.days_ago !== null ? `${f.days_ago}d ago` : 'N/A'}
                                </span>
                            ])}
                        />
                    </section>

                    {/* Section: Code Stats */}
                    <section>
                        <h2 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-4 px-1">Codebase Health</h2>
                        <div className="bg-white rounded-xl border border-gray-100 p-5 shadow-sm space-y-4">

                            <div className="flex justify-between items-center pb-4 border-b border-gray-50">
                                <span className="text-gray-500">Lines of Code</span>
                                <span className="font-bold text-lg">{codeStats?.lines_of_code?.toLocaleString() || 0}</span>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                                <div>
                                    <span className="text-xs text-gray-400 block mb-1">Python Files</span>
                                    <span className="font-semibold">{codeStats?.python_files || 0}</span>
                                </div>
                                <div>
                                    <span className="text-xs text-gray-400 block mb-1">TypeScript Files</span>
                                    <span className="font-semibold">{codeStats?.typescript_files || 0}</span>
                                </div>
                            </div>

                            <div className="pt-2">
                                <div className="flex justify-between items-center mb-1">
                                    <span className="text-sm font-medium text-gray-600">Durability Score</span>
                                    <span className="text-sm font-bold text-green-600">{codeStats?.durability_score || 0}</span>
                                </div>
                                <div className="w-full bg-gray-100 rounded-full h-2">
                                    <div
                                        className="bg-green-500 h-2 rounded-full"
                                        style={{ width: `${codeStats?.durability_score || 0}%` }}
                                    ></div>
                                </div>
                            </div>

                        </div>
                    </section>

                </div>
            </div>
        </div>
    );
}
