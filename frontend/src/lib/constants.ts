export const INGREDIENT_FLAG_LABELS: Record<string, string> = {
  contains_palm_oil: "Palm Oil",
  contains_trans_fat: "Trans Fat",
  contains_added_sugar: "Added Sugar",
  contains_artificial_sweetener: "Artificial Sweeteners",
  contains_artificial_color: "Artificial Colors",
  contains_preservative: "Preservatives",
};

export function getHumanReadableFlag(flagKey: string): string {
  if (INGREDIENT_FLAG_LABELS[flagKey]) {
    return INGREDIENT_FLAG_LABELS[flagKey];
  }
  // Fallback for unlisted flags: strip "contains_" and title-case
  return flagKey
    .replace(/^contains_/, "")
    .split("_")
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(" ");
}

export const COMPLIANCE_FIELD_LABELS: Record<string, string> = {
  manufacturer_address: "Manufacturer / Packer Address & Details",
  product_name: "Product Generic / Common Name",
  net_quantity: "Net Quantity & Standard Unit",
  manufacture_date: "Date of Manufacture / Packing",
  mrp: "Maximum Retail Price (MRP incl. taxes)",
  consumer_care: "Consumer Care & Contact Details",
  fssai_license_number: "FSSAI License Number (14-Digit)",
  ingredients_list: "Ingredients List (Descending by weight)",
  best_before_date: "Best Before / Expiry Date",
  veg_nonveg_symbol: "Veg / Non-Veg Symbol (Green/Brown logo)",
};

export function getHumanReadableField(fieldKey: string): string {
  if (COMPLIANCE_FIELD_LABELS[fieldKey]) {
    return COMPLIANCE_FIELD_LABELS[fieldKey];
  }
  return fieldKey
    .split("_")
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}

export const NUTRI_SCORE_CONFIG: Record<
  string,
  { label: string; bg: string; text: string; ring: string; description: string }
> = {
  A: {
    label: "Grade A",
    bg: "bg-emerald-600",
    text: "text-emerald-700 dark:text-emerald-300",
    ring: "ring-emerald-500",
    description: "High nutritional quality — excellent for regular daily consumption.",
  },
  B: {
    label: "Grade B",
    bg: "bg-lime-500",
    text: "text-lime-700 dark:text-lime-300",
    ring: "ring-lime-500",
    description: "Good nutritional quality — healthy choice for regular consumption.",
  },
  C: {
    label: "Grade C",
    bg: "bg-amber-400",
    text: "text-amber-700 dark:text-amber-300",
    ring: "ring-amber-400",
    description: "Moderate nutritional quality — fine in regular rotation, not a primary staple.",
  },
  D: {
    label: "Grade D",
    bg: "bg-orange-500",
    text: "text-orange-700 dark:text-orange-300",
    ring: "ring-orange-500",
    description: "Low nutritional quality — better suited as an occasional item.",
  },
  E: {
    label: "Grade E",
    bg: "bg-rose-600",
    text: "text-rose-700 dark:text-rose-300",
    ring: "ring-rose-500",
    description: "Poor nutritional quality — high in saturated fat, sugar, or sodium.",
  },
};
