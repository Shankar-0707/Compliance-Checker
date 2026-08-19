"""
storage/cloudinary_client.py
────────────────────────────
Configures the Cloudinary SDK from environment variables and exposes a single
async-safe helper to upload label images.

The returned `secure_url` is stored in the DB audit record but is NOT forwarded
to the frontend — it is purely an internal storage concern.
"""

import os
import asyncio
from functools import partial

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

load_dotenv()

# Configure Cloudinary once at import time
cloudinary.config(
    cloud_name=os.environ["CLOUDINARY_CLOUD_NAME"],
    api_key=os.environ["CLOUDINARY_API_KEY"],
    api_secret=os.environ["CLOUDINARY_API_SECRET"],
    secure=True,
)

_FOLDER = "compliance-checker"


async def upload_image(file_bytes: bytes, filename: str) -> str:
    """
    Upload raw image bytes to Cloudinary.

    Parameters
    ----------
    file_bytes : bytes
        Raw bytes of the uploaded label image.
    filename : str
        Original filename — used as the public_id prefix so images are
        identifiable in the Cloudinary media library.

    Returns
    -------
    str
        HTTPS CDN URL (``secure_url``) of the uploaded image.

    Raises
    ------
    RuntimeError
        If the Cloudinary upload fails for any reason.
    """
    # Derive a clean public_id from the filename (strip extension)
    public_id = f"{_FOLDER}/{os.path.splitext(filename)[0]}"

    # cloudinary.uploader.upload is synchronous — run it in a thread pool
    # so we don't block FastAPI's event loop.
    loop = asyncio.get_running_loop()
    try:
        result = await loop.run_in_executor(
            None,
            partial(
                cloudinary.uploader.upload,
                file_bytes,
                folder=_FOLDER,
                public_id=public_id,
                overwrite=True,
                resource_type="image",
            ),
        )
    except Exception as exc:
        raise RuntimeError(f"Cloudinary upload failed: {exc}") from exc

    secure_url: str = result["secure_url"]
    return secure_url
