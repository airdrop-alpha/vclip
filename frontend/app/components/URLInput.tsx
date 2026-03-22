'use client';

import React, { useState, useCallback } from 'react';
import { Language, LANGUAGE_OPTIONS } from '@/lib/types';

interface URLInputProps {
  onSubmit: (url: string, language: Language) => void;
  isLoading: boolean;
}

const VIDEO_URL_REGEX =
  /^(https?:\/\/)?(www\.)?(youtube\.com\/watch\?v=[\w-]+|youtu\.be\/[\w-]+|youtube\.com\/live\/[\w-]+|bilibili\.com\/video\/(BV|av)[\w]+|b23\.tv\/[\w]+)/;

export default function URLInput({ onSubmit, isLoading }: URLInputProps) {
  const [url, setUrl] = useState('');
  const [language, setLanguage] = useState<Language>('auto');
  const [error, setError] = useState<string | null>(null);
  const [isFocused, setIsFocused] = useState(false);

  const validateUrl = useCallback((value: string): boolean => {
    if (!value.trim()) {
      setError('Please enter a video URL');
      return false;
    }
    if (!VIDEO_URL_REGEX.test(value.trim())) {
      setError('Invalid URL — paste a YouTube or Bilibili video link');
      return false;
    }
    setError(null);
    return true;
  }, []);

  const handleSubmit = useCallback(
    (e: React.FormEvent) => {
      e.preventDefault();
      if (validateUrl(url)) {
        onSubmit(url.trim(), language);
      }
    },
    [url, language, onSubmit, validateUrl]
  );

  const handleUrlChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setUrl(value);
    if (error) {
      setError(null);
    }
  };

  const handlePaste = (e: React.ClipboardEvent<HTMLInputElement>) => {
    // Auto-validate on paste
    setTimeout(() => {
      const pasted = e.currentTarget.value;
      if (pasted && VIDEO_URL_REGEX.test(pasted.trim())) {
        setError(null);
      }
    }, 0);
  };

  return (
    <div className="w-full">
      <form onSubmit={handleSubmit} className="space-y-3">
        {/* URL Input Row */}
        <div
          className={`
            flex flex-col sm:flex-row gap-2 p-2 rounded-xl
            border transition-all duration-300
            ${
              isFocused
                ? 'border-primary-500/40 bg-surface-800/90 shadow-lg shadow-primary-500/5'
                : error
                  ? 'border-red-500/30 bg-surface-800/60'
                  : 'border-white/10 bg-surface-800/60'
            }
          `}
        >
          {/* Input */}
          <div className="flex-1 flex items-center gap-2 px-2">
            <svg
              className={`w-5 h-5 flex-shrink-0 transition-colors duration-200 ${
                isFocused ? 'text-primary-400' : 'text-gray-500'
              }`}
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1"
              />
            </svg>
            <input
              type="text"
              value={url}
              onChange={handleUrlChange}
              onPaste={handlePaste}
              onFocus={() => setIsFocused(true)}
              onBlur={() => setIsFocused(false)}
              placeholder="Paste YouTube or Bilibili URL here..."
              disabled={isLoading}
              className="flex-1 bg-transparent border-none outline-none text-white 
                         placeholder:text-gray-500 text-sm py-2
                         disabled:opacity-50"
              autoFocus
            />
          </div>

          {/* Language select + Submit */}
          <div className="flex items-center gap-2">
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value as Language)}
              disabled={isLoading}
              className="bg-surface-700 border border-white/10 rounded-lg px-3 py-2.5
                         text-sm text-gray-300 outline-none cursor-pointer
                         hover:border-white/20 focus:border-primary-500/40
                         transition-all duration-200
                         disabled:opacity-50 disabled:cursor-not-allowed
                         appearance-none"
              style={{
                backgroundImage: `url("data:image/svg+xml,%3csvg xmlns='http://www.w3.org/2000/svg' fill='none' viewBox='0 0 20 20'%3e%3cpath stroke='%236b7280' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5' d='M6 8l4 4 4-4'/%3e%3c/svg%3e")`,
                backgroundPosition: 'right 0.5rem center',
                backgroundRepeat: 'no-repeat',
                backgroundSize: '1.25em 1.25em',
                paddingRight: '2rem',
              }}
            >
              {LANGUAGE_OPTIONS.map((opt) => (
                <option key={opt.value} value={opt.value}>
                  {opt.label}
                </option>
              ))}
            </select>

            <button
              type="submit"
              disabled={isLoading || !url.trim()}
              className="btn-primary whitespace-nowrap"
            >
              {isLoading ? (
                <>
                  <svg
                    className="w-4 h-4 animate-spin"
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
                  Processing...
                </>
              ) : (
                <>
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2.5}
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
                  Go!
                </>
              )}
            </button>
          </div>
        </div>

        {/* Error message */}
        {error && (
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20 animate-slide-up">
            <svg
              className="w-4 h-4 text-red-400 flex-shrink-0"
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
            <span className="text-sm text-red-400">{error}</span>
          </div>
        )}

        {/* Supported formats hint */}
        <p className="text-xs text-gray-600 px-1">
          Supports youtube.com/watch?v=... and youtu.be/... links • Streams up
          to 8 hours
        </p>
      </form>
    </div>
  );
}
