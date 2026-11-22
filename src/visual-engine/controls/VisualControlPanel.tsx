import { useEffect, useMemo, useState } from "react";
import { getVisualComponent, getDefaultValues, validateVisualValues } from "../registry";
import type { VisualValues } from "../registry";

interface VisualControlPanelProps {
  componentId: string;
  onValuesChange?: (values: VisualValues) => void;
}

export function VisualControlPanel({ componentId, onValuesChange }: VisualControlPanelProps) {
  const definition = useMemo(() => getVisualComponent(componentId), [componentId]);
  const defaults = useMemo(
    () => definition ? getDefaultValues(definition) : {},
    [definition],
  );
  const [values, setValues] = useState<VisualValues>(defaults);
  const [activePreset, setActivePreset] = useState("custom");

  useEffect(() => {
    setValues(defaults);
    setActivePreset("custom");
    onValuesChange?.(defaults);
  }, [defaults, onValuesChange]);

  if (!definition) {
    return <div className="visual-control-empty">Visual component not found.</div>;
  }

  const updateValue = (key: string, value: string | number | boolean) => {
    const next = validateVisualValues(definition, { ...values, [key]: value });
    setValues(next);
    setActivePreset("custom");
    onValuesChange?.(next);
  };

  const applyPreset = (presetId: string) => {
    const preset = definition.presets.find((item) => item.id === presetId);
    if (!preset) {
      setActivePreset("custom");
      return;
    }
    const next = validateVisualValues(definition, preset.values);
    setValues(next);
    setActivePreset(preset.id);
    onValuesChange?.(next);
  };

  return (
    <section className="visual-control-panel" aria-label={definition.name + " controls"}>
      <header className="visual-control-header">
        <div>
          <p className="visual-control-eyebrow">{definition.category}</p>
          <h3>{definition.name}</h3>
          <p>{definition.description}</p>
        </div>
        <span className="visual-control-version">v{definition.version}</span>
      </header>

      {definition.presets.length > 0 && (
        <div className="visual-control-presets">
          <label htmlFor={componentId + "-preset"}>Preset</label>
          <select
            id={componentId + "-preset"}
            value={activePreset}
            onChange={(event) => applyPreset(event.target.value)}
          >
            <option value="custom">Custom</option>
            {definition.presets.map((preset) => (
              <option key={preset.id} value={preset.id}>{preset.name}</option>
            ))}
          </select>
          {activePreset !== "custom" && (
            <small>{definition.presets.find((preset) => preset.id === activePreset)?.description}</small>
          )}
        </div>
      )}

      <div className="visual-control-list">
        {definition.controls.map((control) => {
          const value = values[control.key] ?? control.defaultValue;
          if (control.type === "range") {
            return (
              <label className="visual-control-row" key={control.key}>
                <span>{control.label}</span>
                <span className="visual-control-range">
                  <input
                    type="range"
                    min={control.min}
                    max={control.max}
                    step={control.step ?? 1}
                    value={typeof value === "number" ? value : control.defaultValue}
                    onChange={(event) => updateValue(control.key, Number(event.target.value))}
                  />
                  <output>{value}{control.unit ?? ""}</output>
                </span>
              </label>
            );
          }
          if (control.type === "color") {
            return (
              <label className="visual-control-row" key={control.key}>
                <span>{control.label}</span>
                <input
                  type="color"
                  value={typeof value === "string" ? value : control.defaultValue}
                  onChange={(event) => updateValue(control.key, event.target.value)}
                />
              </label>
            );
          }
          if (control.type === "toggle") {
            return (
              <label className="visual-control-row" key={control.key}>
                <span>{control.label}</span>
                <input
                  type="checkbox"
                  checked={typeof value === "boolean" ? value : control.defaultValue}
                  onChange={(event) => updateValue(control.key, event.target.checked)}
                />
              </label>
            );
          }
          return (
            <label className="visual-control-row" key={control.key}>
              <span>{control.label}</span>
              <select
                value={typeof value === "string" ? value : control.defaultValue}
                onChange={(event) => updateValue(control.key, event.target.value)}
              >
                {control.options.map((option) => (
                  <option key={option.value} value={option.value}>{option.label}</option>
                ))}
              </select>
            </label>
          );
        })}
      </div>
    </section>
  );
}
