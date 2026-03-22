import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'VClip — VTuber Auto Clipper',
  description:
    'AI-powered clipping tool for VTuber streams. Automatically detect highlights, generate clips with subtitles, and export for YouTube Shorts, TikTok, and Bilibili.',
  keywords: [
    'VTuber',
    'clip',
    'highlight',
    'auto clipper',
    'VTuber clips',
    'stream highlights',
    'YouTube Shorts',
    'TikTok',
  ],
  icons: {
    icon: '/favicon.ico',
  },
  openGraph: {
    title: 'VClip — VTuber Auto Clipper',
    description: 'AI-powered automatic clipping for VTuber streams',
    type: 'website',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link
          rel="preconnect"
          href="https://fonts.gstatic.com"
          crossOrigin="anonymous"
        />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&family=Noto+Sans+JP:wght@400;500;700&family=JetBrains+Mono:wght@400;500&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-sans antialiased bg-surface-900 text-gray-200 min-h-screen bg-grid">
        {/* Ambient glow in the background */}
        <div className="fixed inset-0 pointer-events-none z-0">
          <div className="absolute top-0 left-1/4 w-[600px] h-[600px] bg-primary-500/5 rounded-full blur-[120px]" />
          <div className="absolute bottom-0 right-1/4 w-[500px] h-[500px] bg-accent-500/5 rounded-full blur-[120px]" />
        </div>

        {/* Main content */}
        <div className="relative z-10">{children}</div>
      </body>
    </html>
  );
}
