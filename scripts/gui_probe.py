"""Real Edge browser login/DOM probe, screenshots contain no credentials."""
import argparse, json, time, re
from playwright.sync_api import sync_playwright
from common import ROOT, ENV, write_json, now
from native import redis_get

def browser_login(page, user='jsh'):
    captured={}
    def capture(response):
        if response.url.endswith('/user/randomImage'):
            try: captured.update(response.json()['data'])
            except Exception: pass
    page.on('response',capture)
    page.goto(f"http://127.0.0.1:{ENV['HTTP_PORT']}",wait_until='domcontentloaded')
    page.get_by_placeholder('请输入用户名',exact=True).wait_for(timeout=30000)
    page.get_by_placeholder('请输入用户名',exact=True).fill(user)
    page.get_by_placeholder('请输入密码',exact=True).fill(ENV['ERP_TENANT_PASSWORD'] if user=='jsh' else ENV['ERP_DEMO_PASSWORD'])
    page.get_by_placeholder('请输入验证码',exact=True).wait_for(timeout=15000)
    deadline=time.monotonic()+10
    while 'uuid' not in captured and time.monotonic()<deadline: page.wait_for_timeout(100)
    page.get_by_placeholder('请输入验证码',exact=True).fill(redis_get('captcha_codes:'+captured['uuid']))
    # Persisted remember-password feature is explicitly disabled for automated tests.
    cb=page.get_by_role('checkbox')
    if cb.count() and cb.first.is_checked(): cb.first.uncheck()
    page.get_by_role('button',name=re.compile(r'登\s*录')).click()
    page.wait_for_url('**/dashboard/**',timeout=30000)
    page.wait_for_timeout(1200)
    if page.locator('.introjs-skipbutton').count() and page.locator('.introjs-skipbutton').is_visible():
        page.locator('.introjs-skipbutton').click()
    for close in page.locator('.ant-notification-notice-close').all():
        if close.is_visible(): close.click()
    page.remove_listener('response',capture)

def main():
    p=argparse.ArgumentParser(); p.add_argument('--user',default='jsh'); p.add_argument('--route'); p.add_argument('--inspect-warehouse',action='store_true'); args=p.parse_args()
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='msedge',headless=True)
        context=browser.new_context(viewport={'width':1440,'height':1000},locale='zh-CN')
        # Avoid external analytics; tests concern this local ERP only.
        context.route('**/hm.baidu.com/**',lambda route:route.abort())
        page=context.new_page(); errors=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        browser_login(page,args.user)
        if args.route:
            page.goto(f"http://127.0.0.1:{ENV['HTTP_PORT']}{args.route}",wait_until='domcontentloaded'); page.wait_for_timeout(1800)
        if args.inspect_warehouse:
            page.locator('.table-page-search-wrapper .ant-select').first.click(); page.wait_for_timeout(300)
            print(page.locator('.ant-select-dropdown').all_inner_texts())
            print(page.locator('.ant-select-dropdown').evaluate_all('(nodes)=>nodes.map(n=>n.outerHTML)'))
        tag=args.user+('-'+args.route.strip('/').replace('/','-') if args.route else '')
        page.screenshot(path=str(ROOT/'evidence'/f'gui-{tag}.png'),full_page=True)
        text=page.locator('body').inner_text()
        write_json('evidence/gui-'+tag+'.json',{'time':now(),'url':page.url,'user':args.user,'body':text,'page_errors':errors,
          'inputs':[{'placeholder':e.get_attribute('placeholder'),'type':e.get_attribute('type')} for e in page.locator('input').all()]})
        print(text[:4500])
        browser.close()

if __name__=='__main__': main()
