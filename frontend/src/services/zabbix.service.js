const API_BASE = '/api/v1';

class ZabbixService {
  async getDashboardSummary() {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/zabbix/dashboard/summary`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async getGroups() {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/zabbix/groups`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async getGlobalTrends(time_from, time_till, groupid = null) {
    const token = localStorage.getItem('access_token');
    let url = `${API_BASE}/zabbix/dashboard/trends`;
    const params = [];
    if (time_from && time_till) { params.push(`time_from=${time_from}`); params.push(`time_till=${time_till}`); }
    if (groupid && groupid !== 'all') params.push(`groupid=${groupid}`);
    params.push(`_t=${Date.now()}`); // Cache buster
    if (params.length) url += `?${params.join('&')}`;
    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      cache: 'no-store'
    });
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async getAllHosts(time_from, time_till, groupid = null) {
    const token = localStorage.getItem('access_token');
    let url = `${API_BASE}/zabbix/hosts`;
    const params = [];
    if (time_from && time_till) { params.push(`time_from=${time_from}`); params.push(`time_till=${time_till}`); }
    if (groupid && groupid !== 'all') params.push(`groupid=${groupid}`);
    params.push(`_t=${Date.now()}`); // Cache buster
    if (params.length) url += `?${params.join('&')}`;
    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      cache: 'no-store'
    });
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async getHostDetail(hostId, time_range = 3600) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/zabbix/metrics/detail?host_id=${encodeURIComponent(hostId)}&time_range=${time_range}&_t=${Date.now()}`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' },
      cache: 'no-store'
    });
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async getPbxTelephony() {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/zabbix/pbx`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }

  async getFortigates(hostid = null) {
    const token = localStorage.getItem('access_token');
    const url = hostid ? `${API_BASE}/zabbix/fortigates?hostid=${hostid}` : `${API_BASE}/zabbix/fortigates`;
    const response = await fetch(url, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
    });
    if (response.status === 401) {
      localStorage.removeItem('access_token');
      window.location.href = '/login';
    }
    if (!response.ok) throw new Error(`Error HTTP: ${response.status}`);
    return await response.json();
  }
}

export default new ZabbixService();
