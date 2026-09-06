import "./globals.css";

export const metadata = {
  title: "Blue Grid — Lakshadweep Multi-Energy Optimization",
  description:
    "Interactive planner for Solar + Wind + OTEC + BESS microgrids on Lakshadweep islands. CODEQUADRANTS · Ocean Hackathon.",
};

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-screen text-slate-800 antialiased">{children}</body>
    </html>
  );
}
