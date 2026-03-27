import { useEffect, useState } from 'react';
import { fetchOverview } from '../api/client';
import { COLORS } from '../styles/theme';

const DATA_SOURCES = [
  { name: 'ChEMBL Bioactivity', records: '276K+', desc: 'Drug-target-disease associations with clinical trial phase and mechanism of action data.', url: 'https://www.ebi.ac.uk/chembl/' },
  { name: 'Drug-Target Interaction Binding (pKd)', records: '20K+ targets', desc: 'Quantitative drug-target interaction binding affinity measurements (pKd values) and selectivity scores.', url: 'https://www.ebi.ac.uk/chembl/' },
  { name: 'Mount Sinai EHR', records: '41K+', desc: 'Real-world drug-disease associations with odds ratios and hazard ratios from electronic health records.', url: '#' },
  { name: 'UK Biobank', records: '693', desc: 'Drug-cancer associations with odds ratios from UK population cohort data.', url: 'https://www.ukbiobank.ac.uk/' },
  { name: 'CRISPR Drug Response', records: '464K+', desc: 'Drug sensitivity correlations from PRISM and GDSC CRISPR gene knockout screens.', url: 'https://depmap.org/portal/prism/' },
  { name: 'Open Targets', records: '13K+', desc: 'Causal gene-disease associations and target priority scores.', url: 'https://www.opentargets.org/' },
];

export default function About() {
  const [version, setVersion] = useState<any>(null);
  useEffect(() => { fetchOverview().then(d => setVersion(d)); }, []);

  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-xl font-bold text-gray-800 mb-4">About LinkD Agent</h2>

      {/* Data Version */}
      {version?.data_version && (
        <div className="bg-gray-50 rounded-lg border border-gray-200 p-4 mb-6 flex flex-wrap gap-6 text-xs text-gray-600">
          <span>Data Version: <strong>{version.data_version}</strong></span>
          <span>Last Loaded: <strong>{new Date(version.data_loaded_at).toLocaleString()}</strong></span>
          {version.source_versions && Object.entries(version.source_versions).map(([k, v]) => (
            <span key={k}>{k}: <strong>{v as string}</strong></span>
          ))}
        </div>
      )}

      {/* Overview */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-6">
        <p className="text-sm text-gray-600 leading-relaxed mb-4">
          <strong>LinkD Agent</strong> is an integrated drug discovery intelligence platform that combines
          multiple biomedical data sources — drug-target binding affinity, electronic health records, CRISPR
          drug response screens, and clinical trial data — into a unified queryable system with AI-powered
          natural language analysis.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          The platform enables researchers to explore drug-disease-target relationships through interactive
          visualizations and an LLM-powered agent that can break complex biomedical questions into multi-step
          analysis plans, automatically querying across all evidence sources and synthesizing findings.
        </p>
      </div>

      {/* Method */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-6">
        <h3 className="text-lg font-bold text-gray-800 mb-3">Method Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <h4 className="text-sm font-semibold mb-2" style={{ color: COLORS.primary }}>1. Data Integration</h4>
            <p className="text-xs text-gray-600">Six data sources are loaded and indexed at startup. Parquet files use pre-built indexes for sub-second binding affinity lookups across 20K+ targets.</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <h4 className="text-sm font-semibold mb-2" style={{ color: COLORS.primary }}>2. Evidence Aggregation</h4>
            <p className="text-xs text-gray-600">For any drug-target pair, evidence is assessed across binding affinity, drug response, target statistics, and selectivity. Strength is scored as strong (3+ sources), moderate (2), or weak (1).</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <h4 className="text-sm font-semibold mb-2" style={{ color: COLORS.primary }}>3. AI Analysis</h4>
            <p className="text-xs text-gray-600">An LLM agent (OpenAI, Gemini, or Claude) decomposes natural language queries into executable analysis plans, runs each step against the database, and produces a synthesis report.</p>
          </div>
        </div>
      </div>

      {/* Data Sources */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-6">
        <h3 className="text-lg font-bold text-gray-800 mb-3">Data Sources</h3>
        <div className="space-y-3">
          {DATA_SOURCES.map((ds, i) => (
            <div key={i} className="flex items-start gap-3 p-3 bg-gray-50 rounded-lg">
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <a href={ds.url} target="_blank" rel="noopener noreferrer"
                    className="text-sm font-semibold hover:underline" style={{ color: COLORS.primary }}>{ds.name}</a>
                  <span className="text-xs px-2 py-0.5 bg-gray-200 rounded-full text-gray-600">{ds.records}</span>
                </div>
                <p className="text-xs text-gray-500 mt-1">{ds.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Citation */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-6">
        <h3 className="text-lg font-bold text-gray-800 mb-3">Citation & Data</h3>
        <p className="text-sm text-gray-600 mb-2 italic">Citation information will be available upon publication.</p>
        <p className="text-sm text-gray-600"><strong>Data:</strong> <a href="https://doi.org/10.5281/zenodo.19241152" target="_blank" rel="noopener noreferrer" className="text-[#2171B5] hover:underline">doi.org/10.5281/zenodo.19241152</a> (Zenodo, ~16 GB)</p>
      </div>

      {/* Contact & Support */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-6">
        <h3 className="text-lg font-bold text-gray-800 mb-3">Contact & Support</h3>
        <div className="space-y-2 text-sm text-gray-600">
          <p><strong>Institution:</strong> Icahn School of Medicine at Mount Sinai</p>
          <p><strong>Email:</strong> <a href="mailto:cheng.wang@mssm.edu" className="text-[#2171B5] hover:underline">cheng.wang@mssm.edu</a></p>
          <p><strong>GitHub:</strong> <a href="https://github.com/" target="_blank" rel="noopener noreferrer" className="text-[#2171B5] hover:underline">Report issues or request features</a></p>
          <p><strong>Hosting:</strong> This web server is maintained and will remain accessible for at least 5 years following publication.</p>
        </div>
      </div>

      {/* License */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-6">
        <h3 className="text-lg font-bold text-gray-800 mb-3">License</h3>
        <p className="text-sm text-gray-600">LinkD Agent is released under the MIT License. The source code and data processing pipelines are freely available for academic use.</p>
      </div>

      {/* Tech Stack */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm">
        <h3 className="text-lg font-bold text-gray-800 mb-3">Technology</h3>
        <div className="flex flex-wrap gap-2">
          {['Python', 'FastAPI', 'React', 'TypeScript', 'Plotly.js', 'Tailwind CSS', 'pandas', 'pyarrow'].map(t => (
            <span key={t} className="px-3 py-1 bg-gray-100 rounded-full text-xs font-medium text-gray-600">{t}</span>
          ))}
        </div>
      </div>
    </div>
  );
}
