import React from "react";
import { createRoot } from "react-dom/client";
import { VisualGallery } from "../../src/visual-engine/controls/VisualGallery";

createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <main style={{ maxWidth: 1440, margin: "0 auto", padding: 16 }}>
      <VisualGallery />
    </main>
  </React.StrictMode>,
);
