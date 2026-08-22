import type { Metadata } from "next";
import "./globals.css";
import { Header } from "@/components/Header";

export const metadata: Metadata = {
  title: "LabelGuard AI — Product Compliance & Health Rating Copilot",
  description:
    "Automated Legal Metrology & FSSAI regulatory compliance auditing and Open Food Facts ML health rating for e-commerce product labels.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col antialiased">
        <Header />
        <main className="flex-1 px-4 py-8 sm:px-6 lg:px-8 max-w-7xl mx-auto w-full">
          {children}
        </main>
        <footer className="border-t border-slate-200 bg-white py-6 text-center text-xs text-slate-500 dark:border-slate-800 dark:bg-slate-900 dark:text-slate-400">
          <div className="mx-auto max-w-7xl px-4">
            LabelGuard AI &bull; Legal Metrology Rules (2011) &bull; FSSAI Labelling Regulations (2020) &bull; Open Food Facts Nutri-Score ML
          </div>
        </footer>
      </body>
    </html>
  );
}
