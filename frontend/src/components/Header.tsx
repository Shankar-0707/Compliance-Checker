"use client";

import React from "react";
import { ShieldCheck, Server, AlertCircle, FileText } from "lucide-react";
import { IS_REAL_BACKEND_CONFIGURED } from "@/lib/api";

export function Header() {
  return (
    <header className="sticky top-0 z-30 border-b border-slate-200 bg-white/95 backdrop-blur dark:border-slate-800 dark:bg-slate-900/95">
      <div className="mx-auto flex max-w-7xl items-center justify-between px-4 py-3.5 sm:px-6 lg:px-8">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-emerald-600 to-teal-500 text-white shadow-sm shadow-emerald-500/20">
            <ShieldCheck className="h-6 w-6" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h1 className="text-lg font-bold tracking-tight text-slate-900 dark:text-white">
                LabelGuard AI
              </h1>
              <span className="rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-semibold text-emerald-700 ring-1 ring-inset ring-emerald-600/20 dark:bg-emerald-950/60 dark:text-emerald-300">
                Copilot
              </span>
            </div>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              E-Commerce Product Compliance & Health Rating Analyzer
            </p>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {IS_REAL_BACKEND_CONFIGURED ? (
            <div className="flex items-center gap-1.5 rounded-lg border border-emerald-200 bg-emerald-50/70 px-3 py-1.5 text-xs font-medium text-emerald-800 dark:border-emerald-800/60 dark:bg-emerald-950/50 dark:text-emerald-300">
              <Server className="h-3.5 w-3.5 text-emerald-600" />
              <span>Backend Connected: {process.env.NEXT_PUBLIC_API_URL}</span>
            </div>
          ) : (
            <div className="flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50/70 px-3 py-1.5 text-xs font-medium text-amber-800 dark:border-amber-800/60 dark:bg-amber-950/50 dark:text-amber-300">
              <AlertCircle className="h-3.5 w-3.5 text-amber-600" />
              <span>Demo Mode (Mock Route)</span>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
