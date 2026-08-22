import { NextRequest, NextResponse } from "next/server";
import { uploadBufferToCloudinary, isCloudinaryConfigured } from "@/lib/cloudinary";

/**
 * API Route Handler: /api/upload-cloudinary
 * 
 * Securely uploads product label photos to Cloudinary using server-side credentials.
 */
export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const file = formData.get("image") as File | null;

    if (!file) {
      return NextResponse.json(
        { success: false, error: "No image file provided in request." },
        { status: 400 }
      );
    }

    // Check if Cloudinary credentials are set in environment
    if (!isCloudinaryConfigured()) {
      return NextResponse.json(
        {
          success: false,
          configured: false,
          message:
            "Cloudinary keys not yet configured in .env.local (CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET).",
        },
        { status: 200 }
      );
    }

    // Convert file to Buffer
    const arrayBuffer = await file.arrayBuffer();
    const buffer = Buffer.from(arrayBuffer);

    // Upload to Cloudinary
    const uploadResult = await uploadBufferToCloudinary(
      buffer,
      "compliance-checker/product-labels"
    );

    return NextResponse.json({
      success: true,
      configured: true,
      url: uploadResult.secure_url,
      public_id: uploadResult.public_id,
      format: uploadResult.format,
      bytes: uploadResult.bytes,
      created_at: uploadResult.created_at,
    });
  } catch (error: any) {
    console.error("Cloudinary upload failed:", error);
    return NextResponse.json(
      {
        success: false,
        error: error?.message || "Failed to upload image to Cloudinary.",
      },
      { status: 500 }
    );
  }
}
