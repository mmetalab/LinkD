import { Link } from 'react-router-dom';
import { COLORS } from '../styles/theme';

const MODULES = [
  {
    title: 'LinkD-DTI: Drug-Target Interaction Binding Affinity',
    path: '/binding',
    desc: 'Browse and search all gene targets with quantitative binding affinity data.',
    features: [
      'All 1,068 gene targets with binding statistics (Avg pKd, Max pKd, Drug Hits, Target Priority Index)',
      'Click any gene to see its top 20 drug binding affinities as an interactive bar chart',
      'Search by Gene + Drug ID to see multi-source evidence radar (binding, drug response, target stats, selectivity)',
      'Filter by gene name, paginated results',
    ],
  },
  {
    title: 'LinkD-Select: Drug Selectivity Explorer',
    path: '/selectivity',
    desc: 'Explore drug selectivity profiles through UMAP dimensionality reduction.',
    features: [
      'UMAP landscape visualizing 14,981 drugs colored by selectivity type',
      'Three types: Highly Selective, Moderate Poly-Target, Broad-Spectrum',
      'Search a drug ID to see its target affinity profile and position on the UMAP',
      'Paginated drug table with selectivity scores, filterable by type',
    ],
  },
  {
    title: 'LinkD-Pheno: Phenotype-Drug Associations',
    path: '/ehr',
    desc: 'Browse real-world drug-disease associations from electronic health records.',
    features: [
      'Mount Sinai (41K+ associations) and UK Biobank (693) EHR data',
      'Odds ratios indicate protective (OR < 1) or risk-increasing (OR > 1) relationships',
      'Preloaded forest plot showing top significant associations',
      'Filter by source, drug, or disease. Select from top 30 drugs/diseases via dropdown',
      'Detailed risk analysis with comparison chart (protective vs risk-increasing)',
    ],
  },
  {
    title: 'LinkD-Agent: AI Analysis Agent',
    path: '/agent',
    desc: 'Ask complex biomedical questions in natural language.',
    features: [
      'Supports OpenAI (GPT-4o), Google Gemini, and Anthropic Claude models',
      'Automatically decomposes queries into multi-step analysis plans',
      'Each step queries binding affinity, EHR, drug response, or clinical trial data',
      'Produces synthesized analysis summary combining all evidence',
      'Pre-run examples available without API key',
    ],
  },
];

const GLOSSARY = [
  { term: 'pKd', def: 'Negative log of dissociation constant (-log₁₀ Kd). Higher values = stronger binding. pKd > 7 indicates strong binding (Kd < 100 nM).' },
  { term: 'Odds Ratio (OR)', def: 'Ratio of odds of disease in drug-exposed vs unexposed groups. OR < 1 = protective, OR > 1 = risk-increasing, OR = 1 = no effect.' },
  { term: 'TPI', def: 'Target Priority Index — a composite score ranking targets by druggability, combining binding metrics, selectivity, and clinical validation.' },
  { term: 'Selectivity Score', def: 'Measures how specifically a drug binds to its intended target vs off-targets. Higher = more selective (fewer off-targets).' },
  { term: 'UMAP', def: 'Uniform Manifold Approximation and Projection — a dimensionality reduction technique used to visualize drug similarity based on binding profiles.' },
  { term: 'AUC Correlation', def: 'Correlation between CRISPR gene knockout effect and drug sensitivity (Area Under Curve). Negative = gene may be the drug target.' },
  { term: 'FDR', def: 'False Discovery Rate — adjusted p-value accounting for multiple testing. FDR < 0.05 indicates statistical significance.' },
  { term: 'ICD-10', def: 'International Classification of Diseases, 10th revision. Standard coding system for diseases (e.g., C61 = prostate cancer).' },
];

export default function Documentation() {
  return (
    <div className="max-w-4xl mx-auto">
      <h2 className="text-xl font-bold text-gray-800 mb-4">Documentation</h2>

      {/* Quick start */}
      <div className="bg-blue-50 rounded-lg border border-blue-200 p-5 mb-6">
        <h3 className="text-sm font-bold mb-2" style={{ color: COLORS.primary }}>Quick Start</h3>
        <ol className="text-xs text-gray-600 space-y-1 list-decimal ml-4">
          <li>Browse the <Link to="/overview" className="font-semibold underline" style={{ color: COLORS.primary }}>Database Overview</Link> to see available data</li>
          <li>Explore the <Link to="/binding" className="font-semibold underline" style={{ color: COLORS.primary }}>Binding</Link>, <Link to="/selectivity" className="font-semibold underline" style={{ color: COLORS.primary }}>Selectivity</Link>, or <Link to="/ehr" className="font-semibold underline" style={{ color: COLORS.primary }}>EHR</Link> explorers — data loads automatically</li>
          <li>Try <Link to="/agent" className="font-semibold underline" style={{ color: COLORS.primary }}>LinkD-Agent</Link> — click a pre-run example or enter your own query with an API key</li>
        </ol>
      </div>

      {/* Modules */}
      <div className="space-y-4 mb-6">
        {MODULES.map((m, i) => (
          <div key={i} className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm">
            <div className="flex items-center gap-3 mb-2">
              <Link to={m.path} className="text-sm font-bold hover:underline" style={{ color: COLORS.primary }}>{m.title}</Link>
            </div>
            <p className="text-xs text-gray-500 mb-3">{m.desc}</p>
            <ul className="space-y-1">
              {m.features.map((f, j) => (
                <li key={j} className="text-xs text-gray-600 flex gap-2">
                  <span className="text-gray-400 mt-0.5">•</span>
                  <span>{f}</span>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </div>



      {/* Glossary */}
      <div className="bg-white rounded-lg border border-gray-200 p-5 shadow-sm mb-6">
        <h3 className="text-lg font-bold text-gray-800 mb-3">Glossary</h3>
        <div className="space-y-3">
          {GLOSSARY.map((g, i) => (
            <div key={i} className="flex gap-3">
              <span className="text-xs font-bold text-gray-700 w-32 shrink-0">{g.term}</span>
              <span className="text-xs text-gray-500">{g.def}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}
