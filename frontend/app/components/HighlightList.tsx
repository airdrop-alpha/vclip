'use client';

import React, { useState, useMemo, useCallback } from 'react';
import { Highlight, HighlightSelection, SortMode } from '@/lib/types';
import HighlightCard from './HighlightCard';

interface HighlightListProps {
  highlights: Highlight[];
  selection: HighlightSelection;
  onSelectionChange: (selection: HighlightSelection) => void;
  onPreview: (highlight: Highlight) => void;
}

export default function HighlightList({
  highlights,
  selection,
  onSelectionChange,
  onPreview,
}: HighlightListProps) {
  const [sortMode, setSortMode] = useState<SortMode>('score');

  const sortedHighlights = useMemo(() => {
    const sorted = [...highlights];
    if (sortMode === 'score') {
      sorted.sort((a, b) => b.score - a.score);
    } else {
      sorted.sort((a, b) => a.start_time - b.start_time);
    }
    return sorted;
  }, [highlights, sortMode]);

  const selectedCount = useMemo(
    () => Object.values(selection).filter(Boolean).length,
    [selection]
  );

  const allSelected = selectedCount === highlights.length && highlights.length > 0;

  const toggleHighlight = useCallback(
    (id: string) => {
      onSelectionChange({
        ...selection,
        [id]: !selection[id],
      });
    },
    [selection, onSelectionChange]
  );

  const selectAll = useCallback(() => {
    const newSelection: HighlightSelection = {};
    highlights.forEach((h) => {
      newSelection[h.id] = true;
    });
    onSelectionChange(newSelection);
  }, [highlights, onSelectionChange]);

  const deselectAll = useCallback(() => {
    onSelectionChange({});
  }, [onSelectionChange]);

  if (highlights.length === 0) {
    return null;
  }

  return (
    <div className="animate-fade-in">
      {/* Header bar */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-3">
          <h2 className="text-lg font-semibold text-white flex items-center gap-2">
            <svg
              className="w-5 h-5 text-primary-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13 10V3L4 14h7v7l9-11h-7z"
              />
            </svg>
            Highlights Found
          </h2>
          <span className="badge-purple">{highlights.length}</span>
          {selectedCount > 0 && (
            <span className="text-xs text-gray-500">
              {selectedCount} selected
            </span>
          )}
        </div>

        <div className="flex items-center gap-2">
          {/* Sort toggle */}
          <div className="flex items-center bg-surface-800 rounded-lg border border-white/10 p-0.5">
            <button
              onClick={() => setSortMode('score')}
              className={`
                px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200
                ${
                  sortMode === 'score'
                    ? 'bg-primary-500/20 text-primary-400'
                    : 'text-gray-500 hover:text-gray-300'
                }
              `}
            >
              By Score
            </button>
            <button
              onClick={() => setSortMode('time')}
              className={`
                px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200
                ${
                  sortMode === 'time'
                    ? 'bg-primary-500/20 text-primary-400'
                    : 'text-gray-500 hover:text-gray-300'
                }
              `}
            >
              By Time
            </button>
          </div>

          {/* Select all / Deselect */}
          <button
            onClick={allSelected ? deselectAll : selectAll}
            className="btn-ghost text-xs"
          >
            {allSelected ? 'Deselect All' : 'Select All'}
          </button>
        </div>
      </div>

      {/* Highlight cards */}
      <div className="space-y-2">
        {sortedHighlights.map((highlight, index) => (
          <HighlightCard
            key={highlight.id}
            highlight={highlight}
            rank={
              sortMode === 'score'
                ? index + 1
                : highlights
                    .slice()
                    .sort((a, b) => b.score - a.score)
                    .findIndex((h) => h.id === highlight.id) + 1
            }
            selected={!!selection[highlight.id]}
            onToggle={toggleHighlight}
            onPreview={onPreview}
          />
        ))}
      </div>
    </div>
  );
}
