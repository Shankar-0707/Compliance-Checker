"use client";

import React, { useState } from "react";
import { UploadForm } from "@/components/UploadForm";
import { ResultsDashboard } from "@/components/ResultsDashboard";
import { AnalyzeResponse } from "@/types";
import { analyzeProductLabel, uploadImageToCloudinaryClient } from "@/lib/api";
import { ShieldCheck, Sparkles, Cloud, ExternalLink } from "lucide-react";

export default function HomePage() {
  const [results, setResults] = useState<AnalyzeResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [cloudinaryUrl, setCloudinaryUrl] = useState<string | null>(null);
  const [cloudinaryStatus, setCloudinaryStatus] = useState<string | null>(null);

  const handleAnalyze = async (file: File | null, description: string) => {
    setIsLoading(true);
    setError(null);
    setCloudinaryStatus(null);

    let uploadedUrl: string | null = null;

    try {
      // 1. Upload photo to Cloudinary if file is selected
      if (file) {
        setCloudinaryStatus("Uploading product label photo to Cloudinary CDN...");
        const cloudRes = await uploadImageToCloudinaryClient(file);
        if (cloudRes.success && cloudRes.url) {
          uploadedUrl = cloudRes.url;
          setCloudinaryUrl(uploadedUrl);
          setCloudinaryStatus(`Photo securely uploaded to Cloudinary: ${cloudRes.url}`);
        } else if (cloudRes.configured === false) {
          setCloudinaryStatus("Note: Cloudinary keys not configured in .env.local — proceeding with direct analysis.");
        }
      }

      // 2. Call backend analyze endpoint with image, description, and Cloudinary URL
      const response = await analyzeProductLabel(file, description, uploadedUrl);
      setResults(response);
    } catch (err: unknown) {
      console.error("Analysis failed:", err);
      setError(
        err instanceof Error
          ? err.message
          : "An unexpected error occurred while communicating with the analysis service."
      );
    } finally {
      setIsLoading(false);
    }
  };

  const handleReset = () => {
    setResults(null);
    setError(null);
    setCloudinaryUrl(null);
    setCloudinaryStatus(null);
  };

  return (
    <div className="space-y-8">
      {/* Intro hero if not showing results */}
      {!results && (
        <div className="rounded-3xl border border-slate-200/80 bg-gradient-to-b from-white to-slate-50/50 p-6 sm:p-10 shadow-sm dark:border-slate-800 dark:from-slate-900 dark:to-slate-900/50">
          <div className="max-w-3xl space-y-3">
            <div className="inline-flex items-center gap-2 rounded-full bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700 dark:bg-emerald-950/60 dark:text-emerald-300">
              <Sparkles className="h-3.5 w-3.5" />
              <span>AI E-Commerce Label Copilot</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-extrabold tracking-tight text-slate-900 dark:text-white">
              Instant Regulatory Compliance & Nutri-Rating Audit
            </h1>
            <p className="text-sm leading-relaxed text-slate-600 dark:text-slate-300">
              Upload a packaged food or consumer goods product label photo or paste packaging text.
              LabelGuard verifies <strong>Legal Metrology & FSSAI labeling mandates</strong> while our ML model
              computes a <strong>Nutri-Score health grade (A–E)</strong> with flagged additive analysis.
            </p>
          </div>

          <div className="mt-8 border-t border-slate-100 pt-8 dark:border-slate-800">
            <UploadForm
              onSubmit={handleAnalyze}
              isLoading={isLoading}
              error={error}
              cloudinaryStatus={cloudinaryStatus}
            />
          </div>
        </div>
      )}

      {/* Results View */}
      {results && (
        <div className="space-y-4">
          {/* Cloudinary CDN Link Card if uploaded */}
          {cloudinaryUrl && (
            <div className="flex items-center justify-between rounded-xl border border-sky-200 bg-sky-50 px-4 py-2.5 text-xs text-sky-900 dark:border-sky-900/50 dark:bg-sky-950/30 dark:text-sky-300">
              <div className="flex items-center gap-2 truncate">
                <Cloud className="h-4 w-4 flex-shrink-0 text-sky-600 dark:text-sky-400" />
                <span className="font-semibold">Cloudinary Hosted Asset:</span>
                <span className="truncate max-w-md font-mono text-[11px] text-sky-700 dark:text-sky-400">
                  {cloudinaryUrl}
                </span>
              </div>
              <a
                href={cloudinaryUrl}
                target="_blank"
                rel="noreferrer"
                className="inline-flex items-center gap-1 font-semibold text-sky-700 hover:underline dark:text-sky-300"
              >
                <span>View CDN Photo</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          )}

          <ResultsDashboard data={results} onReset={handleReset} />
        </div>
      )}
    </div>
  );
}
