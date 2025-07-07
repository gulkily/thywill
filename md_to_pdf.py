#!/usr/bin/env python3
"""
Convert Markdown files to PDF using markdown library and weasyprint.

Usage:
    python md_to_pdf.py input.md [output.pdf]
    
If output.pdf is not specified, it will use the input filename with .pdf extension.
"""

import sys
import os
from pathlib import Path
import argparse
import markdown
from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration

def convert_md_to_pdf(input_file, output_file=None):
    """Convert a Markdown file to PDF."""
    
    # Determine output filename
    if output_file is None:
        output_file = Path(input_file).with_suffix('.pdf')
    
    # Read the markdown file
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
    except FileNotFoundError:
        print(f"Error: File '{input_file}' not found.")
        return False
    except Exception as e:
        print(f"Error reading file: {e}")
        return False
    
    # Convert markdown to HTML
    md = markdown.Markdown(extensions=[
        'markdown.extensions.tables',
        'markdown.extensions.fenced_code',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
        'markdown.extensions.extra'
    ])
    
    html_content = md.convert(md_content)
    
    # Create a complete HTML document with CSS styling
    full_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Document</title>
        <style>
            @page {{
                size: letter;
                margin: 1in;
            }}
            body {{
                font-family: Times, serif;
                line-height: 1.5;
                color: #000;
                max-width: 100%;
                font-size: 12pt;
            }}
            h1 {{
                color: #000;
                margin-top: 24pt;
                margin-bottom: 12pt;
                font-size: 18pt;
            }}
            h2 {{
                color: #000;
                margin-top: 18pt;
                margin-bottom: 9pt;
                font-size: 14pt;
            }}
            h3 {{
                color: #000;
                margin-top: 12pt;
                margin-bottom: 6pt;
                font-size: 12pt;
                font-weight: bold;
            }}
            p {{
                margin-bottom: 12pt;
                text-align: left;
            }}
            ul, ol {{
                margin-bottom: 12pt;
                padding-left: 20pt;
            }}
            li {{
                margin-bottom: 3pt;
            }}
            strong {{
                color: #000;
            }}
            code {{
                font-family: 'Courier New', monospace;
                font-size: 10pt;
            }}
            pre {{
                font-family: 'Courier New', monospace;
                font-size: 10pt;
                margin: 12pt 0;
                padding: 6pt;
                border: 1px solid #000;
            }}
            blockquote {{
                margin-left: 20pt;
                font-style: italic;
            }}
            table {{
                border-collapse: collapse;
                width: 100%;
                margin-bottom: 12pt;
            }}
            th, td {{
                border: 1px solid #000;
                padding: 4pt 6pt;
                text-align: left;
            }}
            th {{
                font-weight: bold;
            }}
            hr {{
                border: none;
                height: 1pt;
                background-color: #000;
                margin: 18pt 0;
            }}
        </style>
    </head>
    <body>
        {html_content}
    </body>
    </html>
    """
    
    # Convert HTML to PDF
    try:
        # Create font configuration
        font_config = FontConfiguration()
        
        # Create HTML object and convert to PDF
        html_doc = HTML(string=full_html)
        html_doc.write_pdf(output_file, font_config=font_config)
        
        print(f"Successfully converted '{input_file}' to '{output_file}'")
        return True
        
    except Exception as e:
        print(f"Error converting to PDF: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Convert Markdown files to PDF",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python md_to_pdf.py document.md
    python md_to_pdf.py document.md output.pdf
    python md_to_pdf.py thywill_app_overview.md
        """
    )
    
    parser.add_argument('input', help='Input Markdown file')
    parser.add_argument('output', nargs='?', help='Output PDF file (optional)')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.isfile(args.input):
        print(f"Error: Input file '{args.input}' does not exist.")
        return 1
    
    # Convert the file
    success = convert_md_to_pdf(args.input, args.output)
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())