"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { Download, List, Upload, Settings } from "lucide-react";
import clsx from "clsx";

const nav = [
  { href: "/", label: "Kênh & Video", icon: List },
  { href: "/jobs", label: "Hàng đợi", icon: Download },
  { href: "/tiktok", label: "TikTok", icon: Upload },
];

export default function Navbar() {
  const pathname = usePathname();

  return (
    <header className="bg-dark-800 border-b border-dark-600 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 h-14 flex items-center justify-between">
        {/* Logo */}
        <Link href="/" className="flex items-center gap-2 font-bold text-lg">
          <span className="text-2xl">🎵</span>
          <span className="text-brand-500">Douyin</span>
          <span className="text-gray-400 text-sm font-normal">→</span>
          <span className="text-white">TikTok</span>
        </Link>

        {/* Navigation */}
        <nav className="flex items-center gap-1">
          {nav.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className={clsx(
                "flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-all duration-200",
                pathname === href
                  ? "bg-brand-600 text-white"
                  : "text-gray-400 hover:text-white hover:bg-dark-700"
              )}
            >
              <Icon size={16} />
              <span className="hidden sm:inline">{label}</span>
            </Link>
          ))}
        </nav>
      </div>
    </header>
  );
}
