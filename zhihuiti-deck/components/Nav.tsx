"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { href: "/", label: "Home" },
  { href: "/deck", label: "Deck" },
  { href: "/agents", label: "Agents" },
];

export default function Nav() {
  const pathname = usePathname();

  return (
    <nav className="fixed top-0 left-0 w-full h-10 bg-midnight/90 backdrop-blur-md border-b border-ice/8 flex items-center px-6 gap-6 z-50 font-mono">
      <span className="text-[10px] tracking-[0.4em] uppercase text-gold/60 mr-4">
        智慧體
      </span>
      {NAV_ITEMS.map((item) => (
        <Link
          key={item.href}
          href={item.href}
          className={`text-[10px] tracking-[0.3em] uppercase transition-opacity ${
            pathname === item.href
              ? "text-ice opacity-80"
              : "text-ice/30 hover:text-ice/60"
          }`}
        >
          {item.label}
        </Link>
      ))}
    </nav>
  );
}
