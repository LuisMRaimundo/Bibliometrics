# -*- coding: utf-8 -*-
"""
excel_analyzer.py

Intelligent Excel file and sheet selection based on data quality metrics.
Uses multiple criteria to make judicious choices about which Excel file
and which sheet to use for bibliographic data processing.
"""

import os
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class SheetQuality:
    """Quality metrics for an Excel sheet."""
    sheet_name: str
    row_count: int
    column_count: int
    has_title: bool = False
    has_doi: bool = False
    has_year: bool = False
    has_author: bool = False
    has_area: bool = False
    has_metrics: bool = False
    completeness_score: float = 0.0
    data_quality_score: float = 0.0
    recommended: bool = False


@dataclass
class ExcelFileQuality:
    """Quality metrics for an Excel file."""
    file_path: str
    file_name: str
    sheet_count: int
    sheets: List[SheetQuality] = field(default_factory=list)
    best_sheet: Optional[str] = None
    overall_score: float = 0.0
    recommended: bool = False


class ExcelAnalyzer:
    """
    Analyzes Excel files and makes intelligent choices about which file
    and sheet to use based on data quality metrics.
    """
    
    # Column detection patterns (same as select_texts_gui_v6.py)
    AREA_CANDIDATES = ["domain_label", "domain_id", "community_label", "area", "field", "ASJC", "WC"]
    TITLE_CANDIDATES = ["title", "document title", "ti", "titulo"]
    DOI_CANDIDATES = ["doi", "doi number", "pr_doi"]
    YEAR_CANDIDATES = ["year", "py", "publication year", "date", "ano"]
    AUTHOR_CANDIDATES = ["authors", "author_names", "authors_list", "creator", "autores"]
    METRIC_CANDIDATES = ["cf", "mncs", "c_f", "c_use", "usage", "pagerank", "pr", "betweenness", "btw"]
    
    def __init__(self, folder_path: str):
        """
        Initialize analyzer with folder path.
        
        Args:
            folder_path: Path to folder containing Excel files
        """
        self.folder_path = Path(folder_path)
        self.excel_files: List[ExcelFileQuality] = []
    
    def find_excel_files(self) -> List[str]:
        """
        Find all Excel files in the folder.
        
        Returns:
            List of Excel file paths
        """
        excel_extensions = ['.xlsx', '.xls', '.xlsm']
        files = []
        
        for ext in excel_extensions:
            files.extend(self.folder_path.glob(f'*{ext}'))
        
        return [str(f) for f in files if f.is_file()]
    
    def pick_col(self, df: pd.DataFrame, candidates: List[str]) -> Optional[str]:
        """
        Find column matching candidates (case-insensitive).
        
        Args:
            df: DataFrame to search
            candidates: List of candidate column names
        
        Returns:
            Matching column name or None
        """
        cols_lower = {str(c).lower(): c for c in df.columns}
        
        # Exact match (case-insensitive)
        for cand in candidates:
            if cand.lower() in cols_lower:
                return cols_lower[cand.lower()]
        
        # Substring match
        for c in df.columns:
            for cand in candidates:
                if cand.lower() in str(c).lower():
                    return c
        
        return None
    
    def analyze_sheet(self, df: pd.DataFrame, sheet_name: str) -> SheetQuality:
        """
        Analyze a single sheet and calculate quality metrics.
        
        Args:
            df: DataFrame from the sheet
            sheet_name: Name of the sheet
        
        Returns:
            SheetQuality object with metrics
        """
        quality = SheetQuality(
            sheet_name=sheet_name,
            row_count=len(df),
            column_count=len(df.columns)
        )
        
        # Check for required columns
        quality.has_title = self.pick_col(df, self.TITLE_CANDIDATES) is not None
        quality.has_doi = self.pick_col(df, self.DOI_CANDIDATES) is not None
        quality.has_year = self.pick_col(df, self.YEAR_CANDIDATES) is not None
        quality.has_author = self.pick_col(df, self.AUTHOR_CANDIDATES) is not None
        quality.has_area = self.pick_col(df, self.AREA_CANDIDATES) is not None
        
        # Check for metrics
        metric_cols = [self.pick_col(df, [cand]) for cand in self.METRIC_CANDIDATES]
        quality.has_metrics = any(metric_cols)
        
        # Calculate completeness score (0-1)
        required_fields = [quality.has_title, quality.has_doi, quality.has_year, 
                          quality.has_author, quality.has_area]
        quality.completeness_score = sum(required_fields) / len(required_fields)
        
        # Calculate data quality score
        # Factors: completeness, row count, non-null data percentage
        if quality.row_count == 0:
            quality.data_quality_score = 0.0
        else:
            # Check data completeness (non-null percentage)
            title_col = self.pick_col(df, self.TITLE_CANDIDATES)
            doi_col = self.pick_col(df, self.DOI_CANDIDATES)
            
            data_completeness = 0.0
            if title_col:
                data_completeness += (df[title_col].notna().sum() / quality.row_count) * 0.4
            if doi_col:
                data_completeness += (df[doi_col].notna().sum() / quality.row_count) * 0.3
            if quality.has_year:
                year_col = self.pick_col(df, self.YEAR_CANDIDATES)
                if year_col:
                    data_completeness += (df[year_col].notna().sum() / quality.row_count) * 0.3
            
            # Combine completeness and data quality
            quality.data_quality_score = (
                quality.completeness_score * 0.6 +
                data_completeness * 0.4
            )
            
            # Bonus for having metrics
            if quality.has_metrics:
                quality.data_quality_score += 0.1
                quality.data_quality_score = min(1.0, quality.data_quality_score)
        
        return quality
    
    def analyze_file(self, file_path: str) -> ExcelFileQuality:
        """
        Analyze an Excel file and all its sheets.
        
        Args:
            file_path: Path to Excel file
        
        Returns:
            ExcelFileQuality object with analysis
        """
        file_quality = ExcelFileQuality(
            file_path=file_path,
            file_name=os.path.basename(file_path),
            sheet_count=0
        )
        
        try:
            xls = pd.ExcelFile(file_path)
            file_quality.sheet_count = len(xls.sheet_names)
            
            # Analyze each sheet
            for sheet_name in xls.sheet_names:
                try:
                    df = pd.read_excel(xls, sheet_name, nrows=1000)  # Sample first 1000 rows
                    quality = self.analyze_sheet(df, sheet_name)
                    file_quality.sheets.append(quality)
                except Exception as e:
                    # Skip sheets that can't be read
                    continue
            
            # Find best sheet (highest data quality score)
            if file_quality.sheets:
                best = max(file_quality.sheets, key=lambda s: s.data_quality_score)
                file_quality.best_sheet = best.sheet_name
                best.recommended = True
                
                # Overall file score = best sheet score
                file_quality.overall_score = best.data_quality_score
                
                # Recommend if score > 0.5 and has minimum requirements
                file_quality.recommended = (
                    file_quality.overall_score > 0.5 and
                    best.row_count > 10 and
                    best.has_title and
                    best.has_area
                )
        
        except Exception as e:
            # File can't be read
            file_quality.overall_score = 0.0
        
        return file_quality
    
    def analyze_folder(self) -> List[ExcelFileQuality]:
        """
        Analyze all Excel files in the folder.
        
        Returns:
            List of ExcelFileQuality objects, sorted by score
        """
        excel_files = self.find_excel_files()
        
        if not excel_files:
            return []
        
        # Analyze each file
        for file_path in excel_files:
            file_quality = self.analyze_file(file_path)
            self.excel_files.append(file_quality)
        
        # Sort by overall score (descending)
        self.excel_files.sort(key=lambda f: f.overall_score, reverse=True)
        
        return self.excel_files
    
    def get_best_file(self) -> Optional[ExcelFileQuality]:
        """
        Get the best Excel file based on quality metrics.
        
        Returns:
            ExcelFileQuality object or None if no files found
        """
        if not self.excel_files:
            self.analyze_folder()
        
        # Return first recommended file, or highest score if none recommended
        for file_quality in self.excel_files:
            if file_quality.recommended:
                return file_quality
        
        # If no recommended files, return highest score
        return self.excel_files[0] if self.excel_files else None
    
    def get_recommendation(self) -> Dict:
        """
        Get detailed recommendation with reasoning.
        
        Returns:
            Dictionary with recommendation details
        """
        if not self.excel_files:
            self.analyze_folder()
        
        if not self.excel_files:
            return {
                "status": "error",
                "message": "No Excel files found in folder",
                "recommended_file": None
            }
        
        best_file = self.get_best_file()
        
        if not best_file or not best_file.recommended:
            return {
                "status": "warning",
                "message": "No files meet minimum quality requirements",
                "files_analyzed": len(self.excel_files),
                "best_file": best_file.file_name if best_file else None,
                "best_score": best_file.overall_score if best_file else 0.0
            }
        
        best_sheet_quality = next(
            (s for s in best_file.sheets if s.recommended),
            best_file.sheets[0] if best_file.sheets else None
        )
        
        return {
            "status": "success",
            "recommended_file": best_file.file_path,
            "file_name": best_file.file_name,
            "recommended_sheet": best_file.best_sheet,
            "overall_score": best_file.overall_score,
            "sheet_quality": {
                "row_count": best_sheet_quality.row_count,
                "column_count": best_sheet_quality.column_count,
                "has_title": best_sheet_quality.has_title,
                "has_doi": best_sheet_quality.has_doi,
                "has_year": best_sheet_quality.has_year,
                "has_author": best_sheet_quality.has_author,
                "has_area": best_sheet_quality.has_area,
                "has_metrics": best_sheet_quality.has_metrics,
                "completeness_score": best_sheet_quality.completeness_score,
                "data_quality_score": best_sheet_quality.data_quality_score
            },
            "files_analyzed": len(self.excel_files),
            "reasoning": self._generate_reasoning(best_file, best_sheet_quality)
        }
    
    def _generate_reasoning(self, file_quality: ExcelFileQuality, sheet_quality: SheetQuality) -> str:
        """Generate human-readable reasoning for the recommendation."""
        reasons = []
        
        reasons.append(f"File '{file_quality.file_name}' has the highest quality score ({file_quality.overall_score:.2%})")
        reasons.append(f"Sheet '{sheet_quality.sheet_name}' contains {sheet_quality.row_count:,} records")
        
        if sheet_quality.has_title:
            reasons.append("[OK] Contains title information")
        if sheet_quality.has_doi:
            reasons.append("[OK] Contains DOI information")
        if sheet_quality.has_year:
            reasons.append("[OK] Contains publication year")
        if sheet_quality.has_author:
            reasons.append("[OK] Contains author information")
        if sheet_quality.has_area:
            reasons.append("[OK] Contains area/domain classification")
        if sheet_quality.has_metrics:
            reasons.append("[OK] Contains bibliometric metrics")
        
        if sheet_quality.completeness_score >= 0.8:
            reasons.append("[OK] High completeness (all required fields present)")
        
        return "\n".join(reasons)


def analyze_excel_folder(folder_path: str) -> Dict:
    """
    Convenience function to analyze Excel files in a folder.
    
    Args:
        folder_path: Path to folder containing Excel files
    
    Returns:
        Recommendation dictionary
    """
    analyzer = ExcelAnalyzer(folder_path)
    return analyzer.get_recommendation()


if __name__ == "__main__":
    # Test the analyzer
    folder = r"C:\Users\lmr20\Desktop\SoundSpectrAnalyse-Cursor_3\Bibliographics"
    recommendation = analyze_excel_folder(folder)
    
    print("=" * 60)
    print("EXCEL FILE ANALYSIS & RECOMMENDATION")
    print("=" * 60)
    print(f"\nStatus: {recommendation['status']}")
    
    if recommendation['status'] == 'success':
        print(f"\nRecommended File: {recommendation['file_name']}")
        print(f"Recommended Sheet: {recommendation['recommended_sheet']}")
        print(f"Overall Quality Score: {recommendation['overall_score']:.2%}")
        print(f"\nSheet Quality Metrics:")
        sq = recommendation['sheet_quality']
        print(f"  - Rows: {sq['row_count']:,}")
        print(f"  - Columns: {sq['column_count']}")
        print(f"  - Has Title: {sq['has_title']}")
        print(f"  - Has DOI: {sq['has_doi']}")
        print(f"  - Has Year: {sq['has_year']}")
        print(f"  - Has Author: {sq['has_author']}")
        print(f"  - Has Area: {sq['has_area']}")
        print(f"  - Has Metrics: {sq['has_metrics']}")
        print(f"  - Completeness: {sq['completeness_score']:.2%}")
        print(f"  - Data Quality: {sq['data_quality_score']:.2%}")
        print(f"\nReasoning:")
        print(recommendation['reasoning'])
    else:
        print(f"\nMessage: {recommendation['message']}")

