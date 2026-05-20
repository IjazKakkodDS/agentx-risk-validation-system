import markdown2
import pdfkit
import os

# Paths
md_file = "reports/validation_report.md"
html_file = "reports/validation_report.html"
pdf_file = "reports/validation_report.pdf"

# Convert Markdown → HTML
with open(md_file, "r", encoding="utf-8") as f:
    html_content = markdown2.markdown(f.read())

with open(html_file, "w", encoding="utf-8") as f:
    f.write(html_content)

# If wkhtmltopdf is not in PATH, set config manually
config = pdfkit.configuration(wkhtmltopdf=r"C:\Program Files\wkhtmltopdf\bin\wkhtmltopdf.exe")

# Convert HTML → PDF
pdfkit.from_file(html_file, pdf_file, configuration=config)

print("✅ PDF report saved to reports/validation_report.pdf")
