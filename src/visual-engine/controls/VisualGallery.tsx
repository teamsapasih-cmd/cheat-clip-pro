import { useMemo, useState } from "react";
import { visualComponents } from "../registry";
import { VisualWorkbench } from "./VisualWorkbench";
import "./visual-gallery.css";

interface VisualGalleryProps { className?: string; }

export function VisualGallery({ className }: VisualGalleryProps) {
  const [query, setQuery] = useState("");
  const [category, setCategory] = useState("All");
  const [selectedId, setSelectedId] = useState(visualComponents[0]?.id ?? "");
  const categories = useMemo(
    () => ["All", ...Array.from(new Set(visualComponents.map((item) => item.category)))],
    [],
  );
  const filtered = useMemo(() => {
    const normalized = query.trim().toLowerCase();
    return visualComponents.filter((item) => {
      const matchesCategory = category === "All" || item.category === category;
      const haystack = [item.name, item.description, item.category, ...item.tags].join(" ").toLowerCase();
      return matchesCategory && (!normalized || haystack.includes(normalized));
    });
  }, [category, query]);
  const selected = filtered.find((item) => item.id === selectedId) ?? filtered[0];

  return (
    <section className={["visual-gallery", className].filter(Boolean).join(" ")}>
      <header className="visual-gallery-header">
        <div>
          <p className="visual-gallery-eyebrow">VISUAL LIBRARY</p>
          <h2>Explore components</h2>
          <p>Browse original visual effects and customize them in the live workbench.</p>
        </div>
        <span>{filtered.length} components</span>
      </header>
      <div className="visual-gallery-filters">
        <input type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search visuals, tags, or categories…" aria-label="Search visual components" />
        <div className="visual-gallery-categories" aria-label="Filter by category">
          {categories.map((item) => (
            <button key={item} type="button" className={category === item ? "is-active" : ""} onClick={() => setCategory(item)}>{item}</button>
          ))}
        </div>
      </div>
      <div className="visual-gallery-layout">
        <div className="visual-gallery-list">
          {filtered.map((item) => (
            <button key={item.id} type="button" className={selected?.id === item.id ? "visual-gallery-item is-selected" : "visual-gallery-item"} onClick={() => setSelectedId(item.id)}>
              <span className="visual-gallery-item-title">{item.name}</span>
              <span className="visual-gallery-item-description">{item.description}</span>
              <span className="visual-gallery-item-meta">{item.renderer.toUpperCase()} · {item.category}</span>
            </button>
          ))}
          {filtered.length === 0 && <p className="visual-gallery-empty">No visuals match this search.</p>}
        </div>
        <div className="visual-gallery-workbench">
          {selected ? <VisualWorkbench componentId={selected.id} /> : <div className="visual-gallery-empty">Choose a component to preview it.</div>}
        </div>
      </div>
    </section>
  );
}
