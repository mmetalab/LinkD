import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { fetchOverview } from '../api/client';
import { COLORS } from '../styles/theme';

const FEATURES = [
  { title: 'LinkD-DTI', desc: 'Explore 20,000+ drug-target interaction binding affinities (pKd) with selectivity scores from ChEMBL bioactivity data.', path: '/binding', color: COLORS.primary, icon: '🔬' },
  { title: 'LinkD-Select', desc: 'Visualize drug selectivity landscape via UMAP clustering. Identify highly selective vs broad-spectrum compounds.', path: '/selectivity', color: COLORS.green, icon: '🎯' },
  { title: 'LinkD-Pheno', desc: 'Real-world drug-disease associations from Mount Sinai and UK Biobank electronic health records (41K+ associations).', path: '/ehr', color: COLORS.amber, icon: '🏥' },
  { title: 'LinkD-Agent', desc: 'Ask questions in natural language. The LLM agent creates multi-step analysis plans across all data sources.', path: '/agent', color: COLORS.purple, icon: '🤖' },
];

const DATA_SOURCES = [
  { name: 'ChEMBL', desc: 'Drug-target bioactivity database', url: 'https://www.ebi.ac.uk/chembl/' },
  { name: 'Mount Sinai EHR', desc: 'Drug-disease associations with odds ratios', url: '#' },
  { name: 'UK Biobank', desc: 'Drug-cancer associations from UK population cohort', url: 'https://www.ukbiobank.ac.uk/' },
  { name: 'PRISM / GDSC', desc: 'CRISPR drug response screens', url: 'https://depmap.org/portal/prism/' },
  { name: 'Open Targets', desc: 'Causal gene-disease associations', url: 'https://www.opentargets.org/' },
];

export default function Home() {
  const [stats, setStats] = useState<any>(null);

  useEffect(() => { fetchOverview().then(d => setStats(d)); }, []);

  return (
    <div>
      {/* Hero */}
      <div className="text-center mb-10">
        <h1 className="text-3xl font-bold text-gray-900 mb-3">LinkD Agent</h1>
        <p className="text-lg text-gray-600 max-w-2xl mx-auto">
          A multi-evidence supported drug discovery platform combining drug-target interaction binding affinity,
          electronic health records, CRISPR drug response, and AI-powered multi-source evidence analysis.
        </p>
      </div>

      {/* Key stats */}
      {stats && (
        <div className="flex flex-wrap justify-center gap-6 mb-10">
          {stats.cards.slice(0, 5).map((c: any, i: number) => (
            <div key={i} className="text-center">
              <div className="text-2xl font-bold" style={{ color: c.color }}>
                {Number(c.value).toLocaleString()}
              </div>
              <div className="text-xs text-gray-500">{c.label}</div>
            </div>
          ))}
        </div>
      )}

      {/* Feature cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-10">
        {FEATURES.map((f, i) => (
          <Link key={i} to={f.path}
            className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm hover:shadow-md transition-shadow group"
            style={{ borderTop: `3px solid ${f.color}` }}>
            <div className="text-2xl mb-2">{f.icon}</div>
            <h3 className="text-sm font-bold text-gray-800 mb-2 group-hover:text-[#2171B5] transition-colors">{f.title}</h3>
            <p className="text-xs text-gray-500 leading-relaxed">{f.desc}</p>
            <div className="mt-3 text-xs font-medium" style={{ color: f.color }}>
              Explore &rarr;
            </div>
          </Link>
        ))}
      </div>

      {/* How it works */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-8">
        <h2 className="text-lg font-bold text-gray-800 mb-4">How LinkD Agent Works</h2>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div>
            <div className="text-sm font-semibold text-[#2171B5] mb-1">1. Multi-Source Data</div>
            <p className="text-xs text-gray-600">Integrates binding affinity (pKd), EHR odds ratios, CRISPR gene knockout correlations, and clinical trial data into a unified queryable database.</p>
          </div>
          <div>
            <div className="text-sm font-semibold text-[#2171B5] mb-1">2. Evidence Aggregation</div>
            <p className="text-xs text-gray-600">Combines evidence across sources to assess drug-target relationship strength: strong (3+ sources), moderate (2), or weak (1).</p>
          </div>
          <div>
            <div className="text-sm font-semibold text-[#2171B5] mb-1">3. AI-Powered Analysis</div>
            <p className="text-xs text-gray-600">An LLM agent (GPT-4o, Gemini, or Claude) breaks complex questions into multi-step analysis plans and synthesizes findings.</p>
          </div>
        </div>
      </div>

      {/* Data sources */}
      <div className="bg-white rounded-lg border border-gray-200 p-6 shadow-sm mb-8">
        <h2 className="text-lg font-bold text-gray-800 mb-4">Data Sources</h2>
        <div className="flex flex-wrap gap-3">
          {DATA_SOURCES.map((ds, i) => (
            <a key={i} href={ds.url} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-2 px-3 py-2 bg-gray-50 rounded-lg border border-gray-200 hover:border-[#2171B5] hover:bg-blue-50 transition-colors text-xs">
              <span className="font-semibold text-gray-700">{ds.name}</span>
              <span className="text-gray-400">— {ds.desc}</span>
            </a>
          ))}
        </div>
      </div>

      {/* Quick links */}
      <div className="flex justify-center gap-4">
        <Link to="/overview" className="px-5 py-2 bg-[#2171B5] text-white rounded-md text-sm font-medium hover:bg-[#1a5a90] transition-colors">
          View Database Overview
        </Link>
        <Link to="/agent" className="px-5 py-2 bg-gray-600 text-white rounded-md text-sm font-medium hover:bg-gray-700 transition-colors">
          Try LinkD-Agent
        </Link>
      </div>
    </div>
  );
}
