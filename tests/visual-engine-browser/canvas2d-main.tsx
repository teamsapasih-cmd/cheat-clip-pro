import React from "react";
import { createRoot } from "react-dom/client";
import { VisualSurface, createCanvasAuroraEffect } from "../../src/visual-engine";
import "../../src/visual-engine/controls/visual-workbench.css";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <main style={{ maxWidth: 1100, margin: "0 auto", padding: 16 }}>
      <h1>Canvas 2D compatibility preview</h1>
      <div style={{ width: "100%", height: 420, overflow: "hidden", borderRadius: 16 }}>
        <VisualSurface
          renderer="canvas2d"
          effect={createCanvasAuroraEffect()}
          className="visual-workbench-canvas"
          label="Canvas Aurora cross-browser preview"
        />
      </div>
    </main>
  </React.StrictMode>,
);
