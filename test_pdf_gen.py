import sys
import os

try:
    from weasyprint import HTML
    print("✅ WeasyPrint is installed.")
except ImportError:
    print("❌ WeasyPrint is NOT installed.")
    sys.exit(1)
except OSError as e:
    print(f"❌ WeasyPrint installed but missing dependencies (GTK3?): {e}")
    sys.exit(1)

html_content = """
<!DOCTYPE html>
<html>
<head>
<style>
    body { font-family: sans-serif; }
    h1 { color: blue; }
</style>
</head>
<body>
    <h1>Test PDF Generation</h1>
    <p>If you can read this, WeasyPrint is working.</p>
</body>
</html>
"""

output_file = "test_output.pdf"
try:
    HTML(string=html_content).write_pdf(output_file)
    print(f"✅ PDF successfully created at {os.path.abspath(output_file)}")
except Exception as e:
    print(f"❌ PDF generation failed: {e}")
