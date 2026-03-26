// Nature Journal color palette
export const COLORS = {
  primary: '#2171B5',
  secondary: '#6BAED6',
  green: '#238B45',
  red: '#CB181D',
  amber: '#FE9929',
  purple: '#756BB1',
  orange: '#D94701',
  gray: '#636363',
  lightGray: '#f5f5f5',
  white: '#ffffff',
  palette: ['#2171B5', '#6BAED6', '#238B45', '#CB181D', '#FE9929', '#756BB1', '#D94701', '#636363'],
};

// Plotly layout defaults (Nature Journal style)
export const PLOTLY_LAYOUT: Record<string, any> = {
  font: { family: 'Arial, sans-serif', size: 12, color: '#333' },
  plot_bgcolor: 'white',
  paper_bgcolor: 'white',
  margin: { l: 60, r: 20, t: 50, b: 40 },
  xaxis: { showgrid: false, showline: true, linewidth: 0.8, linecolor: '#333' },
  yaxis: { showgrid: false, showline: true, linewidth: 0.8, linecolor: '#333' },
};

export const NAV_ITEMS = [
  { path: '/', label: 'Home' },
  { path: '/overview', label: 'Overview' },
  { path: '/binding', label: 'LinkD-DTI' },
  { path: '/selectivity', label: 'LinkD-Select' },
  { path: '/ehr', label: 'LinkD-Pheno' },
  { path: '/agent', label: 'LinkD-Agent' },
  { path: '/about', label: 'About' },
  { path: '/documentation', label: 'Docs' },
];
