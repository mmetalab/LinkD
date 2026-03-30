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
          <strong>LinkD</strong> is an agentic cancer drug discovery platform that bridges the gap between
          target-centric and phenotype-driven computational approaches. Conventional methods either predict
          drug-target interactions in isolation — missing the broader selectivity landscape across the
          proteome — or leverage phenotypic screens without mechanistic resolution to specific molecular targets.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed mb-4">
          LinkD addresses these limitations by integrating drug-target binding affinity and selectivity metrics
          across the druggable proteome, CRISPR-based genetic dependency maps (PRISM, GDSC) linking functional
          drug response to gene knockouts, and population-scale electronic health record associations from
          Mount Sinai (11.5M individuals) and UK Biobank (500K participants) for real-world clinical validation.
        </p>
        <p className="text-sm text-gray-600 leading-relaxed">
          An AI-powered agent (LinkD-Agent) enables researchers to query across all evidence sources using
          natural language, automatically decomposing complex biomedical questions into multi-step analysis
          plans that systematically retrieve, integrate, and synthesize findings from binding affinity,
          drug response, and EHR data to support drug repurposing decisions.
        </p>
      </div>

      {/* Method */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-6">
        <h3 className="text-lg font-bold text-gray-800 mb-3">Method Overview</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div className="p-4 bg-gray-50 rounded-lg">
            <h4 className="text-sm font-semibold mb-2" style={{ color: COLORS.primary }}>1. Target-Centric Evidence</h4>
            <p className="text-xs text-gray-600">Drug-target binding affinities (pKd) and selectivity landscapes across the druggable proteome, capturing a compound's distribution of affinities — critical for anticipating both therapeutic efficacy and off-target liabilities.</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <h4 className="text-sm font-semibold mb-2" style={{ color: COLORS.primary }}>2. Phenotype-Driven Evidence</h4>
            <p className="text-xs text-gray-600">CRISPR-based genetic dependency screens (PRISM, GDSC) linking gene knockouts to drug sensitivity, and population-scale EHR associations from two independent cohorts validating drug-disease relationships with odds ratios and propensity score matching.</p>
          </div>
          <div className="p-4 bg-gray-50 rounded-lg">
            <h4 className="text-sm font-semibold mb-2" style={{ color: COLORS.primary }}>3. AI-Powered Integration</h4>
            <p className="text-xs text-gray-600">An LLM agent decomposes natural language queries into multi-step analysis plans, systematically querying binding, selectivity, drug response, and EHR data sources, then synthesizing multi-evidence findings for drug repurposing assessment.</p>
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
          <p><strong>GitHub:</strong> <a href="https://github.com/mmetalab/LinkD" target="_blank" rel="noopener noreferrer" className="text-[#2171B5] hover:underline">github.com/mmetalab/LinkD</a></p>
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
