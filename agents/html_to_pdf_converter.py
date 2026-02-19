"""
Convert HTML output to PDF.

Supports multiple backends:
1. Weasyprint (best rendering, requires native libraries)
2. Fallback: Use HTML + suggestion to open in browser or use online converter
"""
from pathlib import Path
from typing import Optional


def convert_html_to_pdf(html_path: str, output_pdf_path: str) -> bool:
    """
    Convert HTML file to PDF.
    
    Tries weasyprint first (best quality), falls back to suggesting HTML-in-browser PDF printing.
    
    Args:
        html_path: Path to HTML file
        output_pdf_path: Path where PDF will be saved
        
    Returns:
        True if successful, False otherwise
    """
    html_file = Path(html_path)
    if not html_file.exists():
        print(f"❌ HTML file not found: {html_path}")
        return False
    
    # Try WeasyPrint (lazy import to avoid loading native libraries if not needed)
    try:
        # Lazy import - only import if actually called
        from weasyprint import HTML
        
        print(f"\n{'='*80}")
        print(f"Converting HTML to PDF: {html_file.name}")
        print(f"{'='*80}\n")
        
        # Use file:// URL for proper image resolution
        HTML(string=html_file.read_text(encoding='utf-8'), base_url=html_file.parent).write_pdf(output_pdf_path)
        
        print(f"✅ PDF generated successfully: {output_pdf_path}\n")
        return True
        
    except ImportError:
        print(f"\n⚠️  Weasyprint not installed - using HTML file instead")
        _suggest_pdf_alternatives(html_path)
        return False
        
    except OSError as e:
        # Missing native libraries (libgobject on Windows)
        print(f"\n⚠️  Weasyprint native libraries not available: {e}")
        _suggest_pdf_alternatives(html_path)
        return False
        
    except Exception as e:
        print(f"\n❌ Error converting HTML to PDF: {e}\n")
        return False


def _suggest_pdf_alternatives(html_path: str) -> None:
    """
    Suggest alternatives for converting HTML to PDF when weasyprint fails.
    """
    html_file = Path(html_path)
    print(f"""
    
📋 PDF Generation Alternatives:
    
1. 🌐 BROWSER METHOD (Easiest):
   - Open: {html_file.absolute()}
   - In your browser, press Ctrl+P (or Cmd+P on Mac)
   - Click "Print to PDF" or "Save as PDF"
   - Choose your location and save
   
2. 📱 ONLINE CONVERTERS:
   - https://cloudconvert.com/ (HTML to PDF)
   - https://pdfcrowd.com/ (HTML to PDF)
   - https://www.zamzar.com/ (HTML to PDF)
   
3. 💻 WINDOWS: Install wkhtmltopdf
   - Download: https://wkhtmltopdf.org/download.html
   - This will automatically enable PDF generation
   
4. 🐧 LINUX/MAC: Install weasyprint dependencies
   - Ubuntu: sudo apt-get install libgobject2.0-0
   - macOS: brew install gtk+3
    """)

