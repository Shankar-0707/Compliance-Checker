import { v2 as cloudinary, UploadApiResponse, UploadApiErrorResponse } from "cloudinary";

// Configure Cloudinary server-side using environment variables
const cloudName = process.env.CLOUDINARY_CLOUD_NAME;
const apiKey = process.env.CLOUDINARY_API_KEY;
const apiSecret = process.env.CLOUDINARY_API_SECRET;

if (cloudName && apiKey && apiSecret) {
  cloudinary.config({
    cloud_name: cloudName,
    api_key: apiKey,
    api_secret: apiSecret,
    secure: true,
  });
}

export const isCloudinaryConfigured = (): boolean => {
  return Boolean(
    (process.env.CLOUDINARY_CLOUD_NAME &&
      process.env.CLOUDINARY_API_KEY &&
      process.env.CLOUDINARY_API_SECRET) ||
      process.env.CLOUDINARY_URL
  );
};

export async function uploadBufferToCloudinary(
  buffer: Buffer,
  folder: string = "compliance-checker/product-labels"
): Promise<UploadApiResponse> {
  if (!isCloudinaryConfigured()) {
    throw new Error(
      "Cloudinary credentials missing in .env.local (CLOUDINARY_CLOUD_NAME, CLOUDINARY_API_KEY, CLOUDINARY_API_SECRET)."
    );
  }

  return new Promise((resolve, reject) => {
    const uploadStream = cloudinary.uploader.upload_stream(
      {
        folder,
        resource_type: "image",
        transformation: [{ quality: "auto" }, { fetch_format: "auto" }],
      },
      (error?: UploadApiErrorResponse, result?: UploadApiResponse) => {
        if (error || !result) {
          return reject(error || new Error("Failed to upload image to Cloudinary"));
        }
        resolve(result);
      }
    );

    uploadStream.end(buffer);
  });
}

export default cloudinary;
