import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import PlotChart from '../components/PlotChart';
import StatCard from '../components/StatCard';
import { fetchOverview } from '../api/client';
import { COLORS } from '../styles/theme';

const BASE_LAYOUT: any = {
  font: { family: 'Arial, sans-serif', size: 12, color: '#333' },
  plot_bgcolor: 'white', paper_bgcolor: 'white',
  margin: { l: 60, r: 20, t: 50, b: 50 }, showlegend: false, height: 320,
};

// Horizontal bars need wider left margin for labels
const HBAR_LAYOUT: any = { ...BASE_LAYOUT, margin: { l: 180, r: 30, t: 50, b: 50 } };

const DATA_SOURCE_LINKS = [
  { label: 'Drug-Target-Disease', desc: '276K+ associations from ChEMBL', url: 'https://www.ebi.ac.uk/chembl/' },
  { label: 'Binding Affinity', desc: '20K+ targets with pKd values', url: 'https://www.ebi.ac.uk/chembl/' },
  { label: 'EHR Mount Sinai', desc: 'Drug-disease odds ratios', url: '#' },
  { label: 'EHR UK Biobank', desc: 'Drug-cancer associations', url: 'https://www.ukbiobank.ac.uk/' },
  { label: 'CRISPR Drug Response', desc: 'PRISM + GDSC screens', url: 'https://depmap.org/portal/prism/' },
  { label: 'Causal Gene-Disease', desc: 'Open Targets associations', url: 'https://www.opentargets.org/' },
];

export default function Overview() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchOverview().then(d => { setData(d); setLoading(false); }).catch(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-center py-20 text-gray-400">Loading database overview...</div>;
  if (!data) return <div className="text-center py-20 text-red-500">Failed to load</div>;

  const { cards, charts, sources_table } = data;

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-800 mb-4">Database Overview</h2>

      {/* Stat Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-3 mb-6">
        {cards.map((c: any, i: number) => (
          <StatCard key={i} label={String(c.label)} value={Number(c.value)} color={String(c.color)} />
        ))}
      </div>

      {/* Feature explorer links */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-6">
        {[
          { label: 'LinkD-DTI', path: '/binding', desc: 'Drug-target interaction binding affinity', color: COLORS.primary },
          { label: 'LinkD-Select', path: '/selectivity', desc: 'Drug selectivity landscape', color: COLORS.green },
          { label: 'LinkD-Pheno', path: '/ehr', desc: 'Phenotype-drug associations', color: COLORS.amber },
          { label: 'LinkD-Agent', path: '/agent', desc: 'AI multi-source analysis', color: COLORS.purple },
        ].map((f, i) => (
          <Link key={i} to={f.path}
            className="bg-white rounded-lg border border-gray-200 p-3 shadow-sm hover:shadow-md transition-shadow text-center"
            style={{ borderTop: `3px solid ${f.color}` }}>
            <div className="text-sm font-semibold text-gray-700">{f.label}</div>
            <div className="text-xs text-gray-400">{f.desc}</div>
          </Link>
        ))}
      </div>

      {/* Charts 2x2 */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-6">
        <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
          <h4 className="text-sm font-semibold text-gray-700 mb-0.5">a) Records per Data Source</h4>
          <p className="text-xs text-gray-400 mb-2">Total number of records available in each integrated data source.</p>
          <PlotChart
            data={[{
              type: 'bar', orientation: 'h',
              y: charts.sources.map((s: any) => s.source),
              x: charts.sources.map((s: any) => s.count),
              marker: { color: COLORS.palette.slice(0, charts.sources.length) },
              text: charts.sources.map((s: any) => s.count.toLocaleString()),
              textposition: 'outside',
              hovertemplate: '<b>%{y}</b><br>Records: %{x:,}<extra></extra>',
            }]}
            layout={{ ...HBAR_LAYOUT, height: 280 }}
            style={{ width: '100%' }}
          />
        </div>
        <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
          <h4 className="text-sm font-semibold text-gray-700 mb-0.5">b) Clinical Trial Phases</h4>
          <p className="text-xs text-gray-400 mb-2">Distribution of drugs across clinical trial phases, from preclinical through approved.</p>
          <PlotChart
            data={[{
              type: 'bar',
              x: charts.phases.map((p: any) => p.phase),
              y: charts.phases.map((p: any) => p.count),
              marker: { color: COLORS.palette.slice(0, charts.phases.length) },
              hovertemplate: '<b>%{x}</b><br>Records: %{y:,}<extra></extra>',
            }]}
            layout={{ ...BASE_LAYOUT, height: 280 }}
            style={{ width: '100%' }}
          />
        </div>
      </div>

      {/* Data sources with external links */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm mb-4">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Data Sources</h3>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {DATA_SOURCE_LINKS.map((ds, i) => (
            <a key={i} href={ds.url} target="_blank" rel="noopener noreferrer"
              className="px-3 py-2 bg-gray-50 rounded border border-gray-200 hover:border-[#2171B5] hover:bg-blue-50 transition-colors text-xs">
              <span className="font-semibold text-gray-700">{ds.label}</span>
              <span className="text-gray-400 ml-1">— {ds.desc}</span>
            </a>
          ))}
        </div>
      </div>

      {/* Datasets table */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        <h3 className="text-sm font-semibold text-gray-700 mb-2">Loaded Datasets</h3>
        <div className="max-h-[300px] overflow-auto">
          <table className="w-full text-xs border-collapse">
            <thead className="sticky top-0">
              <tr className="bg-gray-100 border-b-2 border-gray-300">
                <th className="px-3 py-2 text-left font-semibold">Dataset</th>
                <th className="px-3 py-2 text-right font-semibold">Rows</th>
                <th className="px-3 py-2 text-right font-semibold">Columns</th>
              </tr>
            </thead>
            <tbody>
              {sources_table.map((s: any, i: number) => (
                <tr key={i} className={`border-b border-gray-100 ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                  <td className="px-3 py-1.5">{s.dataset}</td>
                  <td className="px-3 py-1.5 text-right">{s.rows.toLocaleString()}</td>
                  <td className="px-3 py-1.5 text-right">{s.columns}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
