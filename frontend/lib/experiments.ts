export type SaveModeVariant = "manual" | "autoHighPriority";
export type LabelVariant = "priority" | "reason";
export type ResultLayoutVariant = "tableFirst" | "readingContextFirst";

export type AnalysisExperimentConfig = {
  saveMode: SaveModeVariant;
  labelMode: LabelVariant;
  resultLayout: ResultLayoutVariant;
};

export const DEFAULT_ANALYSIS_EXPERIMENT: AnalysisExperimentConfig = {
  saveMode: "manual",
  labelMode: "priority",
  resultLayout: "tableFirst"
};

export const ANALYSIS_EXPERIMENT_STORAGE_KEY = "paperlens.analysisExperiment";

export function parseAnalysisExperiment(value: string | null): AnalysisExperimentConfig {
  if (!value) return DEFAULT_ANALYSIS_EXPERIMENT;
  try {
    const parsed = JSON.parse(value) as Partial<AnalysisExperimentConfig>;
    return {
      saveMode: parsed.saveMode === "autoHighPriority" ? "autoHighPriority" : "manual",
      labelMode: parsed.labelMode === "reason" ? "reason" : "priority",
      resultLayout: parsed.resultLayout === "readingContextFirst" ? "readingContextFirst" : "tableFirst"
    };
  } catch {
    return DEFAULT_ANALYSIS_EXPERIMENT;
  }
}

export function stringifyAnalysisExperiment(config: AnalysisExperimentConfig) {
  return JSON.stringify(config);
}
