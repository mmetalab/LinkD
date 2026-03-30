import { useState, useEffect, useCallback } from 'react';
import PlotChart from '../components/PlotChart';
import DataTable from '../components/DataTable';
import DownloadBar from '../components/DownloadBar';
import Pagination from '../components/Pagination';
import { preloadEHR, downloadCSV } from '../api/client';
import { COLORS } from '../styles/theme';

export default function EHR() {
  const [data, setData] = useState<any>(null);
  const [page, setPage] = useState(1);
  const [source, setSource] = useState('Both');
  const [icdPrefix] = useState('C'); // cancer only
  const [atcCategory, setAtcCategory] = useState('');
  const [drugFilter, setDrugFilter] = useState('');
  const [diseaseFilter, setDiseaseFilter] = useState('');

  const loadData = useCallback(async (p: number, src: string, icd: string, atc: string, drug: string, disease: string) => {
    const d = await preloadEHR({ page: p, page_size: 50, source: src, icd_prefix: icd, atc_category: atc, drug_filter: drug, disease_filter: disease });
    setData(d);
  }, []);

  useEffect(() => { loadData(1, 'Both', 'C', '', '', ''); }, [loadData]);

  const applyFilters = () => { setPage(1); loadData(1, source, icdPrefix, atcCategory, drugFilter, diseaseFilter); };
  const onPageChange = (p: number) => { setPage(p); loadData(p, source, icdPrefix, atcCategory, drugFilter, diseaseFilter); };


  const selectDrugCategory = (cat: string) => {
    const newCat = cat === atcCategory ? '' : cat; // toggle
    setAtcCategory(newCat);
    setPage(1);
    loadData(1, source, icdPrefix, newCat, drugFilter, diseaseFilter);
  };

  const totalPages = data ? Math.ceil((data.total || 0) / (data.page_size || 50)) : 0;

  return (
    <div>
      <h2 className="text-xl font-bold text-gray-800 mb-2">LinkD-Pheno: Cancer Drug-Disease Associations</h2>
      <p className="text-sm text-gray-500 mb-1">
        Real-world cancer drug-disease associations from Mount Sinai (11.5M individuals) and UK Biobank (500K participants) EHR data.
        OR &lt; 1 = protective, OR &gt; 1 = risk-increasing.
      </p>
      {data && (
        <p className="text-xs text-gray-400 mb-4">
          Showing {data.total?.toLocaleString()} deduplicated cancer associations
          {data.total_raw ? ` (from ${data.total_raw.toLocaleString()} raw records)` : ''}
        </p>
      )}

      {/* Source selector */}
      <div className="flex gap-2 mb-3">
        {['Both', 'Mount Sinai', 'UK Biobank'].map(s => (
          <button key={s} onClick={() => { setSource(s); setPage(1); loadData(1, s, icdPrefix, atcCategory, drugFilter, diseaseFilter); }}
            className={`px-3 py-1 text-xs rounded-full border transition-colors ${source === s ? 'bg-[#2171B5] text-white border-[#2171B5]' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-100'}`}>
            {s}
          </button>
        ))}
      </div>

      {/* Drug category panel */}
      {data?.drug_categories?.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-3 mb-3 shadow-sm">
          <div className="text-xs font-semibold text-gray-600 mb-2">Drug Category (ATC)</div>
          <div className="flex flex-wrap gap-1.5">
            <button onClick={() => selectDrugCategory('')}
              className={`px-3 py-1 text-xs rounded-full border transition-colors ${!atcCategory ? 'bg-[#238B45] text-white border-[#238B45]' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-100'}`}>
              All
            </button>
            {data.drug_categories.map((c: any) => (
              <button key={c.category} onClick={() => selectDrugCategory(c.category)}
                className={`px-3 py-1 text-xs rounded-full border transition-colors ${atcCategory === c.category ? 'bg-[#238B45] text-white border-[#238B45]' : 'bg-white text-gray-600 border-gray-300 hover:bg-gray-100'}`}>
                {c.category} ({c.count.toLocaleString()})
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Text filters */}
      <div className="flex flex-wrap gap-2 mb-4 items-end">
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Drug Filter</label>
          <input value={drugFilter} onChange={e => setDrugFilter(e.target.value)} placeholder="Drug ID or name..."
            className="px-3 py-1.5 border border-gray-300 rounded-md text-xs w-40 focus:ring-1 focus:ring-[#2171B5] outline-none" />
        </div>
        <div>
          <label className="block text-xs font-medium text-gray-600 mb-1">Disease Filter</label>
          <input value={diseaseFilter} onChange={e => setDiseaseFilter(e.target.value)} placeholder="ICD-10 or disease..."
            className="px-3 py-1.5 border border-gray-300 rounded-md text-xs w-40 focus:ring-1 focus:ring-[#2171B5] outline-none" />
        </div>
        <button onClick={applyFilters}
          className="px-4 py-1.5 bg-[#2171B5] text-white rounded-md text-xs font-medium hover:bg-[#1a5a90] transition-colors">
          Apply
        </button>
      </div>

      {/* Preloaded forest plot */}
      {data?.forest?.length > 0 && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm mb-4">
          <h4 className="text-sm font-semibold text-gray-700 mb-0.5">Odds Ratio vs Statistical Significance</h4>
          <p className="text-xs text-gray-400 mb-2">Each point is a drug-disease association. X = Odds Ratio (OR=1 dashed line), Y = -log10(P-value). Hover for details.</p>
          <PlotChart
            data={['mount_sinai', 'uk_biobank'].map(src => {
              const srcData = data.forest.filter((f: any) => f.source === src);
              return { type: 'scatter', mode: 'markers',
                x: srcData.map((f: any) => f.or_value),
                y: srcData.map((f: any) => f.neg_log_p),
                marker: { size: 6, color: src === 'mount_sinai' ? COLORS.primary : COLORS.amber, opacity: 0.7 },
                name: src === 'mount_sinai' ? 'Mount Sinai' : 'UK Biobank',
                customdata: srcData.map((f: any) => [f.drug_name, f.disease, f.icd10]),
                hovertemplate: '<b>Drug:</b> %{customdata[0]}<br><b>Disease:</b> %{customdata[1]} (%{customdata[2]})<br>OR: %{x:.3f}<br>-log10(p): %{y:.2f}<extra></extra>',
              };
            }).filter((t: any) => t.x.length > 0)}
            layout={{ font: { family: 'Arial', size: 11 }, plot_bgcolor: 'white', paper_bgcolor: 'white',
              xaxis: { title: { text: 'Odds Ratio', font: { size: 13, family: 'Arial' } }, showgrid: false, showline: true, linecolor: '#333' },
              yaxis: { title: { text: '-log\u2081\u2080(P-value)', font: { size: 13, family: 'Arial' } }, showgrid: true, gridcolor: '#f0f0f0', showline: true, linecolor: '#333' },
              height: 450, showlegend: true,
              margin: { l: 70, r: 20, t: 10, b: 60 },
              shapes: [
                { type: 'line', x0: 1, x1: 1, y0: 0, y1: 1, yref: 'paper', line: { color: COLORS.gray, dash: 'dash', width: 1 } },
                { type: 'line', x0: 0, x1: 1, xref: 'paper', y0: 1.3, y1: 1.3, line: { color: COLORS.red, dash: 'dot', width: 0.8 } },
              ],
              annotations: [{ x: 1.02, xref: 'paper', y: 1.3, text: 'p=0.05', showarrow: false, font: { size: 9, color: COLORS.red } }],
            }}
            style={{ width: '100%' }}
          />
        </div>
      )}

      {/* Main associations table */}
      {data && (
        <div className="bg-white rounded-lg border border-gray-200 p-4 shadow-sm mb-4">
          <h3 className="text-sm font-semibold text-gray-700 mb-2">EHR Associations</h3>
          {data.associations?.length > 0 ? (
            <>
              <DataTable data={data.associations} columns={data.columns || []} />
              <Pagination page={page} totalPages={totalPages} total={data.total || 0} onPageChange={onPageChange} />
              <DownloadBar onCSV={() => downloadCSV('ehr')} />
            </>
          ) : (
            <p className="text-xs text-gray-400 italic">No associations found with current filters.</p>
          )}
        </div>
      )}

    </div>
  );
}
