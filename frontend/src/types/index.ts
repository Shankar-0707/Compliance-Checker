export interface ComplianceResultItem {
  field: string;
  passed: boolean;
  citation: string;
}

export interface ComplianceData {
  results: ComplianceResultItem[];
}

export interface HealthResult {
  grade: "A" | "B" | "C" | "D" | "E" | string;
  flagged_ingredients: string[];
  advice: string;
}

export interface AnalyzeResponse {
  compliance: ComplianceData;
  health: HealthResult | null;
}

export interface ProductPreset {
  id: string;
  name: string;
  category: string;
  description: string;
  imageUrl?: string;
  mockResponse: AnalyzeResponse;
}
