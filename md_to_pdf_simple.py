#!/usr/bin/env python3
"""
Simple Markdown to PDF converter using pandoc.
This is a lightweight alternative that doesn't require complex dependencies.

Usage:
    python md_to_pdf_simple.py input.md [output.pdf]
"""

import sys
import os
import subprocess
from pathlib import Path
import argparse

def convert_md_to_pdf_pandoc(input_file, output_file=None):
    """Convert a Markdown file to PDF using pandoc."""
    
    # Determine output filename
    if output_file is None:
        output_file = Path(input_file).with_suffix('.pdf')
    
    # Check if pandoc is available
    try:
        result = subprocess.run(['pandoc', '--version'], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            raise FileNotFoundError("pandoc not found")
    except FileNotFoundError:
        print("Error: pandoc is not installed or not in PATH")
        print("Install with: sudo apt-get install pandoc")
        return False
    
    # Check if input file exists
    if not os.path.isfile(input_file):
        print(f"Error: Input file '{input_file}' not found.")
        return False
    
    # Convert using pandoc
    try:
        cmd = [
            'pandoc',
            input_file,
            '-o', str(output_file),
            '--pdf-engine=pdflatex',
            '--variable', 'geometry:margin=1in',
            '--variable', 'fontsize=12pt',
            '--variable', 'documentclass=article',
            '--variable', 'mainfont=Times New Roman',
            '--variable', 'linestretch=1.2'
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✓ Successfully converted '{input_file}' to '{output_file}'")
            return True
        else:
            # Try without pdflatex if it fails
            print("pdflatex not available, trying wkhtmltopdf...")
            cmd_alt = [
                'pandoc',
                input_file,
                '-o', str(output_file),
                '--pdf-engine=wkhtmltopdf',
                '--variable', 'geometry:margin=1in'
            ]
            
            result = subprocess.run(cmd_alt, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ Successfully converted '{input_file}' to '{output_file}'")
                return True
            else:
                print(f"Error: pandoc failed to convert file")
                print(f"Command: {' '.join(cmd)}")
                print(f"Error output: {result.stderr}")
                return False
                
    except Exception as e:
        print(f"Error running pandoc: {e}")
        return False

def convert_md_to_pdf_basic(input_file, output_file=None):
    """
    Basic HTML to PDF conversion using built-in tools.
    This is a fallback when pandoc is not available.
    """
    
    # Determine output filename
    if output_file is None:
        output_file = Path(input_file).with_suffix('.pdf')
    
    try:
        import markdown
        
        # Read markdown file
        with open(input_file, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        # Convert to HTML
        md = markdown.Markdown(extensions=['extra', 'codehilite'])
        html_content = md.convert(md_content)
        
        # Create basic HTML document
        html_doc = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <style>
                body {{
                    font-family: Times, serif;
                    font-size: 12pt;
                    line-height: 1.5;
                    max-width: 8.5in;
                    margin: 1in auto;
                    padding: 0;
                }}
                h1 {{ font-size: 18pt; margin-top: 24pt; }}
                h2 {{ font-size: 14pt; margin-top: 18pt; }}
                h3 {{ font-size: 12pt; margin-top: 12pt; font-weight: bold; }}
                p {{ margin-bottom: 12pt; }}
                ul, ol {{ margin-bottom: 12pt; }}
            </style>
        </head>
        <body>
            {html_content}
        </body>
        </html>
        """
        
        # Save HTML file
        html_file = Path(output_file).with_suffix('.html')
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_doc)
        
        # Try to convert HTML to PDF using wkhtmltopdf
        try:
            cmd = ['wkhtmltopdf', str(html_file), str(output_file)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                os.remove(html_file)  # Clean up
                print(f"✓ Successfully converted '{input_file}' to '{output_file}'")
                return True
            else:
                print(f"Warning: Could not convert to PDF. HTML file saved as '{html_file}'")
                print("You can open this HTML file in a browser and print to PDF manually.")
                return False
                
        except FileNotFoundError:
            print(f"Warning: wkhtmltopdf not found. HTML file saved as '{html_file}'")
            print("You can open this HTML file in a browser and print to PDF manually.")
            return False
            
    except ImportError:
        print("Error: markdown library not installed")
        print("Install with: pip install markdown")
        return False
    except Exception as e:
        print(f"Error: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(
        description="Convert Markdown files to PDF using pandoc or basic HTML conversion",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python md_to_pdf_simple.py document.md
    python md_to_pdf_simple.py document.md output.pdf
    python md_to_pdf_simple.py thywill_app_overview.md
        """
    )
    
    parser.add_argument('input', help='Input Markdown file')
    parser.add_argument('output', nargs='?', help='Output PDF file (optional)')
    
    args = parser.parse_args()
    
    # Check if input file exists
    if not os.path.isfile(args.input):
        print(f"Error: Input file '{args.input}' does not exist.")
        return 1
    
    # Try pandoc first, then fallback to basic conversion
    success = convert_md_to_pdf_pandoc(args.input, args.output)
    
    if not success:
        print("Pandoc conversion failed, trying basic HTML conversion...")
        success = convert_md_to_pdf_basic(args.input, args.output)
    
    return 0 if success else 1

if __name__ == '__main__':
    sys.exit(main())