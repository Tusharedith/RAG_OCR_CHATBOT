"""
Table extraction from PDFs - IMPROVED VERSION
Handles structured data with better semantic representation
"""
import camelot
import pandas as pd
from typing import List
import sys
import os
import warnings
warnings.filterwarnings('ignore')

# Add parent directory to path for models import
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import DocumentElement, ModalityType


class TableExtractor:
    """
    Extract and process tables from PDFs with enhanced semantic representation
    """
    
    def __init__(self):
        print("Table extractor initialized")
    
    def extract(self, pdf_path: str) -> List[DocumentElement]:
        """
        Extract table elements from PDF with BOTH lattice and stream methods
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of DocumentElement objects with modality=TABLE
        """
        elements = []
        
        try:
            print("Extracting table elements...")
            
            # Try BOTH methods to catch different table types
            lattice_tables = self._extract_with_lattice(pdf_path)
            stream_tables = self._extract_with_stream(pdf_path)
            
            # Combine and deduplicate by page
            all_tables = lattice_tables + stream_tables
            all_tables = self._deduplicate_tables(all_tables)
            
            elements.extend(all_tables)
            
            print(f"  Found {len(elements)} valid tables")
            return elements
            
        except Exception as e:
            print(f"Table extraction error: {e}")
            return []
    
    def _extract_with_lattice(self, pdf_path: str) -> List[DocumentElement]:
        """Extract bordered/gridded tables using lattice method"""
        elements = []
        
        try:
            tables = camelot.read_pdf(
                pdf_path,
                pages='all',
                flavor='lattice',
                suppress_stdout=True,
                line_scale=40  # Helps detect lighter borders
            )
            
            print(f"  Lattice method: {len(tables)} tables detected")
            
            for idx, table in enumerate(tables, 1):
                element = self._process_table(table, idx, "lattice")
                if element:
                    elements.append(element)
        
        except Exception as e:
            print(f"  Lattice extraction failed: {e}")
        
        return elements
    
    def _extract_with_stream(self, pdf_path: str) -> List[DocumentElement]:
        """Extract tables without clear borders using stream method"""
        elements = []
        
        try:
            tables = camelot.read_pdf(
                pdf_path,
                pages='all',
                flavor='stream',
                suppress_stdout=True,
                edge_tol=50  # Tolerance for edge detection
            )
            
            print(f"  Stream method: {len(tables)} tables detected")
            
            for idx, table in enumerate(tables, 1):
                element = self._process_table(table, idx, "stream")
                if element:
                    elements.append(element)
        
        except Exception as e:
            print(f"  Stream extraction failed: {e}")
        
        return elements
    
    def _process_table(self, table, idx: int, method: str) -> DocumentElement:
        """
        Process a single table with ENHANCED semantic representation
        Combines multiple formats for better retrieval
        """
        try:
            df = table.df
            page_num = table.page
            
            # Skip empty tables
            if df.empty or df.shape[0] == 0:
                return None
            
            # Clean the dataframe
            df = self._clean_dataframe(df)
            
            if df.empty:
                return None
            
            # Generate MULTIPLE representations for better semantic matching
            table_text = self._create_comprehensive_representation(df, page_num, idx)
            
            if not table_text.strip():
                return None
            
            # Extract label
            label = self._extract_table_label(df, idx)
            
            return DocumentElement(
                type=ModalityType.TABLE,
                content=table_text,
                page=page_num,
                section=label,
                metadata={
                    "extraction_method": method,
                    "accuracy": table.accuracy if hasattr(table, 'accuracy') else None,
                    "rows": df.shape[0],
                    "cols": df.shape[1]
                }
            )
        
        except Exception as e:
            print(f"  Table processing error: {e}")
            return None
    
    def _create_comprehensive_representation(self, df: pd.DataFrame, page_num: int, table_num: int) -> str:
        """
        Create COMPREHENSIVE semantic representation of table
        Includes: title, structure description, row-wise data, and summary
        """
        parts = []
        
        # 1. Table identifier and metadata
        parts.append(f"[TABLE {table_num} on Page {page_num}]")
        
        # 2. Structural description
        parts.append(f"Structure: {df.shape[0]} rows × {df.shape[1]} columns")
        
        # 3. Extract and format headers
        headers = self._extract_headers(df)
        if headers:
            parts.append(f"Columns: {', '.join(headers)}")
        
        # 4. Row-wise data representation
        row_data = self._format_rows_with_context(df, headers)
        if row_data:
            parts.append("\nData:")
            parts.append(row_data)
        
        # 5. Add searchable keywords
        keywords = self._extract_keywords(df)
        if keywords:
            parts.append(f"\nKey terms: {', '.join(keywords)}")
        
        return "\n".join(parts)
    
    def _clean_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Clean and normalize DataFrame"""
        # Remove completely empty rows and columns
        df = df.dropna(how='all').dropna(axis=1, how='all')
        
        # Remove rows where all values are empty strings
        df = df[~df.apply(lambda row: all(str(cell).strip() == '' for cell in row), axis=1)]
        
        # Strip whitespace from all cells
        df = df.applymap(lambda x: str(x).strip() if pd.notna(x) else '')
        
        return df
    
    def _extract_headers(self, df: pd.DataFrame) -> List[str]:
        """
        Intelligently extract column headers
        """
        if df.empty:
            return []
        
        # Check if first row contains headers (non-numeric, descriptive text)
        first_row = df.iloc[0]
        
        # Check if first row looks like headers
        is_header = sum(
            1 for cell in first_row 
            if str(cell).strip() and not self._is_numeric(str(cell))
        ) >= len(first_row) * 0.5  # At least 50% are non-numeric
        
        if is_header:
            headers = [str(cell).strip() for cell in first_row]
            # Remove empty headers
            headers = [h if h else f"Col{i+1}" for i, h in enumerate(headers)]
            return headers
        else:
            # Generate generic headers
            return [f"Column_{i+1}" for i in range(len(df.columns))]
    
    def _format_rows_with_context(self, df: pd.DataFrame, headers: List[str]) -> str:
        """
        Format rows with FULL CONTEXT for better semantic matching
        """
        if df.empty:
            return ""
        
        # Check if first row was used as header
        first_row_is_header = any(
            str(cell).strip() and not self._is_numeric(str(cell))
            for cell in df.iloc[0]
        )
        
        data_rows = df.iloc[1:] if first_row_is_header else df
        
        formatted_rows = []
        
        for row_idx, row in data_rows.iterrows():
            row_parts = []
            
            # First column is typically the row label/category
            row_label = str(row.iloc[0]).strip()
            
            if not row_label or row_label == 'nan':
                row_label = f"Row {row_idx + 1}"
            
            # Format: "Category: Header1=Value1, Header2=Value2"
            values = []
            for header, cell in zip(headers[1:], row.iloc[1:]):
                cell_str = str(cell).strip()
                if cell_str and cell_str != 'nan' and cell_str != '':
                    values.append(f"{header}={cell_str}")
            
            if values:
                formatted_rows.append(f"{row_label}: {', '.join(values)}")
        
        return "\n".join(formatted_rows)
    
    def _extract_keywords(self, df: pd.DataFrame) -> List[str]:
        """
        Extract important keywords for searchability
        """
        keywords = set()
        
        # Extract from first column (usually categories/labels)
        for cell in df.iloc[:, 0]:
            cell_str = str(cell).strip().lower()
            if cell_str and cell_str != 'nan' and len(cell_str) > 2:
                # Add significant words
                words = cell_str.split()
                keywords.update(w for w in words if len(w) > 3)
        
        # Limit to top keywords
        return list(keywords)[:10]
    
    def _is_numeric(self, text: str) -> bool:
        """Check if text is numeric (including percentages, decimals)"""
        text = text.strip().replace('%', '').replace(',', '').replace('$', '')
        try:
            float(text)
            return True
        except:
            return False
    
    def _extract_table_label(self, df: pd.DataFrame, table_num: int) -> str:
        """
        Extract table label/title from DataFrame
        """
        if df.empty:
            return f"Table {table_num}"
        
        # Check first cell for table title
        first_cell = str(df.iloc[0, 0]).strip()
        
        # If first cell looks like a title
        if (('table' in first_cell.lower() or 'figure' in first_cell.lower()) 
            and len(first_cell) > 10):
            return first_cell
        
        # Check if first row spans multiple columns (title row)
        first_row = df.iloc[0]
        non_empty = [str(cell).strip() for cell in first_row if str(cell).strip()]
        if len(non_empty) == 1 and len(non_empty[0]) > 15:
            return non_empty[0]
        
        return f"Table {table_num}"
    
    def _deduplicate_tables(self, tables: List[DocumentElement]) -> List[DocumentElement]:
        """
        Remove duplicate tables detected by both methods
        Keep the one with better quality/more content
        """
        # Group by page
        page_tables = {}
        for table in tables:
            page = table.page
            if page not in page_tables:
                page_tables[page] = []
            page_tables[page].append(table)
        
        # Keep best table per page
        deduplicated = []
        for page, page_table_list in page_tables.items():
            if len(page_table_list) == 1:
                deduplicated.append(page_table_list[0])
            else:
                # Keep table with most content
                best_table = max(page_table_list, key=lambda t: len(t.content))
                deduplicated.append(best_table)
        
        return deduplicated