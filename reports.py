"""
reports.py  –  PDF and Excel report generation
"""
import io
from datetime import datetime

# ── PDF ─────────────────────────────────────────────────────────────
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                Table, TableStyle, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# ── Excel ────────────────────────────────────────────────────────────
import xlsxwriter


# ─────────────────────────────────────────────────────────────────────
# COLOUR PALETTE
# ─────────────────────────────────────────────────────────────────────
PRIMARY    = colors.HexColor('#1e3a5f')   # dark navy
SECONDARY  = colors.HexColor('#2563eb')   # blue
SUCCESS    = colors.HexColor('#16a34a')   # green
WARNING    = colors.HexColor('#d97706')   # amber
DANGER     = colors.HexColor('#dc2626')   # red
LIGHT_GREY = colors.HexColor('#f3f4f6')
MID_GREY   = colors.HexColor('#e5e7eb')

GRADE_COLOURS = {'A': SUCCESS, 'B': SECONDARY,
                 'C': WARNING,  'D': WARNING, 'F': DANGER}


# ─────────────────────────────────────────────────────────────────────
# INDIVIDUAL STUDENT PDF
# ─────────────────────────────────────────────────────────────────────
def generate_student_pdf(student: dict, scheme: dict | None = None) -> io.BytesIO:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm,  bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'Title', fontSize=18, textColor=colors.white,
        alignment=TA_CENTER, fontName='Helvetica-Bold', spaceAfter=4)
    sub_style = ParagraphStyle(
        'Sub', fontSize=10, textColor=colors.white,
        alignment=TA_CENTER, fontName='Helvetica')
    section_style = ParagraphStyle(
        'Section', fontSize=12, textColor=PRIMARY,
        fontName='Helvetica-Bold', spaceBefore=14, spaceAfter=6)
    normal = ParagraphStyle(
        'N', fontSize=10, fontName='Helvetica', leading=14)

    story = []

    # ── Header banner ────────────────────────────────────────────────
    header_data = [[
        Paragraph('AI-Based Student Performance Prediction System', title_style),
    ],[
        Paragraph('Individual Student Performance Report', sub_style),
    ],[
        Paragraph(f'Generated: {datetime.now().strftime("%d %B %Y, %H:%M")}', sub_style),
    ]]
    header_table = Table(header_data, colWidths=[17*cm])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), PRIMARY),
        ('ALIGN',      (0,0), (-1,-1), 'CENTER'),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('ROUNDEDCORNERS', [6]),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 14))

    # ── Student info ─────────────────────────────────────────────────
    grade_col = GRADE_COLOURS.get(student['grade_category'], SECONDARY)
    pf_col    = SUCCESS if student['pass_fail'] == 'Pass' else DANGER
    ar_col    = DANGER  if student['at_risk']   == 'Yes'  else SUCCESS

    info_data = [
        ['Student Name',  student['name'],     'Student ID', student['student_id']],
        ['Final Score',   f"{student['final_score']:.2f} / 100",
         'Grade',        student['grade_category']],
        ['Status',       student['pass_fail'], 'At-Risk',    student['at_risk']],
    ]
    info_table = Table(info_data, colWidths=[4*cm, 5*cm, 4*cm, 4*cm])
    info_table.setStyle(TableStyle([
        ('BACKGROUND',   (0,0), (0,-1), LIGHT_GREY),
        ('BACKGROUND',   (2,0), (2,-1), LIGHT_GREY),
        ('FONTNAME',     (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME',     (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE',     (0,0), (-1,-1), 10),
        ('GRID',         (0,0), (-1,-1), 0.5, MID_GREY),
        ('TOPPADDING',   (0,0), (-1,-1), 7),
        ('BOTTOMPADDING',(0,0), (-1,-1), 7),
        ('LEFTPADDING',  (0,0), (-1,-1), 10),
        ('TEXTCOLOR',    (1,1), (1,1), grade_col),
        ('TEXTCOLOR',    (1,2), (1,2), pf_col),
        ('TEXTCOLOR',    (3,2), (3,2), ar_col),
        ('FONTNAME',     (1,1), (1,1), 'Helvetica-Bold'),
        ('FONTNAME',     (1,2), (1,2), 'Helvetica-Bold'),
        ('FONTNAME',     (3,2), (3,2), 'Helvetica-Bold'),
    ]))
    story.append(info_table)
    story.append(Spacer(1, 14))

    # ── Score breakdown ──────────────────────────────────────────────
    story.append(Paragraph('Score Breakdown', section_style))
    story.append(HRFlowable(width='100%', thickness=1, color=MID_GREY))
    story.append(Spacer(1, 6))

    def bar(value, max_val=100, width=120):
        filled = int((value / max_val) * width)
        return '█' * (filled // 8) + '░' * ((width - filled) // 8)

    weights = scheme.get("weights", {}) if scheme else {}
    w_exam = float(weights.get("exam", 60))
    w_tests = float(weights.get("tests", 20))
    w_asgn = float(weights.get("assignments", 10))
    w_att = float(weights.get("attendance", 10))

    breakdown = [
        ['Component', 'Score', 'Weight', 'Contribution', 'Visual'],
        ['Exam Score',       f"{student['exam_score']:.1f}",
         f"{w_exam:.0f}%", f"{student['exam_score']*(w_exam/100):.2f}",
         bar(student['exam_score'])],
        ['Average Tests',    f"{student['avg_test']:.1f}",
         f"{w_tests:.0f}%", f"{student['avg_test']*(w_tests/100):.2f}",
         bar(student['avg_test'])],
        ['Avg Assignments',  f"{student['avg_assignment']:.1f}",
         f"{w_asgn:.0f}%", f"{student['avg_assignment']*(w_asgn/100):.2f}",
         bar(student['avg_assignment'])],
        ['Attendance',       f"{student['attendance']:.1f}%",
         f"{w_att:.0f}%", f"{student['attendance']*(w_att/100):.2f}",
         bar(student['attendance'])],
        ['', '', '', '', ''],
        ['FINAL SCORE', f"{student['final_score']:.2f}", '100%', '', ''],
    ]
    bd_table = Table(breakdown, colWidths=[3.8*cm, 2.2*cm, 1.8*cm, 3*cm, 6.2*cm])
    bd_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), PRIMARY),
        ('TEXTCOLOR',     (0,0), (-1,0), colors.white),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTNAME',      (0,-1),(-1,-1),'Helvetica-Bold'),
        ('BACKGROUND',    (0,-1),(-1,-1), LIGHT_GREY),
        ('ROWBACKGROUNDS',(0,1), (-1,-2), [colors.white, LIGHT_GREY]),
        ('GRID',          (0,0), (-1,-1), 0.4, MID_GREY),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('ALIGN',         (1,0), (3,-1), 'CENTER'),
    ]))
    story.append(bd_table)
    story.append(Spacer(1, 14))

    # ── Individual test & assignment scores ──────────────────────────
    story.append(Paragraph('Individual Assessment Scores', section_style))
    story.append(HRFlowable(width='100%', thickness=1, color=MID_GREY))
    story.append(Spacer(1, 6))

    if scheme:
        test_keys = [
            f"test{i+1}"
            for i in range(scheme.get("num_tests", 0))
            if f"test{i+1}" in student
        ]
        asgn_keys = [
            f"assignment{i+1}"
            for i in range(scheme.get("num_assignments", 0))
            if f"assignment{i+1}" in student
        ]
    else:
        test_keys = sorted(
            [k for k in student if k.startswith("test")],
            key=lambda k: int(k.replace("test", "")) if k[4:].isdigit() else 0,
        )
        asgn_keys = sorted(
            [k for k in student if k.startswith("assignment")],
            key=lambda k: int(k.replace("assignment", "")) if k[10:].isdigit() else 0,
        )

    scores_data = [['Assessment', 'Score', 'Assessment', 'Score']]
    for i in range(max(len(test_keys), len(asgn_keys))):
        t_key = test_keys[i] if i < len(test_keys) else None
        a_key = asgn_keys[i] if i < len(asgn_keys) else None
        t_label = f"Test {i + 1}" if t_key else ""
        a_label = f"Assignment {i + 1}" if a_key else ""
        t_val = f"{float(student.get(t_key, 0)):.1f}" if t_key else ""
        a_val = f"{float(student.get(a_key, 0)):.1f}" if a_key else ""
        scores_data.append([t_label, t_val, a_label, a_val])

    scores_data.append([
        'Avg Test', f"{student.get('avg_test', 0):.2f}",
        'Avg Assignment', f"{student.get('avg_assignment', 0):.2f}",
    ])
    sc_table = Table(scores_data, colWidths=[4.5*cm, 3.5*cm, 4.5*cm, 4.5*cm])
    sc_table.setStyle(TableStyle([
        ('BACKGROUND',    (0,0), (-1,0), SECONDARY),
        ('TEXTCOLOR',     (0,0), (-1,0), colors.white),
        ('FONTNAME',      (0,0), (-1,0), 'Helvetica-Bold'),
        ('ROWBACKGROUNDS',(0,1), (-1,-1), [colors.white, LIGHT_GREY]),
        ('GRID',          (0,0), (-1,-1), 0.4, MID_GREY),
        ('FONTSIZE',      (0,0), (-1,-1), 9),
        ('TOPPADDING',    (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING',   (0,0), (-1,-1), 8),
        ('ALIGN',         (1,0), (1,-1), 'CENTER'),
        ('ALIGN',         (3,0), (3,-1), 'CENTER'),
    ]))
    story.append(sc_table)
    story.append(Spacer(1, 14))

    # ── Risk factors ─────────────────────────────────────────────────
    if student['risk_factors']:
        story.append(Paragraph('Risk Factors Identified', section_style))
        story.append(HRFlowable(width='100%', thickness=1, color=DANGER))
        story.append(Spacer(1, 6))
        for rf in student['risk_factors']:
            story.append(Paragraph(f'⚠  {rf}', ParagraphStyle(
                'RF', fontSize=10, textColor=DANGER,
                fontName='Helvetica', leftIndent=12, spaceAfter=4)))
        story.append(Spacer(1, 6))

    # ── Footer ───────────────────────────────────────────────────────
    story.append(Spacer(1, 20))
    story.append(HRFlowable(width='100%', thickness=0.5, color=MID_GREY))
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        'This report was generated automatically by the AI-Based Student '
        'Performance Prediction System. Predictions are based on machine '
        'learning models trained on historical academic data.',
        ParagraphStyle('Footer', fontSize=8, textColor=colors.grey,
                       alignment=TA_CENTER)))

    doc.build(story)
    buf.seek(0)
    return buf


# ─────────────────────────────────────────────────────────────────────
# CLASS EXCEL EXPORT
# ─────────────────────────────────────────────────────────────────────
def generate_class_excel(students: list, stats: dict, scheme: dict | None = None) -> io.BytesIO:
    buf = io.BytesIO()
    wb  = xlsxwriter.Workbook(buf, {'in_memory': True})

    # ── Formats ──────────────────────────────────────────────────────
    hdr   = wb.add_format({'bold':True,'bg_color':'#1e3a5f','font_color':'white',
                           'border':1,'align':'center','valign':'vcenter'})
    subhdr= wb.add_format({'bold':True,'bg_color':'#2563eb','font_color':'white',
                           'border':1,'align':'center','valign':'vcenter'})
    even  = wb.add_format({'bg_color':'#f3f4f6','border':1,'valign':'vcenter'})
    odd   = wb.add_format({'bg_color':'#ffffff','border':1,'valign':'vcenter'})
    ctr_e = wb.add_format({'bg_color':'#f3f4f6','border':1,'align':'center','valign':'vcenter'})
    ctr_o = wb.add_format({'bg_color':'#ffffff','border':1,'align':'center','valign':'vcenter'})
    pass_f= wb.add_format({'bg_color':'#dcfce7','font_color':'#16a34a',
                           'bold':True,'border':1,'align':'center'})
    fail_f= wb.add_format({'bg_color':'#fee2e2','font_color':'#dc2626',
                           'bold':True,'border':1,'align':'center'})
    risk_f= wb.add_format({'bg_color':'#fee2e2','font_color':'#dc2626',
                           'bold':True,'border':1,'align':'center'})
    safe_f= wb.add_format({'bg_color':'#dcfce7','font_color':'#16a34a',
                           'bold':True,'border':1,'align':'center'})
    grade_fmts = {
        'A': wb.add_format({'bg_color':'#dcfce7','font_color':'#16a34a','bold':True,
                            'border':1,'align':'center'}),
        'B': wb.add_format({'bg_color':'#dbeafe','font_color':'#2563eb','bold':True,
                            'border':1,'align':'center'}),
        'C': wb.add_format({'bg_color':'#fef9c3','font_color':'#ca8a04','bold':True,
                            'border':1,'align':'center'}),
        'D': wb.add_format({'bg_color':'#ffedd5','font_color':'#ea580c','bold':True,
                            'border':1,'align':'center'}),
        'F': wb.add_format({'bg_color':'#fee2e2','font_color':'#dc2626','bold':True,
                            'border':1,'align':'center'}),
    }
    num_e = wb.add_format({'bg_color':'#f3f4f6','border':1,'align':'center',
                           'num_format':'0.00'})
    num_o = wb.add_format({'bg_color':'#ffffff','border':1,'align':'center',
                           'num_format':'0.00'})
    title_f = wb.add_format({'bold':True,'font_size':14,'font_color':'#1e3a5f'})
    stat_label = wb.add_format({'bold':True,'bg_color':'#e5e7eb','border':1})
    stat_val   = wb.add_format({'bg_color':'#ffffff','border':1,'align':'center'})

    # ────────────────────────────────────────────────────────────────
    # Sheet 1 – All Students
    # ────────────────────────────────────────────────────────────────
    ws = wb.add_worksheet('All Students')
    ws.set_zoom(90)
    ws.freeze_panes(3, 0)

    ws.merge_range('A1:R1',
        f'AI-Based Student Performance Prediction System  |  '
        f'Class Report  |  Generated: {datetime.now().strftime("%d %B %Y")}',
        wb.add_format({'bold':True,'font_size':12,'bg_color':'#1e3a5f',
                       'font_color':'white','align':'center','valign':'vcenter'}))
    ws.set_row(0, 28)

    cols = [
        ('Student ID', 10), ('Name', 22),
        ('Attendance', 11), ('Test 1', 8), ('Test 2', 8), ('Test 3', 8),
        ('Asgn 1', 8),      ('Asgn 2', 8), ('Asgn 3', 8),
        ('Exam', 8),        ('Avg Test', 10), ('Avg Asgn', 10),
        ('Final Score', 12),('Grade', 8),
        ('Pass/Fail', 10),  ('At-Risk', 10),
        ('Pass Prob.%', 12),('Risk Prob.%', 12),
    ]
    for c, (label, width) in enumerate(cols):
        ws.write(1, c, label, subhdr)
        ws.set_column(c, c, width)
    ws.set_row(1, 20)

    data_keys = [
        'student_id','name','attendance','test1','test2','test3',
        'assignment1','assignment2','assignment3','exam_score',
        'avg_test','avg_assignment','final_score','grade_category',
        'pass_fail','at_risk','pass_probability','risk_probability'
    ]
    for r, s in enumerate(students):
        row = r + 2
        fmt_e = even if r % 2 == 0 else odd
        fmt_n = num_e if r % 2 == 0 else num_o
        fmt_c = ctr_e if r % 2 == 0 else ctr_o

        for c, key in enumerate(data_keys):
            val = s.get(key, '')
            if key in ('student_id', 'name'):
                ws.write(row, c, val, fmt_e)
            elif key == 'grade_category':
                ws.write(row, c, val, grade_fmts.get(val, fmt_c))
            elif key == 'pass_fail':
                ws.write(row, c, val, pass_f if val == 'Pass' else fail_f)
            elif key == 'at_risk':
                ws.write(row, c, val, risk_f if val == 'Yes' else safe_f)
            elif isinstance(val, (int, float)):
                ws.write(row, c, val, fmt_n)
            else:
                ws.write(row, c, val, fmt_c)

    # ────────────────────────────────────────────────────────────────
    # Sheet 2 – Summary
    # ────────────────────────────────────────────────────────────────
    ws2 = wb.add_worksheet('Summary')
    ws2.set_column('A:A', 24)
    ws2.set_column('B:B', 18)

    ws2.merge_range('A1:B1', 'Class Performance Summary', title_f)
    ws2.set_row(0, 26)

    summary_rows = [
        ('Total Students',     stats.get('total_students', 0)),
        ('Passed',             stats.get('pass_count', 0)),
        ('Failed',             stats.get('fail_count', 0)),
        ('Pass Rate (%)',       stats.get('pass_rate', 0)),
        ('At-Risk Students',   stats.get('at_risk_count', 0)),
        ('Average Score',      stats.get('average_score', 0)),
        ('Highest Score',      stats.get('highest_score', 0)),
        ('Lowest Score',       stats.get('lowest_score', 0)),
    ]
    for i, (label, val) in enumerate(summary_rows):
        ws2.write(i + 2, 0, label, stat_label)
        ws2.write(i + 2, 1, val,   stat_val)

    # Grade distribution table
    ws2.write(12, 0, 'Grade Distribution', wb.add_format(
        {'bold':True,'font_color':'#1e3a5f','font_size':11}))
    ws2.write(13, 0, 'Grade',  hdr)
    ws2.write(13, 1, 'Count',  hdr)
    grade_dist = stats.get('grade_distribution', {})
    for i, g in enumerate(['A','B','C','D','F']):
        ws2.write(14 + i, 0, g,                   grade_fmts.get(g, stat_label))
        ws2.write(14 + i, 1, grade_dist.get(g, 0), stat_val)

    # Grade distribution chart
    chart = wb.add_chart({'type': 'column'})
    chart.add_series({
        'name':       'Students',
        'categories': ['Summary', 14, 0, 18, 0],
        'values':     ['Summary', 14, 1, 18, 1],
        'fill':       {'colors': ['#16a34a','#2563eb','#ca8a04','#ea580c','#dc2626']},
    })
    chart.set_title({'name': 'Grade Distribution'})
    chart.set_x_axis({'name': 'Grade'})
    chart.set_y_axis({'name': 'Number of Students'})
    chart.set_style(10)
    ws2.insert_chart('D2', chart, {'x_scale': 1.5, 'y_scale': 1.4})

    # ────────────────────────────────────────────────────────────────
    # Sheet 3 – At-Risk Students
    # ────────────────────────────────────────────────────────────────
    ws3 = wb.add_worksheet('At-Risk Students')
    ws3.merge_range('A1:K1', 'At-Risk Student List', wb.add_format(
        {'bold':True,'font_size':12,'bg_color':'#dc2626',
         'font_color':'white','align':'center'}))
    ws3.set_row(0, 24)

    ar_cols = [('ID',10),('Name',22),('Final Score',13),('Grade',8),
               ('Exam',8),('Avg Test',10),('Avg Asgn',10),
               ('Attendance',12),('Pass Prob.%',12),('Risk Prob.%',12),('Risk Factors',35)]
    for c, (lbl, w) in enumerate(ar_cols):
        ws3.write(1, c, lbl, subhdr)
        ws3.set_column(c, c, w)

    at_risk_students = [s for s in students if s['at_risk'] == 'Yes']
    for r, s in enumerate(at_risk_students):
        row = r + 2
        fmt = even if r % 2 == 0 else odd
        ws3.write(row, 0,  s['student_id'],         fmt)
        ws3.write(row, 1,  s['name'],                fmt)
        ws3.write(row, 2,  s['final_score'],         num_e)
        ws3.write(row, 3,  s['grade_category'],      grade_fmts.get(s['grade_category'], fmt))
        ws3.write(row, 4,  s['exam_score'],          num_e)
        ws3.write(row, 5,  s['avg_test'],            num_e)
        ws3.write(row, 6,  s['avg_assignment'],      num_e)
        ws3.write(row, 7,  s['attendance'],          num_e)
        ws3.write(row, 8,  s['pass_probability'],    num_e)
        ws3.write(row, 9,  s['risk_probability'],    num_e)
        ws3.write(row, 10, ', '.join(s['risk_factors']), fmt)

    ws3.set_column(10, 10, 40)

    wb.close()
    buf.seek(0)
    return buf