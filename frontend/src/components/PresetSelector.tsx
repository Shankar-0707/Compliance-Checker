"use client";

import React from "react";
import { Sparkles, Utensils } from "lucide-react";

interface PresetSelectorProps {
  onSelect: (description: string) => void;
  disabled?: boolean;
}

const DEMO_PRESETS = [
  {
    name: "Instant Noodles",
    category: "Processed Grain",
    description:
      "Instant Masala Noodles with Tastemaker: Refined wheat flour (maida), palm oil, iodized salt, hydrolysed groundnut protein, spice extract, preservatives (INS 211, INS 319). Energy: 430 kcal, Saturated fat: 9.8g, Sodium: 920mg, Sugar: 2.1g per 100g.",
  },
  {
    name: "Whole Grain Rolled Oats",
    category: "Breakfast Cereal",
    description:
      "100% Whole Grain Rolled Oats with Chia & Flax Seeds. Ingredients: Rolled oats (90%), chia seeds (5%), flax seeds (5%). No added sugar, no preservatives, no artificial colors. Energy: 380 kcal, Protein: 13.5g, Fiber: 10.2g, Saturated fat: 1.2g, Sodium: 5mg per 100g.",
  },
  {
    name: "Carbonated Cola Beverage",
    category: "Soft Drink",
    description:
      "Carbonated Water, High Fructose Corn Syrup, Added Sugar (sucrose), Caramel Color (INS 150d), Phosphoric Acid, Caffeine, Natural Flavors, Preservative (INS 211). Energy: 44 kcal, Added Sugars: 10.6g, Sodium: 12mg per 100ml.",
  },
  {
    name: "Dark Chocolate Protein Bar",
    category: "Snack Bar",
    description:
      "Whey Protein Isolate, Almonds, Dark Chocolate (cocoa mass, cocoa butter), Oats, Honey, Chicory Root Fiber. Energy: 390 kcal, Protein: 20g, Fiber: 8g, Saturated Fat: 4.5g, Sugars: 9g, Sodium: 110mg per 100g.",
  },
];

export function PresetSelector({ onSelect, disabled }: PresetSelectorProps) {
  return (
    <div className="rounded-xl border border-slate-200 bg-slate-50/70 p-4 dark:border-slate-800 dark:bg-slate-900/60">
      <div className="flex items-center gap-2 text-xs font-semibold text-slate-700 dark:text-slate-300">
        <Sparkles className="h-3.5 w-3.5 text-emerald-600 dark:text-emerald-400" />
        <span>Quick Demo Presets (1-Click Fill)</span>
      </div>

      <div className="mt-2.5 grid grid-cols-2 gap-2 sm:grid-cols-4">
        {DEMO_PRESETS.map((preset, idx) => (
          <button
            key={idx}
            type="button"
            disabled={disabled}
            onClick={() => onSelect(preset.description)}
            className="flex flex-col items-start rounded-lg border border-slate-200 bg-white p-2.5 text-left text-xs transition-all hover:border-emerald-400 hover:bg-emerald-50/40 hover:shadow-sm disabled:cursor-not-allowed disabled:opacity-50 dark:border-slate-700 dark:bg-slate-800 dark:hover:border-emerald-500 dark:hover:bg-emerald-950/30"
          >
            <span className="font-semibold text-slate-900 dark:text-white">
              {preset.name}
            </span>
            <span className="mt-0.5 text-[11px] text-slate-500 dark:text-slate-400">
              {preset.category}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
