'use client';

import React, { useState, useMemo } from 'react';
import { AspectRatio, HighlightSelection, Clip, Highlight } from '@/lib/types';
import { getExportUrl, getClipDownloadUrl } from '@/lib/api';

interface ExportPanelProps {
  jobId: string;
  highlights: Highlight[];
  clips: Clip[];
  selection: HighlightSelection;
}

export default function ExportPanel({
  jobId,
  highlights,
  clips,
  selection,
}: ExportPanelProps) {
  const [aspectRatio, setAspectRatio] = useState<AspectRatio>('16:9');
  const [isExporting, setIsExporting] = useState(false);

  const selectedHighlightIds = useMemo(
    () =>
      Object.entries(selection)
        .filter(([, selected]) => selected)
        .map(([id]) => id),
    [selection]
  );

  const selectedClipIds = useMemo(() => {
    return clips
      .filter(
        (clip) =>
          selectedHighlightIds.includes(clip.highlight_id) &&
          clip.aspect_ratio === aspectRatio
      )
      .map((c) => c.id);
  }, [clips, selectedHighlightIds, aspectRatio]);

  // Estimate total size: ~2MB per 60s clip (rough estimate)
  const estimatedSize = useMemo(() => {
    const selectedHighlights = highlights.filter(
      (h) => selection[h.id]
    );
    const totalDuration = selectedHighlights.reduce(
      (acc, h) => acc + (h.end_time - h.start_time),
      0
    );
    const sizeMB = (totalDuration / 60) * 2; // ~2MB per minute
    if (sizeMB < 1) return `${Math.round(sizeMB * 1024)} KB`;
    if (sizeMB >= 1024) return `${(sizeMB / 1024).toFixed(1)} GB`;
    return `${Math.round(sizeMB)} MB`;
  }, [highlights, selection]);

  const handleDownloadSelected = () => {
    if (selectedClipIds.length === 0) return;
    setIsExporting(true);

    const url = getExportUrl(jobId, selectedClipIds, aspectRatio);
    const link = document.createElement('a');
    link.href = url;
    link.download = `vclip-${jobId}-selected.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => setIsExporting(false), 2000);
  };

  const handleDownloadAll = () => {
    setIsExporting(true);

    const allClipIds = clips
      .filter((c) => c.aspect_ratio === aspectRatio)
      .map((c) => c.id);
    const url = getExportUrl(jobId, allClipIds, aspectRatio);
    const link = document.createElement('a');
    link.href = url;
    link.download = `vclip-${jobId}-all.zip`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);

    setTimeout(() => setIsExporting(false), 2000);
  };

  const handleDownloadSingle = (clipId: string, index: number) => {
    const url = getClipDownloadUrl(jobId, clipId);
    const link = document.createElement('a');
    link.href = url;
    link.download = `vclip-clip-${index + 1}.mp4`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="card p-5 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        {/* Left: aspect ratio toggle */}
        <div className="flex items-center gap-4">
          <h3 className="text-sm font-semibold text-white flex items-center gap-2">
            <svg
              className="w-4 h-4 text-accent-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
              />
            </svg>
            Export
          </h3>

          {/* Aspect ratio buttons */}
          <div className="flex items-center bg-surface-800 rounded-lg border border-white/10 p-0.5">
            <button
              onClick={() => setAspectRatio('16:9')}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium 
                transition-all duration-200
                ${
                  aspectRatio === '16:9'
                    ? 'bg-primary-500/20 text-primary-400'
                    : 'text-gray-500 hover:text-gray-300'
                }
              `}
            >
              {/* 16:9 icon */}
              <svg className="w-4 h-3" viewBox="0 0 16 9" fill="none">
                <rect
                  x="0.5"
                  y="0.5"
                  width="15"
                  height="8"
                  rx="1"
                  stroke="currentColor"
                />
              </svg>
              16:9
            </button>
            <button
              onClick={() => setAspectRatio('9:16')}
              className={`
                flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium 
                transition-all duration-200
                ${
                  aspectRatio === '9:16'
                    ? 'bg-accent-500/20 text-accent-400'
                    : 'text-gray-500 hover:text-gray-300'
                }
              `}
            >
              {/* 9:16 icon */}
              <svg className="w-3 h-4" viewBox="0 0 9 16" fill="none">
                <rect
                  x="0.5"
                  y="0.5"
                  width="8"
                  height="15"
                  rx="1"
                  stroke="currentColor"
                />
              </svg>
              9:16
            </button>
          </div>

          {/* Size estimate */}
          {selectedHighlightIds.length > 0 && (
            <span className="text-xs text-gray-500">
              ~{estimatedSize} estimated
            </span>
          )}
        </div>

        {/* Right: download buttons */}
        <div className="flex items-center gap-2">
          {/* Download Selected */}
          <button
            onClick={handleDownloadSelected}
            disabled={selectedHighlightIds.length === 0 || isExporting}
            className="btn-primary text-xs"
          >
            {isExporting ? (
              <>
                <svg
                  className="w-3.5 h-3.5 animate-spin"
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
                Exporting...
              </>
            ) : (
              <>
                <svg
                  className="w-3.5 h-3.5"
                  fill="none"
                  viewBox="0 0 24 24"
                  stroke="currentColor"
                  strokeWidth={2}
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                  />
                </svg>
                Download Selected ({selectedHighlightIds.length})
              </>
            )}
          </button>

          {/* Download All */}
          <button
            onClick={handleDownloadAll}
            disabled={clips.length === 0 || isExporting}
            className="btn-secondary text-xs"
          >
            <svg
              className="w-3.5 h-3.5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M19 9l-7 7-7-7"
              />
            </svg>
            All Clips
          </button>
        </div>
      </div>

      {/* Individual clip download list (compact) */}
      {clips.length > 0 && selectedHighlightIds.length > 0 && (
        <div className="mt-4 pt-4 border-t border-white/5">
          <div className="flex flex-wrap gap-2">
            {clips
              .filter(
                (clip) =>
                  selectedHighlightIds.includes(clip.highlight_id) &&
                  clip.aspect_ratio === aspectRatio
              )
              .map((clip, i) => {
                const hl = highlights.find(
                  (h) => h.id === clip.highlight_id
                );
                return (
                  <button
                    key={clip.id}
                    onClick={() => handleDownloadSingle(clip.id, i)}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 
                               rounded-lg bg-surface-700/50 border border-white/5
                               text-xs text-gray-400 hover:text-white hover:border-white/10
                               transition-all duration-200"
                    title={
                      hl
                        ? `Score: ${hl.score.toFixed(2)} — ${hl.transcript_snippet?.slice(0, 40) || ''}`
                        : ''
                    }
                  >
                    <svg
                      className="w-3 h-3"
                      fill="none"
                      viewBox="0 0 24 24"
                      stroke="currentColor"
                      strokeWidth={2}
                    >
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
                      />
                    </svg>
                    Clip {i + 1}
                    <span className="text-gray-600">
                      ({Math.round(clip.duration)}s)
                    </span>
                  </button>
                );
              })}
          </div>
        </div>
      )}

      {/* Aspect ratio hint */}
      <div className="mt-3 flex items-center gap-1.5 text-[11px] text-gray-600">
        <svg
          className="w-3 h-3"
          fill="none"
          viewBox="0 0 24 24"
          stroke="currentColor"
          strokeWidth={2}
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
          />
        </svg>
        {aspectRatio === '16:9'
          ? 'Optimized for YouTube — standard horizontal format'
          : 'Optimized for Shorts / TikTok — vertical format with center crop'}
      </div>
    </div>
  );
}
