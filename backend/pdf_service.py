"""
PDF Service - Generate table plans and reports
"""
import io
from datetime import datetime
from typing import List, Dict, Optional
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.enums import TA_CENTER, TA_LEFT


def generate_table_plan_pdf(
    reservations: List[dict],
    area_map: Dict[str, str],
    date_str: str,
    restaurant_name: str = "Restaurant",
    filter_area_id: Optional[str] = None
) -> io.BytesIO:
    """
    Generate an A4 PDF table plan.
    
    Args:
        reservations: List of reservation documents
        area_map: Dict mapping area_id to area_name
        date_str: Date string (YYYY-MM-DD)
        restaurant_name: Name of the restaurant
        filter_area_id: Optional area filter
    
    Returns:
        BytesIO buffer containing the PDF
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.5*cm,
        leftMargin=1.5*cm,
        topMargin=1.5*cm,
        bottomMargin=1.5*cm
    )
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        spaceAfter=20,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#00280b')
    )
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=14,
        spaceAfter=15,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#4a5d4e')
    )
    area_title_style = ParagraphStyle(
        'AreaTitle',
        parent=styles['Heading3'],
        fontSize=12,
        spaceBefore=15,
        spaceAfter=8,
        textColor=colors.HexColor('#00280b')
    )
    
    # Build content
    elements = []
    
    # Title
    try:
        formatted_date = datetime.strptime(date_str, "%Y-%m-%d").strftime("%d.%m.%Y")
    except:
        formatted_date = date_str
    
    elements.append(Paragraph(restaurant_name, title_style))
    elements.append(Paragraph(f"Tischplan für {formatted_date}", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Group reservations by area
    reservations_by_area = {}
    for res in reservations:
        area_id = res.get("area_id", "unassigned")
        if filter_area_id and area_id != filter_area_id:
            continue
        
        if area_id not in reservations_by_area:
            reservations_by_area[area_id] = []
        reservations_by_area[area_id].append(res)
    
    if not reservations_by_area:
        elements.append(Paragraph("Keine Reservierungen für diesen Tag.", styles['Normal']))
    else:
        # Stats
        total_guests = sum(r.get("party_size", 0) for r in reservations)
        total_reservations = len(reservations)
        stats_text = f"Gesamt: {total_reservations} Reservierungen, {total_guests} Gäste"
        elements.append(Paragraph(stats_text, subtitle_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Table for each area
        for area_id, area_reservations in sorted(reservations_by_area.items(), key=lambda x: area_map.get(x[0], 'ZZZ')):
            area_name = area_map.get(area_id, "Nicht zugewiesen")
            area_guests = sum(r.get("party_size", 0) for r in area_reservations)
            
            elements.append(Paragraph(f"{area_name} ({len(area_reservations)} Reservierungen, {area_guests} Gäste)", area_title_style))
            
            # Table data
            table_data = [['Zeit', 'Tisch', 'Gast', 'Pers.', 'Anlass', 'Status']]
            
            for res in sorted(area_reservations, key=lambda x: x.get("time", "")):
                table_data.append([
                    res.get("time", "-"),
                    res.get("table_number", "-"),
                    res.get("guest_name", "-")[:25],  # Truncate long names
                    str(res.get("party_size", "-")),
                    (res.get("occasion", "") or "-")[:15],
                    get_status_label(res.get("status", ""))
                ])
            
            # Create table
            col_widths = [2*cm, 2*cm, 5*cm, 1.5*cm, 3*cm, 2.5*cm]
            table = Table(table_data, colWidths=col_widths)
            
            # Table style
            table.setStyle(TableStyle([
                # Header
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#00280b')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                ('TOPPADDING', (0, 0), (-1, 0), 8),
                
                # Body
                ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fafbed')),
                ('TEXTCOLOR', (0, 1), (-1, -1), colors.HexColor('#00280b')),
                ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
                ('ALIGN', (3, 1), (3, -1), 'CENTER'),  # Party size centered
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                
                # Grid
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dce0c5')),
                
                # Alternating rows
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fafbed'), colors.HexColor('#f3f6de')]),
            ]))
            
            elements.append(table)
            elements.append(Spacer(1, 0.3*cm))
    
    # Footer
    elements.append(Spacer(1, 1*cm))
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.gray,
        alignment=TA_CENTER
    )
    generated_at = datetime.now().strftime("%d.%m.%Y %H:%M")
    elements.append(Paragraph(f"Erstellt am {generated_at} | {restaurant_name}", footer_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return buffer


def get_status_label(status: str) -> str:
    """Get German label for status"""
    labels = {
        "neu": "Neu",
        "bestaetigt": "Bestätigt",
        "angekommen": "Angekomm.",
        "abgeschlossen": "Fertig",
        "no_show": "No-Show",
        "storniert": "Storniert"
    }
    return labels.get(status, status)
