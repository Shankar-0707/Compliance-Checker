"use client";

import React, { useState, useRef } from "react";
import { UploadCloud, Image as ImageIcon, X, Loader2, ArrowRight, FileText, AlertCircle, Cloud } from "lucide-react";
import { PresetSelector } from "./PresetSelector";

interface UploadFormProps {
  onSubmit: (file: File | null, description: string) => Promise<void>;
  isLoading: boolean;
  error: string | null;
  cloudinaryStatus?: string | null;
}

function generateCanvasLabelImage(text: string, title: string = "PRODUCT LABEL"): Promise<File> {
  return new Promise((resolve) => {
    const canvas = document.createElement("canvas");
    canvas.width = 650;
    canvas.height = 420;
    const ctx = canvas.getContext("2d");
    if (ctx) {
      // Background
      ctx.fillStyle = "#ffffff";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      ctx.strokeStyle = "#cbd5e1";
      ctx.lineWidth = 4;
      ctx.strokeRect(10, 10, canvas.width - 20, canvas.height - 20);

      // Title
      ctx.fillStyle = "#047857";
      ctx.font = "bold 20px sans-serif";
      ctx.fillText("PRODUCT SPECIFICATION LABEL", 30, 45);

      ctx.fillStyle = "#0f172a";
      ctx.font = "bold 16px sans-serif";
      ctx.fillText(title.slice(0, 45), 30, 75);

      // Body text wrapping
      ctx.fillStyle = "#334155";
      ctx.font = "13px sans-serif";
      const words = (text || "Standard packaged commodity specifications").split(" ");
      let line = "";
      let y = 105;
      for (let n = 0; n < words.length; n++) {
        const testLine = line + words[n] + " ";
        const metrics = ctx.measureText(testLine);
        if (metrics.width > 580 && n > 0) {
          ctx.fillText(line, 30, y);
          line = words[n] + " ";
          y += 20;
          if (y > 390) break;
        } else {
          line = testLine;
        }
      }
      ctx.fillText(line, 30, y);
    }

    canvas.toBlob((blob) => {
      if (blob) {
        resolve(new File([blob], "label_snapshot.png", { type: "image/png" }));
      } else {
        resolve(new File(["label"], "label_snapshot.png", { type: "image/png" }));
      }
    }, "image/png");
  });
}

export function UploadForm({ onSubmit, isLoading, error, cloudinaryStatus }: UploadFormProps) {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [description, setDescription] = useState<string>("");
  const [isDragOver, setIsDragOver] = useState<boolean>(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleFileChange = (file: File | null) => {
    if (!file) return;
    if (!file.type.startsWith("image/")) {
      alert("Please upload a valid image file (.jpg or .png).");
      return;
    }
    setSelectedFile(file);
    const url = URL.createObjectURL(file);
    setPreviewUrl(url);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFileChange(e.dataTransfer.files[0]);
    }
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const handleClearFile = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFile(null);
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      setPreviewUrl(null);
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile && !description.trim()) {
      alert("Please provide either a product label image or product description to analyze.");
      return;
    }

    // If only text was provided without an image, generate a clean label snapshot
    let fileToSend = selectedFile;
    if (!fileToSend && description.trim()) {
      fileToSend = await generateCanvasLabelImage(description, "Packaging Text Label");
    }

    await onSubmit(fileToSend, description);
  };

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      {/* Error Alert */}
      {error && (
        <div className="flex items-start gap-3 rounded-xl border border-rose-200 bg-rose-50 p-4 text-xs text-rose-800 dark:border-rose-900/60 dark:bg-rose-950/40 dark:text-rose-300">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-rose-600 dark:text-rose-400" />
          <div className="space-y-1">
            <span className="font-bold">Analysis Error:</span>
            <p className="leading-relaxed">{error}</p>
          </div>
        </div>
      )}

      {/* Cloudinary Status Notice if active */}
      {cloudinaryStatus && (
        <div className="flex items-center gap-2 rounded-xl border border-sky-200 bg-sky-50 px-4 py-2.5 text-xs text-sky-800 dark:border-sky-900/60 dark:bg-sky-950/40 dark:text-sky-300">
          <Cloud className="h-4 w-4 text-sky-600" />
          <span>{cloudinaryStatus}</span>
        </div>
      )}

      {/* Preset Selector */}
      <PresetSelector
        disabled={isLoading}
        onSelect={(desc) => {
          setDescription(desc);
        }}
      />

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Dropzone */}
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
              1. Upload Product Label Photo <span className="font-normal text-slate-400">(.jpg, .png)</span>
            </label>
            <span className="inline-flex items-center gap-1 text-[11px] font-medium text-slate-400">
              <Cloud className="h-3 w-3 text-sky-500" />
              Cloudinary Sync Enabled
            </span>
          </div>

          <div
            onClick={() => fileInputRef.current?.click()}
            onDrop={handleDrop}
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            className={`group relative flex min-h-[220px] cursor-pointer flex-col items-center justify-center rounded-2xl border-2 border-dashed p-6 text-center transition-all ${
              isDragOver
                ? "border-emerald-500 bg-emerald-50/50 dark:border-emerald-400 dark:bg-emerald-950/20"
                : previewUrl
                ? "border-slate-300 bg-slate-50/50 dark:border-slate-700 dark:bg-slate-900/40"
                : "border-slate-300 hover:border-emerald-500 hover:bg-slate-50/80 dark:border-slate-700 dark:hover:border-emerald-500 dark:hover:bg-slate-800/40"
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/jpg"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files?.[0] || null)}
              disabled={isLoading}
            />

            {previewUrl ? (
              <div className="relative flex flex-col items-center gap-3">
                <div className="relative h-32 w-48 overflow-hidden rounded-xl border border-slate-200 shadow-sm dark:border-slate-700">
                  <img
                    src={previewUrl}
                    alt="Label preview"
                    className="h-full w-full object-cover"
                  />
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium text-slate-700 dark:text-slate-300 truncate max-w-[180px]">
                    {selectedFile?.name}
                  </span>
                  <button
                    type="button"
                    onClick={handleClearFile}
                    className="rounded-full bg-rose-100 p-1 text-rose-600 hover:bg-rose-200 dark:bg-rose-950 dark:text-rose-300"
                    title="Remove image"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                </div>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-3">
                <div className="flex h-12 w-12 items-center justify-center rounded-full bg-emerald-50 text-emerald-600 transition-transform group-hover:scale-110 dark:bg-emerald-950/60 dark:text-emerald-400">
                  <UploadCloud className="h-6 w-6" />
                </div>
                <div className="space-y-1">
                  <p className="text-xs font-semibold text-slate-900 dark:text-white">
                    Click to browse or drag and drop
                  </p>
                  <p className="text-[11px] text-slate-500 dark:text-slate-400">
                    High resolution front/back packaging label photo
                  </p>
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Description Textarea */}
        <div className="space-y-2">
          <label className="block text-xs font-bold uppercase tracking-wider text-slate-700 dark:text-slate-300">
            2. Product Description & Ingredients / Nutritional Text
          </label>
          <textarea
            rows={8}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            disabled={isLoading}
            placeholder="Paste raw label ingredients list, nutrition table text (energy, saturated fat, sugars, sodium, protein, fiber), FSSAI number, or product marketing description..."
            className="w-full rounded-2xl border border-slate-300 bg-white p-4 text-xs leading-relaxed text-slate-900 shadow-sm placeholder:text-slate-400 focus:border-emerald-500 focus:outline-none focus:ring-1 focus:ring-emerald-500 dark:border-slate-700 dark:bg-slate-900 dark:text-white dark:placeholder:text-slate-500"
          />
        </div>
      </div>

      {/* Submit Button */}
      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isLoading || (!selectedFile && !description.trim())}
          className="inline-flex items-center gap-2 rounded-xl bg-gradient-to-r from-emerald-600 to-teal-600 px-6 py-3 text-sm font-semibold text-white shadow-md shadow-emerald-500/20 transition-all hover:from-emerald-500 hover:to-teal-500 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {isLoading ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Analyzing Label & Uploading to Cloud...</span>
            </>
          ) : (
            <>
              <span>Run Compliance & Health Rating Audit</span>
              <ArrowRight className="h-4 w-4" />
            </>
          )}
        </button>
      </div>
    </form>
  );
}
