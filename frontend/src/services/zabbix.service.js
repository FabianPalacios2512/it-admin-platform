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

  async getGlobalTrends(time_from, time_till) {
    const token = localStorage.getItem('access_token');
    let url = `${API_BASE}/zabbix/dashboard/trends`;
    if (time_from && time_till) url += `?time_from=${time_from}&time_till=${time_till}`;
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

  async getAllHosts(time_from, time_till) {
    const token = localStorage.getItem('access_token');
    let url = `${API_BASE}/zabbix/hosts`;
    if (time_from && time_till) url += `?time_from=${time_from}&time_till=${time_till}`;
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

  async getHostDetail(hostId, time_range = 3600) {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/zabbix/metrics/detail?host_id=${encodeURIComponent(hostId)}&time_range=${time_range}`, {
      headers: { 'Authorization': `Bearer ${token}`, 'Content-Type': 'application/json' }
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

  async getFortigates() {
    const token = localStorage.getItem('access_token');
    const response = await fetch(`${API_BASE}/zabbix/fortigates`, {
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
