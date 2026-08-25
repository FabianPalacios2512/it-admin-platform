const API_BASE = '/api/v1';

class FortigateService {
  async getDiagnostics(ip) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/fortigate/${ip}/diagnostics`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async getHosts(ip) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/fortigate/${ip}/hosts`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new Error(detail?.detail || `Error HTTP: ${response.status}`);
    }
    return await response.json();
  }

  async reserveDhcp(ip, reservationData) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/fortigate/${ip}/dhcp/reservation`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(reservationData)
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async getSessionDetail(ip, { srcip, dstip = null, dst_host = null } = {}) {
    const token = localStorage.getItem('access_token');
    const qs = new URLSearchParams({ srcip });
    if (dstip) qs.set('dstip', dstip);
    if (dst_host) qs.set('dst_host', dst_host);
    const response = await fetch(`${API_BASE}/fortigate/${ip}/traffic/session-detail?${qs}`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async getTrafficAudit(ip, { realtime = true, start = null, end = null, srcip = null } = {}) {
    const token = localStorage.getItem('access_token');
    const qs = new URLSearchParams({ realtime: String(realtime) });
    if (start) qs.set('start', String(start));
    if (end) qs.set('end', String(end));
    if (srcip) qs.set('srcip', srcip);
    const response = await fetch(`${API_BASE}/fortigate/${ip}/traffic/audit?${qs}`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async getBannedIps(ip) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/fortigate/${ip}/security/banned`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async banIp(ip, targetIp, expiry = 3600, extras = {}) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/fortigate/${ip}/security/ban`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({
        ip: targetIp || extras.ip || '',
        mac: extras.mac || '',
        expiry,
        reason: extras.reason || '',
      })
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new Error(detail?.detail || `Error HTTP: ${response.status}`);
    }
    return await response.json();
  }

  async banMac(ip, mac, reason = '', targetIp = '') {
    return this._postJson(`${API_BASE}/fortigate/${ip}/security/ban-mac`, { mac, reason, ip: targetIp });
  }

  async unbanMac(ip, mac) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/fortigate/${ip}/security/ban-mac/${encodeURIComponent(mac)}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new Error(detail?.detail || `Error HTTP: ${response.status}`);
    }
    return await response.json();
  }

  async unbanIp(ip, targetIp) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/fortigate/${ip}/security/ban/${encodeURIComponent(targetIp)}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new Error(detail?.detail || `Error HTTP: ${response.status}`);
    }
    return await response.json();
  }

  async revokeDhcp(ip, mac, serverMkey) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/fortigate/${ip}/dhcp/reservation`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify({ mac, server_mkey: serverMkey || null })
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  // ------------------------------------------------------------------
  // God Mode: acciones tácticas del módulo de Administración (NOC/SOC)
  // ------------------------------------------------------------------

  async _postJson(url, body) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      body: JSON.stringify(body || {})
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new Error(detail?.detail || `Error HTTP: ${response.status}`);
    }
    return await response.json();
  }

  async killSession(ip, session) {
    return this._postJson(`${API_BASE}/fortigate/${ip}/security/session/kill`, {
      srcip: session.srcip || session.srcIp,
      dstip: session.dstip || session.dstIp,
      proto: session.proto,
      sport: Number(session.sport || 0),
      dport: Number(session.dport || 0)
    });
  }

  async getShapingAssignments(ip) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/fortigate/${ip}/shaping/assignments`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async getShaperProfiles(ip) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/fortigate/${ip}/shaping/profiles`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async applyTrafficShaper(ip, targetIp, maxMbps, extras = {}) {
    return this._postJson(`${API_BASE}/fortigate/${ip}/shaping/apply`, {
      target_ip: targetIp,
      max_mbps: maxMbps,
      direction: extras.direction || 'symmetric',
      origin: extras.origin || 'manual',
    });
  }

  async applyDestinationShaper(ip, { srcip, dstip, dst_host, max_mbps, srcintf, dstintf }) {
    return this._postJson(`${API_BASE}/fortigate/${ip}/shaping/destination`, {
      srcip, dstip, dst_host, max_mbps, srcintf, dstintf,
    });
  }

  async previewDestinationBlock(ip, { srcip, dstip, dst_host }) {
    return this._postJson(`${API_BASE}/fortigate/${ip}/security/destination/block/preview`, {
      srcip, dstip, dst_host,
    });
  }

  async blockDestination(ip, { srcip, dstip, dst_host, cascade = true }) {
    return this._postJson(`${API_BASE}/fortigate/${ip}/security/destination/block`, {
      srcip, dstip, dst_host, cascade,
    });
  }

  async getDestinationBlocks(ip) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/fortigate/${ip}/security/destination/blocks`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async unblockDestination(ip, { srcip, dest_name }) {
    const token = localStorage.getItem('access_token');
    const qs = new URLSearchParams({ srcip });
    if (dest_name) qs.set('dest_name', dest_name);
    const response = await fetch(`${API_BASE}/fortigate/${ip}/security/destination/block?${qs}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new Error(detail?.detail || `Error HTTP: ${response.status}`);
    }
    return await response.json();
  }

  async getNocAudit(limit = 80) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/audit?source=FortiGate-NOC&limit=${limit}`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async removeTrafficShaper(ip, targetIp, policyName = '') {
    const token = localStorage.getItem('access_token');
    const url = policyName
      ? `${API_BASE}/fortigate/${ip}/shaping/assignment?policy_name=${encodeURIComponent(policyName)}`
      : `${API_BASE}/fortigate/${ip}/shaping/apply/${encodeURIComponent(targetIp)}`;
    const response = await fetch(url, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) { localStorage.removeItem('access_token'); window.location.href = '/login'; }
    if (!response.ok) {
      const detail = await response.json().catch(() => null);
      throw new Error(detail?.detail || `Error HTTP: ${response.status}`);
    }
    return await response.json();
  }

  async blockApplication(ip, appName, profileName = 'default') {
    return this._postJson(`${API_BASE}/fortigate/${ip}/security/block-application`, { app_name: appName, profile_name: profileName });
  }
}

export default new FortigateService();
