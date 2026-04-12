import type { Metadata } from "next";
import "./globals.css";
import Nav from "@/components/Nav";

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
      <body className="bg-midnight min-h-screen antialiased pt-10">
        <Nav />
        {children}
      </body>
    </html>
  );
}
