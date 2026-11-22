import type { VisualComponentDefinition, VisualControl, VisualValues } from "./types";

function isValidControlValue(control: VisualControl, value: unknown): value is string | number | boolean {
  switch (control.type) {
    case "range":
      return typeof value === "number"
        && Number.isFinite(value)
        && value >= control.min
        && value <= control.max;
    case "color":
      return typeof value === "string" && /^#[0-9a-fA-F]{6}$/.test(value);
    case "toggle":
      return typeof value === "boolean";
    case "select":
      return typeof value === "string" && control.options.some((option) => option.value === value);
  }
}

export function getDefaultValues(definition: VisualComponentDefinition): VisualValues {
  return Object.fromEntries(definition.controls.map((control) => [control.key, control.defaultValue]));
}

export function validateVisualValues(
  definition: VisualComponentDefinition,
  candidate: Record<string, unknown>,
): VisualValues {
  const values = getDefaultValues(definition);

  for (const control of definition.controls) {
    const value = candidate[control.key];
    if (value !== undefined && isValidControlValue(control, value)) {
      values[control.key] = value;
    }
  }

  return values;
}
