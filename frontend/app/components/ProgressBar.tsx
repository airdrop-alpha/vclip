'use client';

import React, { useEffect, useState, useRef, useCallback } from 'react';
import { JobStatus, ProgressData, STAGE_LABELS, STAGE_ORDER } from '@/lib/types';
import { connectJobWebSocket, pollJobStatus, getJob } from '@/lib/api';
import type { Job } from '@/lib/types';

interface ProgressBarProps {
  jobId: string;
  onComplete: (job: Job) => void;
  onError: (error: string) => void;
}

export default function ProgressBar({
  jobId,
  onComplete,
  onError,
}: ProgressBarProps) {
  const [stage, setStage] = useState<JobStatus>('pending');
  const [progress, setProgress] = useState(0);
  const [message, setMessage] = useState('Queued — waiting for worker...');
  const cleanupRef = useRef<(() => void) | null>(null);

  /** Map backend stage to our simplified STAGE_ORDER display step */
  const getDisplayStageIndex = (s: JobStatus): number => {
    const map: Record<JobStatus, number> = {
      pending:      0,
      queued:       0,
      downloading:  1,
      transcribing: 2,
      parsing_chat: 2,
      detecting:    3,
      subtitling:   4,
      clipping:     4,
      complete:     5,
      failed:       -1,
    };
    return map[s] ?? 0;
  };

  const handleProgress = useCallback(
    (data: ProgressData) => {
      // Backend sends `status` (not `stage`)
      const newStage = data.status;
      if (!newStage) return;

      setStage(newStage);
      setProgress(data.progress);
      setMessage(data.message || STAGE_LABELS[newStage] || newStage);

      if (newStage === 'complete') {
        getJob(jobId).then(onComplete).catch(() => {
          onError('Failed to fetch completed job');
        });
      }
      if (newStage === 'failed') {
        onError(data.message || 'Job failed');
      }
    },
    [jobId, onComplete, onError]
  );

  const handleJobUpdate = useCallback(
    (job: Job) => {
      setStage(job.status);
      setProgress(job.progress);
      setMessage(job.message || STAGE_LABELS[job.status] || job.status);

      if (job.status === 'complete') {
        onComplete(job);
      }
      if (job.status === 'failed') {
        onError(job.error || 'Job failed');
      }
    },
    [onComplete, onError]
  );

  useEffect(() => {
    let wsCleanup: (() => void) | null = null;
    let pollCleanup: (() => void) | null = null;
    let wsConnected = false;

    wsCleanup = connectJobWebSocket(
      jobId,
      (data) => {
        wsConnected = true;
        handleProgress(data);
      },
      () => {
        if (!wsConnected) {
          pollCleanup = pollJobStatus(jobId, handleJobUpdate, 2000);
        }
      },
      () => {
        if (!wsConnected) {
          pollCleanup = pollJobStatus(jobId, handleJobUpdate, 2000);
        }
      }
    );

    const fallbackTimeout = setTimeout(() => {
      if (!wsConnected) {
        pollCleanup = pollJobStatus(jobId, handleJobUpdate, 3000);
      }
    }, 3000);

    cleanupRef.current = () => {
      clearTimeout(fallbackTimeout);
      wsCleanup?.();
      pollCleanup?.();
    };

    return () => {
      cleanupRef.current?.();
    };
  }, [jobId, handleProgress, handleJobUpdate]);

  const currentStageIndex = getDisplayStageIndex(stage);

  return (
    <div className="card p-5 animate-fade-in">
      {/* Stage indicators */}
      <div className="flex items-center gap-1 mb-4 overflow-x-auto pb-1">
        {STAGE_ORDER.slice(0, -1).map((s, i) => {
          const isActive = i === currentStageIndex;
          const isComplete = i < currentStageIndex;
          const isFailed = stage === 'failed' && i === currentStageIndex;

          return (
            <React.Fragment key={s}>
              <div className="flex items-center gap-1.5 flex-shrink-0">
                <div
                  className={`
                    w-2.5 h-2.5 rounded-full transition-all duration-500
                    ${
                      isFailed
                        ? 'bg-red-500 shadow-sm shadow-red-500/50'
                        : isComplete
                          ? 'bg-primary-500 shadow-sm shadow-primary-500/50'
                          : isActive
                            ? 'bg-primary-400 shadow-sm shadow-primary-400/50 animate-pulse'
                            : 'bg-surface-600'
                    }
                  `}
                />
                <span
                  className={`
                    text-xs font-medium whitespace-nowrap transition-colors duration-300
                    ${
                      isFailed
                        ? 'text-red-400'
                        : isComplete
                          ? 'text-primary-400'
                          : isActive
                            ? 'text-white'
                            : 'text-gray-600'
                    }
                  `}
                >
                  {STAGE_LABELS[s].replace('...', '')}
                </span>
              </div>
              {i < STAGE_ORDER.length - 2 && (
                <div
                  className={`
                    w-6 h-px flex-shrink-0 transition-colors duration-500
                    ${isComplete ? 'bg-primary-500/50' : 'bg-surface-600'}
                  `}
                />
              )}
            </React.Fragment>
          );
        })}
      </div>

      {/* Progress bar */}
      <div className="relative h-3 bg-surface-700 rounded-full overflow-hidden">
        <div
          className={`
            absolute inset-y-0 left-0 rounded-full progress-bar-fill
            ${
              stage === 'failed'
                ? 'bg-gradient-to-r from-red-600 to-red-500'
                : stage === 'complete'
                  ? 'bg-gradient-to-r from-green-600 to-green-400'
                  : 'bg-gradient-to-r from-primary-600 via-primary-500 to-accent-500'
            }
          `}
          style={{ width: `${Math.max(progress, 2)}%` }}
        >
          {stage !== 'complete' && stage !== 'failed' && (
            <div className="absolute inset-0 shimmer" />
          )}
        </div>
      </div>

      {/* Status text */}
      <div className="flex items-center justify-between mt-3">
        <div className="flex items-center gap-2">
          {stage === 'failed' ? (
            <svg className="w-4 h-4 text-red-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : stage === 'complete' ? (
            <svg className="w-4 h-4 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          ) : (
            <svg className="w-4 h-4 text-primary-400 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
            </svg>
          )}
          <span
            className={`text-sm font-medium ${
              stage === 'failed'
                ? 'text-red-400'
                : stage === 'complete'
                  ? 'text-green-400'
                  : 'text-gray-300'
            }`}
          >
            {message}
          </span>
        </div>
        <span className="text-xs text-gray-500 font-mono">{Math.round(progress)}%</span>
      </div>
    </div>
  );
}
