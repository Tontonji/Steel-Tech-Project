"use client";

import { FileText, GitBranch, Beaker } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";

export default function Navbar() {
  const router = useRouter();

  return (
    <nav className="fixed top-0 left-0 right-0 z-50 border-b border-white/5 bg-black/60 backdrop-blur-xl">
      <div className="max-w-7xl mx-auto px-6 py-4 flex items-center justify-between">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center">
            <FileText className="w-4 h-4 text-white" />
          </div>
          <span className="font-bold text-white text-lg tracking-tight">
            Steel<span className="text-blue-400">BOQ</span>
          </span>
          <span className="px-1.5 py-0.5 text-[10px] font-semibold rounded bg-blue-500/20 text-blue-400 border border-blue-500/30 uppercase tracking-wide">
            MVP
          </span>
        </div>

        {/* Nav links */}
        <div className="hidden md:flex items-center gap-6 text-sm text-gray-400">
          <Link href="#features" className="hover:text-white transition-colors">
            Features
          </Link>
          <Link href="#how-it-works" className="hover:text-white transition-colors">
            How it works
          </Link>
          <Link href="#research" className="hover:text-white transition-colors">
            Research
          </Link>
        </div>

        {/* CTA buttons */}
        <div className="flex items-center gap-3">
          <a
            href="https://github.com/Tontonji/Steel-Tech-Project"
            target="_blank"
            rel="noopener noreferrer"
            className="p-2 rounded-lg border border-white/10 hover:border-white/25 hover:bg-white/5 transition-all"
            title="GitHub Repository"
          >
            <GitBranch className="w-4 h-4 text-gray-400" />
          </a>
          <button
            onClick={() => router.push("/extractor")}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
          >
            <Beaker className="w-4 h-4" />
            Open App
          </button>
        </div>
      </div>
    </nav>
  );
}
