import "@fontsource/inter/400.css";
import "@fontsource/inter/500.css";
import "@fontsource/inter/600.css";
import "@fontsource/inter/700.css";
import "@fontsource/inter/800.css";
import "@fontsource/inter/900.css";
import "./globals.css";
import Providers from "@/components/providers";

export const metadata = {
  title: { default: "NEXUS", template: "%s · NEXUS" },
  description: "Adaptive Competency & Career Learning Loop — Empowering Statistical Officers for a Data-Ready India.",
};
export const viewport = { width: "device-width", initialScale: 1, themeColor: "#1464E8" };
// Rendered per request so the middleware's CSP nonce is applied to Next's own scripts.
export const dynamic = "force-dynamic";

export default function RootLayout({ children }) {
  return (
    <html lang="en">
      <body className="min-h-dvh">
        <a href="#main" className="sr-only focus:not-sr-only focus:fixed focus:left-2 focus:top-2 focus:z-50 focus:rounded-md focus:bg-surface focus:px-3 focus:py-2">Skip to content</a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
