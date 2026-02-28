'use client';

import React, { useRef, useEffect, useState, forwardRef, useImperativeHandle } from 'react';

export interface CameraPreviewHandle {
    captureFrame: () => string | null;
}

export interface CameraPreviewProps {
    className?: string;
    onCapture?: (frame: string) => void;
    autoCaptureInterval?: number; // ms
}

const CameraPreview = forwardRef<CameraPreviewHandle, CameraPreviewProps>((props, ref) => {
    const videoRef = useRef<HTMLVideoElement>(null);
    const canvasRef = useRef<HTMLCanvasElement>(null);
    const [isActive, setIsActive] = useState(false);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        let stream: MediaStream | null = null;

        const startCamera = async () => {
            try {
                stream = await navigator.mediaDevices.getUserMedia({
                    video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 } }
                });
                if (videoRef.current) {
                    videoRef.current.srcObject = stream;
                    setIsActive(true);
                }
            } catch (err) {
                console.error("Camera access error:", err);
                setError("Could not access camera. Please check permissions.");
            }
        };

        startCamera();

        return () => {
            if (stream) {
                stream.getTracks().forEach(track => track.stop());
            }
        };
    }, []);

    useImperativeHandle(ref, () => ({
        captureFrame: () => {
            if (videoRef.current && canvasRef.current && isActive) {
                const video = videoRef.current;
                const canvas = canvasRef.current;
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                const ctx = canvas.getContext('2d');
                if (ctx) {
                    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
                    return canvas.toDataURL('image/jpeg', 0.8);
                }
            }
            return null;
        }
    }));

    if (error) {
        return <div className="camera-error p-4 bg-red-900/20 text-red-400 rounded-lg text-sm">{error}</div>;
    }

    return (
        <div className={`camera-preview-container relative overflow-hidden rounded-xl border border-white/10 ${props.className}`}>
            <video
                ref={videoRef}
                autoPlay
                playsInline
                muted
                className={`w-full h-full object-cover grayscale contrast-125 transition-opacity duration-1000 ${isActive ? 'opacity-80' : 'opacity-0'}`}
            />
            <canvas ref={canvasRef} className="hidden" />
            <div className="absolute top-2 left-2 px-2 py-1 bg-black/50 backdrop-blur-md rounded text-[10px] uppercase tracking-widest text-white/70 flex items-center gap-2">
                <span className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse" />
                {props.autoCaptureInterval ? 'AI WATCHING' : 'Live Feed'}
            </div>
            {props.autoCaptureInterval && (
                <div className="absolute bottom-2 right-2 px-2 py-1 bg-cyan-900/40 backdrop-blur-md rounded text-[9px] uppercase tracking-tighter text-cyan-400 border border-cyan-400/30">
                    Real-time Analysis Active
                </div>
            )}
        </div>
    );
});

CameraPreview.displayName = 'CameraPreview';

export default CameraPreview;
