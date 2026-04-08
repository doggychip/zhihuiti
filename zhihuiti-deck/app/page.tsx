"use client";

import { motion } from "framer-motion";
import OntologyGraph from "@/components/OntologyGraph";
import StatusBar from "@/components/StatusBar";

export default function ZhihuitiDeck() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-midnight overflow-hidden relative">
      {/* 背景微粒效果 */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(96,165,250,0.03)_0%,_transparent_70%)]" />

      {/* 圖譜 */}
      <OntologyGraph />

      {/* 標題 */}
      <motion.h1
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 0.5, y: 0 }}
        transition={{ delay: 0.5, duration: 1.5 }}
        className="mt-10 text-[10px] tracking-[0.6em] uppercase font-light text-ice"
      >
        Zhihuiti City / Midnight Watch
      </motion.h1>

      <motion.p
        initial={{ opacity: 0 }}
        animate={{ opacity: 0.25 }}
        transition={{ delay: 1.2, duration: 2 }}
        className="mt-2 text-[9px] tracking-[0.3em] text-ice/40"
      >
        Autonomous Intelligence Mesh — Observing
      </motion.p>

      {/* 狀態條 */}
      <StatusBar />
    </main>
  );
}
