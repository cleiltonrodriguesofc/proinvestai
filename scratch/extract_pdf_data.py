import pdfplumber
import json
import os

files = [
    r"C:\Users\cleil\Documents\PROJETOS\proinvestai\RELATÓRIO_INVESTIMENTOS_IPSEMB_Abril_2026__1778766753023.pdf",
    r"C:\Users\cleil\Documents\PROJETOS\proinvestai\RELATÓRIO_RISCO_IPSEMB_1778766853546 - ABRIL-2026.pdf"
]

results = {}

for file_path in files:
    if not os.path.exists(file_path):
        results[file_path] = "File not found"
        continue
        
    text_content = ""
    tables_content = []
    
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text_content += page.extract_text() + "\n"
            tables = page.extract_tables()
            for table in tables:
                tables_content.append(table)
                
    results[file_path] = {
        "text_preview": text_content[:2000], # First 2k chars
        "table_count": len(tables_content),
        "tables_preview": tables_content[:3] # First 3 tables
    }

print(json.dumps(results, indent=2))
