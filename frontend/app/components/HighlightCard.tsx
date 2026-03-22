'use client';

import React, { useState } from 'react';
import { Highlight, DetectionSource } from '@/lib/types';

interface HighlightCardProps {
  highlight: Highlight;
  rank: number;
  selected: boolean;
  onToggle: (id: string) => void;
  onPreview: (highlight: Highlight) => void;
}

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) {
    return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  }
  return `${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
}

function getScoreColor(score: number): string {
  if (score >= 0.8) return 'text-green-400';
  if (score >= 0.6) return 'text-yellow-400';
  return 'text-orange-400';
}

function getScoreBgColor(score: number): string {
  if (score >= 0.8) return 'bg-green-500/10 border-green-500/20';
  if (score >= 0.6) return 'bg-yellow-500/10 border-yellow-500/20';
  return 'bg-orange-500/10 border-orange-500/20';
}

function getSourceIcon(source: DetectionSource): string {
  switch (source) {
    case 'chat':
      return '💬';
    case 'audio':
      return '🔊';
    case 'keyword':
      return '🏷️';
  }
}

function getSourceLabel(source: DetectionSource): string {
  switch (source) {
    case 'chat':
      return 'Chat spike';
    case 'audio':
      return 'Audio peak';
    case 'keyword':
      return 'Keyword';
  }
}

export default function HighlightCard({
  highlight,
  rank,
  selected,
  onToggle,
  onPreview,
}: HighlightCardProps) {
  const [isHovered, setIsHovered] = useState(false);

  const duration = highlight.end_time - highlight.start_time;

  return (
    <div
      className={`
        card group cursor-pointer
        ${selected ? 'border-primary-500/30 bg-primary-500/5' : ''}
        ${isHovered ? 'border-white/15 shadow-lg shadow-primary-500/5' : ''}
      `}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      onClick={() => onToggle(highlight.id)}
    >
      <div className="p-4">
        <div className="flex items-start gap-3">
          {/* Checkbox */}
          <div className="pt-0.5">
            <input
              type="checkbox"
              checked={selected}
              onChange={() => onToggle(highlight.id)}
              onClick={(e) => e.stopPropagation()}
              className="checkbox-custom"
            />
          </div>

          {/* Rank badge */}
          <div
            className={`
              flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center
              text-xs font-bold transition-all duration-200
              ${
                rank <= 3
                  ? 'bg-gradient-to-br from-primary-500 to-accent-500 text-white shadow-sm shadow-primary-500/20'
                  : 'bg-surface-700 text-gray-400'
              }
            `}
          >
            #{rank}
          </div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            {/* Top row: score + time range */}
            <div className="flex items-center flex-wrap gap-2 mb-2">
              {/* Score badge */}
              <span
                className={`
                  inline-flex items-center gap-1 px-2 py-0.5 rounded-md text-xs font-bold
                  border ${getScoreBgColor(highlight.score)}
                  ${getScoreColor(highlight.score)}
                `}
              >
                <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                  <path d="M9.049 2.927c.3-.921 1.603-.921 1.902 0l1.07 3.292a1 1 0 00.95.69h3.462c.969 0 1.371 1.24.588 1.81l-2.8 2.034a1 1 0 00-.364 1.118l1.07 3.292c.3.921-.755 1.688-1.54 1.118l-2.8-2.034a1 1 0 00-1.175 0l-2.8 2.034c-.784.57-1.838-.197-1.539-1.118l1.07-3.292a1 1 0 00-.364-1.118L2.98 8.72c-.783-.57-.38-1.81.588-1.81h3.461a1 1 0 00.951-.69l1.07-3.292z" />
                </svg>
                {highlight.score.toFixed(2)}
              </span>

              {/* Time range */}
              <span className="text-xs font-mono text-gray-400 bg-surface-700 px-2 py-0.5 rounded-md">
                {formatTime(highlight.start_time)} – {formatTime(highlight.end_time)}
              </span>

              {/* Duration */}
              <span className="text-xs text-gray-500">
                {Math.round(duration)}s
              </span>
            </div>

            {/* Transcript snippet */}
            {highlight.transcript_snippet && (
              <p className="text-sm text-gray-300 mb-2 line-clamp-2 leading-relaxed">
                &ldquo;{highlight.transcript_snippet}&rdquo;
              </p>
            )}

            {/* Detection sources */}
            <div className="flex items-center flex-wrap gap-1.5">
              {highlight.detection_sources.map((source) => (
                <span
                  key={source}
                  className="inline-flex items-center gap-1 text-[11px] text-gray-400 bg-surface-700/80 px-2 py-0.5 rounded-full"
                >
                  {getSourceIcon(source)} {getSourceLabel(source)}
                </span>
              ))}

              {/* Chat intensity indicator */}
              {highlight.chat_intensity > 0.5 && (
                <span className="inline-flex items-center gap-1 text-[11px] text-accent-400 bg-accent-500/10 px-2 py-0.5 rounded-full border border-accent-500/20">
                  🔥 {Math.round(highlight.chat_intensity * 100)}% chat
                </span>
              )}
            </div>
          </div>

          {/* Preview button */}
          <button
            onClick={(e) => {
              e.stopPropagation();
              onPreview(highlight);
            }}
            className="flex-shrink-0 btn-ghost text-gray-500 hover:text-primary-400 
                       opacity-0 group-hover:opacity-100 transition-opacity duration-200"
            title="Preview clip"
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
                d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z"
              />
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
              />
            </svg>
          </button>
        </div>
      </div>
    </div>
  );
}
