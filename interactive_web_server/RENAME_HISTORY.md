# Label Rename History

All user-facing label changes made to improve readability and clarity.

## Date: 2026-03-25

### Overview Page — Stat Cards

| Original Label | New Label | Reason |
|----------------|-----------|--------|
| `Drug-Target-Disease` | `Associations` | Too long for a stat card; abbreviated |
| `Drug Response` | `Drug Response (CRISPR)` | Clarify data source |
| `Causal Gene-Disease` | `Gene-Disease Links` | Simpler wording |

### Overview Page — Chart: Records per Source

| Original Label | New Label | Reason |
|----------------|-----------|--------|
| `Drug-Target-Disease` | `Drug-Target-Disease Associations` | Full description |
| `Causal Gene-Disease` | `Causal Gene-Disease Links` | Full description |
| `Drug Response` | `CRISPR Drug Response` | Clarify data source |

### Overview Page — Chart: Clinical Trial Phases

| Original Label | New Label | Reason |
|----------------|-----------|--------|
| `Phase 0.5` | `Preclinical` | Standard terminology |
| `Phase 1.0` | `Phase I` | Roman numeral convention |
| `Phase 2.0` | `Phase II` | Roman numeral convention |
| `Phase 3.0` | `Phase III` | Roman numeral convention |
| `Phase 4.0` | `Approved (IV)` | Indicate marketed drug |

### Binding Page — Stats and Table Headers

| Original Label | New Label | Reason |
|----------------|-----------|--------|
| `TPI` | `Target Priority` (table) / `Target Priority Index` (stat) | Expand abbreviation |
| `Avg pKd` | `Avg Binding (pKd)` | Clarify metric |
| `Max pKd` | `Max Binding (pKd)` | Clarify metric |
| `Drug Hits` | `No. Drug Hits` | Clarify it's a count |
| `Min pKd` (filter) | `Min Binding (pKd)` | Clarify metric |

### Selectivity Page

| Original Label | New Label | Reason |
|----------------|-----------|--------|
| `Score:` | `Selectivity Score:` | Explicit |
| `Targets:` | `No. Targets Measured:` | Clarify meaning |

### EHR Page — Preloaded Table Columns

| Original Label | New Label | Reason |
|----------------|-----------|--------|
| `Drug Chembl ID` | `Drug ChEMBL ID` | Correct capitalization |
| `ICD10` | `ICD-10 Code` | Standard format with hyphen |
| `Disease Description` | `Disease` | Shorter, clearer |
| `logit_or` | `Odds Ratio` | Human-readable name |
| `logit_p` | `P-Value` | Human-readable name |

### Layout Fixes

| Component | Change | Reason |
|-----------|--------|--------|
| Overview horizontal bars | Left margin 60→180px | Labels were truncated |
| Overview charts | Height 300→320px | Better proportions |
