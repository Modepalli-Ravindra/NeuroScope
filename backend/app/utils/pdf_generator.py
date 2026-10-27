import io
import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from typing import Dict, Any

def generate_pdf_report(analysis_data: Dict[str, Any]) -> io.BytesIO:
    """Generate a clean, professional research PDF report for NeuroScope."""
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=letter,
        rightMargin=40, leftMargin=40,
        topMargin=40, bottomMargin=40
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    header_style = ParagraphStyle(
        'DocHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#004741')  # Cyprus green
    )
    
    subhead_style = ParagraphStyle(
        'SubHeader',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#4A5568')
    )
    
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=16,
        textColor=colors.HexColor('#004741'),
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'ReportBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#1A202C')
    )

    story = []

    # Title Banner
    story.append(Paragraph("NeuroScope — Explainable Movement AI", header_style))
    story.append(Paragraph("Differential Screening Research Report: MSA vs. Parkinson's Disease", subhead_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor('#004741'), spaceAfter=14))


    # Recording & Analysis Metadata Table
    pred = analysis_data.get("prediction", {})
    meta = analysis_data.get("input_metadata", {})
    
    report_date = datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    meta_table_data = [
        [Paragraph("<b>Report Date:</b>", body_style), Paragraph(report_date, body_style),
         Paragraph("<b>Sampling Rate:</b>", body_style), Paragraph(f"{meta.get('sampling_rate_hz', 200)} Hz", body_style)],
        [Paragraph("<b>Recording File:</b>", body_style), Paragraph(str(meta.get("filename", "N/A")), body_style),
         Paragraph("<b>Duration:</b>", body_style), Paragraph(f"{meta.get('duration_sec', 0.0):.2f} seconds", body_style)],
        [Paragraph("<b>Participant ID:</b>", body_style), Paragraph(str(meta.get("person_id", "ANONYMOUS")), body_style),
         Paragraph("<b>Trial:</b>", body_style), Paragraph(str(meta.get("trial_id", "trial1")), body_style)],
        [Paragraph("<b>Ground Truth Label:</b>", body_style), Paragraph(str(meta.get("original_label", "Hidden/N/A")), body_style),
         Paragraph("<b>Model Version:</b>", body_style), Paragraph("NeuroScope-RF v1.0.0", body_style)]
    ]
    meta_table = Table(meta_table_data, colWidths=[110, 155, 110, 155])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F7FAFC')),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 5),
    ]))
    story.append(Paragraph("1. Recording & Evaluation Context", section_title))
    story.append(meta_table)
    story.append(Spacer(1, 14))

    # Classification & Uncertainty Status
    pred_class = pred.get("predicted_class", "UNKNOWN")
    conf = pred.get("confidence_score", 0.0)
    p_msa = pred.get("probabilities", {}).get("MSA", 0.0)
    p_pd = pred.get("probabilities", {}).get("PD", 0.0)
    knn_pred = pred.get("knn_baseline_class", "UNKNOWN")
    is_uncertain = pred.get("is_uncertain", False)

    pred_bg = '#E6FFFA' if pred_class == 'MSA' else '#EBF8FF'
    pred_box_data = [
        [
            Paragraph(f"<b>Primary Prediction:</b> <font size=13 color='#004741'><b>{pred_class}</b></font>", body_style),
            Paragraph(f"<b>Model Score:</b> <b>{conf * 100:.1f}%</b>", body_style),
            Paragraph(f"<b>KNN Baseline:</b> <b>{knn_pred}</b>", body_style)
        ],
        [
            Paragraph(f"MSA Probability: <b>{p_msa * 100:.1f}%</b> | PD Probability: <b>{p_pd * 100:.1f}%</b>", body_style),
            Paragraph(f"Uncertainty Flag: <b>{'EVIDENCE UNCERTAIN' if is_uncertain else 'STABLE'}</b>", body_style),
            Paragraph(f"Cohort Subtype: <b>MSA-P Predominant</b>", body_style)
        ]
    ]
    pred_table = Table(pred_box_data, colWidths=[200, 160, 170])
    pred_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor(pred_bg)),
        ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#004741')),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(Paragraph("2. Screening Inference & Confidence", section_title))
    story.append(pred_table)

    if is_uncertain:
        story.append(Spacer(1, 6))
        reasons = "<br/>• ".join(pred.get("uncertainty_reasons", ["Score near decision threshold"]))
        unc_alert = Table([[Paragraph(f"<b>Uncertainty Details:</b><br/>• {reasons}", disclaimer_style)]], colWidths=[530])
        unc_alert.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FFFAF0')),
            ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor('#FBD38D')),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        story.append(unc_alert)

    story.append(Spacer(1, 14))

    # SHAP Evidence Table
    story.append(Paragraph("3. Explainable AI: Key SHAP Feature Contributions", section_title))
    shap_data = [["Rank", "Kinematic Feature", "Measured Value", "SHAP Impact", "Attribution"]]
    top_feats = analysis_data.get("shap_explanation", {}).get("top_features", [])[:8]
    
    for i, item in enumerate(top_feats):
        shap_data.append([
            str(i + 1),
            item.get("feature", "N/A"),
            f"{item.get('feature_value', 0.0):.3f}",
            f"{item.get('shap_value', 0.0):+.4f}",
            item.get("direction", "N/A")
        ])

    shap_table = Table(shap_data, colWidths=[35, 175, 90, 80, 150])
    shap_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#004741')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F7FAFC')]),
        ('PADDING', (0, 0), (-1, -1), 4),
    ]))
    story.append(shap_table)
    story.append(Spacer(1, 14))

    # Core Tapping Kinematics Summary
    story.append(Paragraph("4. Key Finger-Tapping Kinematics", section_title))
    feats = analysis_data.get("extracted_features", {})
    kinematics_data = [
        [
            Paragraph("<b>Tap Rate (Hz):</b>", body_style), Paragraph(f"{feats.get('tap_rate_hz', 0.0):.2f}", body_style),
            Paragraph("<b>Total Tap Count:</b>", body_style), Paragraph(f"{feats.get('tap_count', 0.0):.0f}", body_style)
        ],
        [
            Paragraph("<b>Rhythm Irregularity (CV):</b>", body_style), Paragraph(f"{feats.get('tap_interval_cv', 0.0):.3f}", body_style),
            Paragraph("<b>Amplitude Decay:</b>", body_style), Paragraph(f"{feats.get('tap_amplitude_decay', 0.0):.4f}", body_style)
        ],
        [
            Paragraph("<b>Relative Velocity RMS:</b>", body_style), Paragraph(f"{feats.get('relative_mag_rms', 0.0):.3f}", body_style),
            Paragraph("<b>Thumb Movement RMS:</b>", body_style), Paragraph(f"{feats.get('thumb_mag_rms', 0.0):.3f}", body_style)
        ]
    ]
    kin_table = Table(kinematics_data, colWidths=[150, 115, 150, 115])
    kin_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#E2E8F0')),
        ('PADDING', (0, 0), (-1, -1), 5),
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#FAFAFA'))
    ]))
    story.append(kin_table)
    story.append(Spacer(1, 16))

    # Model & Scientific Validation Footer
    footer_text = (
        "<b>Model Methodology & Validation:</b> 5-Fold Stratified Group Cross-Validation on 140 recordings "
        "across 27 independent participants (leakage-free subject isolation). Random Forest Balanced Accuracy: ~72.8%, "
        "ROC-AUC: ~0.767. Dataset Source: Innovation Center ETF, University of Belgrade (Heliyon 2023)."
    )
    story.append(Paragraph(footer_text, ParagraphStyle('FooterNote', parent=styles['Normal'], fontSize=7.5, leading=10, textColor=colors.HexColor('#718096'))))

    doc.build(story)
    buffer.seek(0)
    return buffer
