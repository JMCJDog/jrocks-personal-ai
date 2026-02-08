'use client';

import dynamic from 'next/dynamic';

// Dynamically import map component with no SSR
const Heatmap = dynamic(() => import('@/components/analytics/Heatmap'), {
    ssr: false,
    loading: () => <div className="map-loading">Loading Map...</div>
});

export default function AnalyticsPage() {
    return (
        <div className="analytics-page">
            <header className="page-header">
                <h1 className="page-title">Visual Analytics</h1>
                <p className="page-subtitle">Geospatial visualization of your professional network.</p>
            </header>

            <div className="analytics-content">
                <div className="card map-card">
                    <div className="card-header">
                        <h2>Network Heatmap</h2>
                        <div className="card-actions">
                            <button className="btn btn-sm btn-ghost" onClick={() => window.location.reload()}>
                                Refresh
                            </button>
                        </div>
                    </div>
                    <div className="card-body">
                        <Heatmap />
                    </div>
                </div>

                <div className="stats-grid">
                    <div className="card stat-card">
                        <h3>Total Contacts</h3>
                        <p className="stat-value">Loading...</p>
                    </div>
                    <div className="card stat-card">
                        <h3>Regions</h3>
                        <p className="stat-value">Loading...</p>
                    </div>
                </div>
            </div>

            <style jsx>{`
        .analytics-page {
          padding: var(--spacing-lg);
          max-width: 1600px;
          margin: 0 auto;
        }

        .page-header {
          margin-bottom: var(--spacing-xl);
        }

        .page-title {
          font-size: 2rem;
          font-weight: 700;
          color: var(--text-primary);
          margin-bottom: var(--spacing-xs);
        }

        .page-subtitle {
          color: var(--text-secondary);
        }

        .analytics-content {
          display: flex;
          flex-direction: column;
          gap: var(--spacing-xl);
        }

        .map-card {
          min-height: 700px;
          display: flex;
          flex-direction: column;
        }

        .map-loading {
          height: 600px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--bg-secondary);
          color: var(--text-secondary);
          border-radius: var(--radius-lg);
        }

        .stats-grid {
          display: grid;
          grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
          gap: var(--spacing-lg);
        }

        .stat-card {
          padding: var(--spacing-lg);
        }

        .stat-value {
          font-size: 2rem;
          font-weight: 700;
          color: var(--accent-primary);
        }
      `}</style>
        </div>
    );
}
