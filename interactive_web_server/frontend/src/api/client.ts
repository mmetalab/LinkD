import axios from 'axios';

const api = axios.create({ baseURL: '/api' });

// Overview
export const fetchOverview = () => api.get('/overview').then(r => r.data);
export const fetchExamples = () => api.get('/examples').then(r => r.data);

// Preload endpoints (data shown on page load, with pagination + filters)
export const preloadBinding = (params?: { page?: number; page_size?: number; gene_filter?: string }) =>
  api.get('/binding/preload', { params }).then(r => r.data);
export const preloadSelectivity = (params?: { page?: number; page_size?: number; type_filter?: string; drug_filter?: string }) =>
  api.get('/selectivity/preload', { params }).then(r => r.data);
export const preloadEHR = (params?: { page?: number; page_size?: number; source?: string; drug_filter?: string; disease_filter?: string; icd_prefix?: string; atc_category?: string }) =>
  api.get('/ehr/preload', { params }).then(r => r.data);

// Search endpoints
export const searchBinding = (params: { gene: string; drug_id: string; min_affinity?: number }) =>
  api.post('/binding/search', params).then(r => r.data);

export const searchSelectivity = (params: { drug_id: string; selectivity_type: string }) =>
  api.post('/selectivity/search', params).then(r => r.data);

export const searchEHR = (params: {
  drug_id: string; drug_name: string; icd_code: string; disease_name: string; source: string;
}) => api.post('/ehr/search', params).then(r => r.data);

// Agent endpoints
export const initAgent = (params: { provider: string; model: string; api_key: string }) =>
  api.post('/agent/init', params).then(r => r.data);

export const generatePlan = (query: string) =>
  api.post('/agent/plan', { query }).then(r => r.data);

export const executePlan = () =>
  api.post('/agent/execute').then(r => r.data);

export const fetchProviders = () => api.get('/agent/providers').then(r => r.data);
export const fetchHistory = () => api.get('/agent/history').then(r => r.data);
export const fetchPrerun = (name: string) => api.get(`/agent/prerun/${name}`).then(r => r.data);

// Download helpers
export const downloadCSV = (module: string) => {
  window.open(`/api/${module}/download/csv`, '_blank');
};

export default api;
