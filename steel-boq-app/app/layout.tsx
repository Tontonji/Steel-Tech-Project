import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Steel BOQ Extractor — AI-Powered Structural Steel Takeoff",
  description:
    "Upload a structural steel drawing PDF. Gemini Vision extracts every member, section, length, and quantity into an editable Bill of Quantities — ready to export as Excel.",
  keywords: ["steel", "BOQ", "bill of quantities", "structural", "AI", "Gemini", "CAD", "takeoff"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className={inter.variable}>
      <body className="antialiased min-h-screen bg-background text-foreground">
        {children}
      </body>
    </html>
  );
}
