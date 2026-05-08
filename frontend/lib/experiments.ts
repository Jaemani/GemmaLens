export type SaveModeVariant = "manual" | "autoHighPriority";
export type LabelVariant = "priority" | "reason";
export type ResultLayoutVariant = "tableFirst" | "readingContextFirst";
export type ItemDetailVariant = "compact" | "learningCard";
export type ReviewStateVariant = "simple" | "study";
export type UserFitVariant = "onboarding" | "actionLearning";

export type AnalysisExperimentConfig = {
  saveMode: SaveModeVariant;
  labelMode: LabelVariant;
  resultLayout: ResultLayoutVariant;
  itemDetail: ItemDetailVariant;
  reviewState: ReviewStateVariant;
  userFit: UserFitVariant;
};

export const DEFAULT_ANALYSIS_EXPERIMENT: AnalysisExperimentConfig = {
  saveMode: "manual",
  labelMode: "priority",
  resultLayout: "tableFirst",
  itemDetail: "compact",
  reviewState: "simple",
  userFit: "onboarding"
};

export const ANALYSIS_EXPERIMENT_STORAGE_KEY = "paperlens.analysisExperiment";

export function parseAnalysisExperiment(value: string | null): AnalysisExperimentConfig {
  if (!value) return DEFAULT_ANALYSIS_EXPERIMENT;
  try {
    const parsed = JSON.parse(value) as Partial<AnalysisExperimentConfig>;
    return {
      saveMode: parsed.saveMode === "autoHighPriority" ? "autoHighPriority" : "manual",
      labelMode: parsed.labelMode === "reason" ? "reason" : "priority",
      resultLayout: parsed.resultLayout === "readingContextFirst" ? "readingContextFirst" : "tableFirst",
      itemDetail: parsed.itemDetail === "learningCard" ? "learningCard" : "compact",
      reviewState: parsed.reviewState === "study" ? "study" : "simple",
      userFit: parsed.userFit === "actionLearning" ? "actionLearning" : "onboarding"
    };
  } catch {
    return DEFAULT_ANALYSIS_EXPERIMENT;
  }
}

export function stringifyAnalysisExperiment(config: AnalysisExperimentConfig) {
  return JSON.stringify(config);
}

export function isBaselineA(config: AnalysisExperimentConfig) {
  return (
    config.saveMode === "manual" &&
    config.labelMode === "priority" &&
    config.resultLayout === "tableFirst" &&
    config.itemDetail === "compact" &&
    config.reviewState === "simple" &&
    config.userFit === "onboarding"
  );
}
