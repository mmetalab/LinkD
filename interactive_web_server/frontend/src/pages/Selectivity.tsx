import { useState, useEffect, useCallback } from 'react';
import PlotChart from '../components/PlotChart';
import DataTable from '../components/DataTable';
import DownloadBar from '../components/DownloadBar';
import Pagination from '../components/Pagination';
import StatCard from '../components/StatCard';
import { preloadSelectivity, searchSelectivity, downloadCSV } from '../api/client';
import { COLORS } from '../styles/theme';

export default function Selectivity() {
  const [data, setData] = useState<any>(null);
  const [page, setPage] = useState(1);
  const [typeFilter, setTypeFilter] = useState('All');
  const [drugFilter, setDrugFilter] = useState('');
  const [searchDrugId, setSearchDrugId] = useState('');
  const [searchResult, setSearchResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async (p: number, tf: string, df: string) => {
    const d = await preloadSelectivity({ page: p, page_size: 50, type_filter: tf, drug_filter: df });
    setData(d);
  }, []);

  useEffect(() => { loadData(1, 'All', ''); }, [loadData]);

  const onPageChange = (p: number) => { setPage(p); loadData(p, typeFilter, drugFilter); };
  const applyFilters = () => { setPage(1); loadData(1, typeFilter, drugFilter); };

  const doSearch = async () => {
    if (!searchDrugId) return;
    setLoading(true);
    const res = await searchSelectivity({ drug_id: searchDrugId, selectivity_type: 'All' });
    setSearchResult(res);
    setLoading(false);
  };

  const typeDist = data?.type_distribution || {};
  const totalPages = data ? Math.ceil((data.total || 0) / (data.page_size || 50)) : 0;

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-800 mb-2">LinkD-Select: Drug Selectivity Explorer</h2>
      <p className="text-sm text-gray-500 mb-4">Browse all {data?.total?.toLocaleString() || '...'} drugs with selectivity profiles. Use filters or search a specific drug for detailed analysis.</p>

      {/* Type distribution cards */}
      {Object.keys(typeDist).length > 0 && (
        <div className="grid grid-cols-3 gap-3 mb-4">
          <StatCard label="Highly Selective" value={typeDist['Highly Selective'] || 0} color={COLORS.green} />
          <StatCard label="Moderate Poly-Target" value={typeDist['Moderate poly-target'] || 0} color={COLORS.amber} />
          <StatCard label="Broad-Spectrum" value={typeDist['Broad-spectrum'] || 0} color={COLORS.red} />
        </div>
      )}

      {/* UMAP (always visible) */}
      {data?.umap && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm mb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-0.5">Drug Selectivity Landscape (UMAP)</h4>
          <p className="text-xs text-gray-400 mb-2">Each point represents a drug. Colors indicate selectivity type. Hover to see drug ID.</p>
          <PlotChart
            data={[
              ...(data.umap.traces || []).map((t: any) => ({
                type: 'scatter', mode: 'markers',
                x: t.x, y: t.y, marker: { size: 3, color: t.color, opacity: 0.4 },
                name: t.type, customdata: t.drugs,
                hovertemplate: 'Drug: %{customdata}<br>Type: ' + t.type + '<extra></extra>',
              })),
              ...(searchResult?.umap?.highlight ? [{
                type: 'scatter', mode: 'markers',
                x: [searchResult.umap.highlight.x], y: [searchResult.umap.highlight.y],
                marker: { size: 14, color: 'black', symbol: 'star' },
                name: searchResult.umap.highlight.drug,
              }] : []),
            ]}
            layout={{
              font: { family: 'Arial', size: 11, color: '#333' },
              plot_bgcolor: 'white', paper_bgcolor: 'white',
              xaxis: { title: 'UMAP-1', showgrid: false, showline: true, linecolor: '#333' },
              yaxis: { title: 'UMAP-2', showgrid: false, showline: true, linecolor: '#333' },
              height: 450, showlegend: true, legend: { font: { size: 10 } },
              margin: { l: 60, r: 20, t: 20, b: 50 },
            }}
            style={{ width: '100%' }}
          />
        </div>
      )}

      {/* Drug detail search */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 shadow-sm">
        <h4 className="text-sm font-semibold text-gray-700 mb-2">Search Drug Detail</h4>
        <div className="flex gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Drug ChEMBL ID</label>
            <input value={searchDrugId} onChange={e => setSearchDrugId(e.target.value)} placeholder="e.g., CHEMBL1229517"
              className="px-3 py-2 border border-gray-300 rounded-md text-sm w-48 focus:ring-1 focus:ring-[#2171B5] outline-none" />
          </div>
          <button onClick={doSearch} disabled={loading}
            className="px-5 py-2 bg-[#2171B5] text-white rounded-md text-sm font-medium hover:bg-[#1a5a90] disabled:opacity-50 transition-colors">
            {loading ? 'Searching...' : 'Search Drug'}
          </button>
        </div>
      </div>

      {/* Drug detail results */}
      {searchResult?.info && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 shadow-sm"
          style={{ borderLeft: `4px solid ${searchResult.info.drug_type === 'Highly Selective' ? COLORS.green : COLORS.amber}` }}>
          <h3 className="text-sm font-semibold text-gray-700 mb-1">{searchResult.info.drug} Selectivity</h3>
          <div className="flex gap-6 text-sm text-gray-600">
            <span>Selectivity Score: <strong>{searchResult.info.selectivity_score?.toFixed(3) ?? 'N/A'}</strong></span>
            <span>Type: <strong>{searchResult.info.drug_type ?? 'N/A'}</strong></span>
            <span>No. Targets Measured: <strong>{searchResult.info.n_targets ?? 'N/A'}</strong></span>
          </div>
        </div>
      )}
      {searchResult?.bars?.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm mb-4">
          <PlotChart
            data={[{ type: 'bar', orientation: 'h',
              y: searchResult.bars.map((b: any) => b.target).reverse(),
              x: searchResult.bars.map((b: any) => b.affinity).reverse(),
              marker: { color: searchResult.bars.map((b: any) => b.affinity >= 7 ? COLORS.green : COLORS.secondary).reverse() },
              hovertemplate: '<b>%{y}</b><br>pKd: %{x:.2f}<extra></extra>',
            }]}
            layout={{ title: `Target Affinities for ${searchDrugId}`, font: { family: 'Arial', size: 11 },
              plot_bgcolor: 'white', paper_bgcolor: 'white', margin: { l: 120, r: 20, t: 40, b: 40 },
              xaxis: { title: 'Binding Affinity (pKd)', showgrid: false, showline: true, linecolor: '#333' },
              height: Math.max(300, searchResult.bars.length * 25), showlegend: false,
              shapes: [{ type: 'line', x0: 7, x1: 7, y0: -0.5, y1: searchResult.bars.length - 0.5, line: { color: COLORS.red, dash: 'dash', width: 1 } }],
            }}
            style={{ width: '100%' }}
          />
        </div>
      )}

      {/* All drugs table with filters + pagination */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-gray-700">All Drugs</h3>
          <div className="flex gap-2">
            <select value={typeFilter} onChange={e => { setTypeFilter(e.target.value); setPage(1); loadData(1, e.target.value, drugFilter); }}
              className="px-2 py-1.5 border border-gray-300 rounded-md text-xs bg-white focus:ring-1 focus:ring-[#2171B5] outline-none">
              <option>All</option>
              <option>Highly Selective</option>
              <option>Moderate poly-target</option>
              <option>Broad-spectrum</option>
            </select>
            <input value={drugFilter} onChange={e => setDrugFilter(e.target.value)} onKeyDown={e => e.key === 'Enter' && applyFilters()}
              placeholder="Filter by drug ID..." className="px-2 py-1.5 border border-gray-300 rounded-md text-xs w-40 focus:ring-1 focus:ring-[#2171B5] outline-none" />
            <button onClick={applyFilters} className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded border border-gray-300">Apply</button>
          </div>
        </div>
        {data?.drugs?.length > 0 && (
          <>
            <DataTable data={data.drugs} columns={data.drug_columns || []} />
            <Pagination page={page} totalPages={totalPages} total={data.total || 0} onPageChange={onPageChange} />
            <DownloadBar onCSV={() => downloadCSV('selectivity')} />
          </>
        )}
      </div>
    </div>
  );
}
