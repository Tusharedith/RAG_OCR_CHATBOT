"""
Table extraction from PDFs
Handles structured data in table format
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
    Extract and process tables from PDFs
    Uses Camelot-py for table detection
    """
    
    def __init__(self):
        print("Table extractor initialized")
    
    def extract(self, pdf_path: str) -> List[DocumentElement]:
        """
        Extract table elements from PDF
        
        Args:
            pdf_path: Path to PDF file
            
        Returns:
            List of DocumentElement objects with modality=TABLE
        """
        elements = []
        
        try:
            print("Extracting table elements...")
            
            # Use Camelot with lattice flavor for bordered tables
            tables = camelot.read_pdf(
                pdf_path,
                pages='all',
                flavor='lattice',
                suppress_stdout=True
            )
            
            print(f"  Camelot detected {len(tables)} tables")
            
            for idx, table in enumerate(tables, 1):
                # Get page number
                page_num = table.page
                
                # Convert to human-readable row-wise format
                df = table.df
                table_text = self._dataframe_to_row_format(df)
                
                if table_text.strip():
                    # Extract table title/label from first row or use default
                    label = self._extract_table_label(df, idx)
                    
                    elements.append(DocumentElement(
                        type=ModalityType.TABLE,
                        content=table_text,
                        page=page_num,
                        section=label
                    ))
            
            print(f"  Found {len(elements)} valid tables")
            return elements
            
        except Exception as e:
            print(f"Table extraction error: {e}")
            return []
    
    def _dataframe_to_row_format(self, df: pd.DataFrame) -> str:
        """
        Convert DataFrame to row-wise human-readable format
        Preserves headers, units, and row labels
        
        Example output:
        "Real GDP growth (%): 2023: 1.2 | 2024: 2.0 | 2025: 2.7"
        """
        if df.empty:
            return ""
        
        try:
            # Clean up
            df = df.dropna(how='all').dropna(axis=1, how='all')
            if df.empty:
                return ""
            
            lines = []
            
            # Check if first row contains column headers (years, categories, etc.)
            first_row = df.iloc[0].astype(str).tolist()
            has_header_row = any(
                str(cell).strip() and not str(cell).replace('.', '').replace('-', '').isdigit()
                for cell in first_row if str(cell).strip()
            )
            
            if has_header_row:
                # Use first row as column headers
                headers = [str(cell).strip() for cell in df.iloc[0]]
                data_rows = df.iloc[1:]
            else:
                # Generate generic headers
                headers = [f"Col{i+1}" for i in range(len(df.columns))]
                data_rows = df
            
            # Process each data row
            for _, row in data_rows.iterrows():
                row_values = [str(cell).strip() for cell in row]
                
                # Skip empty rows
                if not any(val for val in row_values if val and val != 'nan'):
                    continue
                
                # First column is typically the row label
                row_label = row_values[0] if row_values[0] and row_values[0] != 'nan' else "Value"
                
                # Build row-wise format: "Label: Header1: Value1 | Header2: Value2"
                value_parts = []
                for header, value in zip(headers[1:], row_values[1:]):
                    if value and value != 'nan':
                        value_parts.append(f"{header}: {value}")
                
                if value_parts:
                    row_text = f"{row_label}: {' | '.join(value_parts)}"
                    lines.append(row_text)
            
            return '\n'.join(lines)
            
        except Exception as e:
            print(f"  Table conversion error: {e}")
            # Fallback to simple string representation
            return df.to_string()
    
    def _extract_table_label(self, df: pd.DataFrame, table_num: int) -> str:
        """
        Extract table label/title from DataFrame or generate default
        """
        if df.empty:
            return f"Table {table_num}"
        
        # Check first cell for table title
        first_cell = str(df.iloc[0, 0]).strip()
        
        # If first cell looks like a title (contains "Table" or is long text)
        if 'table' in first_cell.lower() and len(first_cell) > 10:
            return first_cell
        
        return f"Table {table_num}"
    
    def _dataframe_to_markdown(self, df: pd.DataFrame) -> str:
        """
        DEPRECATED: Use _dataframe_to_row_format instead
        Convert pandas DataFrame to markdown table format
        
        Args:
            df: Pandas DataFrame
            
        Returns:
            Markdown formatted table string
        """
        if df.empty:
            return ""
        
        try:
            # Clean up empty rows and columns
            df = df.dropna(how='all').dropna(axis=1, how='all')
            
            if df.empty:
                return ""
            
            # Use first row as header if appropriate
            if df.shape[0] > 1:
                headers = df.iloc[0].astype(str).tolist()
                data = df.iloc[1:]
            else:
                headers = [f"Col{i}" for i in range(len(df.columns))]
                data = df
            
            # Build markdown table
            markdown = "| " + " | ".join(headers) + " |\n"
            markdown += "| " + " | ".join(["---"] * len(headers)) + " |\n"
            
            for _, row in data.iterrows():
                markdown += "| " + " | ".join(str(cell) for cell in row) + " |\n"
            
            return markdown
            
        except Exception as e:
            print(f"  Table conversion error: {e}")
            return ""
