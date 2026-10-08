"""Create a single A4 truthful project-experience PDF and render for visual QA."""
from pathlib import Path
from html import escape
import json
from reportlab.pdfgen import canvas
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.colors import HexColor
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import pymupdf

root=Path(__file__).resolve().parents[1]; out=root/'output/pdf'; out.mkdir(parents=True,exist_ok=True)
pdfmetrics.registerFont(TTFont('Chinese','C:/Windows/Fonts/simsun.ttc',subfontIndex=0))
pdfmetrics.registerFont(TTFont('ChineseBold','C:/Windows/Fonts/simhei.ttf'))
src=(root/'docs/项目经历-实施岗.md').read_text(encoding='utf-8').splitlines()
title=ParagraphStyle('title',fontName='ChineseBold',fontSize=18,leading=25,textColor=HexColor('#16324f'),spaceAfter=7)
meta=ParagraphStyle('meta',fontName='Chinese',fontSize=9.8,leading=15,textColor=HexColor('#576574'),spaceAfter=10,wordWrap='CJK')
body=ParagraphStyle('body',fontName='Chinese',fontSize=10.8,leading=17,spaceAfter=9,wordWrap='CJK')
bullet=ParagraphStyle('bullet',parent=body,leftIndent=11,firstLineIndent=-11,spaceAfter=10)
styles=[title,meta]; story=[]
def rich(s):
    import re
    s=escape(s)
    return re.sub(r'\*\*(.*?)\*\*',r'<font name="ChineseBold">\1</font>',s)
for i,line in enumerate(src):
    if not line.strip(): continue
    if line.startswith('# '):
        story.append(Paragraph(rich(line[2:]),title))
        story.append(HRFlowable(width='100%',thickness=1.2,color=HexColor('#2b6f8f'),spaceAfter=10))
    elif line.startswith('个人实战'): story.append(Paragraph(rich(line),meta))
    elif line.startswith('- '): story.append(Paragraph('• '+rich(line[2:]),bullet))
    else: story.append(Paragraph(rich(line),body))
path=out/'FlowPilot-实施岗项目经历.pdf'
doc=SimpleDocTemplate(str(path),pagesize=A4,rightMargin=18*mm,leftMargin=18*mm,topMargin=18*mm,bottomMargin=17*mm,title='FlowPilot ERP - 实施岗项目经历',author='hamiaNa1')
def footer(c,d):
    c.saveState(); c.setFont('Chinese',8); c.setFillColor(HexColor('#657482'))
    c.drawString(18*mm,11*mm,'个人实施实验 · 真实成果与未完成范围均有证据')
    c.drawRightString(A4[0]-18*mm,11*mm,str(d.page)); c.restoreState()
doc.build(story,onFirstPage=footer,onLaterPages=footer)
with pymupdf.open(path) as pdf:
    assert len(pdf)==1,'Resume must fit one A4 page'
    page=pdf[0]; assert abs(page.rect.width-A4[0])<1 and abs(page.rect.height-A4[1])<1
    text=page.get_text(); assert 'FlowPilot' in text and '17' in text and '30' in text
    page.get_pixmap(matrix=pymupdf.Matrix(1.6,1.6)).save(root/'evidence/resume-a4-preview.png')
    report={'pages':len(pdf),'page_points':[page.rect.width,page.rect.height],'format':'A4','embedded_chinese_fonts':True,'text_extraction_checked':True,'visual_review':'pending','source':'docs/项目经历-实施岗.md'}
(root/'evidence/resume-pdf-verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Created one A4 PDF page, rendered PNG; visual review pending.')
