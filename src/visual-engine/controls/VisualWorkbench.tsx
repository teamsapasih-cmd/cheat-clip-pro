import { useMemo, useState } from "react";
import { VisualSurface } from "../VisualSurface";
import { getDefaultValues, getVisualComponent } from "../registry";
import type { VisualValues } from "../registry";
import { VisualControlPanel } from "./VisualControlPanel";
import "./visual-controls.css";
import "./visual-workbench.css";
interface VisualWorkbenchProps { componentId: string; className?: string; }
export function VisualWorkbench(props: VisualWorkbenchProps) {
  return <VisualWorkbenchInstance key={props.componentId} {...props} />;
}
function VisualWorkbenchInstance({ componentId, className }: VisualWorkbenchProps) {
  const definition = useMemo(() => getVisualComponent(componentId), [componentId]);
  const defaults = useMemo(() => definition ? getDefaultValues(definition) : {}, [definition]);
  const [values, setValues] = useState<VisualValues>(defaults);
  const effect = useMemo(() => definition?.createEffect(values), [definition, values]);
  if (!definition || !effect) return <div className="visual-workbench-empty">This visual is not available.</div>;
  return (
    <section className={["visual-workbench", className].filter(Boolean).join(" ")}>
      <div className="visual-workbench-preview"><VisualSurface effect={effect} renderer={definition.renderer} className="visual-workbench-canvas" label={definition.name + " visual preview"} /><span className="visual-workbench-preview-label">LIVE PREVIEW</span></div>
      <VisualControlPanel componentId={componentId} onValuesChange={setValues} />
    </section>
  );
}
