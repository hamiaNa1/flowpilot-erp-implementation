"""Actual role menus and negative authorization tests on disposable draft bills."""
import json, re, time
from playwright.sync_api import sync_playwright
from common import ROOT, ENV, API, query, now, write_json
from gui_probe import browser_login
from business_uat import bill, get_bill, stock

def main():
    results=[]; records=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge',headless=True)
        for login in ['fp_manager','fp_purchase','fp_warehouse','fp_sales']:
            api=API(); res=api.login(login,ENV['ERP_DEMO_PASSWORD']); uid=res['data']['user']['id']
            menus=api.call('POST','/function/findMenuByPNumber',json={'pNumber':'0','userId':str(uid)})
            paths=[]
            def walk(items):
                for item in items:
                    if item.get('url'): paths.append(item['url'])
                    walk(item.get('children',[]))
            walk(menus)
            context=browser.new_context(viewport={'width':1600,'height':1000},locale='zh-CN')
            context.route('**/hm.baidu.com/**',lambda r:r.abort())
            page=context.new_page(); browser_login(page,login)
            page.screenshot(path=str(ROOT/'evidence'/f'role-{login}.png'),full_page=True)
            body=page.locator('body').inner_text()
            expected=(('/bill/purchase_in' in paths and '/bill/sale_out' not in paths) if login=='fp_purchase' else
                ('/bill/sale_out' in paths and '/bill/purchase_in' not in paths) if login=='fp_sales' else
                ('/report/material_stock' in paths and '/bill/purchase_in' not in paths and '/bill/sale_out' not in paths) if login=='fp_warehouse' else True)
            results.append({'id':'UAT-11-'+login,'scene':'岗位菜单权限 '+login,'precondition':'原生角色和用户关系已配置','steps':'使用岗位账号真实浏览器登录，读取原生菜单接口','expected':'采购、销售、仓库菜单按岗位可见','actual':{'paths':paths,'visible_text':body},'status':'通过' if expected else '失败','evidence':[f'role-{login}.png','permissions-api.json'],'time':now()})
            write_json('evidence/permissions-uat.json',results)
            write_json('evidence/permissions-api.json',records+api.records)
            if login=='fp_sales':
                old=get_bill('FP-UAT-20261008-ROLE-CROSS')
                if old:
                    assert old[0]['status']=='0' and old[0]['creator']==uid, 'Refuse to clean non-test/effective document'
                    api.call('DELETE','/depotHead/delete',params={'id':old[0]['id']})
                    write_json('evidence/own-test-draft-cleanup.json',{'recovered_previous_test_draft':old,'removed_from_active_docs':not get_bill('FP-UAT-20261008-ROLE-CROSS')})
                # Direct API attempt is intentionally separate from menu filtering.
                res,number,_=bill(api,'ROLE-CROSS','采购订单',1)
                accepted=isinstance(res,dict) and res.get('code')==200
                draft=get_bill(number)
                capture=None
                if accepted:
                    manager=API(); manager.login('fp_manager',ENV['ERP_DEMO_PASSWORD'])
                    manager_context=browser.new_context(viewport={'width':1600,'height':1000},locale='zh-CN')
                    manager_context.route('**/hm.baidu.com/**',lambda r:r.abort())
                    page=manager_context.new_page(); browser_login(page,'fp_manager')
                    page.goto(f"http://127.0.0.1:{ENV['HTTP_PORT']}/bill/purchase_order",wait_until='domcontentloaded'); page.wait_for_timeout(900)
                    page.screenshot(path=str(ROOT/'evidence'/'defect-cross-role-draft.png'),full_page=True)
                    capture=page.locator('body').inner_text()
                    cleanup=manager.call('DELETE','/depotHead/delete',params={'id':draft[0]['id']})
                    records+=manager.records
                else: cleanup=None
                results.append({'id':'UAT-12','scene':'销售岗位调用采购写入接口','precondition':'fp_sales没有采购菜单和采购按钮','steps':'销售账号直接提交采购订单1件，查询SQL并截图；仅清理本测试草稿','expected':'后端拒绝未经授权的采购写入','actual':{'response':res,'created_draft':draft,'browser_text':capture,'cleanup':cleanup,'stock':stock()},'status':'失败' if accepted else '通过','evidence':['permissions-api.json','defect-cross-role-draft.png'],'time':now()})
                write_json('evidence/permissions-uat.json',results)
                write_json('evidence/permissions-api.json',records+api.records)
                res,number,_=bill(api,'NEG-SCREEN','销售',-1)
                draft=get_bill(number)
                if res.get('code')==200:
                    page.goto(f"http://127.0.0.1:{ENV['HTTP_PORT']}/bill/sale_out",wait_until='domcontentloaded'); page.wait_for_timeout(1000)
                    page.screenshot(path=str(ROOT/'evidence'/'defect-negative-quantity-draft.png'),full_page=True)
                    visible=page.locator('body').inner_text()
                    api.call('DELETE','/depotHead/delete',params={'id':draft[0]['id']})
                    write_json('evidence/negative-quantity-reproduction.json',{'time':now(),'response':res,'sql_draft':draft,'visible_text':visible,'deleted_own_draft':not get_bill(number),'stock':stock()})
                # Redis rapid-submit protection, separate from permanent number check.
                res,number,payload= bill(api,'DUP-RAPID','销售订单',1)
                assert res.get('code')==200,res
                dup=api.call('POST','/depotHead/addDepotHeadAndDetail',json=payload,throttle=False)
                count=len(get_bill(number)); cleanup=api.call('DELETE','/depotHead/delete',params={'id':get_bill(number)[0]['id']})
                results.append({'id':'UAT-13','scene':'立即重复提交','precondition':'成功保存本测试销售订单，Redis防重复TTL为2秒','steps':'立即重放相同请求，SQL核对仅一个头；清理本测试草稿','expected':'Redis防重复拒绝第二次提交','actual':{'first':res,'second':dup,'count':count,'cleanup':cleanup},'status':'通过' if dup.get('code')!=200 and count==1 else '失败','evidence':['permissions-api.json'],'time':now()})
                if accepted: manager_context.close()
            context.close(); records+=api.records
        browser.close()
    write_json('evidence/permissions-api.json',records)
    write_json('evidence/permissions-uat.json',results)
    print([(r['id'],r['status']) for r in results])

if __name__=='__main__': main()
