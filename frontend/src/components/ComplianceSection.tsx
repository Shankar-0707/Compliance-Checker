"use client";

import React, { useState } from "react";
import { CheckCircle2, XCircle, AlertTriangle, ShieldCheck, Scale, FileText, Filter } from "lucide-react";
import { ComplianceData } from "@/types";
import { getHumanReadableField } from "@/lib/constants";

interface ComplianceSectionProps {
  compliance: ComplianceData;
}

export function ComplianceSection({ compliance }: ComplianceSectionProps) {
  const [filter, setFilter] = useState<"all" | "failed" | "passed">("all");

  const results = compliance?.results || [];
  const passedCount = results.filter((r) => r.passed).length;
  const failedCount = results.filter((r) => !r.passed).length;
  const totalCount = results.length;
  const complianceRate = totalCount > 0 ? Math.round((passedCount / totalCount) * 100) : 0;

  const filteredResults = results.filter((r) => {
    if (filter === "failed") return !r.passed;
    if (filter === "passed") return r.passed;
    return true;
  });

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      {/* Header & Stats */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-5 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-blue-50 text-blue-600 dark:bg-blue-950/60 dark:text-blue-400">
            <Scale className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">
              Regulatory Compliance Audit
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Evaluated against Legal Metrology Rules (2011) & FSSAI Labelling Regulations (2020)
            </p>
          </div>
        </div>

        {/* Counter Badges */}
        <div className="flex items-center gap-2 text-xs">
          <span className="inline-flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 font-medium text-slate-700 dark:bg-slate-800 dark:text-slate-300">
            <span className="font-bold">{totalCount}</span> Rules Checked
          </span>
          <span className="inline-flex items-center gap-1.5 rounded-full bg-emerald-50 px-3 py-1 font-medium text-emerald-700 dark:bg-emerald-950/50 dark:text-emerald-300">
            <CheckCircle2 className="h-3.5 w-3.5" />
            <span className="font-bold">{passedCount}</span> Passed
          </span>
          {failedCount > 0 && (
            <span className="inline-flex items-center gap-1.5 rounded-full bg-rose-50 px-3 py-1 font-medium text-rose-700 dark:bg-rose-950/50 dark:text-rose-300">
              <XCircle className="h-3.5 w-3.5" />
              <span className="font-bold">{failedCount}</span> Issues
            </span>
          )}
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="mt-4 flex items-center justify-between">
        <div className="inline-flex rounded-lg bg-slate-100 p-1 dark:bg-slate-800">
          <button
            type="button"
            onClick={() => setFilter("all")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              filter === "all"
                ? "bg-white text-slate-900 shadow-sm dark:bg-slate-700 dark:text-white"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            }`}
          >
            All ({totalCount})
          </button>
          <button
            type="button"
            onClick={() => setFilter("failed")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              filter === "failed"
                ? "bg-white text-rose-700 shadow-sm dark:bg-slate-700 dark:text-rose-400"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            }`}
          >
            Issues Only ({failedCount})
          </button>
          <button
            type="button"
            onClick={() => setFilter("passed")}
            className={`rounded-md px-3 py-1 text-xs font-medium transition-colors ${
              filter === "passed"
                ? "bg-white text-emerald-700 shadow-sm dark:bg-slate-700 dark:text-emerald-400"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-400 dark:hover:text-white"
            }`}
          >
            Passed ({passedCount})
          </button>
        </div>

        <div className="text-xs text-slate-500 dark:text-slate-400">
          Compliance Score: <span className="font-bold text-slate-900 dark:text-white">{complianceRate}%</span>
        </div>
      </div>

      {/* Checklist items */}
      <div className="mt-4 space-y-2.5">
        {filteredResults.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-200 py-8 text-center text-xs text-slate-500 dark:border-slate-800">
            No checklist items match the selected filter.
          </div>
        ) : (
          filteredResults.map((item, idx) => {
            const isPassed = item.passed;
            return (
              <div
                key={idx}
                className={`flex flex-col sm:flex-row sm:items-center justify-between gap-3 rounded-xl border p-3.5 transition-all ${
                  isPassed
                    ? "border-emerald-100 bg-emerald-50/30 hover:border-emerald-200 dark:border-emerald-950/40 dark:bg-emerald-950/10"
                    : "border-rose-200 bg-rose-50/40 hover:border-rose-300 dark:border-rose-900/50 dark:bg-rose-950/20"
                }`}
              >
                <div className="flex items-start gap-3">
                  <div className="mt-0.5 flex-shrink-0">
                    {isPassed ? (
                      <CheckCircle2 className="h-5 w-5 text-emerald-600 dark:text-emerald-400" />
                    ) : (
                      <XCircle className="h-5 w-5 text-rose-600 dark:text-rose-400" />
                    )}
                  </div>
                  <div>
                    <h3 className="text-sm font-semibold text-slate-900 dark:text-slate-100">
                      {getHumanReadableField(item.field)}
                    </h3>
                    <div className="mt-1 flex items-center gap-1.5 text-xs text-slate-600 dark:text-slate-300">
                      <FileText className="h-3.5 w-3.5 text-slate-400" />
                      <span>{item.citation}</span>
                    </div>
                  </div>
                </div>

                <div className="flex-shrink-0 self-start sm:self-center">
                  <span
                    className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-semibold ${
                      isPassed
                        ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                        : "bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300"
                    }`}
                  >
                    {isPassed ? "COMPLIANT" : "NON-COMPLIANT"}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
}
