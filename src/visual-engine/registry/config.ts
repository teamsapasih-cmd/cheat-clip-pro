import { getVisualComponent } from "./components";
import { getDefaultValues, validateVisualValues } from "./validate";
import type { VisualValues } from "./types";

export interface VisualConfiguration {
  schemaVersion: 1;
  componentId: string;
  values: VisualValues;
}

export function createVisualConfiguration(componentId: string, candidate: Record<string, unknown>): VisualConfiguration {
  const definition = getVisualComponent(componentId);
  if (!definition) throw new Error("Unknown visual component: " + componentId);
  return {
    schemaVersion: 1,
    componentId,
    values: validateVisualValues(definition, candidate),
  };
}

export function exportVisualConfiguration(configuration: VisualConfiguration): string {
  const normalized = createVisualConfiguration(configuration.componentId, configuration.values);
  return JSON.stringify(normalized, null, 2);
}

export function importVisualConfiguration(serialized: string): VisualConfiguration {
  if (serialized.length > 65_536) {
    throw new Error("Configuration file is too large (maximum 64 KB).");
  }
  let parsed: unknown;
  try {
    parsed = JSON.parse(serialized);
  } catch {
    throw new Error("Configuration file is not valid JSON.");
  }
  if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
    throw new Error("Configuration must be a JSON object.");
  }
  const candidate = parsed as Record<string, unknown>;
  if (candidate.schemaVersion !== 1) throw new Error("Unsupported visual configuration version.");
  if (typeof candidate.componentId !== "string" || !candidate.componentId.trim()) {
    throw new Error("Configuration is missing a component ID.");
  }
  if (!candidate.values || typeof candidate.values !== "object" || Array.isArray(candidate.values)) {
    throw new Error("Configuration values must be an object.");
  }
  const definition = getVisualComponent(candidate.componentId);
  if (!definition) throw new Error("Configuration references an unknown visual component.");
  return {
    schemaVersion: 1,
    componentId: definition.id,
    values: validateVisualValues(definition, candidate.values as Record<string, unknown>),
  };
}

export function resetVisualConfiguration(componentId: string): VisualConfiguration {
  const definition = getVisualComponent(componentId);
  if (!definition) throw new Error("Unknown visual component: " + componentId);
  return { schemaVersion: 1, componentId, values: getDefaultValues(definition) };
}
