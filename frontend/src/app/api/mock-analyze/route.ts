import { NextRequest, NextResponse } from "next/server";
import { AnalyzeResponse } from "@/types";

/**
 * DEV-ONLY TEMPORARY STAND-IN ROUTE: /api/mock-analyze
 * 
 * NOTICE:
 * This endpoint exists SOLELY for local development, UI testing, and demo scenarios
 * prior to the completion of the backend teammate's OCR + compliance rule engine service.
 * 
 * Once the teammate provides the backend URL (e.g. http://localhost:8000/api/analyze),
 * set `NEXT_PUBLIC_API_URL` in .env.local. The frontend will then communicate 100%
 * directly with the real backend and will NEVER call this mock route.
 */

export async function POST(req: NextRequest) {
  try {
    const formData = await req.formData();
    const description = (formData.get("description") as string) || "";
    const image = formData.get("image") as File | null;

    const lowerDesc = description.toLowerCase();

    // Default mock response
    let responseData: AnalyzeResponse;

    if (lowerDesc.includes("noodle") || lowerDesc.includes("maggi") || lowerDesc.includes("ramen")) {
      responseData = {
        compliance: {
          results: [
            {
              field: "fssai_license_number",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(7)",
            },
            {
              field: "net_quantity",
              passed: true,
              citation: "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(c)",
            },
            {
              field: "mrp_declaration",
              passed: true,
              citation: "Legal Metrology Rules, 2011 — Rule 6(1)(e)",
            },
            {
              field: "expiry_or_best_before",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(9)",
            },
            {
              field: "ingredients_list",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(1)",
            },
            {
              field: "veg_non_veg_logo",
              passed: false,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(4) [Symbol missing on principal display panel]",
            },
            {
              field: "nutritional_info_table",
              passed: false,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(2) [Per-serve values missing]",
            },
          ],
        },
        health: {
          grade: "D",
          flagged_ingredients: ["contains_palm_oil", "contains_preservative"],
          advice: "High in sodium and saturated fat with refined flour base — better suited as an occasional item than a daily staple.",
        },
      };
    } else if (lowerDesc.includes("oat") || lowerDesc.includes("granola") || lowerDesc.includes("muesli") || lowerDesc.includes("seed")) {
      responseData = {
        compliance: {
          results: [
            {
              field: "fssai_license_number",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(7)",
            },
            {
              field: "net_quantity",
              passed: true,
              citation: "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(c)",
            },
            {
              field: "mrp_declaration",
              passed: true,
              citation: "Legal Metrology Rules, 2011 — Rule 6(1)(e)",
            },
            {
              field: "expiry_or_best_before",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(9)",
            },
            {
              field: "veg_non_veg_logo",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(4)",
            },
            {
              field: "ingredients_list",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(1)",
            },
            {
              field: "nutritional_info_table",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(2)",
            },
          ],
        },
        health: {
          grade: "A",
          flagged_ingredients: [],
          advice: "A reasonably healthy choice for regular consumption. High in dietary fiber and whole grain content with minimal processing.",
        },
      };
    } else if (lowerDesc.includes("cola") || lowerDesc.includes("soda") || lowerDesc.includes("drink") || lowerDesc.includes("beverage")) {
      responseData = {
        compliance: {
          results: [
            {
              field: "fssai_license_number",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(7)",
            },
            {
              field: "net_quantity",
              passed: true,
              citation: "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(c)",
            },
            {
              field: "mrp_declaration",
              passed: true,
              citation: "Legal Metrology Rules, 2011 — Rule 6(1)(e)",
            },
            {
              field: "expiry_or_best_before",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(9)",
            },
            {
              field: "veg_non_veg_logo",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(4)",
            },
            {
              field: "ingredients_list",
              passed: false,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(1) [Caffeine content declaration missing]",
            },
          ],
        },
        health: {
          grade: "E",
          flagged_ingredients: ["contains_added_sugar", "contains_artificial_color", "contains_preservative"],
          advice: "High in added sugar and artificial colors with zero dietary fiber — better suited as an occasional item than a daily staple.",
        },
      };
    } else {
      // General packaged food scenario
      responseData = {
        compliance: {
          results: [
            {
              field: "fssai_license_number",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(7)",
            },
            {
              field: "net_quantity",
              passed: true,
              citation: "Legal Metrology (Packaged Commodities) Rules, 2011 — Rule 6(1)(c)",
            },
            {
              field: "mrp_declaration",
              passed: true,
              citation: "Legal Metrology Rules, 2011 — Rule 6(1)(e)",
            },
            {
              field: "expiry_or_best_before",
              passed: false,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(9) [Date format non-compliant]",
            },
            {
              field: "ingredients_list",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(1)",
            },
            {
              field: "veg_non_veg_logo",
              passed: true,
              citation: "FSS (Labelling and Display) Regulations, 2020 — Reg. 2.2(4)",
            },
          ],
        },
        health: {
          grade: "C",
          flagged_ingredients: ["contains_added_sugar"],
          advice: "A moderate choice — fine in your regular rotation, not a primary staple. Contains added sugar in moderate quantity.",
        },
      };
    }

    // Simulate realistic OCR / rule engine processing latency
    await new Promise((resolve) => setTimeout(resolve, 800));

    return NextResponse.json(responseData);
  } catch (error) {
    return NextResponse.json(
      { detail: error instanceof Error ? error.message : "Internal Mock Server Error" },
      { status: 500 }
    );
  }
}
