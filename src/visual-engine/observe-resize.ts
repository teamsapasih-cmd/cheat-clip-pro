export function observeCanvasResize(target: HTMLCanvasElement, callback: () => void): () => void {
  if (typeof ResizeObserver !== "undefined") {
    const observer = new ResizeObserver(callback);
    observer.observe(target);
    return () => observer.disconnect();
  }

  window.addEventListener("resize", callback, { passive: true });
  return () => window.removeEventListener("resize", callback);
}
