// Labels only. Authorization decisions come from the API.
export function accessLevelLabel(level) {
  return level === 5 ? 'Level 5 — Explicit review assignments' : typeof level === 'number' ? `Level ${level} — Assigned access` : 'External — Assigned access'
}
export function accessBadgeClass(level) { return level === 5 ? 'badge-gold' : level === 4 ? 'badge-teal' : 'badge-slate' }
