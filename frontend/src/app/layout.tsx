import type { Metadata } from "next";
import { IBM_Plex_Mono, Outfit, Space_Grotesk } from "next/font/google";

import { AppShell } from "@/components/layout/AppShell";
import { QueryProvider } from "@/lib/query/provider";

import "./globals.css";

const display = Space_Grotesk({
  variable: "--font-display",
  subsets: ["latin"],
  weight: ["500", "600", "700"],
});

const body = Outfit({
  variable: "--font-body",
  subsets: ["latin"],
  weight: ["400", "500", "600", "700"],
});

const mono = IBM_Plex_Mono({
  variable: "--font-mono",
  subsets: ["latin"],
  weight: ["400", "500", "600"],
});

export const metadata: Metadata = {
  title: {
    default: "CENTINELA · Consola del analista",
    template: "%s · CENTINELA",
  },
  description: "Consola moderna de revisión de casos de fraude.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="es">
      <body
        className={`${display.variable} ${body.variable} ${mono.variable} antialiased`}
      >
        <QueryProvider>
          <AppShell>{children}</AppShell>
        </QueryProvider>
      </body>
    </html>
  );
}
