"use client";

import React, { useState } from "react";
import { Warp } from "@paper-design/shaders-react";
import {
  Sparkles,
  Zap,
  Puzzle,
  Sliders,
  Smartphone,
  Cpu,
  ArrowRight,
  X,
} from "lucide-react";

interface Feature {
  title: string;
  description: string;
  detail: string;
  icon: React.ReactNode;
}

const features: Feature[] = [
  {
    title: "Vision AI Extraction",
    description:
      "Gemini multimodal vision reads CAD-exported PDFs and extracts every steel member automatically.",
    detail:
      "Using Google Gemini 3.8 Flash (Vision mode), the app renders each PDF page to a high-resolution PNG (up to 300 DPI) and sends it as an image payload to the model. The model returns a structured JSON array containing member_id, section, length_mm, quantity, and notes for every steel member it detects on the drawing — with zero manual input required.",
    icon: <Sparkles className="w-10 h-10 text-white" />,
  },
  {
    title: "High Performance",
    description:
      "Optimized WebGL shaders and image payloads keep latency under 10 seconds per extraction.",
    detail:
      "Pages are rendered at 220 DPI by default (adjustable via slider). The DPI-to-payload tradeoff is explicitly designed: lower DPI = faster response, higher DPI = better legibility for dense drawings. Each extraction run is capped at 10 pages per API call to stay within token limits. Typical latency for a 2-page member schedule is 6–9 seconds.",
    icon: <Zap className="w-10 h-10 text-white" />,
  },
  {
    title: "Instant Integration",
    description:
      "Upload a PDF, click Extract, and get an editable BOQ table in seconds — no manual data entry.",
    detail:
      "The workflow is a single Streamlit page: upload PDF → select page range → click Extract → review & correct inline → download Excel. There is no login, no database, no cloud storage. All data stays on your local machine. The app is designed to be dropped into any research environment with a single 'streamlit run app.py' command.",
    icon: <Puzzle className="w-10 h-10 text-white" />,
  },
  {
    title: "Inline Editing",
    description:
      "Correct AI errors directly in the table. Every cell is editable before you export.",
    detail:
      "The extracted BOQ is rendered as a Streamlit st.data_editor table. You can correct any cell — member ID, section designation, length, quantity, or notes — before downloading. The Excel export always reflects your final corrected version, not the raw AI output. This human-in-the-loop design is intentional for research accuracy.",
    icon: <Sliders className="w-10 h-10 text-white" />,
  },
  {
    title: "Excel Export",
    description:
      "Download a timestamped .xlsx with a BOQ sheet and Summary showing total tonnage.",
    detail:
      "The exported Excel file (boq_{filename}_{timestamp}.xlsx) contains two sheets: 'BOQ' with the full edited table (member_id, section, length_mm, quantity, unit_weight_kg_m, notes) and 'Summary' with aggregate totals — distinct member count, total quantity, and estimated total weight in kg. The timestamp links the file to its corresponding JSON log entry.",
    icon: <Smartphone className="w-10 h-10 text-white" />,
  },
  {
    title: "Research Grade Logging",
    description:
      "Every run logs raw response, latency, parsed rows, and model info to a local JSON file.",
    detail:
      "Each click of Extract writes a timestamped JSON file to logs/YYYYMMDD_HHMMSS.json containing: timestamp, app_version, source_filename, model name, pages extracted, DPI used, latency_s (from API call start to parse complete), error (null if success), raw_response (the full model output string), and parsed_rows (the final structured array). These logs are the primary dataset for the research comparison against manual takeoff.",
    icon: <Cpu className="w-10 h-10 text-white" />,
  },
];

export default function FeaturesCards() {
  const [selectedFeature, setSelectedFeature] = useState<Feature | null>(null);

  const getShaderConfig = (index: number) => {
    const configs = [
      {
        proportion: 0.3, softness: 0.8, distortion: 0.15, swirl: 0.6,
        swirlIterations: 8, shape: "checks" as const, shapeScale: 0.08,
        colors: ["hsl(210, 100%, 18%)", "hsl(200, 100%, 45%)", "hsl(190, 90%, 28%)", "hsl(205, 100%, 60%)"],
      },
      {
        proportion: 0.4, softness: 1.2, distortion: 0.2, swirl: 0.9,
        swirlIterations: 12, shape: "stripes" as const, shapeScale: 0.12,
        colors: ["hsl(220, 80%, 15%)", "hsl(240, 90%, 55%)", "hsl(230, 80%, 30%)", "hsl(245, 100%, 70%)"],
      },
      {
        proportion: 0.35, softness: 0.9, distortion: 0.18, swirl: 0.7,
        swirlIterations: 10, shape: "checks" as const, shapeScale: 0.1,
        colors: ["hsl(175, 100%, 15%)", "hsl(180, 100%, 45%)", "hsl(165, 90%, 25%)", "hsl(178, 100%, 60%)"],
      },
      {
        proportion: 0.45, softness: 1.1, distortion: 0.22, swirl: 0.8,
        swirlIterations: 15, shape: "stripes" as const, shapeScale: 0.09,
        colors: ["hsl(195, 100%, 20%)", "hsl(210, 100%, 55%)", "hsl(200, 90%, 30%)", "hsl(212, 100%, 68%)"],
      },
      {
        proportion: 0.38, softness: 0.95, distortion: 0.16, swirl: 0.85,
        swirlIterations: 11, shape: "checks" as const, shapeScale: 0.11,
        colors: ["hsl(250, 80%, 20%)", "hsl(260, 100%, 58%)", "hsl(255, 90%, 32%)", "hsl(265, 100%, 72%)"],
      },
      {
        proportion: 0.42, softness: 1.0, distortion: 0.19, swirl: 0.75,
        swirlIterations: 9, shape: "edge" as const, shapeScale: 0.13,
        colors: ["hsl(185, 100%, 18%)", "hsl(195, 100%, 48%)", "hsl(190, 90%, 28%)", "hsl(200, 100%, 65%)"],
      },
    ];
    return configs[index % configs.length];
  };

  return (
    <>
      <section className="py-24 px-4">
        <div className="max-w-7xl mx-auto">
          <div className="text-center mb-16">
            <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full border border-blue-500/30 bg-blue-500/10 text-blue-400 text-sm font-medium mb-6">
              <Sparkles className="w-3.5 h-3.5" />
              Powered by Gemini 3.8 Vision
            </div>
            <h2 className="text-4xl md:text-5xl font-bold text-white mb-6 tracking-tight">
              Why Steel BOQ Extractor?
            </h2>
            <p className="text-xl text-gray-400 max-w-2xl mx-auto leading-relaxed">
              Everything you need to turn a structural drawing PDF into a verified
              Bill of Quantities — in seconds, not hours.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {features.map((feature, index) => {
              const shaderConfig = getShaderConfig(index);
              return (
                <div key={index} className="relative h-80 group cursor-pointer"
                  onClick={() => setSelectedFeature(feature)}
                >
                  {/* Shader background */}
                  <div className="absolute inset-0 rounded-2xl overflow-hidden transition-transform duration-500 group-hover:scale-[1.02]">
                    <Warp
                      style={{ height: "100%", width: "100%" }}
                      proportion={shaderConfig.proportion}
                      softness={shaderConfig.softness}
                      distortion={shaderConfig.distortion}
                      swirl={shaderConfig.swirl}
                      swirlIterations={shaderConfig.swirlIterations}
                      shape={shaderConfig.shape}
                      shapeScale={shaderConfig.shapeScale}
                      scale={1}
                      rotation={0}
                      speed={0.6}
                      colors={shaderConfig.colors}
                    />
                  </div>

                  {/* Glass card overlay */}
                  <div className="relative z-10 p-7 rounded-2xl h-full flex flex-col bg-black/75 backdrop-blur-md border border-white/10 transition-all duration-300 group-hover:border-white/30 group-hover:bg-black/65">
                    <div className="mb-5 p-2.5 w-fit rounded-xl bg-white/10 backdrop-blur-sm">
                      {feature.icon}
                    </div>

                    <h3 className="text-xl font-bold mb-3 text-white">
                      {feature.title}
                    </h3>

                    <p className="text-sm leading-relaxed flex-grow text-gray-300">
                      {feature.description}
                    </p>

                    <button
                      onClick={(e) => { e.stopPropagation(); setSelectedFeature(feature); }}
                      className="mt-5 flex items-center gap-1.5 text-xs font-semibold text-blue-400 group-hover:text-blue-300 transition-colors cursor-pointer hover:gap-2.5"
                    >
                      <span>Learn more</span>
                      <ArrowRight className="w-3.5 h-3.5 transition-transform group-hover:translate-x-1" />
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Feature Detail Modal */}
      {selectedFeature && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center p-4"
          onClick={() => setSelectedFeature(null)}
        >
          {/* Backdrop */}
          <div className="absolute inset-0 bg-black/70 backdrop-blur-sm" />

          {/* Modal */}
          <div
            className="relative z-10 w-full max-w-lg rounded-2xl border border-white/15 bg-[#161b22] shadow-2xl shadow-black/60 p-8"
            onClick={(e) => e.stopPropagation()}
          >
            {/* Close button */}
            <button
              onClick={() => setSelectedFeature(null)}
              className="absolute top-4 right-4 p-1.5 rounded-lg hover:bg-white/10 text-gray-500 hover:text-white transition-all"
            >
              <X className="w-4 h-4" />
            </button>

            {/* Icon */}
            <div className="mb-5 p-3 w-fit rounded-xl bg-blue-500/15 border border-blue-500/20">
              {selectedFeature.icon}
            </div>

            <h3 className="text-2xl font-bold text-white mb-3">
              {selectedFeature.title}
            </h3>

            <p className="text-sm text-gray-400 leading-relaxed mb-6">
              {selectedFeature.detail}
            </p>

            <div className="flex gap-3">
              <a
                href="http://localhost:8501"
                target="_blank"
                rel="noopener noreferrer"
                className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium transition-colors"
              >
                Try it in the App
                <ArrowRight className="w-4 h-4" />
              </a>
              <button
                onClick={() => setSelectedFeature(null)}
                className="px-4 py-2.5 rounded-xl border border-white/10 hover:border-white/25 text-gray-400 hover:text-white text-sm font-medium transition-all"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
