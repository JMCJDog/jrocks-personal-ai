'use client';

import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, CircleMarker, Popup, Tooltip, useMap } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';

// Fix for default marker icon in Next.js
// though we are using CircleMarkers so might not need this, but good to have
const iconRetinaUrl = '/leaflet/marker-icon-2x.png';
const iconUrl = '/leaflet/marker-icon.png';
const shadowUrl = '/leaflet/marker-shadow.png';

// We need to fetch data from our API
interface ContactLocation {
    lat: number;
    lng: number;
    weight: number;
    name: string;
    address: string;
    email?: string;
    source?: 'contact' | 'history';
}

export default function Heatmap() {
    const [data, setData] = useState<ContactLocation[]>([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const res = await fetch('http://localhost:8000/api/analytics/heatmap');
                if (res.ok) {
                    const json = await res.json();
                    setData(json);
                }
            } catch (err) {
                console.error('Failed to fetch heatmap data', err);
            } finally {
                setLoading(false);
            }
        };

        fetchData();
    }, []);

    if (loading) return <div className="loading-map">Loading Contact Data...</div>;

    return (
        <div className="map-container">
            <MapContainer
                center={[39.8283, -98.5795]} // Center of US
                zoom={4}
                style={{ height: '100%', width: '100%' }}
                scrollWheelZoom={true}
            >
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />

                {data.map((point, idx) => {
                    const isHistory = point.source === 'history';
                    const color = isHistory ? '#00C2FF' : '#F5428D';
                    const radius = isHistory ? 4 + (point.weight || 0) : 8;
                    const opacity = isHistory ? 0.4 : 0.8;

                    return (
                        <CircleMarker
                            key={idx}
                            center={[point.lat, point.lng]}
                            pathOptions={{
                                color: color,
                                fillColor: color,
                                fillOpacity: opacity,
                                weight: 1
                            }}
                            radius={radius}
                        >
                            <Popup>
                                <div className="popup-content">
                                    <strong>{point.name}</strong><br />
                                    {point.address}<br />
                                    {point.email && <small>{point.email}</small>}
                                </div>
                            </Popup>
                            {!isHistory && <Tooltip>{point.name}</Tooltip>}
                        </CircleMarker>
                    );
                })}
            </MapContainer>

            <style jsx>{`
        .map-container {
          height: 600px;
          width: 100%;
          border-radius: var(--radius-lg);
          overflow: hidden;
          border: 1px solid var(--border-subtle);
          position: relative;
          z-index: 1; /* Ensure map stays below other fixed elements if any */
        }
        
        .loading-map {
          height: 600px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: var(--bg-secondary);
          color: var(--text-secondary);
          border-radius: var(--radius-lg);
        }

        /* Leaflet override to match dark theme if needed, implies filtering */
        :global(.leaflet-tile) {
          filter: invert(100%) hue-rotate(180deg) brightness(95%) contrast(90%);
        }
        
        /* Popup styling */
        :global(.leaflet-popup-content-wrapper) {
          background: var(--bg-secondary);
          color: var(--text-primary);
        }
        :global(.leaflet-popup-tip) {
          background: var(--bg-secondary);
        }
      `}</style>
        </div>
    );
}
