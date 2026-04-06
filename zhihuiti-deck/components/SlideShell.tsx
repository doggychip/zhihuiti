"use client";

import { motion } from "framer-motion";
import { ReactNode } from "react";

interface SlideShellProps {
  children: ReactNode;
  index: number;
  total: number;
}

export default function SlideShell({ children, index, total }: SlideShellProps) {
  return (
    <section
      id={`slide-${index}`}
      className="relative min-h-screen w-full flex flex-col items-center justify-center px-6 py-20 snap-start"
    >
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_center,_rgba(96,165,250,0.03)_0%,_transparent_70%)]" />
      <motion.div
        initial={{ opacity: 0, y: 24 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: "-100px" }}
        transition={{ duration: 0.8, ease: "easeOut" }}
        className="relative z-10 max-w-3xl w-full"
      >
        {children}
      </motion.div>

      {/* Slide counter */}
      <div className="absolute bottom-6 right-6 text-[9px] tracking-[0.3em] opacity-20 font-mono">
        {String(index + 1).padStart(2, "0")} / {String(total).padStart(2, "0")}
      </div>
    </section>
  );
}
