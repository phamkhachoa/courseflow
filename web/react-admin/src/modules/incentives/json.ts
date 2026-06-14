import type { ActionSpec, RuleSpec } from "./types";

export const ruleTemplates: RuleSpec[] = [
  {
    type: "MIN_ORDER_AMOUNT",
    schemaVersion: 1,
    parameters: {
      amount: 100,
      currency: "USD"
    }
  }
];

export const actionTemplates: ActionSpec[] = [
  {
    type: "ORDER_FIXED_OFF",
    schemaVersion: 1,
    parameters: {
      amount: 10,
      currency: "USD"
    }
  }
];

export function loyaltyPointsEarnActionTemplate(programId: string, points: number): ActionSpec {
  return {
    type: "LOYALTY_POINTS_EARN",
    schemaVersion: 1,
    parameters: {
      programId,
      points
    }
  };
}

export function formatJson(value: unknown): string {
  return JSON.stringify(value ?? [], null, 2);
}

export function parseSpecList<T extends { type: string }>(raw: string, label: string): T[] {
  let parsed: unknown;
  try {
    parsed = JSON.parse(raw);
  } catch (error) {
    throw new Error(`${label} không phải JSON hợp lệ`);
  }

  if (!Array.isArray(parsed)) {
    throw new Error(`${label} phải là một mảng JSON`);
  }

  parsed.forEach((item, index) => {
    if (!item || typeof item !== "object" || typeof (item as { type?: unknown }).type !== "string") {
      throw new Error(`${label}[${index}] phải có trường type`);
    }
  });

  return parsed as T[];
}
