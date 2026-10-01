import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { Source_Serif_4 } from "next/font/google";
import { Navbar } from "@/components/navbar";
import { AuthProvider } from "@/lib/auth";
import { ThemeProvider } from "@/lib/theme";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

const sourceSerif = Source_Serif_4({
  variable: "--font-source-serif",
  subsets: ["latin"],
  weight: ["400", "600", "700"],
});

export const metadata: Metadata = {
  title: "ResearchForge AI",
  description: "Autonomous multi-agent research and intelligence platform",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} ${sourceSerif.variable} h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script
          dangerouslySetInnerHTML={{
            __html: `(function(){try{var t=localStorage.getItem('rf_theme');var d=t==='dark'||(t!=='light'&&matchMedia('(prefers-color-scheme:dark)').matches);document.documentElement.setAttribute('data-theme',d?'dark':'light')}catch(e){}})()`,
          }}
        />
      </head>
      <body className="flex min-h-full flex-col bg-background">
        <AuthProvider>
          <ThemeProvider>
            <Navbar />
            <main className="flex-1">
              <div className="mx-auto max-w-6xl px-6 py-10">{children}</div>
            </main>
          </ThemeProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
