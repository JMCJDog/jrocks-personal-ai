import React from 'react';

export type StatusType = 'healthy' | 'warning' | 'critical' | 'neutral' | 'fresh' | 'stale' | 'outdated' | 'missing';

interface StatusBadgeProps {
    status: StatusType | string;
    label?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label }) => {
    const s = status.toLowerCase() as StatusType;

    const styles: Record<string, string> = {
        healthy: 'bg-green-100 text-green-700 border-green-200',
        fresh: 'bg-green-100 text-green-700 border-green-200',
        warning: 'bg-yellow-100 text-yellow-700 border-yellow-200',
        stale: 'bg-yellow-100 text-yellow-700 border-yellow-200',
        critical: 'bg-red-100 text-red-700 border-red-200',
        outdated: 'bg-red-100 text-red-700 border-red-200',
        missing: 'bg-gray-100 text-gray-500 border-gray-200',
        neutral: 'bg-blue-50 text-blue-700 border-blue-200',
    };

    const style = styles[s] || styles.neutral;
    const displayLabel = label || status;

    return (
        <span className={`px-2 py-0.5 rounded-full text-xs font-semibold border ${style}`}>
            {displayLabel.toUpperCase()}
        </span>
    );
};

interface MetricCardProps {
    title: string;
    value: string | number;
    subtitle?: string;
    status?: StatusType;
    icon?: React.ReactNode;
    trend?: 'up' | 'down' | 'neutral';
    trendValue?: string;
    className?: string; // Allow custom classes
}

export const MetricCard: React.FC<MetricCardProps> = ({
    title,
    value,
    subtitle,
    status,
    icon,
    trend,
    trendValue,
    className = ''
}) => {
    const statusBorders = {
        healthy: 'border-l-4 border-l-green-500',
        warning: 'border-l-4 border-l-yellow-500',
        critical: 'border-l-4 border-l-red-500',
        neutral: '',
        fresh: 'border-l-4 border-l-green-500',
        stale: 'border-l-4 border-l-yellow-500',
        outdated: 'border-l-4 border-l-red-500',
        missing: 'border-l-4 border-l-gray-300'
    };

    const borderClass = status ? statusBorders[status as StatusType] || '' : '';

    return (
        <div className={`bg-white p-5 rounded-xl border border-gray-100 shadow-sm hover:shadow-md transition-shadow duration-200 ${borderClass} ${className}`}>
            <div className="flex justify-between items-start mb-2">
                <h3 className="text-sm font-medium text-gray-500 uppercase tracking-wide">{title}</h3>
                {icon && <div className="text-gray-400 p-1.5 bg-gray-50 rounded-lg">{icon}</div>}
            </div>

            <div className="flex items-end gap-2 mb-1">
                <div className="text-2xl font-bold text-gray-900">{value}</div>
                {trend && (
                    <div className={`flex items-center text-xs font-medium mb-1 ${trend === 'up' ? 'text-green-600' :
                            trend === 'down' ? 'text-red-600' : 'text-gray-500'
                        }`}>
                        {trend === 'up' ? '↑' : trend === 'down' ? '↓' : '•'} {trendValue}
                    </div>
                )}
            </div>

            {subtitle && <div className="text-xs text-gray-400 mt-1">{subtitle}</div>}
        </div>
    );
};

interface TableCardProps {
    title: string;
    headers: string[];
    rows: (string | number | React.ReactNode)[][];
    icon?: React.ReactNode;
}

export const TableCard: React.FC<TableCardProps> = ({ title, headers, rows, icon }) => {
    return (
        <div className="bg-white rounded-xl border border-gray-100 shadow-sm overflow-hidden flex flex-col h-full">
            <div className="px-6 py-4 border-b border-gray-50 bg-white flex items-center gap-2">
                {icon && <span className="text-gray-400">{icon}</span>}
                <h3 className="font-semibold text-gray-800">{title}</h3>
            </div>
            <div className="overflow-x-auto flex-1">
                <table className="min-w-full divide-y divide-gray-50">
                    <thead className="bg-gray-50/50">
                        <tr>
                            {headers.map((header, idx) => (
                                <th key={idx} className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                                    {header}
                                </th>
                            ))}
                        </tr>
                    </thead>
                    <tbody className="bg-white divide-y divide-gray-50">
                        {rows.map((row, rowIndex) => (
                            <tr key={rowIndex} className="hover:bg-gray-50/50 transition-colors">
                                {row.map((cell, cellIndex) => (
                                    <td key={cellIndex} className="px-6 py-3 whitespace-nowrap text-sm text-gray-600">
                                        {cell}
                                    </td>
                                ))}
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};
