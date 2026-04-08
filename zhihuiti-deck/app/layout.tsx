import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "智慧體 Zhihuiti — Midnight Watch",
  description: "Autonomous multi-agent intelligence system. Observing.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="bg-midnight min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
