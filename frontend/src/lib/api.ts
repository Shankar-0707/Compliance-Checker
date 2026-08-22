import { AnalyzeResponse } from "@/types";

/**
 * Backend API Client for Product Label Compliance & Health Rating.
 * 
 * IMPORTANT ARCHITECTURAL NOTE:
 * When NEXT_PUBLIC_API_URL is configured (e.g. "http://localhost:8000/api/analyze"),
 * this client calls the real backend service directly via multipart/form-data.
 * Any errors (network failures, OCR errors, validation issues) are raised explicitly
 * to the caller — it NEVER falls back to canned/mock data silently.
 * 
 * When NEXT_PUBLIC_API_URL is empty/undefined, the client calls the local dev-only
 * mock route (`/api/mock-analyze`) to facilitate standalone UI testing and evaluation.
 */

export const IS_REAL_BACKEND_CONFIGURED = Boolean(
  process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL.trim() !== ""
);

export interface CloudinaryUploadResponse {
  success: boolean;
  configured?: boolean;
  url?: string;
  public_id?: string;
  message?: string;
  error?: string;
}

/**
 * Uploads product label photo to Cloudinary via Next.js server route.
 */
export async function uploadImageToCloudinaryClient(
  imageFile: File
): Promise<CloudinaryUploadResponse> {
  const formData = new FormData();
  formData.append("image", imageFile);

  try {
    const res = await fetch("/api/upload-cloudinary", {
      method: "POST",
      body: formData,
    });
    return await res.json();
  } catch (err) {
    console.error("Client Cloudinary upload error:", err);
    return {
      success: false,
      error: err instanceof Error ? err.message : "Failed to reach upload endpoint",
    };
  }
}

/**
 * Main analysis invocation sending image, description, and optional Cloudinary URL.
 */
export async function analyzeProductLabel(
  imageFile: File | null,
  description: string,
  cloudinaryUrl?: string | null
): Promise<AnalyzeResponse> {
  const targetUrl =
    process.env.NEXT_PUBLIC_API_URL && process.env.NEXT_PUBLIC_API_URL.trim() !== ""
      ? process.env.NEXT_PUBLIC_API_URL
      : "/api/mock-analyze";

  const formData = new FormData();
  if (imageFile) {
    formData.append("image", imageFile);
  }
  if (description) {
    formData.append("description", description);
  }
  if (cloudinaryUrl) {
    formData.append("image_url", cloudinaryUrl);
  }

  const response = await fetch(targetUrl, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorMessage = `Server returned HTTP ${response.status} (${response.statusText})`;
    try {
      const errorJson = await response.json();
      if (errorJson.detail) {
        errorMessage = typeof errorJson.detail === "string" ? errorJson.detail : JSON.stringify(errorJson.detail);
      } else if (errorJson.message) {
        errorMessage = errorJson.message;
      }
    } catch {
      // response wasn't JSON
    }
    throw new Error(errorMessage);
  }

  const data: AnalyzeResponse = await response.json();

  if (!data || !data.compliance || !data.health) {
    throw new Error("Invalid response format received from backend server: missing 'compliance' or 'health' fields.");
  }

  return data;
}
