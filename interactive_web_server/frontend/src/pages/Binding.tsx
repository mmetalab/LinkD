import { useState, useEffect, useCallback } from 'react';
import PlotChart from '../components/PlotChart';
import DataTable from '../components/DataTable';
import DownloadBar from '../components/DownloadBar';
import Pagination from '../components/Pagination';
import { preloadBinding, searchBinding, downloadCSV } from '../api/client';
import { COLORS } from '../styles/theme';

export default function Binding() {
  const [data, setData] = useState<any>(null);
  const [page, setPage] = useState(1);
  const [geneFilter, setGeneFilter] = useState('');
  const [searchGene, setSearchGene] = useState('');
  const [drugId, setDrugId] = useState('');
  const [minAff, setMinAff] = useState('');
  const [searchResult, setSearchResult] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  const loadData = useCallback(async (p: number, filter: string) => {
    const d = await preloadBinding({ page: p, page_size: 50, gene_filter: filter });
    setData(d);
  }, []);

  useEffect(() => { loadData(1, ''); }, [loadData]);

  const onFilterChange = (val: string) => {
    setGeneFilter(val);
    setPage(1);
    loadData(1, val);
  };

  const onPageChange = (p: number) => {
    setPage(p);
    loadData(p, geneFilter);
  };

  const doSearch = async (g?: string) => {
    const gene = g || searchGene;
    if (!gene && !drugId) return;
    setLoading(true);
    setSearchGene(gene);
    const res = await searchBinding({ gene, drug_id: drugId, min_affinity: minAff ? parseFloat(minAff) : undefined });
    setSearchResult(res);
    setLoading(false);
  };

  const totalPages = data ? Math.ceil((data.total || 0) / (data.page_size || 50)) : 0;

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-800 mb-2">LinkD-DTI: Drug-Target Interaction Binding Affinity</h2>
      <p className="text-sm text-gray-500 mb-4">Browse all {data?.total?.toLocaleString() || '...'} gene targets with binding statistics. Click a gene to explore its drug binding landscape.</p>

      {/* Search bar */}
      <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 shadow-sm">
        <div className="flex flex-wrap gap-3 items-end">
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Gene Symbol</label>
            <input value={searchGene} onChange={e => setSearchGene(e.target.value)} placeholder="e.g., BRAF, EGFR"
              className="px-3 py-2 border border-gray-300 rounded-md text-sm w-40 focus:ring-1 focus:ring-[#2171B5] outline-none" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Drug ChEMBL ID</label>
            <input value={drugId} onChange={e => setDrugId(e.target.value)} placeholder="e.g., CHEMBL1229517"
              className="px-3 py-2 border border-gray-300 rounded-md text-sm w-48 focus:ring-1 focus:ring-[#2171B5] outline-none" />
          </div>
          <div>
            <label className="block text-xs font-medium text-gray-600 mb-1">Min Binding (pKd)</label>
            <input value={minAff} onChange={e => setMinAff(e.target.value)} placeholder="e.g., 7.0"
              className="px-3 py-2 border border-gray-300 rounded-md text-sm w-24 focus:ring-1 focus:ring-[#2171B5] outline-none" />
          </div>
          <button onClick={() => doSearch()} disabled={loading}
            className="px-5 py-2 bg-[#2171B5] text-white rounded-md text-sm font-medium hover:bg-[#1a5a90] disabled:opacity-50 transition-colors">
            {loading ? 'Searching...' : 'Search'}
          </button>
        </div>
      </div>

      {/* Search results (charts) */}
      {searchResult && !searchResult.error && (
        <>
          {searchResult.stats && (
            <div className="bg-white rounded-lg border border-gray-200 p-4 mb-4 shadow-sm" style={{ borderLeft: `4px solid ${COLORS.primary}` }}>
              <h3 className="text-sm font-semibold text-gray-700 mb-1">{searchGene} Binding Statistics</h3>
              <div className="flex gap-6 text-sm text-gray-600">
                <span>Avg Binding (pKd): <strong>{searchResult.stats.avg_pkd?.toFixed(2) ?? 'N/A'}</strong></span>
                <span>Max Binding (pKd): <strong>{searchResult.stats.max_pkd?.toFixed(2) ?? 'N/A'}</strong></span>
                <span>No. Drug Hits: <strong>{searchResult.stats.drug_hits ?? 'N/A'}</strong></span>
                <span>Target Priority Index: <strong>{typeof searchResult.stats.tpi === 'number' ? searchResult.stats.tpi.toFixed(2) : 'N/A'}</strong></span>
              </div>
            </div>
          )}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
            {searchResult.landscape?.length > 0 && (
              <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
                <PlotChart
                  data={[{ type: 'bar', orientation: 'h',
                    y: searchResult.landscape.map((d: any) => d.drug).reverse(),
                    x: searchResult.landscape.map((d: any) => d.affinity).reverse(),
                    marker: { color: searchResult.landscape.map((d: any) => d.affinity >= 7 ? COLORS.green : COLORS.secondary).reverse() },
                    hovertemplate: '<b>%{y}</b><br>pKd: %{x:.2f}<extra></extra>',
                  }]}
                  layout={{ title: `Drug Binding Affinities for ${searchGene}`, font: { family: 'Arial', size: 11 },
                    plot_bgcolor: 'white', paper_bgcolor: 'white', margin: { l: 120, r: 20, t: 40, b: 40 },
                    xaxis: { title: 'Binding Affinity (pKd)', showgrid: false, showline: true, linecolor: '#333' },
                    height: Math.max(350, searchResult.landscape.length * 25), showlegend: false,
                    shapes: [{ type: 'line', x0: 7, x1: 7, y0: -0.5, y1: searchResult.landscape.length - 0.5, line: { color: COLORS.red, dash: 'dash', width: 1 } }],
                  }}
                  style={{ width: '100%' }}
                />
              </div>
            )}
            {searchResult.radar && (
              <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
                <PlotChart
                  data={[{ type: 'scatterpolar',
                    r: [...searchResult.radar.values, searchResult.radar.values[0]],
                    theta: [...searchResult.radar.categories, searchResult.radar.categories[0]],
                    fill: 'toself', fillcolor: 'rgba(33,113,181,0.2)',
                    line: { color: COLORS.primary, width: 2 }, marker: { size: 8, color: COLORS.primary },
                  }]}
                  layout={{ title: `Evidence: ${drugId} / ${searchGene} — ${searchResult.radar.overall_strength.toUpperCase()}`,
                    font: { family: 'Arial', size: 11 }, plot_bgcolor: 'white', paper_bgcolor: 'white',
                    polar: { radialaxis: { visible: true, range: [0, 1.1] } },
                    height: 400, showlegend: false, margin: { l: 40, r: 40, t: 50, b: 40 },
                  }}
                  style={{ width: '100%' }}
                />
              </div>
            )}
          </div>
          {searchResult.table?.length > 0 && (
            <><DataTable data={searchResult.table} columns={searchResult.table_columns} /><DownloadBar onCSV={() => downloadCSV('binding')} /></>
          )}
          <button onClick={() => setSearchResult(null)} className="mt-4 text-xs text-[#2171B5] hover:underline">&larr; Back to all genes</button>
        </>
      )}
      {searchResult?.error && <p className="text-red-500 text-sm mb-4">{searchResult.error}</p>}

      {/* All genes table (shown when no search result) */}
      {!searchResult && data && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm">
          <div className="flex items-center justify-between mb-3">
            <h3 className="text-sm font-semibold text-gray-700">All Gene Targets</h3>
            <input value={geneFilter} onChange={e => onFilterChange(e.target.value)} placeholder="Filter by gene name..."
              className="px-3 py-1.5 border border-gray-300 rounded-md text-xs w-48 focus:ring-1 focus:ring-[#2171B5] outline-none" />
          </div>
          <div className="max-h-[500px] overflow-auto">
            <table className="w-full text-xs border-collapse">
              <thead className="sticky top-0">
                <tr className="bg-gray-100 border-b-2 border-gray-300">
                  <th className="px-3 py-2 text-left font-semibold">Gene</th>
                  <th className="px-3 py-2 text-right font-semibold">No. Drugs</th>
                  <th className="px-3 py-2 text-right font-semibold">Avg Binding (pKd)</th>
                  <th className="px-3 py-2 text-right font-semibold">Max Binding (pKd)</th>
                  <th className="px-3 py-2 text-right font-semibold">Target Priority</th>
                </tr>
              </thead>
              <tbody>
                {data.genes?.map((g: any, i: number) => (
                  <tr key={i} onClick={() => doSearch(g.gene)}
                    className={`border-b border-gray-100 cursor-pointer hover:bg-blue-50 transition-colors ${i % 2 === 0 ? 'bg-white' : 'bg-gray-50'}`}>
                    <td className="px-3 py-2 font-medium text-[#2171B5]">{g.gene}</td>
                    <td className="px-3 py-2 text-right">{g.drug_count?.toLocaleString()}</td>
                    <td className="px-3 py-2 text-right">{g.avg_pkd?.toFixed(2) ?? '—'}</td>
                    <td className="px-3 py-2 text-right">{g.max_pkd?.toFixed(2) ?? '—'}</td>
                    <td className="px-3 py-2 text-right">{typeof g.tpi === 'number' ? g.tpi.toFixed(2) : '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination page={page} totalPages={totalPages} total={data.total || 0} onPageChange={onPageChange} />
        </div>
      )}
    </div>
  );
}
