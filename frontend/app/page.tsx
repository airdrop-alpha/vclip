'use client';

import React, { useState, useCallback, useMemo } from 'react';
import {
  Job,
  Language,
  Highlight,
  HighlightSelection,
} from '@/lib/types';
import { createJob } from '@/lib/api';
import Header from './components/Header';
import URLInput from './components/URLInput';
import ProgressBar from './components/ProgressBar';
import HighlightList from './components/HighlightList';
import ClipPreview from './components/ClipPreview';
import ExportPanel from './components/ExportPanel';

type AppState = 'idle' | 'submitting' | 'processing' | 'complete' | 'error';

export default function Home() {
  // Core state
  const [appState, setAppState] = useState<AppState>('idle');
  const [job, setJob] = useState<Job | null>(null);
  const [error, setError] = useState<string | null>(null);

  // UI state
  const [selection, setSelection] = useState<HighlightSelection>({});
  const [previewHighlight, setPreviewHighlight] = useState<Highlight | null>(null);

  // Submit a new job
  const handleSubmit = useCallback(async (url: string, language: Language) => {
    setAppState('submitting');
    setError(null);
    setJob(null);
    setSelection({});
    setPreviewHighlight(null);

    try {
      const newJob = await createJob(url, {
        languages: language === 'auto' ? undefined : [language],
      });
      setJob(newJob);
      setAppState('processing');
    } catch (err) {
      const message =
        err instanceof Error ? err.message : 'Failed to submit job';
      setError(message);
      setAppState('error');
    }
  }, []);

  // Job completed
  const handleComplete = useCallback((completedJob: Job) => {
    setJob(completedJob);
    setAppState('complete');

    // Auto-select all highlights
    const autoSelection: HighlightSelection = {};
    completedJob.highlights.forEach((h) => {
      autoSelection[h.id] = true;
    });
    setSelection(autoSelection);
  }, []);

  // Job failed
  const handleError = useCallback((errorMessage: string) => {
    setError(errorMessage);
    setAppState('error');
  }, []);

  // Preview a highlight
  const handlePreview = useCallback(
    (highlight: Highlight) => {
      setPreviewHighlight(highlight);
    },
    []
  );

  // Find matching clip for a highlight
  const previewClipId = useMemo(() => {
    if (!previewHighlight || !job) return undefined;
    const clip = job.clips.find(
      (c) => c.highlight_id === previewHighlight.id
    );
    return clip?.id;
  }, [previewHighlight, job]);

  // Reset to start over
  const handleReset = useCallback(() => {
    setAppState('idle');
    setJob(null);
    setError(null);
    setSelection({});
    setPreviewHighlight(null);
  }, []);

  const isLoading = appState === 'submitting' || appState === 'processing';

  return (
    <div className="min-h-screen flex flex-col">
      <Header />

      <main className="flex-1 flex flex-col">
        <div className="max-w-3xl w-full mx-auto px-4 sm:px-6 py-8 space-y-6">
          {/* Hero section — visible only in idle state */}
          {appState === 'idle' && (
            <div className="text-center py-8 animate-fade-in">
              <h2 className="text-3xl sm:text-4xl font-bold mb-3">
                <span className="gradient-text">Auto-clip</span>{' '}
                <span className="text-white">your VTuber streams</span>
              </h2>
              <p className="text-gray-400 text-sm sm:text-base max-w-lg mx-auto leading-relaxed">
                Paste a YouTube VOD link. Our AI detects highlights using chat
                spikes, audio peaks, and keywords — then generates clips with
                subtitles in minutes, not hours.
              </p>

              {/* Feature pills */}
              <div className="flex flex-wrap items-center justify-center gap-2 mt-5">
                {[
                  { icon: '💬', label: 'Chat Spike Detection' },
                  { icon: '🔊', label: 'Audio Peak Analysis' },
                  { icon: '🏷️', label: 'Keyword Triggers' },
                  { icon: '📝', label: 'Auto Subtitles' },
                  { icon: '📱', label: '9:16 for Shorts' },
                  { icon: '🎮', label: 'Bilibili & Twitch' },
                ].map((f) => (
                  <span
                    key={f.label}
                    className="inline-flex items-center gap-1.5 px-3 py-1.5 
                               rounded-full bg-surface-800/80 border border-white/5
                               text-xs text-gray-400"
                  >
                    {f.icon} {f.label}
                  </span>
                ))}
              </div>
            </div>
          )}

          {/* URL Input — always visible */}
          <URLInput
            onSubmit={handleSubmit}
            isLoading={isLoading}
          />

          {/* Global error */}
          {appState === 'error' && error && (
            <div className="card p-4 border-red-500/20 bg-red-500/5 animate-slide-up">
              <div className="flex items-start gap-3">
                <svg
                  className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5"
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
                <div className="flex-1">
                  <p className="text-sm font-medium text-red-400">
                    Something went wrong
                  </p>
                  <p className="text-xs text-red-400/70 mt-1">{error}</p>
                </div>
                <button
                  onClick={handleReset}
                  className="btn-ghost text-xs text-red-400 hover:text-red-300"
                >
                  Try again
                </button>
              </div>
            </div>
          )}

          {/* Progress bar — during processing */}
          {appState === 'processing' && job && (
            <ProgressBar
              jobId={job.id}
              onComplete={handleComplete}
              onError={handleError}
            />
          )}

          {/* Results — after completion */}
          {appState === 'complete' && job && (
            <>
              {/* Success banner */}
              <div className="card p-4 border-green-500/20 bg-green-500/5 animate-slide-up">
                <div className="flex items-center gap-3">
                  <svg
                    className="w-5 h-5 text-green-400"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                  <div className="flex-1">
                    <p className="text-sm font-medium text-green-400">
                      Analysis complete!
                    </p>
                    <p className="text-xs text-green-400/70 mt-0.5">
                      Found {job.highlights.length} highlights and generated{' '}
                      {job.clips.length} clips
                      {job.title && <> from &ldquo;{job.title}&rdquo;</>}
                    </p>
                  </div>
                  <button
                    onClick={handleReset}
                    className="btn-ghost text-xs text-gray-400 hover:text-white"
                  >
                    New clip
                  </button>
                </div>
              </div>

              {/* Export panel */}
              <ExportPanel
                jobId={job.id}
                highlights={job.highlights}
                clips={job.clips}
                selection={selection}
              />

              {/* Highlight list */}
              <HighlightList
                highlights={job.highlights}
                selection={selection}
                onSelectionChange={setSelection}
                onPreview={handlePreview}
              />
            </>
          )}

          {/* Empty state / waiting indicator */}
          {appState === 'submitting' && (
            <div className="card p-8 animate-fade-in">
              <div className="flex flex-col items-center gap-4">
                <div className="relative">
                  <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 flex items-center justify-center animate-pulse-slow">
                    <svg
                      className="w-6 h-6 text-white animate-spin"
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
                  <div className="absolute inset-0 rounded-xl bg-gradient-to-br from-primary-500 to-accent-500 blur-xl opacity-20 animate-pulse" />
                </div>
                <div className="text-center">
                  <p className="text-sm font-medium text-gray-300">
                    Submitting job...
                  </p>
                  <p className="text-xs text-gray-500 mt-1">
                    Hang tight, we&apos;re getting things ready
                  </p>
                </div>
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <footer className="mt-auto border-t border-white/5 py-6">
          <div className="max-w-3xl mx-auto px-4 sm:px-6 flex items-center justify-between">
            <p className="text-xs text-gray-600">
              VClip • AI-powered VTuber clipping
            </p>
            <div className="flex items-center gap-3 text-xs text-gray-600">
              <span className="inline-flex items-center gap-1">
                <span className="w-1.5 h-1.5 rounded-full bg-green-500" />
                API Connected
              </span>
            </div>
          </div>
        </footer>
      </main>

      {/* Clip Preview Modal */}
      {previewHighlight && job && (
        <ClipPreview
          jobId={job.id}
          highlight={previewHighlight}
          clipId={previewClipId}
          onClose={() => setPreviewHighlight(null)}
        />
      )}
    </div>
  );
}
