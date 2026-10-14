// The save: which part of segment 1 she has reached. localStorage when it is available; the
// game must also run where it is not (private windows, previews), so every access is guarded.

const KEY = 'amagishi.save';

export function loadSave() {
  try { const s = JSON.parse(localStorage.getItem(KEY) || 'null'); return s && typeof s.stage === 'string' ? s : null; }
  catch (e) { return null; }
}

export function writeSave(stage) {
  try { localStorage.setItem(KEY, JSON.stringify({ stage, at: Date.now() })); } catch (e) { /* not available */ }
}
