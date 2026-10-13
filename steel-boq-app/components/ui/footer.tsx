import { FileText, GitBranch, ExternalLink } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-white/5 py-12 px-4 mt-16">
      <div className="max-w-7xl mx-auto flex flex-col md:flex-row items-center justify-between gap-6">
        {/* Logo */}
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center">
            <FileText className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="font-bold text-white">
            Steel<span className="text-blue-400">BOQ</span>
          </span>
          <span className="text-gray-600 text-sm">MVP · Research Project</span>
        </div>

        {/* Links */}
        <div className="flex items-center gap-6 text-sm text-gray-500">
          <a
            href="https://github.com/Tontonji/Steel-Tech-Project"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 hover:text-gray-300 transition-colors"
          >
            <GitBranch className="w-4 h-4" />
            GitHub
          </a>
          <a
            href="http://localhost:8501"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1.5 hover:text-gray-300 transition-colors"
          >
            <ExternalLink className="w-4 h-4" />
            Streamlit App
          </a>
        </div>

        <p className="text-xs text-gray-600 text-center md:text-right">
          Built with Gemini 3.8 Flash · Python + Streamlit · Next.js
        </p>
      </div>
    </footer>
  );
}
