"use client";

import { Upload, Cpu, TableProperties, Download, ArrowRight } from "lucide-react";

const steps = [
  {
    step: "01",
    icon: <Upload className="w-6 h-6" />,
    title: "Upload Drawing PDF",
    description:
      "Drop in a CAD-exported structural steel drawing — member schedules and framing plans. Select which pages to analyze.",
  },
  {
    step: "02",
    icon: <Cpu className="w-6 h-6" />,
    title: "Gemini Vision Extracts",
    description:
      "Pages are rendered to high-res PNG and sent to Gemini 3.8 Flash. The model returns a structured JSON of every detected steel member.",
  },
  {
    step: "03",
    icon: <TableProperties className="w-6 h-6" />,
    title: "Review & Correct",
    description:
      "An editable table shows member_id, section, length_mm, quantity, and calculated unit weight. Fix AI errors inline before export.",
  },
  {
    step: "04",
    icon: <Download className="w-6 h-6" />,
    title: "Export to Excel",
    description:
      "Download a timestamped .xlsx with a BOQ sheet and a Summary sheet showing total quantity and estimated tonnage.",
  },
];

export default function HowItWorks() {
  return (
    <section id="how-it-works" className="py-24 px-4 border-t border-white/5">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-16">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-4 tracking-tight">
            How it works
          </h2>
          <p className="text-lg text-gray-400 max-w-xl mx-auto">
            Four steps from PDF upload to an accurate, auditable Bill of Quantities.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {steps.map((item, index) => (
            <div key={index} className="relative group">
              {/* Connector line */}
              {index < steps.length - 1 && (
                <div className="hidden lg:block absolute top-8 left-[calc(100%-1rem)] w-8 z-10">
                  <ArrowRight className="w-5 h-5 text-gray-600" />
                </div>
              )}

              <div className="p-6 rounded-2xl border border-white/8 bg-white/3 hover:border-blue-500/30 hover:bg-blue-500/5 transition-all duration-300 h-full">
                {/* Step number */}
                <div className="text-xs font-mono font-bold text-blue-500/60 mb-4">
                  {item.step}
                </div>

                {/* Icon */}
                <div className="w-12 h-12 rounded-xl bg-blue-500/15 border border-blue-500/20 flex items-center justify-center text-blue-400 mb-5">
                  {item.icon}
                </div>

                <h3 className="text-base font-bold text-white mb-2">
                  {item.title}
                </h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  {item.description}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
