// FILE: frontend/app/layout.tsx

import type { Metadata, Viewport } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Script from "next/script";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

// 1. Next.js 14+ Viewport Specification (ThemeColor fix)
export const viewport: Viewport = {
  themeColor: "#8b5cf6",
  width: "device-width",
  initialScale: 1,
};

// 2. Metadata (without deprecated themeColor)
export const metadata: Metadata = {
  title: "Aura",
  description: "Virtual AI Companion",
  manifest: "/manifest.json",
  icons: {
    apple: "https://placehold.co/192x192/8b5cf6/ffffff?text=Aura",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`} suppressHydrationWarning>
      <head>
        <link rel="manifest" href="/manifest.json" />
        <meta name="theme-color" content="#8b5cf6" />
        <link rel="apple-touch-icon" href="https://placehold.co/192x192/8b5cf6/ffffff?text=Aura" />
      </head>
      <body className="min-h-full flex flex-col" suppressHydrationWarning>
        {children}
        {/* Next.js Native Script loader for Service Worker */}
        <Script id="register-sw" strategy="afterInteractive">
          {`
            if ('serviceWorker' in navigator) {
              window.addEventListener('load', function() {
                navigator.serviceWorker.register('/sw.js').then(
                  function(reg) { console.log('⚡ [SW] Scope:', reg.scope); },
                  function(err) { console.log('❌ [SW] Failed:', err); }
                );
              });
            }
          `}
        </Script>
      </body>
    </html>
  );
}