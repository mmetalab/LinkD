"""
Database Query Module for Drug-Disease-Target Associations

This module provides functions to query information about drugs, diseases, targets,
and their associations from the CSV database files.
"""

import pandas as pd
import os
import json as _json
from typing import List, Dict, Optional, Union
from pathlib import Path

try:
    import pyarrow.parquet as pq
    PYARROW_AVAILABLE = True
except ImportError:
    PYARROW_AVAILABLE = False


class DrugDiseaseTargetDB:
    """Database class for querying drug, disease, and target information."""
    
    def __init__(self, database_dir: str = "Database", load_full_data: bool = True):
        """
        Initialize the database with CSV files.
        
        Args:
            database_dir: Path to the directory containing CSV files
            load_full_data: If True, load full data even for large files (>200MB).
                           If False, sample large files to 100,000 rows for performance.
        """
        self.database_dir = Path(database_dir)
        self.dfs = {}
        self.load_full_data = load_full_data
        self._load_databases()
    
    def _load_databases(self):
        """Load all CSV files into memory."""
        print("Loading database files...")
        if not self.load_full_data:
            print("Note: Large files will be sampled to 100,000 rows for performance.")
        else:
            print("Note: Loading full data from all files (this may take time for large files).")
        
        # Association files are in Target_Disease_Association folder
        association_dir = self.database_dir.parent / "Target_Disease_Association"
        
        # Drug-Target-Disease associations
        drug_file = association_dir / "drug_target_disease.csv"
        if drug_file.exists():
            print(f"Loading {drug_file.name}...")
            self.dfs['drug_target_disease'] = pd.read_csv(drug_file, low_memory=False)
            print(f"  Loaded {len(self.dfs['drug_target_disease']):,} records")
        
        # Causal gene-disease associations
        causal_file = association_dir / "causal_gene_disease.csv"
        if causal_file.exists():
            print(f"Loading {causal_file.name}...")
            self.dfs['causal_gene_disease'] = pd.read_csv(causal_file, low_memory=False)
            print(f"  Loaded {len(self.dfs['causal_gene_disease']):,} records")
        
        # Oncogene information (in Database folder)
        onco_file = self.database_dir / "onco_genes.csv"
        if onco_file.exists():
            print(f"Loading {onco_file.name}...")
            self.dfs['onco_genes'] = pd.read_csv(onco_file, low_memory=False)
            print(f"  Loaded {len(self.dfs['onco_genes']):,} records")
        
        # Target priority information (in Target_Disease_Association folder)
        target_priority_file = association_dir / "target_priority.csv"
        if target_priority_file.exists():
            print(f"Loading {target_priority_file.name}...")
            self.dfs['target_priority'] = pd.read_csv(target_priority_file, low_memory=False)
            print(f"  Loaded {len(self.dfs['target_priority']):,} records")
        
        # Disease-target associations (by source) - load sample if too large and load_full_data is False
        disease_target_source_file = association_dir / "disease_target_by_source.csv"
        if disease_target_source_file.exists():
            file_size = disease_target_source_file.stat().st_size / (1024 * 1024)  # MB
            if file_size > 200 and not self.load_full_data:
                print(f"Loading sample from {disease_target_source_file.name} (file is {file_size:.1f} MB)...")
                self.dfs['disease_target_source'] = pd.read_csv(disease_target_source_file, nrows=100000, low_memory=False)
                print(f"  Loaded sample of {len(self.dfs['disease_target_source']):,} records")
            else:
                if file_size > 200:
                    print(f"Loading full data from {disease_target_source_file.name} (file is {file_size:.1f} MB, this may take a while)...")
                else:
                    print(f"Loading {disease_target_source_file.name}...")
                self.dfs['disease_target_source'] = pd.read_csv(disease_target_source_file, low_memory=False)
                print(f"  Loaded {len(self.dfs['disease_target_source']):,} records")
        
        # Disease-target associations (overall) - load sample if too large and load_full_data is False
        disease_target_overall_file = association_dir / "disease_target_overall.csv"
        if disease_target_overall_file.exists():
            file_size = disease_target_overall_file.stat().st_size / (1024 * 1024)  # MB
            if file_size > 200 and not self.load_full_data:
                print(f"Loading sample from {disease_target_overall_file.name} (file is {file_size:.1f} MB)...")
                self.dfs['disease_target_overall'] = pd.read_csv(disease_target_overall_file, nrows=100000, low_memory=False)
                print(f"  Loaded sample of {len(self.dfs['disease_target_overall']):,} records")
            else:
                if file_size > 200:
                    print(f"Loading full data from {disease_target_overall_file.name} (file is {file_size:.1f} MB, this may take a while)...")
                else:
                    print(f"Loading {disease_target_overall_file.name}...")
                self.dfs['disease_target_overall'] = pd.read_csv(disease_target_overall_file, low_memory=False)
                print(f"  Loaded {len(self.dfs['disease_target_overall']):,} records")
        
        # EHR Results data (Mount Sinai and UK Biobank)
        ehr_dir = self.database_dir.parent / "EHR_Results"
        
        # Mount Sinai drug-disease associations
        mount_sinai_file = ehr_dir / "mount_sinai_drug_disease.csv"
        if mount_sinai_file.exists():
            print(f"Loading {mount_sinai_file.name}...")
            self.dfs['ehr_mount_sinai'] = pd.read_csv(mount_sinai_file, low_memory=False)
            print(f"  Loaded {len(self.dfs['ehr_mount_sinai']):,} records")
        
        # UK Biobank drug-disease associations
        uk_biobank_file = ehr_dir / "uk_biobank_drug_disease.csv"
        if uk_biobank_file.exists():
            print(f"Loading {uk_biobank_file.name}...")
            self.dfs['ehr_uk_biobank'] = pd.read_csv(uk_biobank_file, low_memory=False)
            print(f"  Loaded {len(self.dfs['ehr_uk_biobank']):,} records")
        
        # Drug Response data (CRISPR correlation)
        drug_response_dir = self.database_dir.parent / "DrugResponse"
        drug_response_file = drug_response_dir / "drug_response_crispr_correlation.csv"
        if drug_response_file.exists():
            print(f"Loading {drug_response_file.name}...")
            self.dfs['drug_response'] = pd.read_csv(drug_response_file, low_memory=False)
            print(f"  Loaded {len(self.dfs['drug_response']):,} records")
        
        # Drug-Target Metrics data (binding affinity and selectivity)
        metrics_dir = self.database_dir.parent / "DrugTargetMetrics"
        
        # Drug selectivity metrics
        drug_selectivity_file = metrics_dir / "drug_selectivity_metrics.csv"
        if drug_selectivity_file.exists():
            print(f"Loading {drug_selectivity_file.name}...")
            self.dfs['drug_selectivity'] = pd.read_csv(drug_selectivity_file, low_memory=False)
            print(f"  Loaded {len(self.dfs['drug_selectivity']):,} records")
        
        # Drug UMAP clustering
        drug_umap_file = metrics_dir / "drug_umap_clustering.csv"
        if drug_umap_file.exists():
            print(f"Loading {drug_umap_file.name}...")
            self.dfs['drug_umap'] = pd.read_csv(drug_umap_file, low_memory=False)
            print(f"  Loaded {len(self.dfs['drug_umap']):,} records")
        
        # Target binding statistics
        target_binding_file = metrics_dir / "target_binding_stats.csv"
        if target_binding_file.exists():
            print(f"Loading {target_binding_file.name}...")
            self.dfs['target_binding_stats'] = pd.read_csv(target_binding_file, low_memory=False)
            print(f"  Loaded {len(self.dfs['target_binding_stats']):,} records")
        
        # Store parquet directory path for on-demand loading
        self.parquet_dir = metrics_dir / "target_centric_pan"

        # Load pre-built indexes for fast parquet lookups
        self._parquet_drug_index = {}
        self._parquet_target_index = {}
        drug_idx = self.parquet_dir / "drug_index.json"
        target_idx = self.parquet_dir / "target_index.json"
        if drug_idx.exists():
            with open(drug_idx) as f:
                self._parquet_drug_index = _json.load(f)
            print(f"  Loaded parquet drug index: {len(self._parquet_drug_index):,} drugs")
        if target_idx.exists():
            with open(target_idx) as f:
                self._parquet_target_index = _json.load(f)
            print(f"  Loaded parquet target index: {len(self._parquet_target_index):,} targets")

        print("Database loading complete!\n")
    
    def get_database_info(self) -> Dict:
        """Get summary information about all loaded databases."""
        info = {}
        for name, df in self.dfs.items():
            info[name] = {
                'rows': len(df),
                'columns': list(df.columns),
                'column_count': len(df.columns)
            }
        return info
    
    # ========== Drug Queries ==========
    
    def search_drugs(self, drug_id: Optional[str] = None, 
                    gene: Optional[str] = None,
                    disease_id: Optional[str] = None,
                    phase: Optional[Union[float, int]] = None,
                    status: Optional[str] = None) -> pd.DataFrame:
        """
        Search for drugs based on various criteria.
        
        Args:
            drug_id: ChEMBL drug ID (e.g., 'CHEMBL265502')
            gene: Gene symbol (e.g., 'FGF1')
            disease_id: Disease ID (e.g., 'DOID_10113')
            phase: Clinical trial phase (0.5, 1.0, 2.0, 3.0, 4.0)
            status: Trial status (e.g., 'Completed', 'Active, not recruiting')
        
        Returns:
            DataFrame with matching drug records
        """
        if 'drug_target_disease' not in self.dfs:
            return pd.DataFrame()
        
        df = self.dfs['drug_target_disease'].copy()
        
        if drug_id:
            df = df[df['drugId'].str.contains(drug_id, case=False, na=False)]
        if gene:
            df = df[df['Gene'].str.contains(gene, case=False, na=False)]
        if disease_id:
            df = df[df['diseaseId'].str.contains(disease_id, case=False, na=False)]
        if phase is not None:
            df = df[df['phase'] == phase]
        if status:
            df = df[df['status'].str.contains(status, case=False, na=False)]
        
        return df
    
    def get_drugs_by_target(self, target_gene: str) -> pd.DataFrame:
        """Get all drugs targeting a specific gene."""
        return self.search_drugs(gene=target_gene)
    
    def get_drugs_by_disease(self, disease_id: str) -> pd.DataFrame:
        """Get all drugs for a specific disease."""
        return self.search_drugs(disease_id=disease_id)
    
    # ========== Disease Queries ==========
    
    def search_diseases(self, disease_id: Optional[str] = None,
                       icd_code: Optional[str] = None,
                       disease_name: Optional[str] = None,
                       gene: Optional[str] = None) -> pd.DataFrame:
        """
        Search for diseases based on various criteria.
        
        Args:
            disease_id: Disease ID (e.g., 'DOID_10113', 'EFO_0000094')
            icd_code: ICD code (e.g., 'A54', 'C16')
            disease_name: Disease name (partial match)
            gene: Associated gene symbol
        
        Returns:
            DataFrame with matching disease records
        """
        results = []
        
        # Search in drug-target-disease associations
        if 'drug_target_disease' in self.dfs:
            df = self.dfs['drug_target_disease'].copy()
            mask = pd.Series([True] * len(df))
            
            if disease_id:
                mask &= df['diseaseId'].str.contains(disease_id, case=False, na=False)
            if icd_code:
                mask &= df['ICD_Code'].str.contains(icd_code, case=False, na=False)
            if disease_name:
                mask &= df['subject_label'].str.contains(disease_name, case=False, na=False)
            if gene:
                mask &= df['Gene'].str.contains(gene, case=False, na=False)
            
            if mask.any():
                disease_cols = ['diseaseId', 'subject_label', 'ICD_Code', 'Gene', 'targetName', 'drugId']
                available_cols = [c for c in disease_cols if c in df.columns]
                results.append(df.loc[mask, available_cols].drop_duplicates())
        
        # Search in causal gene-disease associations
        if 'causal_gene_disease' in self.dfs:
            df = self.dfs['causal_gene_disease'].copy()
            mask = pd.Series([True] * len(df))
            
            if disease_id:
                mask &= df['Disease Name'].str.contains(disease_id, case=False, na=False)
            if icd_code:
                mask &= df['ICD_Code'].str.contains(icd_code, case=False, na=False)
            if disease_name:
                mask &= df['Disease Name'].str.contains(disease_name, case=False, na=False)
            if gene:
                mask &= df['Gene'].str.contains(gene, case=False, na=False)
            
            if mask.any():
                results.append(df.loc[mask].drop_duplicates())
        
        if results:
            return pd.concat(results, ignore_index=True).drop_duplicates()
        return pd.DataFrame()
    
    def get_diseases_by_gene(self, gene: str) -> pd.DataFrame:
        """Get all diseases associated with a specific gene."""
        return self.search_diseases(gene=gene)
    
    # ========== Target/Gene Queries ==========
    
    def search_targets(self, gene: Optional[str] = None,
                      target_id: Optional[str] = None,
                      target_name: Optional[str] = None,
                      disease_id: Optional[str] = None,
                      is_oncogene: Optional[bool] = None) -> pd.DataFrame:
        """
        Search for targets/genes based on various criteria.
        
        Args:
            gene: Gene symbol (e.g., 'BRAF', 'EGFR')
            target_id: Target ID (e.g., 'ENSG00000113578')
            target_name: Target name (partial match)
            disease_id: Associated disease ID
            is_oncogene: Filter by oncogene status (True for oncogene, False for TSG)
        
        Returns:
            DataFrame with matching target records
        """
        results = []
        
        # Search in drug-target-disease associations
        if 'drug_target_disease' in self.dfs:
            df = self.dfs['drug_target_disease'].copy()
            mask = pd.Series([True] * len(df))
            
            if gene:
                mask &= df['Gene'].str.contains(gene, case=False, na=False)
            if target_id:
                mask &= df['targetId'].str.contains(target_id, case=False, na=False)
            if target_name:
                mask &= df['targetName'].str.contains(target_name, case=False, na=False)
            if disease_id:
                mask &= df['diseaseId'].str.contains(disease_id, case=False, na=False)
            
            if mask.any():
                target_cols = ['targetId', 'Gene', 'targetName', 'mechanismOfAction', 'diseaseId', 'drugId']
                available_cols = [c for c in target_cols if c in df.columns]
                results.append(df.loc[mask, available_cols].drop_duplicates())
        
        # Search in oncogene database
        if 'onco_genes' in self.dfs and gene:
            df = self.dfs['onco_genes'].copy()
            mask = df['Gene'].str.contains(gene, case=False, na=False)
            
            if is_oncogene is not None:
                if is_oncogene:
                    mask &= df['Role'].isin(['Oncogene', 'Both'])
                else:
                    mask &= df['Role'].isin(['TSG', 'Both'])
            
            if mask.any():
                results.append(df.loc[mask])
        
        # Search in target priority database
        if 'target_priority' in self.dfs:
            df = self.dfs['target_priority'].copy()
            mask = pd.Series([True] * len(df))
            
            if gene:
                mask &= df['Gene'].str.contains(gene, case=False, na=False)
            if target_id:
                mask &= df['targetId'].str.contains(target_id, case=False, na=False)
            if disease_id:
                mask &= df['diseaseId'].str.contains(disease_id, case=False, na=False)
            
            if mask.any():
                priority_cols = ['targetId', 'Gene', 'diseaseId', 'score', 'evidenceCount', 'subject_label']
                available_cols = [c for c in priority_cols if c in df.columns]
                results.append(df.loc[mask, available_cols].drop_duplicates())
        
        if results:
            return pd.concat(results, ignore_index=True).drop_duplicates()
        return pd.DataFrame()
    
    def get_target_info(self, gene: str) -> Dict:
        """Get comprehensive information about a target/gene."""
        info = {
            'gene': gene,
            'drugs': [],
            'diseases': [],
            'onco_info': None,
            'target_priority': []
        }
        
        # Get drugs targeting this gene
        drugs = self.get_drugs_by_target(gene)
        if not drugs.empty:
            info['drugs'] = drugs[['drugId', 'targetName', 'mechanismOfAction', 'diseaseId', 'phase', 'status']].to_dict('records')
        
        # Get diseases associated with this gene
        diseases = self.get_diseases_by_gene(gene)
        if not diseases.empty:
            disease_cols = ['diseaseId', 'subject_label', 'ICD_Code', 'Disease Name', 'CausalType']
            available_cols = [c for c in disease_cols if c in diseases.columns]
            info['diseases'] = diseases[available_cols].drop_duplicates().to_dict('records')
        
        # Get oncogene information
        if 'onco_genes' in self.dfs:
            onco = self.dfs['onco_genes'][self.dfs['onco_genes']['Gene'] == gene]
            if not onco.empty:
                info['onco_info'] = onco.iloc[0].to_dict()
        
        # Get target priority information
        if 'target_priority' in self.dfs:
            priority = self.dfs['target_priority'][self.dfs['target_priority']['Gene'] == gene]
            if not priority.empty:
                info['target_priority'] = priority[['diseaseId', 'score', 'evidenceCount', 'subject_label']].to_dict('records')
        
        return info
    
    # ========== Association Queries ==========
    
    def get_drug_disease_associations(self, drug_id: Optional[str] = None,
                                     disease_id: Optional[str] = None) -> pd.DataFrame:
        """Get drug-disease associations."""
        if 'drug_target_disease' not in self.dfs:
            return pd.DataFrame()
        
        df = self.dfs['drug_target_disease'].copy()
        
        if drug_id:
            df = df[df['drugId'].str.contains(drug_id, case=False, na=False)]
        if disease_id:
            df = df[df['diseaseId'].str.contains(disease_id, case=False, na=False)]
        
        return df[['drugId', 'diseaseId', 'subject_label', 'ICD_Code', 'Gene', 'targetName', 'phase', 'status']].drop_duplicates()
    
    def get_disease_target_associations(self, disease_id: Optional[str] = None,
                                       gene: Optional[str] = None) -> pd.DataFrame:
        """Get disease-target associations with scores."""
        results = []
        
        if 'disease_target_overall' in self.dfs:
            df = self.dfs['disease_target_overall'].copy()
            mask = pd.Series([True] * len(df))
            
            if disease_id:
                mask &= df['diseaseId'].str.contains(disease_id, case=False, na=False)
            if gene:
                mask &= df['Gene'].str.contains(gene, case=False, na=False)
            
            if mask.any():
                cols = ['diseaseId', 'subject_label', 'ICD_Code', 'targetId', 'Gene', 'score', 'evidenceCount']
                available_cols = [c for c in cols if c in df.columns]
                results.append(df.loc[mask, available_cols])
        
        if 'target_priority' in self.dfs:
            df = self.dfs['target_priority'].copy()
            mask = pd.Series([True] * len(df))
            
            if disease_id:
                mask &= df['diseaseId'].str.contains(disease_id, case=False, na=False)
            if gene:
                mask &= df['Gene'].str.contains(gene, case=False, na=False)
            
            if mask.any():
                cols = ['diseaseId', 'subject_label', 'ICD_Code', 'targetId', 'Gene', 'score', 'evidenceCount']
                available_cols = [c for c in cols if c in df.columns]
                results.append(df.loc[mask, available_cols])
        
        if results:
            return pd.concat(results, ignore_index=True).drop_duplicates()
        return pd.DataFrame()
    
    def get_causal_gene_disease_associations(self, gene: Optional[str] = None,
                                            disease_name: Optional[str] = None) -> pd.DataFrame:
        """Get causal gene-disease associations."""
        if 'causal_gene_disease' not in self.dfs:
            return pd.DataFrame()
        
        df = self.dfs['causal_gene_disease'].copy()
        mask = pd.Series([True] * len(df))
        
        if gene:
            mask &= df['Gene'].str.contains(gene, case=False, na=False)
        if disease_name:
            mask &= df['Disease Name'].str.contains(disease_name, case=False, na=False)
        
        return df.loc[mask]
    
    # ========== Statistics and Summaries ==========
    
    def get_statistics(self) -> Dict:
        """Get overall statistics about the database."""
        stats = {}
        
        if 'drug_target_disease' in self.dfs:
            df = self.dfs['drug_target_disease']
            stats['drugs'] = {
                'total_records': len(df),
                'unique_drugs': df['drugId'].nunique() if 'drugId' in df.columns else 0,
                'unique_targets': df['Gene'].nunique() if 'Gene' in df.columns else 0,
                'unique_diseases': df['diseaseId'].nunique() if 'diseaseId' in df.columns else 0,
                'phases': df['phase'].value_counts().to_dict() if 'phase' in df.columns else {}
            }
        
        if 'causal_gene_disease' in self.dfs:
            df = self.dfs['causal_gene_disease']
            stats['causal_associations'] = {
                'total_records': len(df),
                'unique_genes': df['Gene'].nunique() if 'Gene' in df.columns else 0,
                'unique_diseases': df['Disease Name'].nunique() if 'Disease Name' in df.columns else 0,
                'causal_types': df['CausalType'].value_counts().to_dict() if 'CausalType' in df.columns else {}
            }
        
        if 'onco_genes' in self.dfs:
            df = self.dfs['onco_genes']
            stats['oncogenes'] = {
                'total_genes': len(df),
                'role_distribution': df['Role'].value_counts().to_dict() if 'Role' in df.columns else {}
            }
        
        if 'ehr_mount_sinai' in self.dfs:
            df = self.dfs['ehr_mount_sinai']
            stats['ehr_mount_sinai'] = {
                'total_records': len(df),
                'unique_drugs': df['Drug Chembl ID'].nunique() if 'Drug Chembl ID' in df.columns else 0,
                'unique_diseases': df['ICD10'].nunique() if 'ICD10' in df.columns else 0
            }
        
        if 'ehr_uk_biobank' in self.dfs:
            df = self.dfs['ehr_uk_biobank']
            stats['ehr_uk_biobank'] = {
                'total_records': len(df),
                'unique_drugs': df['Drug Chembl ID'].nunique() if 'Drug Chembl ID' in df.columns else 0,
                'unique_diseases': df['ICD10'].nunique() if 'ICD10' in df.columns else 0
            }
        
        if 'drug_response' in self.dfs:
            df = self.dfs['drug_response']
            stats['drug_response'] = {
                'total_records': len(df),
                'unique_drugs': df['drugs'].nunique() if 'drugs' in df.columns else 0,
                'unique_genes': df['genes'].nunique() if 'genes' in df.columns else 0,
                'sources': df['source'].value_counts().to_dict() if 'source' in df.columns else {}
            }
        
        return stats
    
    # ========== EHR Data Queries ==========
    
    def get_ehr_drug_disease_associations(self, 
                                         drug_id: Optional[str] = None,
                                         drug_name: Optional[str] = None,
                                         icd_code: Optional[str] = None,
                                         disease_name: Optional[str] = None,
                                         source: Optional[str] = None) -> pd.DataFrame:
        """
        Get EHR drug-disease associations from Mount Sinai or UK Biobank.
        
        Args:
            drug_id: ChEMBL drug ID (e.g., 'CHEMBL716')
            drug_name: Drug name (partial match)
            icd_code: ICD10 code (e.g., 'C61', 'I10')
            disease_name: Disease description (partial match)
            source: 'mount_sinai', 'uk_biobank', or None for both
        
        Returns:
            DataFrame with EHR associations
        """
        results = []
        
        sources = []
        if source == 'mount_sinai' or source is None:
            if 'ehr_mount_sinai' in self.dfs:
                sources.append(('ehr_mount_sinai', self.dfs['ehr_mount_sinai']))
        if source == 'uk_biobank' or source is None:
            if 'ehr_uk_biobank' in self.dfs:
                sources.append(('ehr_uk_biobank', self.dfs['ehr_uk_biobank']))
        
        for source_name, df in sources:
            mask = pd.Series([True] * len(df))
            
            if drug_id:
                mask &= df['Drug Chembl ID'].str.contains(drug_id, case=False, na=False)
            if drug_name:
                mask &= df['Drug Name'].str.contains(drug_name, case=False, na=False)
            if icd_code:
                mask &= df['ICD10'].str.contains(icd_code, case=False, na=False)
            if disease_name:
                mask &= df['Disease Description'].str.contains(disease_name, case=False, na=False)
            
            if mask.any():
                result_df = df.loc[mask].copy()
                result_df['ehr_source'] = source_name
                results.append(result_df)
        
        if results:
            return pd.concat(results, ignore_index=True).drop_duplicates()
        return pd.DataFrame()
    
    def assess_prevention_risk(self,
                              drug_id: Optional[str] = None,
                              drug_name: Optional[str] = None,
                              icd_code: Optional[str] = None,
                              disease_name: Optional[str] = None) -> Dict:
        """
        Assess prevention risk for drug-disease associations based on EHR data.
        
        Args:
            drug_id: ChEMBL drug ID
            drug_name: Drug name
            icd_code: ICD10 code
            disease_name: Disease description
        
        Returns:
            Dictionary with risk assessment results
        """
        # Get EHR associations
        ehr_data = self.get_ehr_drug_disease_associations(
            drug_id=drug_id,
            drug_name=drug_name,
            icd_code=icd_code,
            disease_name=disease_name
        )
        
        if ehr_data.empty:
            return {
                'found': False,
                'message': 'No EHR data found for this drug-disease combination'
            }
        
        assessment = {
            'found': True,
            'total_associations': len(ehr_data),
            'mount_sinai': {},
            'uk_biobank': {}
        }
        
        # Analyze Mount Sinai data
        ms_data = ehr_data[ehr_data.get('ehr_source') == 'ehr_mount_sinai'] if 'ehr_source' in ehr_data.columns else pd.DataFrame()
        if not ms_data.empty:
            if 'logit_or' in ms_data.columns:
                protective = ms_data[ms_data['logit_or'] < 1]
                risk_increasing = ms_data[ms_data['logit_or'] > 1]
                significant = ms_data[ms_data.get('logit_p', pd.Series([1] * len(ms_data))) < 0.05]
                
                assessment['mount_sinai'] = {
                    'total': len(ms_data),
                    'protective': len(protective),
                    'risk_increasing': len(risk_increasing),
                    'significant': len(significant),
                    'avg_or': ms_data['logit_or'].mean() if 'logit_or' in ms_data.columns else None,
                    'min_or': ms_data['logit_or'].min() if 'logit_or' in ms_data.columns else None,
                    'max_or': ms_data['logit_or'].max() if 'logit_or' in ms_data.columns else None
                }
        
        # Analyze UK Biobank data
        ukb_data = ehr_data[ehr_data.get('ehr_source') == 'ehr_uk_biobank'] if 'ehr_source' in ehr_data.columns else pd.DataFrame()
        if not ukb_data.empty:
            if 'odds_ratio' in ukb_data.columns:
                protective = ukb_data[ukb_data['odds_ratio'] < 1]
                risk_increasing = ukb_data[ukb_data['odds_ratio'] > 1]
                
                assessment['uk_biobank'] = {
                    'total': len(ukb_data),
                    'protective': len(protective),
                    'risk_increasing': len(risk_increasing),
                    'avg_or': ukb_data['odds_ratio'].mean() if 'odds_ratio' in ukb_data.columns else None,
                    'min_or': ukb_data['odds_ratio'].min() if 'odds_ratio' in ukb_data.columns else None,
                    'max_or': ukb_data['odds_ratio'].max() if 'odds_ratio' in ukb_data.columns else None
                }
        
        return assessment
    
    def get_drug_name_from_id(self, drug_id: str) -> Optional[str]:
        """Get drug name from ChEMBL ID using EHR data."""
        ehr_data = self.get_ehr_drug_disease_associations(drug_id=drug_id)
        if not ehr_data.empty and 'Drug Name' in ehr_data.columns:
            return ehr_data['Drug Name'].iloc[0]
        return None
    
    def get_disease_name_from_icd(self, icd_code: str) -> Optional[str]:
        """Get disease name from ICD10 code using EHR data."""
        ehr_data = self.get_ehr_drug_disease_associations(icd_code=icd_code)
        if not ehr_data.empty and 'Disease Description' in ehr_data.columns:
            return ehr_data['Disease Description'].iloc[0]
        return None
    
    # ========== Drug Response (CRISPR Correlation) Queries ==========
    
    def get_drug_response_associations(self,
                                      drug_name: Optional[str] = None,
                                      drug_id: Optional[str] = None,
                                      gene: Optional[str] = None,
                                      significant_only: bool = False,
                                      source: Optional[str] = None) -> pd.DataFrame:
        """
        Get drug-target associations from drug response (CRISPR correlation) data.
        
        Args:
            drug_name: Drug name (e.g., 'Erlotinib')
            drug_id: ChEMBL ID (e.g., 'CHEMBL553')
            gene: Gene symbol (e.g., 'EGFR')
            significant_only: If True, only return significant associations (FDR < 0.05)
            source: 'PRISM', 'GDSC', or None for both
        
        Returns:
            DataFrame with drug response associations
        """
        if 'drug_response' not in self.dfs:
            return pd.DataFrame()
        
        df = self.dfs['drug_response'].copy()
        mask = pd.Series([True] * len(df))
        
        if drug_name:
            mask &= df['drugs'].str.contains(drug_name, case=False, na=False)
        if drug_id:
            mask &= df['ChEMBL_ID'].str.contains(drug_id, case=False, na=False)
        if gene:
            mask &= df['genes'].str.contains(gene, case=False, na=False)
        if source:
            mask &= df['source'].str.contains(source, case=False, na=False)
        if significant_only:
            # Significant if either AUC or IC50 is significant
            auc_sig = df.get('AUC_FDR_sig', pd.Series([False] * len(df)))
            ic50_sig = df.get('IC50_FDR_sig', pd.Series([False] * len(df)))
            mask &= (auc_sig | ic50_sig)
        
        return df.loc[mask]
    
    def get_drug_target_evidence(self,
                                drug_name: Optional[str] = None,
                                drug_id: Optional[str] = None,
                                gene: Optional[str] = None) -> Dict:
        """
        Get evidence for drug-target associations from drug response data.
        
        Args:
            drug_name: Drug name
            drug_id: ChEMBL ID
            gene: Gene symbol
        
        Returns:
            Dictionary with evidence summary
        """
        associations = self.get_drug_response_associations(
            drug_name=drug_name,
            drug_id=drug_id,
            gene=gene,
            significant_only=True
        )
        
        if associations.empty:
            return {
                'found': False,
                'message': 'No significant drug-target associations found'
            }
        
        evidence = {
            'found': True,
            'total_associations': len(associations),
            'significant_associations': len(associations),
            'by_source': {},
            'correlation_summary': {}
        }
        
        # Group by source
        if 'source' in associations.columns:
            for source in associations['source'].unique():
                source_data = associations[associations['source'] == source]
                evidence['by_source'][source] = {
                    'count': len(source_data),
                    'avg_auc_corr': source_data['AUC_corr'].mean() if 'AUC_corr' in source_data.columns else None,
                    'avg_ic50_corr': source_data['IC50_corr'].mean() if 'IC50_corr' in source_data.columns else None
                }
        
        # Correlation summary
        if 'AUC_corr' in associations.columns:
            evidence['correlation_summary']['auc'] = {
                'mean': associations['AUC_corr'].mean(),
                'median': associations['AUC_corr'].median(),
                'min': associations['AUC_corr'].min(),
                'max': associations['AUC_corr'].max(),
                'positive': len(associations[associations['AUC_corr'] > 0]),
                'negative': len(associations[associations['AUC_corr'] < 0])
            }
        
        if 'IC50_corr' in associations.columns:
            evidence['correlation_summary']['ic50'] = {
                'mean': associations['IC50_corr'].mean(),
                'median': associations['IC50_corr'].median(),
                'min': associations['IC50_corr'].min(),
                'max': associations['IC50_corr'].max(),
                'positive': len(associations[associations['IC50_corr'] > 0]),
                'negative': len(associations[associations['IC50_corr'] < 0])
            }
        
        return evidence
    
    # ========== Drug-Target Metrics Queries ==========
    
    def get_drug_selectivity_info(self, drug_id: Optional[str] = None, 
                                 drug_name: Optional[str] = None) -> Optional[Dict]:
        """
        Get selectivity information for a drug.
        
        Args:
            drug_id: ChEMBL drug ID (e.g., 'CHEMBL1000')
            drug_name: Drug name (e.g., 'Cetirizine')
        
        Returns:
            Dictionary with selectivity metrics, or None if not found
        """
        if 'drug_selectivity' not in self.dfs:
            return None
        
        df = self.dfs['drug_selectivity'].copy()
        
        # Search by drug ID or name
        if drug_id:
            mask = df['Drug'].str.contains(drug_id, case=False, na=False)
            if not mask.any() and 'Drug Chembl ID' in df.columns:
                mask = df['Drug Chembl ID'].str.contains(drug_id, case=False, na=False)
        elif drug_name:
            mask = df['Drug Name'].str.contains(drug_name, case=False, na=False)
        else:
            return None
        
        if not mask.any():
            return None
        
        result = df[mask].iloc[0].to_dict()
        
        # Merge with UMAP clustering if available
        if 'drug_umap' in self.dfs:
            umap_df = self.dfs['drug_umap']
            if 'Drug' in umap_df.columns:
                umap_match = umap_df[umap_df['Drug'] == result.get('Drug', '')]
                if not umap_match.empty:
                    result.update({
                        'drug_type': umap_match.iloc[0].get('Type'),
                        'cluster': umap_match.iloc[0].get('cluster'),
                        'umap_x': umap_match.iloc[0].get('x'),
                        'umap_y': umap_match.iloc[0].get('y')
                    })
        
        return result
    
    def get_target_binding_stats(self, gene: Optional[str] = None,
                                 target: Optional[str] = None) -> Optional[Dict]:
        """
        Get binding statistics for a target.
        
        Args:
            gene: Gene symbol (e.g., 'BRAF', 'EGFR')
            target: Target protein name (e.g., 'BRAF_HUMAN')
        
        Returns:
            Dictionary with binding statistics, or None if not found
        """
        if 'target_binding_stats' not in self.dfs:
            return None
        
        df = self.dfs['target_binding_stats'].copy()
        
        # Search by gene or target
        if gene:
            mask = df['Gene'].str.contains(gene, case=False, na=False)
        elif target:
            mask = df['Target'].str.contains(target, case=False, na=False)
        else:
            return None
        
        if not mask.any():
            return None
        
        result = df[mask].iloc[0].to_dict()
        return result
    
    def _resolve_target_name(self, gene: str) -> Optional[str]:
        """Resolve gene symbol to target name used in parquet files."""
        if 'target_binding_stats' in self.dfs:
            target_df = self.dfs['target_binding_stats']
            gene_match = target_df[target_df['Gene'].str.contains(gene, case=False, na=False)]
            if not gene_match.empty:
                return gene_match.iloc[0].get('Target')
        return None

    def _parquet_files_for_drug(self, drug_id: str) -> list:
        """Get parquet files containing a drug, using index if available."""
        if self._parquet_drug_index and drug_id in self._parquet_drug_index:
            return [self.parquet_dir / fn for fn in self._parquet_drug_index[drug_id]]
        return list(self.parquet_dir.glob("*.parquet"))

    def _parquet_files_for_target(self, target_name: str) -> list:
        """Get parquet files containing a target, using index if available."""
        if self._parquet_target_index and target_name in self._parquet_target_index:
            return [self.parquet_dir / fn for fn in self._parquet_target_index[target_name]]
        return list(self.parquet_dir.glob("*.parquet"))

    def _read_parquet_filtered(self, parquet_file, columns, filters):
        """Read parquet with pyarrow predicate pushdown, fallback to pandas."""
        if PYARROW_AVAILABLE:
            table = pq.read_table(parquet_file, columns=columns, filters=filters)
            return table.to_pandas()
        else:
            df = pd.read_parquet(parquet_file, columns=columns)
            for col, op, val in filters:
                if op == "==":
                    df = df[df[col] == val]
            return df

    def get_drug_target_binding_affinity(self, drug_id: str, gene: str) -> Optional[Dict]:
        """
        Get specific binding affinity for a drug-target pair from parquet files.
        Uses pyarrow predicate pushdown for fast reads.
        """
        if not hasattr(self, 'parquet_dir') or not self.parquet_dir.exists():
            return None

        target_name = self._resolve_target_name(gene)
        if not target_name:
            return None

        cols = ["Drug", "Target", "aff_local", "Selectivity_Score", "Rank_Select"]
        filters = [("Drug", "==", drug_id), ("Target", "==", target_name)]

        for pf in self._parquet_files_for_drug(drug_id):
            try:
                df = self._read_parquet_filtered(pf, cols, filters)
                if not df.empty:
                    row = df.iloc[0]
                    return {
                        'drug_id': row.get('Drug'),
                        'target': row.get('Target'),
                        'binding_affinity': row.get('aff_local'),
                        'selectivity_score': row.get('Selectivity_Score'),
                        'rank_select': row.get('Rank_Select'),
                    }
            except Exception:
                continue
        return None

    def get_drugs_for_target_with_affinity(self, gene: str, limit: int = 20) -> pd.DataFrame:
        """
        Get top drugs binding to a target, sorted by affinity. Single-pass read.
        Uses target index + pyarrow filtering for speed.
        """
        if not hasattr(self, 'parquet_dir') or not self.parquet_dir.exists():
            return pd.DataFrame()

        target_name = self._resolve_target_name(gene)
        if not target_name:
            return pd.DataFrame()

        cols = ["Drug", "Target", "aff_local", "Selectivity_Score"]
        filters = [("Target", "==", target_name)]
        results = []

        for pf in self._parquet_files_for_target(target_name):
            try:
                df = self._read_parquet_filtered(pf, cols, filters)
                if not df.empty:
                    results.append(df)
            except Exception:
                continue

        if not results:
            return pd.DataFrame()
        combined = pd.concat(results, ignore_index=True)
        return combined.sort_values("aff_local", ascending=False).head(limit)
    
    def get_targets_for_drug_with_affinity(self, drug_id: str,
                                          min_affinity: Optional[float] = None,
                                          limit: int = 100) -> pd.DataFrame:
        """
        Get all targets with binding affinities for a drug, sorted by binding strength.
        Uses pyarrow predicate pushdown for fast reads.
        """
        if not hasattr(self, 'parquet_dir') or not self.parquet_dir.exists():
            return pd.DataFrame()

        cols = ["Drug", "Target", "aff_local", "Selectivity_Score", "Rank_Select"]
        filters = [("Drug", "==", drug_id)]
        results = []

        for pf in self._parquet_files_for_drug(drug_id):
            try:
                df = self._read_parquet_filtered(pf, cols, filters)
                if not df.empty:
                    if min_affinity is not None and 'aff_local' in df.columns:
                        df = df[df['aff_local'] >= min_affinity]
                    if not df.empty:
                        results.append(df)
            except Exception:
                continue

        if results:
            combined = pd.concat(results, ignore_index=True)
            if 'aff_local' in combined.columns:
                combined = combined.sort_values('aff_local', ascending=False)
            return combined.head(limit)
        return pd.DataFrame()
    
    def get_drugs_by_selectivity_type(self, selectivity_type: str) -> pd.DataFrame:
        """
        Get drugs filtered by selectivity type.
        
        Args:
            selectivity_type: 'Highly Selective', 'Moderate poly-target', or 'Broad-spectrum'
        
        Returns:
            DataFrame with matching drugs
        """
        if 'drug_umap' not in self.dfs:
            return pd.DataFrame()
        
        df = self.dfs['drug_umap'].copy()
        mask = df['Type'].str.contains(selectivity_type, case=False, na=False)
        
        if mask.any():
            return df[mask]
        return pd.DataFrame()
    
    def get_comprehensive_drug_target_evidence(self, drug_id: str, gene: str) -> Dict:
        """
        Get comprehensive evidence for a drug-target association from multiple sources.
        
        Args:
            drug_id: ChEMBL drug ID
            gene: Gene symbol
        
        Returns:
            Dictionary with comprehensive evidence summary
        """
        evidence = {
            'drug_id': drug_id,
            'gene': gene,
            'sources': {},
            'overall_strength': 'unknown'
        }
        
        # 1. Binding affinity (direct binding evidence)
        binding = self.get_drug_target_binding_affinity(drug_id, gene)
        if binding:
            evidence['sources']['binding_affinity'] = {
                'found': True,
                'aff_local': binding.get('binding_affinity'),
                'selectivity_score': binding.get('selectivity_score'),
                'rank': binding.get('rank_select'),
                'strength': 'strong' if binding.get('binding_affinity', 0) > 7 else 'moderate'
            }
        else:
            evidence['sources']['binding_affinity'] = {'found': False}
        
        # 2. Drug response correlations (functional evidence)
        drug_response = self.get_drug_response_associations(drug_id=drug_id, gene=gene, significant_only=True)
        if not drug_response.empty:
            evidence['sources']['drug_response'] = {
                'found': True,
                'count': len(drug_response),
                'avg_auc_corr': drug_response['AUC_corr'].mean() if 'AUC_corr' in drug_response.columns else None,
                'avg_ic50_corr': drug_response['IC50_corr'].mean() if 'IC50_corr' in drug_response.columns else None
            }
        else:
            evidence['sources']['drug_response'] = {'found': False}
        
        # 3. Target binding statistics
        target_stats = self.get_target_binding_stats(gene=gene)
        if target_stats:
            evidence['sources']['target_stats'] = {
                'found': True,
                'avg_pkd': target_stats.get('Avg_pKd'),
                'max_pkd': target_stats.get('Max_pKd'),
                'n_hit': target_stats.get('N_hit'),
                'tpi': target_stats.get('TPI')
            }
        else:
            evidence['sources']['target_stats'] = {'found': False}
        
        # 4. Drug selectivity info
        drug_sel = self.get_drug_selectivity_info(drug_id=drug_id)
        if drug_sel:
            evidence['sources']['drug_selectivity'] = {
                'found': True,
                'selectivity_score': drug_sel.get('Selectivity_Score'),
                'drug_type': drug_sel.get('drug_type'),
                'n_targets_measured': drug_sel.get('n_targets_measured')
            }
        else:
            evidence['sources']['drug_selectivity'] = {'found': False}
        
        # Calculate overall evidence strength
        found_sources = sum(1 for s in evidence['sources'].values() if s.get('found', False))
        if found_sources >= 3:
            evidence['overall_strength'] = 'strong'
        elif found_sources >= 2:
            evidence['overall_strength'] = 'moderate'
        elif found_sources >= 1:
            evidence['overall_strength'] = 'weak'
        else:
            evidence['overall_strength'] = 'none'
        
        return evidence


# Convenience function to create a database instance
def load_database(database_dir: str = "Database", load_full_data: bool = True) -> DrugDiseaseTargetDB:
    """
    Load and return a database instance.
    
    Args:
        database_dir: Path to the directory containing CSV files
        load_full_data: If True, load full data even for large files (>200MB).
                       If False, sample large files to 100,000 rows for performance.
    
    Returns:
        DrugDiseaseTargetDB instance
    """
    return DrugDiseaseTargetDB(database_dir, load_full_data=load_full_data)
