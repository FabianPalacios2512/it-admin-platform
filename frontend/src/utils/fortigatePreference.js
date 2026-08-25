const STORAGE_KEY = 'noc.lastFortigateIp';

export function readLastFortigateIp() {
  try {
    return String(localStorage.getItem(STORAGE_KEY) || '').trim();
  } catch {
    return '';
  }
}

export function saveLastFortigateIp(ip) {
  const value = String(ip || '').trim();
  if (!value) return;
  try {
    localStorage.setItem(STORAGE_KEY, value);
  } catch {
    /* ignore quota / private mode */
  }
}

export function pickFortigateIp(fortigates = [], currentIp = '') {
  const list = Array.isArray(fortigates) ? fortigates : [];
  if (!list.length) return currentIp || '';
  const remembered = readLastFortigateIp();
  const match = (ip) => list.find((fg) => fg && fg.ip === ip);
  return match(currentIp)?.ip || match(remembered)?.ip || list[0].ip;
}
