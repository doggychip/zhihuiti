"use client";

import { useEffect, useState } from "react";
import { NODES } from "./OntologyGraph";

export default function StatusBar() {
  const [latency, setLatency] = useState(24);
  const [tokenCount, setTokenCount] = useState(0);

  useEffect(() => {
    const interval = setInterval(() => {
      setLatency(Math.floor(18 + Math.random() * 12));
      setTokenCount((prev) => prev + Math.floor(Math.random() * 50));
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  return (
    <footer className="fixed bottom-0 left-0 w-full h-8 border-t border-ice/10 bg-midnight/90 backdrop-blur-md flex items-center px-4 justify-between text-[10px] tracking-widest font-mono z-50">
      <div className="flex gap-4">
        <span className="text-gold">● ONLINE</span>
        <span className="opacity-40">NODES: {NODES.length}</span>
        <span className="opacity-30">AGENTS_ACTIVE: 3</span>
      </div>
      <div className="opacity-30 hidden sm:block">
        LATENCY: {latency}MS &nbsp;|&nbsp; TOKENS: {tokenCount.toLocaleString()} &nbsp;|&nbsp; MODE: SENTINEL
      </div>
    </footer>
  );
}
