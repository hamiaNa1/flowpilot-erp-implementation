"""Render actual XLS read-back values, without implying Microsoft Excel GUI testing."""
from html import escape
import xlrd
from playwright.sync_api import sync_playwright
from common import ROOT, now, write_json

sections=[]; books=[]
for name in ['suppliers-native.xls','customers-native.xls','materials-native.xls','initial-stock.xls']:
    s=xlrd.open_workbook(str(ROOT/'data'/name)).sheet_by_index(0)
    header=0 if name=='initial-stock.xls' else 1
    if name=='materials-native.xls':
        columns=[0,1,8,10,14,16]+[i for i in range(27,s.ncols) if str(s.cell_value(header,i)).startswith('FlowPilot')]
    elif name=='initial-stock.xls': columns=list(range(s.ncols))
    else: columns=[0,1,6,8,11,12,14]
    heads=[s.cell_value(header,c) for c in columns]
    rows=[[s.cell_value(r,c) for c in columns] for r in range(header+1,s.nrows)]
    assert rows and all(any('FlowPilot' in str(v) or 'FP-MAT' in str(v) for v in row) for row in rows)
    markup='<h2>'+escape(name)+'</h2><table><tr>'+''.join('<th>'+escape(str(h))+'</th>' for h in heads)+'</tr>'
    markup+=''.join('<tr>'+''.join('<td>'+escape(str(v))+'</td>' for v in row)+'</tr>' for row in rows)+'</table>'
    sections.append(markup); books.append({'file':'data/'+name,'rows':s.nrows-header-1,'columns':s.ncols,'preview_columns':columns,'utf8_chinese_readback':True})
html='''<!doctype html><html lang="zh"><meta charset="utf-8"><style>body{font:15px "Microsoft YaHei";margin:30px;color:#16324f}h1{font-size:25px}h2{font-size:19px;margin-top:30px}table{border-collapse:collapse;width:100%;font-size:14px}th,td{border:1px solid #c9d4df;padding:8px;text-align:left}th{background:#16324f;color:white}tr:nth-child(odd){background:#f0f5f8}</style><h1>FlowPilot 原生 XLS 模板 - 实际文件读回预览</h1><p>来自 xlrd 读回值；未使用 Microsoft Excel GUI。物料仅展示业务关键列，完整列保存在原文件。</p>'''+''.join(sections)+'</html>'
path=ROOT/'runtime/xls-preview.html'; path.write_text(html,encoding='utf-8')
with sync_playwright() as pw:
    b=pw.chromium.launch(channel='msedge',headless=True); page=b.new_page(viewport={'width':1800,'height':1300})
    page.goto(path.as_uri()); page.screenshot(path=str(ROOT/'evidence/xls-template-preview.png'),full_page=True); b.close()
write_json('evidence/xls-template-verification.json',{'time':now(),'books':books,'method':'xlrd readback + browser rendering of actual values','excel_gui_executed':False,'visual_review':'pending'})
print('Rendered four actual XLS read-back previews.')
