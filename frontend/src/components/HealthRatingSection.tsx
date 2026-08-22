"use client";

import React from "react";
import { HeartPulse, AlertCircle, Sparkles, Check, Flame, Info, HelpCircle } from "lucide-react";
import { HealthResult } from "@/types";
import { getHumanReadableFlag, NUTRI_SCORE_CONFIG } from "@/lib/constants";

interface HealthRatingSectionProps {
  health: HealthResult | null;
}

const GRADES = ["A", "B", "C", "D", "E"] as const;

export function HealthRatingSection({ health }: HealthRatingSectionProps) {
  if (!health) {
    return (
      <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-slate-100 pb-5 dark:border-slate-800">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-slate-100 text-slate-500 dark:bg-slate-800 dark:text-slate-400">
              <HeartPulse className="h-5 w-5" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-slate-900 dark:text-white">
                Health Quality & Nutri-Rating
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Machine Learning health evaluation
              </p>
            </div>
          </div>
          <span className="rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600 dark:bg-slate-800 dark:text-slate-400">
            Rating Unavailable
          </span>
        </div>

        <div className="mt-6 flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-200 py-12 text-center dark:border-slate-800">
          <HelpCircle className="h-10 w-10 text-slate-300 dark:text-slate-600" />
          <p className="mt-3 text-sm font-semibold text-slate-700 dark:text-slate-300">
            Health score is currently unavailable
          </p>
          <p className="mt-1 max-w-sm text-xs text-slate-500 dark:text-slate-400">
            The external ML service did not return a prediction for this product (service may be offline or unreachable).
          </p>
        </div>
      </div>
    );
  }

  const currentGrade = (health.grade || "C").toUpperCase();
  const flaggedIngredients = health.flagged_ingredients || [];
  const advice = health.advice || "No health advice available.";
  const config = NUTRI_SCORE_CONFIG[currentGrade] || NUTRI_SCORE_CONFIG["C"];

  return (
    <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-100 pb-5 dark:border-slate-800">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-50 text-emerald-600 dark:bg-emerald-950/60 dark:text-emerald-400">
            <HeartPulse className="h-5 w-5" />
          </div>
          <div>
            <h2 className="text-base font-semibold text-slate-900 dark:text-white">
              Health Quality & Nutri-Rating
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Machine Learning evaluation trained on Open Food Facts nutrient & ingredient taxonomy
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1.5 rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700 dark:bg-slate-800 dark:text-slate-300">
          <Sparkles className="h-3.5 w-3.5 text-emerald-600" />
          <span>ML Health Score</span>
        </div>
      </div>

      {/* Nutri-Score Bar + Current Grade Display */}
      <div className="mt-6 flex flex-col items-center justify-between gap-6 rounded-2xl bg-slate-50 p-6 sm:flex-row dark:bg-slate-800/50">
        <div className="space-y-2 text-center sm:text-left">
          <span className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
            Assigned Rating
          </span>
          <div className="flex items-center justify-center sm:justify-start gap-3">
            <div
              className={`flex h-14 w-14 items-center justify-center rounded-2xl text-2xl font-black text-white shadow-md ${config.bg}`}
            >
              {currentGrade}
            </div>
            <div>
              <div className="text-lg font-bold text-slate-900 dark:text-white">
                Nutri-Score {currentGrade}
              </div>
              <div className={`text-xs font-medium ${config.text}`}>
                {config.description}
              </div>
            </div>
          </div>
        </div>

        {/* 5-Grade Visual Scale */}
        <div className="flex flex-col items-center gap-2">
          <div className="flex items-center gap-1 rounded-xl bg-white p-1.5 shadow-sm dark:bg-slate-900">
            {GRADES.map((g) => {
              const isActive = g === currentGrade;
              const gradeCfg = NUTRI_SCORE_CONFIG[g];
              return (
                <div
                  key={g}
                  className={`flex flex-col items-center justify-center rounded-lg transition-all ${
                    isActive
                      ? `${gradeCfg.bg} h-12 w-10 text-white font-bold shadow-md scale-105 ring-2 ring-offset-2 ring-slate-400 dark:ring-offset-slate-900`
                      : "h-9 w-8 bg-slate-100 text-slate-400 opacity-60 dark:bg-slate-800 dark:text-slate-500"
                  }`}
                >
                  <span className={`text-xs font-black ${isActive ? "text-white" : ""}`}>{g}</span>
                </div>
              );
            })}
          </div>
          <span className="text-[10px] text-slate-400">Nutri-Score Front-of-Pack Scale (A: Best → E: Least Healthy)</span>
        </div>
      </div>

      {/* Flagged Ingredients & Concerns */}
      <div className="mt-6">
        <h3 className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">
          Detected Ingredient Flags & Additives
        </h3>

        <div className="mt-2.5 flex flex-wrap gap-2">
          {flaggedIngredients.length === 0 ? (
            <div className="flex items-center gap-2 rounded-xl border border-emerald-200 bg-emerald-50/60 px-3.5 py-2 text-xs font-medium text-emerald-800 dark:border-emerald-900/50 dark:bg-emerald-950/40 dark:text-emerald-300">
              <Check className="h-4 w-4 text-emerald-600" />
              <span>No negative additive or ultra-processed flags detected</span>
            </div>
          ) : (
            flaggedIngredients.map((flag, idx) => (
              <span
                key={idx}
                className="inline-flex items-center gap-1.5 rounded-lg border border-amber-200 bg-amber-50 px-3 py-1.5 text-xs font-semibold text-amber-900 shadow-sm dark:border-amber-800/60 dark:bg-amber-950/60 dark:text-amber-300"
              >
                <AlertCircle className="h-3.5 w-3.5 text-amber-600 dark:text-amber-400" />
                {getHumanReadableFlag(flag)}
              </span>
            ))
          )}
        </div>
      </div>

      {/* Qualitative Guidance Box */}
      <div className="mt-6 rounded-xl border border-slate-200 bg-white p-4 shadow-sm dark:border-slate-800 dark:bg-slate-800/70">
        <div className="flex items-start gap-3">
          <div className="mt-0.5 flex-shrink-0 text-slate-600 dark:text-slate-300">
            <Info className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              Qualitative Consumption Guidance
            </h4>
            <p className="mt-1 text-sm leading-relaxed text-slate-800 dark:text-slate-200">
              {advice}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
