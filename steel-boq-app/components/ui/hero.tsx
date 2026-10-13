"use client";

import { Beaker, ArrowRight, GitBranch, FileText, Layers } from "lucide-react";
import { useRouter } from "next/navigation";

export default function Hero() {
  const router = useRouter();

  return (
    <section className="relative min-h-screen flex flex-col items-center justify-center px-4 pt-20 overflow-hidden">
      {/* Background grid */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `
            linear-gradient(rgba(88,166,255,0.08) 1px, transparent 1px),
            linear-gradient(90deg, rgba(88,166,255,0.08) 1px, transparent 1px)
          `,
          backgroundSize: "48px 48px",
        }}
      />

      {/* Radial glow */}
      <div
        className="absolute top-1/4 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full opacity-10"
        style={{
          background: "radial-gradient(circle, hsl(210,100%,50%) 0%, transparent 70%)",
          filter: "blur(80px)",
        }}
      />

      {/* Content */}
      <div className="relative z-10 text-center max-w-4xl mx-auto">
        {/* Badge */}
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-sm font-medium mb-8">
          <Layers className="w-3.5 h-3.5" />
          Undergraduate Research MVP · Gemini 3.8 Flash
        </div>

        {/* Headline */}
        <h1 className="text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 leading-[1.05] tracking-tight">
          Steel Drawing{" "}
          <span className="bg-gradient-to-r from-blue-400 via-cyan-400 to-blue-500 bg-clip-text text-transparent">
            → BOQ
          </span>
          <br />
          in Seconds
        </h1>

        {/* Sub-headline */}
        <p className="text-xl text-gray-400 max-w-2xl mx-auto mb-10 leading-relaxed">
          Upload any CAD-exported structural steel PDF. Gemini Vision extracts every
          member, section, length, and quantity into an editable Bill of Quantities —
          then exports to Excel.
        </p>

        {/* CTA row */}
        <div className="flex flex-wrap items-center justify-center gap-4 mb-16">
          <button
            onClick={() => router.push("/extractor")}
            className="flex items-center gap-2.5 px-7 py-3.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold text-base transition-all shadow-lg shadow-blue-600/25 hover:shadow-blue-500/40 hover:-translate-y-0.5"
          >
            <Beaker className="w-5 h-5" />
            Launch Extractor
            <ArrowRight className="w-4 h-4" />
          </button>
          <a
            href="https://github.com/Tontonji/Steel-Tech-Project"
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2.5 px-7 py-3.5 rounded-xl border border-white/[0.12] hover:border-white/25 hover:bg-white/5 text-gray-300 hover:text-white font-semibold text-base transition-all"
          >
            <GitBranch className="w-5 h-5" />
            View Source
          </a>
        </div>

        {/* Stats row */}
        <div className="flex flex-wrap items-center justify-center gap-8 text-sm text-gray-500">
          {[
            { label: "Members extracted", value: "12+" },
            { label: "Avg. latency", value: "~7s" },
            { label: "Supported formats", value: "CAD PDF" },
            { label: "Export formats", value: "Excel" },
          ].map((stat) => (
            <div key={stat.label} className="text-center">
              <div className="text-2xl font-bold text-white mb-0.5">{stat.value}</div>
              <div>{stat.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Floating mockup card */}
      <div className="relative z-10 mt-16 w-full max-w-3xl mx-auto">
        <div className="rounded-2xl border border-white/10 bg-[#161b22]/80 backdrop-blur-xl overflow-hidden shadow-2xl shadow-black/50">
          {/* Window bar */}
          <div className="flex items-center gap-2 px-5 py-3.5 border-b border-white/8">
            <div className="w-3 h-3 rounded-full bg-red-500/60" />
            <div className="w-3 h-3 rounded-full bg-yellow-500/60" />
            <div className="w-3 h-3 rounded-full bg-green-500/60" />
            <div className="flex items-center gap-2 ml-4 text-xs text-gray-500 font-mono">
              <FileText className="w-3.5 h-3.5" />
              steel_boq_extractor · localhost:3000/extractor
            </div>
          </div>

          {/* BOQ Table mockup */}
          <div className="p-5 overflow-x-auto">
            <table className="w-full text-xs font-mono">
              <thead>
                <tr className="text-gray-500">
                  <th className="text-left py-2 pr-6 font-medium">member_id</th>
                  <th className="text-left py-2 pr-6 font-medium">section</th>
                  <th className="text-right py-2 pr-6 font-medium">length_mm</th>
                  <th className="text-right py-2 pr-6 font-medium">qty</th>
                  <th className="text-right py-2 font-medium">unit_wt (kg/m)</th>
                </tr>
              </thead>
              <tbody className="text-gray-300">
                {[
                  { id: "B1", section: "H-300×150×6.5×9", len: "6,000", qty: 8, wt: "36.7" },
                  { id: "C2", section: "H-350×350×12×19", len: "4,500", qty: 4, wt: "137.0" },
                  { id: "GB-01", section: "H-400×200×8×13", len: "7,500", qty: 6, wt: "66.0" },
                  { id: "BR-1", section: "L-90×90×9", len: "—", qty: 12, wt: "—" },
                  { id: "P1", section: "W12×26", len: "3,600", qty: 2, wt: "38.7" },
                ].map((row, i) => (
                  <tr key={i} className="border-t border-white/5 hover:bg-white/3 transition-colors">
                    <td className="py-2.5 pr-6 text-blue-400 font-semibold">{row.id}</td>
                    <td className="py-2.5 pr-6">{row.section}</td>
                    <td className="py-2.5 pr-6 text-right">{row.len}</td>
                    <td className="py-2.5 pr-6 text-right">{row.qty}</td>
                    <td className="py-2.5 text-right text-green-400">{row.wt}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {/* Footer bar */}
          <div className="flex items-center justify-between px-5 py-3 border-t border-white/8 text-xs text-gray-500">
            <span>5 members · Total qty: 32</span>
            <span className="px-2 py-0.5 rounded bg-green-500/15 text-green-400 border border-green-500/20">
              Extracted in 6.4 s
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
