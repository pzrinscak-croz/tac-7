const STORAGE_KEY = 'queryHistory';
const MAX_ENTRIES = 20;

export function getHistory(): QueryHistoryEntry[] {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) return [];
    return parsed;
  } catch {
    return [];
  }
}

export function saveToHistory(entry: QueryHistoryEntry): void {
  try {
    let history = getHistory();
    // Deduplicate by query text — remove existing entry with same query
    history = history.filter(h => h.query !== entry.query);
    // Add new entry at the front (most recent first)
    history.unshift(entry);
    // Cap at MAX_ENTRIES
    if (history.length > MAX_ENTRIES) {
      history = history.slice(0, MAX_ENTRIES);
    }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch {
    // localStorage unavailable — degrade silently
  }
}

export function removeFromHistory(query: string): void {
  try {
    const history = getHistory().filter(h => h.query !== query);
    localStorage.setItem(STORAGE_KEY, JSON.stringify(history));
  } catch {
    // localStorage unavailable — degrade silently
  }
}

export function clearHistory(): void {
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {
    // localStorage unavailable — degrade silently
  }
}
