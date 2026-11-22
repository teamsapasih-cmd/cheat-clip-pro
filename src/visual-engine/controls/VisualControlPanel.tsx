import { useMemo, useRef, useState } from "react";
import { exportVisualConfiguration, getVisualComponent, getDefaultValues, importVisualConfiguration, resetVisualConfiguration, validateVisualValues } from "../registry";
import type { VisualValues } from "../registry";

interface VisualControlPanelProps {
  componentId: string;
  onValuesChange?: (values: VisualValues) => void;
}

export function VisualControlPanel({ componentId, onValuesChange }: VisualControlPanelProps) {
  const definition = useMemo(() => getVisualComponent(componentId), [componentId]);
  const defaults = useMemo(() => definition ? getDefaultValues(definition) : {}, [definition]);
  const [values, setValues] = useState<VisualValues>(defaults);
  const [activePreset, setActivePreset] = useState("custom");
  const [message, setMessage] = useState("");
  const fileInputRef = useRef<HTMLInputElement>(null);

  if (!definition) return <div className="visual-control-empty">Visual component not found.</div>;

  const updateValue = (key: string, value: string | number | boolean) => {
    const next = validateVisualValues(definition, { ...values, [key]: value });
    setValues(next);
    setActivePreset("custom");
    setMessage("");
    onValuesChange?.(next);
  };

  const applyPreset = (presetId: string) => {
    const preset = definition.presets.find((item) => item.id === presetId);
    if (!preset) { setActivePreset("custom"); return; }
    const next = validateVisualValues(definition, preset.values);
    setValues(next);
    setActivePreset(preset.id);
    setMessage("");
    onValuesChange?.(next);
  };

  const exportConfiguration = () => {
    try {
      const serialized = exportVisualConfiguration({ schemaVersion: 1, componentId, values });
      const blob = new Blob([serialized], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = componentId + "-config.json";
      anchor.click();
      window.setTimeout(() => URL.revokeObjectURL(url), 1000);
      setMessage("Configuration exported.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not export configuration.");
    }
  };

  const importConfiguration = async (file?: File) => {
    if (!file) return;
    try {
      const configuration = importVisualConfiguration(await file.text());
      if (configuration.componentId !== componentId) {
        throw new Error("This file belongs to a different visual component.");
      }
      setValues(configuration.values);
      setActivePreset("custom");
      onValuesChange?.(configuration.values);
      setMessage("Configuration imported.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Could not import configuration.");
    } finally {
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  const resetConfiguration = () => {
    const next = resetVisualConfiguration(componentId).values;
    setValues(next);
    setActivePreset("custom");
    setMessage("Controls reset to defaults.");
    onValuesChange?.(next);
  };

  return (
    <section className="visual-control-panel" aria-label={definition.name + " controls"}>
      <header className="visual-control-header">
        <div><p className="visual-control-eyebrow">{definition.category}</p><h3>{definition.name}</h3><p>{definition.description}</p></div>
        <span className="visual-control-version">v{definition.version}</span>
      </header>
      {definition.presets.length > 0 && (
        <div className="visual-control-presets">
          <label htmlFor={componentId + "-preset"}>Preset</label>
          <select id={componentId + "-preset"} value={activePreset} onChange={(event) => applyPreset(event.target.value)}>
            <option value="custom">Custom</option>
            {definition.presets.map((preset) => <option key={preset.id} value={preset.id}>{preset.name}</option>)}
          </select>
          {activePreset !== "custom" && <small>{definition.presets.find((preset) => preset.id === activePreset)?.description}</small>}
        </div>
      )}
      <div className="visual-control-list">
        {definition.controls.map((control) => {
          const value = values[control.key] ?? control.defaultValue;
          if (control.type === "range") return (
            <label className="visual-control-row" key={control.key}>
              <span>{control.label}</span>
              <span className="visual-control-range">
                <input type="range" min={control.min} max={control.max} step={control.step ?? 1} value={typeof value === "number" ? value : control.defaultValue} onChange={(event) => updateValue(control.key, Number(event.target.value))} />
                <output>{value}{control.unit ?? ""}</output>
              </span>
            </label>
          );
          if (control.type === "color") return (
            <label className="visual-control-row" key={control.key}><span>{control.label}</span><input type="color" value={typeof value === "string" ? value : control.defaultValue} onChange={(event) => updateValue(control.key, event.target.value)} /></label>
          );
          if (control.type === "toggle") return (
            <label className="visual-control-row" key={control.key}><span>{control.label}</span><input type="checkbox" checked={typeof value === "boolean" ? value : control.defaultValue} onChange={(event) => updateValue(control.key, event.target.checked)} /></label>
          );
          return (
            <label className="visual-control-row" key={control.key}>
              <span>{control.label}</span>
              <select value={typeof value === "string" ? value : control.defaultValue} onChange={(event) => updateValue(control.key, event.target.value)}>
                {control.options.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
              </select>
            </label>
          );
        })}
      </div>
      <div className="visual-control-actions">
        <button type="button" onClick={exportConfiguration}>Export JSON</button>
        <button type="button" onClick={() => fileInputRef.current?.click()}>Import JSON</button>
        <button type="button" onClick={resetConfiguration}>Reset</button>
        <input ref={fileInputRef} type="file" accept="application/json,.json" hidden onChange={(event) => void importConfiguration(event.target.files?.[0])} />
      </div>
      <p className="visual-control-message" role="status" aria-live="polite">{message}</p>
    </section>
  );
}
