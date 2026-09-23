export const labels = {
  reliability: "Reliability",
  usability: "Usability",
  capability: "New capability",
  pricing: "Pricing",
  other: "Other / unclear",
};

export function percentage(value) {
  return `${(value * 100).toFixed(1)}%`;
}

export function themePolicy(probability, threshold) {
  return probability < threshold / 100;
}
