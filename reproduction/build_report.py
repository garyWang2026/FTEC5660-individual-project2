"""Render the editable coursework report to PDF. Requires requirements-report.txt."""
import argparse
from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Image, KeepTogether


def inline(text):
    text=escape(text)
    text=re.sub(r'\*\*(.+?)\*\*',r'<b>\1</b>',text)
    text=re.sub(r'`(.+?)`',r'<font name="Courier" size="8.4">\1</font>',text)
    return text


def build(root, figures_root=None):
    source=root/'submission/REPORT.md'
    output=root/'output/pdf/SimpleMem_Reproducibility_Report.pdf'
    output.parent.mkdir(parents=True,exist_ok=True)
    styles=getSampleStyleSheet()
    styles.add(ParagraphStyle(name='ReportBody',fontName='Helvetica',fontSize=10.1,leading=14.1,textColor=colors.HexColor('#243444'),spaceAfter=8,splitLongWords=True))
    styles.add(ParagraphStyle(name='ReportTitle',fontName='Helvetica-Bold',fontSize=22,leading=27,textColor=colors.HexColor('#173B55'),spaceAfter=15))
    styles.add(ParagraphStyle(name='ReportHeading',fontName='Helvetica-Bold',fontSize=17,leading=22,textColor=colors.HexColor('#173B55'),spaceAfter=14))
    styles.add(ParagraphStyle(name='ReportSub',fontName='Helvetica-Bold',fontSize=11.5,leading=16,textColor=colors.HexColor('#173B55'),spaceBefore=8,spaceAfter=7))
    styles.add(ParagraphStyle(name='ReportCell',fontName='Helvetica',fontSize=8.8,leading=12,textColor=colors.HexColor('#243444'),spaceAfter=0))
    styles.add(ParagraphStyle(name='ReportCaption',fontName='Helvetica-Oblique',fontSize=8.3,leading=11,textColor=colors.HexColor('#536575'),spaceAfter=9))
    width=A4[0]-100
    story=[];lines=source.read_text().splitlines();i=0;first=True
    while i<len(lines):
        line=lines[i].strip()
        if not line:i+=1;continue
        if line=='<!-- pagebreak -->':story.append(PageBreak());i+=1;continue
        if line.startswith('|'):
            rows=[]
            while i<len(lines) and lines[i].strip().startswith('|'):
                cells=[c.strip() for c in lines[i].strip().strip('|').split('|')]
                if not all(re.fullmatch(r':?-+:?',c) for c in cells):rows.append(cells)
                i+=1
            n=len(rows[0]);ratios=([.27,.73] if n==2 else [.24]+[.76/(n-1)]*(n-1))
            data=[[Paragraph(inline(c),styles['ReportCell']) for c in row] for row in rows]
            table=Table(data,colWidths=[width*x for x in ratios],repeatRows=1,hAlign='LEFT')
            table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#E2EBF1')),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#F5F8FA')]),('VALIGN',(0,0),(-1,-1),'TOP'),('TOPPADDING',(0,0),(-1,-1),5),('BOTTOMPADDING',(0,0),(-1,-1),5),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,0),.6,colors.HexColor('#A8BCCB'))]))
            story.extend([table,Spacer(1,11)]);continue
        if line.startswith('!['):
            match=re.match(r'!\[(.*?)\]\((.*?)\)',line)
            path=(source.parent/match.group(2)).resolve()
            if not path.exists() and figures_root:path=(figures_root/'submission'/match.group(2)).resolve()
            img=Image(str(path));scale=width/img.imageWidth;img.drawWidth=width;img.drawHeight=img.imageHeight*scale
            story.extend([img,Paragraph('Figure 1. Combined means; error bars show sample SD across three trial aggregates.',styles['ReportCaption'])]);i+=1;continue
        if line.startswith('# '):
            style=styles['ReportTitle'] if first else styles['ReportHeading'];first=False
            story.append(Paragraph(inline(line[2:]),style));i+=1;continue
        if line.startswith('##'):
            story.append(Paragraph(inline(line.lstrip('# ')),styles['ReportSub']));i+=1;continue
        if re.match(r'^\d+\. ',line):
            story.append(Paragraph(inline(line),styles['ReportBody']));i+=1;continue
        parts=[line];i+=1
        while i<len(lines) and lines[i].strip() and not lines[i].startswith(('#','|','![','<!--')) and not re.match(r'^\d+\. ',lines[i]):
            parts.append(lines[i].strip());i+=1
        story.append(Paragraph(inline(' '.join(parts)),styles['ReportBody']))

    def page(canvas,doc):
        canvas.saveState();canvas.setStrokeColor(colors.HexColor('#BBCAD4'));canvas.setLineWidth(.5)
        canvas.line(50,43,A4[0]-50,43)
        canvas.setFont('Helvetica',8);canvas.setFillColor(colors.HexColor('#536575'))
        canvas.drawString(50,29,'FTEC5660 | SimpleMem reproduction | garyWang2026')
        canvas.drawRightString(A4[0]-50,29,str(doc.page));canvas.restoreState()
    doc=SimpleDocTemplate(str(output),pagesize=A4,rightMargin=50,leftMargin=50,topMargin=43,bottomMargin=55,title='Reproducing SimpleMem on a Budget',author='garyWang2026',subject='FTEC5660 reproducibility study and controlled reflection ablation')
    doc.build(story,onFirstPage=page,onLaterPages=page)
    print(output)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--root',type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument('--figures-root',type=Path)
    a=p.parse_args();build(a.root,a.figures_root)
