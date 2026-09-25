import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'HazardLens — AI Safety Monitoring',
  description:
    'AI-powered safety monitoring for construction and industrial sites. Detect PPE violations and restricted zone intrusions in real-time.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <head>
        <link rel="icon" href="/favicon.ico" />
      </head>
      <body>{children}</body>
    </html>
  );
}
