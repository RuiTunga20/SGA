import io
from django.core.files.base import ContentFile
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import Paragraph, Frame, KeepInFrame
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from django.utils import timezone

def gerar_pdf_despacho(documento, texto_despacho, usuario_responsavel, novo_status):
    """
    Gera um PDF contendo o despacho do documento.
    Retorna um ContentFile pronto para ser salvo em um FileField.
    """
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    # --- Cabeçalho ---
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(width / 2, height - 2*cm, "REPÚBLICA DE ANGOLA")
    
    # Nome da Instituição (Dinâmico se possível, aqui estático ou do documento)
    nome_instituicao = documento.administracao.nome if documento.administracao else "ADMINISTRAÇÃO MUNICIPAL"
    c.setFont("Helvetica-Bold", 12)
    c.drawCentredString(width / 2, height - 2.7*cm, nome_instituicao.upper())
    
    c.line(2*cm, height - 3.2*cm, width - 2*cm, height - 3.2*cm)

    # --- Título do Documento ---
    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2, height - 5*cm, "NOTA DE DESPACHO")

    # --- Detalhes do Documento ---
    c.setFont("Helvetica", 10)
    start_y = height - 7*cm
    
    c.drawString(2.5*cm, start_y, f"Nº Protocolo: {documento.numero_protocolo}")
    c.drawString(2.5*cm, start_y - 0.7*cm, f"Assunto: {documento.titulo}")
    c.drawString(2.5*cm, start_y - 1.4*cm, f"Utente: {documento.utente}")
    c.drawString(2.5*cm, start_y - 2.1*cm, f"Data do Pedido: {documento.data_criacao.strftime('%d/%m/%Y')}")

    # --- Estado e Decisão ---
    c.setFont("Helvetica-Bold", 10)
    c.drawString(2.5*cm, start_y - 3.5*cm, f"Estado/Decisão: {novo_status.upper() if novo_status else 'DESPACHADO'}")

    # --- Conteúdo do Despacho (Texto Longo) ---
    c.setFont("Helvetica-Bold", 11)
    c.drawString(2.5*cm, start_y - 5*cm, "TEOR DO DESPACHO:")
    
    # Usar Platypus para quebra de linha automática do texto do despacho
    style_sheet = getSampleStyleSheet()
    style = style_sheet["BodyText"]
    style.fontName = "Helvetica"
    style.fontSize = 10
    style.leading = 14
    
    p = Paragraph(texto_despacho.replace("\n", "<br/>"), style)
    
    # Frame para o texto
    frame_x = 2.5*cm
    frame_y = 5*cm # Margem inferior
    frame_w = width - 5*cm
    frame_h = (start_y - 5.5*cm) - frame_y
    
    frame = Frame(frame_x, frame_y, frame_w, frame_h, showBoundary=0)
    story = [p]
    story_in_frame = KeepInFrame(frame_w, frame_h, story)
    frame.addFromList([story_in_frame], c)

    # --- Rodapé / Assinatura ---
    rodape_y = 3*cm
    c.line(width/2 - 4*cm, rodape_y, width/2 + 4*cm, rodape_y)
    
    c.setFont("Helvetica", 9)
    c.drawCentredString(width / 2, rodape_y - 0.5*cm, f"O(A) Responsável: {usuario_responsavel.get_full_name() or usuario_responsavel.username}")
    
    c.setFont("Helvetica-Oblique", 8)
    c.drawCentredString(width / 2, rodape_y - 1*cm, f"Gerado em: {timezone.now().strftime('%d/%m/%Y %H:%M')}")
    
    c.showPage()
    c.save()

    buffer.seek(0)
    return ContentFile(buffer.getvalue(), name=f"despacho_{documento.numero_protocolo.replace('/', '-')}.pdf")
