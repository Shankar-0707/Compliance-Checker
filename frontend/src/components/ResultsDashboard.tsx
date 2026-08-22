"use client";

import React, { useState } from "react";
import { CheckCircle2, XCircle, RotateCcw, Code2, Copy, Check, ShieldCheck, HeartPulse, ExternalLink } from "lucide-react";
import { AnalyzeResponse } from "@/types";
import { ComplianceSection } from "./ComplianceSection";
import { HealthRatingSection } from "./HealthRatingSection";
import { NUTRI_SCORE_CONFIG } from "@/lib/constants";

interface ResultsDashboardProps {
  data: AnalyzeResponse;
  onReset: () => void;
}

export function ResultsDashboard({ data, onReset }: ResultsDashboardProps) {
  const [showJsonModal, setShowJsonModal] = useState<boolean>(false);
  const [copied, setCopied] = useState<boolean>(false);

  const complianceResults = data.compliance?.results || [];
  const failedCompliance = complianceResults.filter((r) => !r.passed);
  const isFullyCompliant = failedCompliance.length === 0;

  const healthGrade = data.health?.grade ? data.health.grade.toUpperCase() : null;
  const gradeConfig = healthGrade ? NUTRI_SCORE_CONFIG[healthGrade] || NUTRI_SCORE_CONFIG["C"] : null;

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(data, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="space-y-6">
      {/* Top Banner Summary Card */}
      <div className="relative overflow-hidden rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex flex-col gap-5 md:flex-row md:items-center md:justify-between">
          <div className="space-y-1.5">
            <div className="flex items-center gap-2">
              <span
                className={`inline-flex items-center gap-1.5 rounded-full px-3 py-1 text-xs font-bold ${
                  isFullyCompliant
                    ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                    : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                }`}
              >
                {isFullyCompliant ? (
                  <>
                    <CheckCircle2 className="h-3.5 w-3.5" />
                    <span>ALL REGULATORY CHECKS PASSED</span>
                  </>
                ) : (
                  <>
                    <XCircle className="h-3.5 w-3.5" />
                    <span>{failedCompliance.length} REGULATORY NON-COMPLIANCE DETECTED</span>
                  </>
                )}
              </span>

              {healthGrade && gradeConfig && (
                <span
                  className={`inline-flex items-center rounded-full px-3 py-1 text-xs font-bold text-white ${gradeConfig.bg}`}
                >
                  Nutri-Score {healthGrade}
                </span>
              )}
            </div>

            <h2 className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
              {isFullyCompliant
                ? "Product Label Meets Regulatory Standards"
                : "Action Required: Rectify Labeling Non-Compliances"}
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Analysis completed. Review the legal Metrology & FSSAI checklist and health evaluation below.
            </p>
          </div>

          <div className="flex items-center gap-2.5 self-start md:self-center">
            <button
              type="button"
              onClick={() => setShowJsonModal(true)}
              className="inline-flex items-center gap-1.5 rounded-xl border border-slate-200 bg-slate-50 px-3.5 py-2 text-xs font-semibold text-slate-700 hover:bg-slate-100 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200 dark:hover:bg-slate-700"
            >
              <Code2 className="h-4 w-4" />
              <span>Inspect API JSON</span>
            </button>

            <button
              type="button"
              onClick={onReset}
              className="inline-flex items-center gap-1.5 rounded-xl bg-slate-900 px-4 py-2 text-xs font-semibold text-white shadow-sm hover:bg-slate-800 dark:bg-emerald-600 dark:hover:bg-emerald-500"
            >
              <RotateCcw className="h-4 w-4" />
              <span>Analyze Another Product</span>
            </button>
          </div>
        </div>
      </div>

      {/* Main Results Grid */}
      <div className="grid grid-cols-1 gap-6 xl:grid-cols-2">
        {/* Compliance Checklist Column */}
        <ComplianceSection compliance={data.compliance} />

        {/* Health Rating Column */}
        <HealthRatingSection health={data.health} />
      </div>

      {/* JSON Inspector Modal */}
      {showJsonModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm">
          <div className="relative max-h-[85vh] w-full max-w-2xl overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-2xl dark:border-slate-800 dark:bg-slate-900">
            <div className="flex items-center justify-between border-b border-slate-200 px-6 py-4 dark:border-slate-800">
              <div className="flex items-center gap-2">
                <Code2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Backend API Response JSON (/api/analyze)
                </h3>
              </div>
              <button
                type="button"
                onClick={() => setShowJsonModal(false)}
                className="rounded-lg p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-700 dark:hover:bg-slate-800 dark:hover:text-slate-200"
              >
                ✕
              </button>
            </div>

            <div className="overflow-auto p-6 max-h-[60vh]">
              <pre className="rounded-xl bg-slate-950 p-4 text-xs font-mono text-emerald-400 leading-relaxed overflow-x-auto">
                {JSON.stringify(data, null, 2)}
              </pre>
            </div>

            <div className="flex items-center justify-between border-t border-slate-200 px-6 py-3 bg-slate-50 dark:border-slate-800 dark:bg-slate-900/50">
              <span className="text-xs text-slate-500">
                Matches exact section 4.3 specification contract
              </span>
              <button
                type="button"
                onClick={handleCopyJson}
                className="inline-flex items-center gap-1.5 rounded-lg bg-white px-3 py-1.5 text-xs font-semibold text-slate-800 shadow-sm border border-slate-200 hover:bg-slate-50 dark:border-slate-700 dark:bg-slate-800 dark:text-white dark:hover:bg-slate-700"
              >
                {copied ? <Check className="h-3.5 w-3.5 text-emerald-600" /> : <Copy className="h-3.5 w-3.5" />}
                <span>{copied ? "Copied!" : "Copy JSON"}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
