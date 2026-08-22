# LabelGuard AI — Frontend Application

Next.js (App Router), TypeScript, and Tailwind CSS user interface for the **AI Compliance & Health Rating Copilot for E-Commerce Product Labels**.

---

## 1. Overview & Key Capabilities

- **Drag-and-Drop Label Photo Upload**: Supports high-resolution `.jpg` and `.png` label images with instant preview and removal controls.
- **Automated Cloudinary Cloud Storage**: Label images uploaded by users are securely sent to Cloudinary via server-side API routes, returning CDN-hosted secure URLs.
- **Packaging Description & Ingredients Input**: Textarea for ingredient lists, OCR transcripts, nutrition tables, and product copy.
- **1-Click Quick Demo Presets**: Pre-loaded product scenarios (Instant Noodles, Whole Grain Oats, Carbonated Soda, Protein Bar) for instant evaluation and demo presentations.
- **Regulatory Compliance Audit Checklist**:
  - Validates **Legal Metrology (Packaged Commodities) Rules, 2011** (MRP, Net Quantity, Dates, Manufacturer details).
  - Validates **FSSAI (Labelling and Display) Regulations, 2020** (FSSAI 14-digit license, Veg/Non-Veg symbol, Nutritional table per 100g, Ingredients descending by weight).
  - Filterable tabs: *All Rules*, *Issues Found Only*, *Passed*.
- **Nutri-Score Health Rating Badge (A–E)**:
  - Color-coded 5-tier visual grade scale (A: Green → E: Red).
  - **Human-Readable Ingredient Flags**: Detected additive/ultra-processed tags mapped to clear consumer labels (e.g. `contains_palm_oil` → *"Palm Oil"*, `contains_added_sugar` → *"Added Sugar"*).
  - **Qualitative Advice Card**: Front-of-pack qualitative consumption guidance based on predicted grade and ingredient attributions.
- **Developer / Evaluator JSON Inspector**: In-app modal to view and copy the raw JSON response received from the backend `/api/analyze` endpoint.

---

## 2. Environment Variable Configuration

Create `.env.local` in the `frontend` directory:

```env
# =============================================================================
# BACKEND API CONFIGURATION
# =============================================================================
# Real Backend URL (FastAPI teammate backend)
# Example: http://localhost:8000/api/analyze
NEXT_PUBLIC_API_URL=

# =============================================================================
# CLOUDINARY CONFIGURATION (Product Label Image Storage)
# =============================================================================
# Get these keys from your Cloudinary Dashboard: https://cloudinary.com/console
CLOUDINARY_CLOUD_NAME=your_cloud_name_here
CLOUDINARY_API_KEY=your_api_key_here
CLOUDINARY_API_SECRET=your_api_secret_here
```

### Strict Backend Routing & Cloudinary Storage:
- **Cloudinary Integration**: When `CLOUDINARY_*` keys are defined in `.env.local`, uploaded product photos are automatically saved to your Cloudinary media library under `compliance-checker/product-labels` and the CDN URL is attached to the analysis request.
- **When `NEXT_PUBLIC_API_URL` is set**: The frontend communicates **100% directly with the real backend endpoint**. Any errors (e.g. network failure, OCR error) are surfaced directly to the user as real errors without silent fallback to mock data.
- **When `NEXT_PUBLIC_API_URL` is empty**: The frontend operates in **Demo Mode** using the dev-only stand-in route `/api/mock-analyze` to facilitate offline UI testing and grading.

---

## 3. Local Development

### 3.1 Install Dependencies
```bash
cd frontend
npm install
```

### 3.2 Run Development Server
```bash
npm run dev
```
Open [http://localhost:3000](http://localhost:3000) in your browser.

### 3.3 Production Build
```bash
npm run build
npm start
```
