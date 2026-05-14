from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class PDFReportService:
    """
    Service to generate PDF reports for the user's portfolio and gap analysis.
    """
    def generate_report(self, user_name: str, analysis_data: dict) -> bytes:
        buffer = BytesIO()
        
        # Simple reportlab canvas implementation
        # In a real app, you might use weasyprint with HTML templates for better styling
        p = canvas.Canvas(buffer, pagesize=letter)
        p.setFont("Helvetica-Bold", 16)
        p.drawString(50, 750, f"Relatório de Análise de Portfólio - {user_name}")
        
        p.setFont("Helvetica", 12)
        y = 700
        p.drawString(50, y, "Resumo da Carteira:")
        y -= 20
        
        # Mock data iteration
        if "potential_gain_lost" in analysis_data:
            p.drawString(50, y, f"Custo de Oportunidade: R$ {analysis_data['potential_gain_lost']:.2f} / ano")
            y -= 20
            
        if "narration" in analysis_data:
            p.drawString(50, y, "Parecer IA:")
            y -= 20
            # Split narration into multiple lines if needed (simplified here)
            text = p.beginText(50, y)
            text.setFont("Helvetica-Oblique", 10)
            # A real implementation would handle text wrapping
            text.textLine(analysis_data["narration"][:100] + "...")
            p.drawText(text)
            
        p.showPage()
        p.save()
        
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes
