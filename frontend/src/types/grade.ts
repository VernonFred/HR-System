export type GradeCutoffs = {
  [grade: string]: number; // e.g., { A:90, B:75, C:60 }
};

export function gradeFromScore(score: number, cutoffs: GradeCutoffs): string {
  // Higher first
  const sorted = Object.entries(cutoffs).sort((a, b) => b[1] - a[1]);
  for (const [grade, min] of sorted) {
    if (score >= min) return grade;
  }
  return "N/A";
}
