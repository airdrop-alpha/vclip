'use client';

import React, { useRef, useState, useEffect, useCallback } from 'react';
import { Highlight } from '@/lib/types';
import { getClipDownloadUrl } from '@/lib/api';

interface ClipPreviewProps {
  jobId: string;
  highlight: Highlight;
  clipId?: string;
  onClose: () => void;
}

export default function ClipPreview({
  jobId,
  highlight,
  clipId,
  onClose,
}: ClipPreviewProps) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const videoUrl = clipId
    ? getClipDownloadUrl(jobId, clipId)
    : null;

  // Keyboard handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
      if (e.key === ' ') {
        e.preventDefault();
        togglePlay();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  });

  const togglePlay = useCallback(() => {
    if (!videoRef.current) return;
    if (videoRef.current.paused) {
      videoRef.current.play();
    } else {
      videoRef.current.pause();
    }
  }, []);

  const handleTimeUpdate = () => {
    if (videoRef.current) {
      setCurrentTime(videoRef.current.currentTime);
    }
  };

  const handleLoadedMetadata = () => {
    if (videoRef.current) {
      setDuration(videoRef.current.duration);
      setIsLoading(false);
    }
  };

  const handleSeek = (e: React.ChangeEvent<HTMLInputElement>) => {
    const time = parseFloat(e.target.value);
    if (videoRef.current) {
      videoRef.current.currentTime = time;
      setCurrentTime(time);
    }
  };

  const formatTime = (seconds: number): string => {
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div
        className="relative w-full max-w-3xl card overflow-hidden"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-white/5">
          <div>
            <h3 className="text-sm font-semibold text-white">Clip Preview</h3>
            <p className="text-xs text-gray-500 mt-0.5">
              {formatTime(highlight.start_time)} – {formatTime(highlight.end_time)}
              {highlight.transcript_snippet && (
                <> · &ldquo;{highlight.transcript_snippet.slice(0, 50)}...&rdquo;</>
              )}
            </p>
          </div>
          <button
            onClick={onClose}
            className="btn-ghost text-gray-400 hover:text-white"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Video area */}
        <div className="relative bg-black aspect-video">
          {videoUrl ? (
            <>
              <video
                ref={videoRef}
                src={videoUrl}
                className="w-full h-full object-contain"
                onTimeUpdate={handleTimeUpdate}
                onLoadedMetadata={handleLoadedMetadata}
                onPlay={() => setIsPlaying(true)}
                onPause={() => setIsPlaying(false)}
                onError={() => setError('Failed to load clip')}
                onWaiting={() => setIsLoading(true)}
                onCanPlay={() => setIsLoading(false)}
                playsInline
              />

              {/* Loading overlay */}
              {isLoading && !error && (
                <div className="absolute inset-0 flex items-center justify-center bg-black/50">
                  <svg
                    className="w-10 h-10 text-primary-400 animate-spin"
                    fill="none"
                    viewBox="0 0 24 24"
                  >
                    <circle
                      className="opacity-25"
                      cx="12"
                      cy="12"
                      r="10"
                      stroke="currentColor"
                      strokeWidth="4"
                    />
                    <path
                      className="opacity-75"
                      fill="currentColor"
                      d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                    />
                  </svg>
                </div>
              )}

              {/* Error overlay */}
              {error && (
                <div className="absolute inset-0 flex flex-col items-center justify-center bg-black/70 gap-2">
                  <svg
                    className="w-10 h-10 text-red-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <p className="text-sm text-red-400">{error}</p>
                </div>
              )}

              {/* Click-to-play overlay */}
              {!isPlaying && !isLoading && !error && (
                <button
                  className="absolute inset-0 flex items-center justify-center group/play"
                  onClick={togglePlay}
                >
                  <div className="w-16 h-16 rounded-full bg-white/10 backdrop-blur-sm flex items-center justify-center transition-all duration-200 group-hover/play:bg-white/20 group-hover/play:scale-110">
                    <svg
                      className="w-8 h-8 text-white ml-1"
                      fill="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path d="M8 5v14l11-7z" />
                    </svg>
                  </div>
                </button>
              )}
            </>
          ) : (
            /* No clip available — show placeholder */
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3">
              <div className="w-16 h-16 rounded-full bg-surface-700 flex items-center justify-center">
                <svg
                  className="w-8 h-8 text-gray-500"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={1.5}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z"
                  />
                </svg>
              </div>
              <p className="text-sm text-gray-500">
                Clip will be available after processing
              </p>
              <p className="text-xs text-gray-600">
                Highlight: {formatTime(highlight.start_time)} – {formatTime(highlight.end_time)}
              </p>
            </div>
          )}
        </div>

        {/* Controls */}
        {videoUrl && !error && (
          <div className="p-4 border-t border-white/5">
            <div className="flex items-center gap-3">
              {/* Play/Pause */}
              <button
                onClick={togglePlay}
                className="btn-ghost text-gray-300 hover:text-white"
              >
                {isPlaying ? (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M6 4h4v16H6zm8 0h4v16h-4z" />
                  </svg>
                ) : (
                  <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                )}
              </button>

              {/* Time */}
              <span className="text-xs font-mono text-gray-500 w-16 text-right">
                {formatTime(currentTime)}
              </span>

              {/* Seek bar */}
              <input
                type="range"
                min={0}
                max={duration || 100}
                step={0.1}
                value={currentTime}
                onChange={handleSeek}
                className="flex-1 h-1.5 rounded-full appearance-none bg-surface-600 cursor-pointer
                           [&::-webkit-slider-thumb]:appearance-none
                           [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3
                           [&::-webkit-slider-thumb]:rounded-full
                           [&::-webkit-slider-thumb]:bg-primary-500
                           [&::-webkit-slider-thumb]:shadow-sm [&::-webkit-slider-thumb]:shadow-primary-500/30
                           [&::-webkit-slider-thumb]:cursor-pointer
                           [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:duration-150
                           [&::-webkit-slider-thumb]:hover:scale-125"
              />

              {/* Duration */}
              <span className="text-xs font-mono text-gray-500 w-16">
                {formatTime(duration)}
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
