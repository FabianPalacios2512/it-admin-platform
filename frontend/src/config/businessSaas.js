import { ref } from 'vue';

const STORAGE_KEY = 'noc.businessSaas.v1';
const IPV4 = /^\d{1,3}(\.\d{1,3}){3}$/;

export const DEFAULT_CATALOG = [
  {
    id: 'adinfo',
    name: 'Adinfo',
    role: 'Nómina / RH',
    domains: [],
    ips: [],
    labels: ['adinfo'],
  },
  {
    id: 'wolkvox',
    name: 'Wolkvox',
    role: 'Contact center',
    domains: [],
    ips: [],
    labels: ['wolkvox', 'wolvox'],
  },
  {
    id: 'pos105',
    name: '105 POS Pro',
    role: 'Punto de venta',
    domains: ['105pos.pro'],
    ips: [],
    labels: ['105 POS', '105POS'],
  },
];

function cloneCatalog(rows) {
  return rows.map((app) => normalizeApp(app));
}

export function parseList(value) {
  if (Array.isArray(value)) {
    return value.map((item) => String(item).trim()).filter(Boolean);
  }
  return String(value || '')
    .split(/[\s,;]+/)
    .map((item) => item.trim())
    .filter(Boolean);
}

export function normalizeDomain(raw) {
  let text = String(raw || '').trim().toLowerCase();
  if (!text) return '';
  text = text.replace(/^https?:\/\//, '');
  text = text.split('/')[0];
  text = text.split('?')[0];
  text = text.replace(/:\d+$/, '');
  text = text.replace(/^\*\./, '');
  if (text.startsWith('www.')) text = text.slice(4);
  return text;
}

export function normalizeApp(app = {}) {
  const domains = parseList(app.domains).map(normalizeDomain).filter((item) => item && !IPV4.test(item));
  const ips = parseList(app.ips).map((item) => normalizeDomain(item)).filter((item) => IPV4.test(item));
  return {
    id: String(app.id || `app-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`),
    name: String(app.name || '').trim() || 'Sin nombre',
    role: String(app.role || '').trim(),
    domains: [...new Set(domains)],
    ips: [...new Set(ips)],
    labels: parseList(app.labels),
  };
}

export function loadCatalog() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (!raw) return cloneCatalog(DEFAULT_CATALOG);
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed) || !parsed.length) return cloneCatalog(DEFAULT_CATALOG);
    return parsed.map(normalizeApp);
  } catch (_) {
    return cloneCatalog(DEFAULT_CATALOG);
  }
}

export function saveCatalog(rows) {
  const clean = rows.map(normalizeApp);
  localStorage.setItem(STORAGE_KEY, JSON.stringify(clean));
  return clean;
}

export const catalog = ref(loadCatalog());

export function persistCatalog() {
  catalog.value = saveCatalog(catalog.value);
}

export function upsertApp(payload) {
  const next = normalizeApp(payload);
  const rows = [...catalog.value];
  const index = rows.findIndex((row) => row.id === next.id);
  if (index >= 0) rows[index] = next;
  else rows.push(next);
  catalog.value = saveCatalog(rows);
  return next;
}

export function removeApp(id) {
  catalog.value = saveCatalog(catalog.value.filter((row) => row.id !== id));
}

export function hostsFromValue(value) {
  let text = String(value || '').trim().toLowerCase();
  if (!text || text === '—') return [];
  text = text.replace(/^https?:\/\//, '');
  text = text.split('/')[0];
  text = text.split('?')[0];
  text = text.replace(/:\d+$/, '');
  text = text.replace(/^\*\./, '');
  return text ? [text] : [];
}

export function sessionHosts(session) {
  const fields = [
    session.destDomain,
    session.dstIp,
    session.dstHost,
    session.app,
    session.destIpRaw,
  ];
  const seen = new Set();
  const hosts = [];
  for (const field of fields) {
    for (const host of hostsFromValue(field)) {
      if (!seen.has(host)) {
        seen.add(host);
        hosts.push(host);
      }
    }
  }
  return hosts;
}

export function hostMatchesDomain(host, domain) {
  const h = String(host || '').toLowerCase();
  const d = String(domain || '').toLowerCase().replace(/^\*\./, '');
  if (!h || !d || IPV4.test(h)) return false;
  return h === d || h.endsWith(`.${d}`);
}

export function sessionMatchesApp(session, app) {
  const hosts = sessionHosts(session);
  const domains = app.domains || [];
  if (domains.some((domain) => hosts.some((host) => hostMatchesDomain(host, domain)))) {
    return true;
  }
  const ips = new Set((app.ips || []).map((ip) => String(ip).toLowerCase()));
  if (ips.size && hosts.some((host) => ips.has(host))) {
    return true;
  }
  const haystack = hosts.join(' ');
  return (app.labels || []).some((label) => label && haystack.includes(String(label).toLowerCase()));
}

export function scopeLabel(app) {
  const parts = [];
  for (const domain of app.domains || []) parts.push(`*.${domain}`);
  for (const ip of app.ips || []) parts.push(ip);
  if (parts.length) return parts.join(' · ');
  return 'Falta dominio o IP';
}
