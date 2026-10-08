"""Generate delivery documents from recorded evidence; never invent execution results."""
import json
from pathlib import Path
from datetime import datetime

ROOT=Path(__file__).resolve().parents[1]
DOCS=ROOT/'docs'
DOCS.mkdir(exist_ok=True)
def load(name): return json.loads((ROOT/'evidence'/name).read_text(encoding='utf-8-sig'))
def save(name,text): (DOCS/name).write_text(text.strip()+'\n',encoding='utf-8')
def link(name): return f'[{name}](../evidence/{name})'
def table(head,rows):
    def cell(x): return str(x).replace('|','\\|').replace('\n','<br>')
    return '\n'.join(['| '+' | '.join(head)+' |','| '+' | '.join(['---']*len(head))+' |']+['| '+' | '.join(map(cell,r))+' |' for r in rows])

VERSION='v3.6 / 8f28e7c2fe54d54de3621a414f5df1833dc5a55f'
STAMP='2026-10-08（Asia/Hong_Kong，个人实验）'
uat=load('uat-results.json')+load('permissions-uat.json')+load('gui-operation-uat.json')
assert len(uat)==19 and sum(r['status']=='失败' for r in uat)==2
backup=load('backup-restore-verification.json')
roles=load('migration-result.json')['roles']
stocks=load('sql-reconciliation.json')['results'][2]['rows']
ledger=load('sql-reconciliation.json')['results'][4]['rows']
audit=load('npm-audit.json')['metadata']['vulnerabilities']

save('01-项目背景与实施范围.md',f'''
# 项目背景与实施范围

记录日期：{STAMP}。

FlowPilot 汽车零部件有限公司是虚构演示企业，模拟旧 Excel 台账迁移至开源进销存系统。项目面向软件实施、ERP 实施及交付岗位，实施范围为环境部署、业务配置、数据迁移、采购库存销售联调、UAT 和备份恢复。

采用 [jshERP](https://github.com/jishenghua/jshERP) {VERSION}，保留 Apache-2.0 协议和版权。官方参考：[部署文档](https://www.gyjerp.com/doc/archive/deploy.html)、[用户手册](https://www.gyjerp.com/doc/archive/user-manual.html)。原项目目录为 `upstream/jshERP-boot`、`upstream/jshERP-web`；原始 SQL 为 `upstream/jshERP-boot/docs/jsh_erp.sql`。

## 实施边界

- 实际部署在 Windows 本机便携进程环境，四个服务均监听 127.0.0.1；没有 Docker 或可用 WSL Linux 发行版。
- 基于原生资料、XLS 导入、订单、入出库、审核、角色菜单功能实施；没有自行开发 ERP 或独立管理平台。
- 汽车零部件是业务背景，不表示已实施 BOM、MRP、生产排程、工单或成本核算。
- 原 SQL 自带样例保留，新数据采用 FlowPilot 名称、FP 条码及 legacy-code 备注区分，tenant_id=63。
- 19 条已执行 UAT 中 17 条通过、2 条失败，实验可演示，生产上线验收不通过。

## 阶段结果

|阶段|实际结果|证据|
|---|---|---|
|部署|前后端真实构建，四服务启动，浏览器登录|[部署健康](../evidence/deployment-health.json)|
|资料与迁移|3 供应商、3 客户、6 物料、2 仓库、4 岗位；原生 XLS 导入|[迁移结果](../evidence/migration-result.json)|
|业务联调|采购120、销售30；库存50→170→140|[单据台账](../evidence/business-ledger.json)|
|UAT|17通过、2失败|[验收报告](08-UAT验收用例与结果.md)|
|运维|四服务停止重启，30表隔离恢复一致|[恢复证据](../evidence/backup-restore-verification.json)|
|Docker/Linux|配置已准备，运行验证未执行|[真实障碍](../evidence/compose-execution-attempt.log)|
''')

save('02-环境检查与部署手册.md',f'''
# 环境检查与部署手册

## 固定版本与环境

实际路径 `D:\\7800\\flowpilot-erp`，Windows，PowerShell 7.6.5。代码固定为 {VERSION}。后端 pom 标识 `3.6-SNAPSHOT`，前端 package.json 标识 `3.5.0`，界面显示 V3.6；本交付的版本依据是 Git tag 和 commit，不修改上游版本号。

|组件|实测版本|用途|
|---|---|---|
|Java|Zulu 8.0.504|后端兼容运行时|
|Maven|3.9.9|Java 构建，Central 镜像|
|Spring Boot|2.0.0.RELEASE|上游后端依赖|
|Vue|2.x，锁文件固定|上游前端|
|Node|20.17.0|配合 OpenSSL legacy provider 构建旧前端|
|MySQL|8.0.44|独立数据库与数据目录|
|Redis|Windows 3.0.504|原生兼容实验；已停止维护|
|Nginx|1.28.0|静态资源与反向代理|
|Python|3.10，本地 .venv|迁移、验收和运维脚本|

完整检查见 {link('environment.json')}。已有其他项目服务未改动；本项目端口为 3308、6388、9999、8088。

## 当前机器启动和检查（已执行）

```powershell
Set-Location D:\\7800\\flowpilot-erp
.\\scripts\\start.ps1
.\\.venv\\Scripts\\python.exe scripts\\native.py status
.\\.venv\\Scripts\\python.exe scripts\\sql_verify.py
Invoke-WebRequest http://127.0.0.1:8088/healthz
# 关闭 / 重启：保留数据
.\\scripts\\stop.ps1
.\\.venv\\Scripts\\python.exe scripts\\native.py restart
# 日志检查，勿将未经脱敏日志上传
Get-Content runtime\\logs\\backend.log -Tail 80
Get-Content runtime\\logs\\mysql-server.log -Tail 80
Get-Content runtime\\logs\\nginx-error.log -Tail 80
```

浏览器打开 http://127.0.0.1:8088，使用 `fp_manager`；密码在本地 `.env` 的 `ERP_DEMO_PASSWORD`，手工输入页面验证码。租户配置账号 `jsh` 使用 `ERP_TENANT_PASSWORD`；平台 `admin` 使用 `ERP_ADMIN_PASSWORD`。两项默认密码已轮换，原样例 test123 已禁用。验证码测试通过本地 Redis 读取生成值，原验证码机制保留。

## 兼容新机器复现（完整干净机流程尚未实测）

前提：Windows x64、PowerShell、Git、Python 3.10 可用，端口空闲，可访问官方资源和 Maven/npm/PyPI。所有大资源和缓存保留在项目 `tools/`。先在 D 盘克隆此交付仓库：

```powershell
git clone https://github.com/hamiaNa1/flowpilot-erp-implementation.git D:\\Codex\\Projects\\flowpilot-erp
Set-Location D:\\Codex\\Projects\\flowpilot-erp
.\\scripts\\setup.ps1
.\\.venv\\Scripts\\python.exe scripts\\migrate.py templates
.\\.venv\\Scripts\\python.exe scripts\\migrate.py validate
.\\.venv\\Scripts\\python.exe scripts\\migrate.py import
.\\.venv\\Scripts\\python.exe scripts\\sql_verify.py
# 仅在新演示库、未创建验收单据时执行一次
.\\.venv\\Scripts\\python.exe scripts\\business_uat.py
```

setup 下载固定运行时，克隆 v3.6 并校验 commit，应用唯一兼容补丁，安装锁定依赖，构建，初始化新库并启动。首次运行由 native.py 自动生成随机 `.env`；Windows 原生路径不要先复制含占位密码的 `.env.example`。已有 datadir 时禁止重新初始化。资源下载失败应检查网络和日志，不删除数据库或切换 ERP 框架。setup 各组件已在本机分别执行，整段脚本在干净机器上尚未运行，不能宣称已验证全自动重部署。

## Docker / Linux 待验证路径

已准备 `compose.yaml`、两个 Dockerfile、Nginx 配置和初始化安全脚本。本机执行 Compose 检查因 Docker 未安装失败：{link('compose-execution-attempt.log')}。容器部署、容器重启、镜像可拉取性及 Linux VM 均未验证。

后续安装 Docker Desktop 的 Linux 容器环境或独立 Linux VM 后，先准备上游源码及安全环境文件；本交付默认数据库名为jsh_erp，保持示例数据库名以便复用核对步骤。与便携服务不能同时占用相同端口。

```bash
# 以下是 Linux 待执行命令，不是已成功的执行记录
git clone --depth 1 --branch v3.6 https://github.com/jishenghua/jshERP.git upstream
test "$(git -C upstream rev-parse HEAD)" = "8f28e7c2fe54d54de3621a414f5df1833dc5a55f"
git -C upstream apply ../deployment/windows-export.patch
python3 scripts/generate_env.py
sh scripts/compose.sh check
sh scripts/compose.sh start
sh scripts/compose.sh status
```

不要使用 `down -v` 清理业务卷。Docker Compose 的业务迁移还需在兼容 Python 环境安装 requirements；主机 Python API 测试可通过已映射的 MySQL/Redis/Nginx localhost 端口运行，Windows 专用进程管理脚本不能在 Linux 使用。

构建证据：{link('maven-patched-build-retry.log')}、{link('frontend-build.log')}。Maven BUILD SUCCESS，前端 Build complete；上游构建跳过测试源码编译，不能写“单元测试全部通过”。
''')

save('03-系统架构与服务配置.md',f'''
# 系统架构与服务配置

```mermaid
flowchart LR
    B[Edge 浏览器] --> N[Nginx 127.0.0.1:8088]
    N --> F[Vue 静态 dist]
    N --> A[Spring Boot 127.0.0.1:9999]
    A --> M[MySQL 127.0.0.1:3308]
    A --> R[Redis 127.0.0.1:6388]
```

后端接口前缀 `/jshERP-boot`，Nginx 保留该路径反代。SPA history 路由由 try_files 回落 index.html。浏览器业务调用 Nginx 同源接口，不需另设公共 API 地址。

|配置/数据|本机路径|说明|
|---|---|---|
|安全参数|.env|随机密码；Git 忽略|
|后端配置|runtime/application.properties|保留原配置并追加连接、目录和 INFO 日志覆盖|
|MySQL|runtime/my.ini、runtime/mysql|独立端口和 datadir，utf8mb4|
|Redis|runtime/redis.conf、runtime/redis|bind localhost、认证、AOF|
|Nginx|runtime/nginx/nginx.conf|由 native.py 生成，执行 nginx -t|
|实际运行 JAR|runtime/jshERP.jar|从 target 复制，避免构建产物被 Windows 锁住|
|附件与导出|runtime/upload、runtime/exports|本机持久目录|
|进程登记|runtime/processes.json|停止前核验 PID 对应可执行文件路径|

数据库应用用户 `flowpilot` 只有 jsh_erp 的 SELECT/INSERT/UPDATE/DELETE；备份恢复使用本地 root 配置文件，不把密码放在命令参数。数据库对象与约束来自原 SQL，不新增业务表。库存关联 material_id、depot_id，单据 head/detail、material_extend 与条码关联，租户63和 delete_flag 必须同时注意。

Compose 使用服务 DNS mysql、redis、backend，具备健康检查、依赖条件和 named volumes。数据库、Redis和Nginx映射地址限制127.0.0.1，后端仅容器网络可见。Compose 暂未运行，配置设计不等于测试通过。

基础安全：默认密码已轮换，所有本机端口仅 loopback；旧 Spring Boot/Vue/Redis 存在维护风险。npm audit 报告 {audit['total']} 项依赖问题（low {audit['low']}、moderate {audit['moderate']}、high {audit['high']}、critical {audit['critical']}），包含开发和间接依赖，不等同于同数量可利用漏洞；没有用自动大版本升级破坏兼容。

实测跨角色写入缺陷意味着菜单过滤不能作为服务端授权控制。本系统仅作隔离个人实验，当前不满足生产安全验收。

证据：{link('deployment-health.json')}、{link('nginx-config-check.log')}、{link('npm-audit.json')}、{link('permissions-uat.json')}。
''')

save('04-基础资料与业务配置说明.md',f'''
# 基础资料与业务配置说明

企业为“FlowPilot汽车零部件有限公司（虚构演示企业）”。租户参数：forceApprovalFlag=1（强制审核），minusStockFlag=0（不允许负库存），inOutManageFlag=0（关闭独立出入库管理）。实际数据库值以最终核对记录为准。

## 资料配置

- 供应商：精密钢材、标准件、包装材料3家；SUP-FP-001～003。
- 客户：汽车总装、售后配件、底盘系统3家；CUS-FP-001～003。
- 仓库：FlowPilot原料仓、FlowPilot成品仓。
- 结算：FP-ACC-001，演示结算账户，期初100000，非真实银行账户。
- 物料：支架、轴套、螺栓、垫圈、钢板、包装箱；件/个/千克使用原生基础单位。

{table(['条码','名称','单位','仓库','期初','当前'],[(r['bar_code'],r['name'],r['unit'],r['warehouse'],r['initial_quantity'],r['current_number']) for r in stocks])}

零期初仓库输入为0，原生系统可能不建立零值库存行。不能按全库总数判断本项目迁移量，保留的原样例不属于FlowPilot。

## 用户和角色（真实原生权限）

{table(['账号','用户ID','角色ID','岗位','数据范围'],[(r['login'],r['user_id'],r['role_id'],r['role_name'],r['data_scope']) for r in roles])}

所有岗位密码仅存在 .env 的 ERP_DEMO_PASSWORD。菜单/按钮使用原生 jsh_function 与 jsh_user_business，仓库与客户授权复用 UserDepot / UserCustomer；没有伪造新的后端权限模型。菜单细节见 {link('migration-result.json')}，采购、销售、仓库账号真实浏览器登录截图见 {link('role-fp_purchase.png')}、{link('role-fp_sales.png')}、{link('role-fp_warehouse.png')}。

管理员拥有原生全菜单；采购员可操作采购订单/入库；销售员可操作销售订单/出库；仓库员配置库存和原生仓库相关功能。只验证了记录列出的菜单行为，不宣称所有数据范围隔离均通过。

## 页面查看与编辑

fp_manager 登录 → 基础资料 → 供应商，按 FlowPilot 名称查询 → 编辑联系人 → 保存。已真实修改 SUP-FP-001 的联系人为“供应联系人甲（页面验收）”，SQL核对 ID 和 legacy-code 备注保留。

证据：{link('gui-vendor-edit-dialog.png')}、{link('gui-vendor-edited.png')}、{link('gui-operation-uat.json')}。原生XLS重复导入会按名称更新联系人；业务使用后不要无目的重新导入覆盖页面维护内容。
''')

save('05-Excel数据迁移与SQL核对.md',f'''
# Excel 数据迁移与 SQL 核对

## 输入与原生模板

`data/` 包含 suppliers.csv、customers.csv、materials.csv、initial-stock.csv（UTF-8 BOM），及对应旧台账 XLS、原生 suppliers-native.xls、customers-native.xls、materials-native.xls。供应商3行、客户3行、物料6行、期初仓库输入12行。CSV不是ERP直接导入格式，由脚本预校验后转换为原生XLS。

供应商/客户必须两行表头，第三行开始，15列。物料前27列为原生固定合同，后续列按当前真实仓库顺序追加；模板依据实际导出及 MaterialService / SupplierService，不按主观猜测填写。

## 字段映射

{table(['源字段','原生输入/目标表字段','约束与转换'],[
('code（往来单位）','jsh_supplier.description','原系统没有独立旧编码字段；存 legacy-code:SUP-FP-001 / CUS-FP-001'),
('name / type','supplier / type','供应商或客户；同租户同名称同类型原生更新，脚本先查编码冲突'),
('contact / address','contacts / address','中文原值；XLS联系人列1、地址列11、备注列12'),
('effective_date','仅迁移来源审计','YYYY-MM-DD预校验，不虚构目标生效日字段'),
('barcode','jsh_material_extend.bar_code','FP-MAT-001～006；唯一性预检查，原生基本条码列10'),
('name / specification / unit','jsh_material.name / standard / unit','原生列0/1/8；必填名称和基本单位'),
('purchase_price / sale_price','material_extend.purchase_decimal / wholesale_decimal','原生采购价列14，零售/销售价列15/16'),
('raw_stock / finished_stock','jsh_material_initial_stock.number','按仓库列定位，非负有限数；与独立库存台账一致'),
('warehouse','jsh_depot.id → depot_id','按已配置真实仓库名解析，不硬写跨环境ID')])}

物料完整27列合同和生成逻辑见 [迁移脚本](../scripts/migrate.py)。期初库存通过商品原生XLS的仓库列一起导入，未采用直接INSERT业务库存表。

## 执行与复核

```powershell
.\\.venv\\Scripts\\python.exe scripts\\migrate.py validate
# 新库初始化时执行；已有业务后不反复覆盖期初
.\\.venv\\Scripts\\python.exe scripts\\migrate.py import
.\\.venv\\Scripts\\python.exe scripts\\sql_verify.py
```

首次资料创建：往来单位最初通过原生 /supplier/add；之后查明原生 importVendor/importCustomer，补充用XLS真实导入两轮，ID和数量均保持3+3，所有映射值SQL核对一致。最终迁移脚本已优先调用原生XLS接口。物料和期初库存首次已通过 /material/importExcel 成功导入，随后角色配置失败不否定此前成功导入的事实，原始成功请求保留于 migration-permission-length-failure.json。

重复保护：往来单位先检查名称和旧编码冲突，再用原生名称+type更新；物料已存在全套FP条码时跳过，部分存在则阻止自动继续，避免覆盖进行中的库存。business_uat.py 检测既有验收单号后拒绝重复运行。

7类负例在源数据内存副本上执行：必填名称、重复编码、负数量、非法数字、日期格式、未知物料、未知仓库，均在修改ERP前拒绝；没有改坏有效台账制造故障经历。

中文保存经原生XLS读回、接口返回、数据库和页面截图验证。服务器 utf8mb4/utf8mb4_unicode_ci，客户端 utf8mb4；PowerShell控制台的编码表现不能替代文件和页面数据判断。另有真实XLS读回渲染预览：[模板截图](../evidence/xls-template-preview.png)、[检查记录](../evidence/xls-template-verification.json)；没有宣称Microsoft Excel GUI验收。

核对SQL见 [reconciliation.sql](../sql/reconciliation.sql)，包含迁移量、库存期初+已审核净变动、单据关联、重复条码/旧编码/单号。最终差异为0，三类重复查询均空。

证据：{link('migration-precheck.json')}、{link('migration-result.json')}、{link('migration-permission-length-failure.json')}、{link('partner-native-import.json')}、{link('partner-native-api.json')}、{link('migration-validation-tests.json')}、{link('sql-reconciliation.json')}。
''')

save('06-采购库存销售业务流程.md',f'''
# 采购、库存、销售业务流程

验证物料 FP-MAT-001 FlowPilot制动支架，基本单位件，FlowPilot原料仓 id19；供应商SUP-FP-001，客户CUS-FP-001。操作账号采购 fp_purchase（147）、销售 fp_sales（149）、页面复核 fp_manager（146）。单价采购68，销售95，均为虚构演示价格。

## 真实单据链

{table(['单号','原生type/sub_type','创建人','数量','最终状态','关联单号'],[(r['number'],r['type']+'/'+r['sub_type'],r['creator'],r['oper_number'],r['status'],r['link_number']) for r in ledger])}

订单最终状态2表示完成，入出库状态1表示已审核；不可把4张单据全部写成status1。订单不产生库存变化。强制审核下入出库草稿不计库存，审核后才生效。

|步骤|操作|原料仓数量|
|---|---|---|
|期初|原生物料XLS导入|50|
|采购订单|保存120件并审核|50|
|采购入库|关联订单、保存120件、审核|170|
|销售订单|保存30件并审核|170|
|销售出库|关联订单、保存30件、审核|140|
|反审核销售出库|原生接口及真实页面均验证|170|
|重新审核|原生接口及真实页面均验证|140|

成品仓支架仍10件，因此不指定仓库的总库存不能直接与原料仓140比较。

主业务单据由原生API创建，浏览器真实登录并按仓库/条码核实三个库存阶段；页面另外真实操作了销售单反审核/审核。没有把接口创建写成页面手工创建。

## 异常业务实测

- 141件出库：被原生接口拒绝，头表未残留，库存仍140。
- 已有同号重放：原生校验拒绝。立即重放新单：Redis2秒防重复拒绝，code8500032，仅1个头。
- 缺仓库：拒绝保存。
- 负数-1：后端接受未审核草稿（失败），未改变库存，已用原生删除接口清理本测试草稿。
- 销售账号直接写采购订单：接口成功而菜单不可见（失败），已清理自建未审核草稿。

删除为原生软删除，仅测试草稿；最终4张有效主单保留。不宣称验证了未测试的取消审批、生产工单等功能。

页面证据：{link('stock-01-initial.png')}、{link('stock-02-purchase-approved.png')}、{link('stock-03-sales-approved.png')}、{link('gui-sale-status-0.png')}、{link('gui-sale-status-1.png')}。

接口/SQL证据：{link('business-api.json')}、{link('business-ledger.json')}、{link('business-stock-snapshots.json')}、{link('gui-operation-api.json')}、{link('sql-reconciliation.json')}。
''')

save('07-接口联调记录.md','''
# 接口联调记录

实际工具为 Python requests、Edge 网络监听和 SQL 查询。Postman 集合可导入，但未把“导出集合”写成“Postman GUI已执行全部测试”。请求/响应与调用时间已脱敏保留。

基址 http://127.0.0.1:8088/jshERP-boot，认证头 X-Access-Token。原生登录密码为MD5格式，验证码uuid/code必填，HTTP200不代表业务成功，应检查业务code和data.msgTip。

|场景|实际接口|返回及数据库核对|证据|
|---|---|---|---|
|认证|GET /user/randomImage；POST /user/login|msgTip=user can login；岗位userId对应146～149|[角色请求](../evidence/permissions-api.json)|
|基础资料|GET /supplier/list|按type和FlowPilot过滤，供应商3、客户3；SQL旧编码各3|[查询复核](../evidence/api-readonly-verification.json)|
|原生迁移|POST /supplier/importVendor、/supplier/importCustomer；/material/importExcel|multipart file，3+3、6物料，中文与期初核对|[往来单位导入](../evidence/partner-native-api.json)|
|采购/销售保存|POST /depotHead/addDepotHeadAndDetail|info与rows是JSON字符串；SQL头/行、关联单号和creator核对|[业务请求](../evidence/business-api.json)|
|审核|POST /depotHead/batchSetStatus|ids为字符串，status0反审核/1审核；库存170/140|[页面操作](../evidence/gui-operation-api.json)|
|单据查询|GET /depotHead/getDetailByNumber；GET /depotItem/getDetailList|PI/SI头信息及PO/SO行ID，分别对应头表和行表|[只读请求](../evidence/api-readonly-verification.json)|
|库存|GET /material/getListWithStock|depotIds=19，materialParam=FP-MAT-001，currentStock=140|[库存快照](../evidence/business-stock-snapshots.json)|
|角色菜单|POST /function/findMenuByPNumber|pNumber=0及登录userId；按岗位菜单过滤|[权限记录](../evidence/permissions-uat.json)|

## Postman 操作

导入 [集合](../postman/FlowPilot.postman_collection.json) 和 [环境模板](../postman/FlowPilot.local.postman_environment.json)。密码、password_md5、token、captcha_code为空，导出环境前清空敏感值。先执行验证码请求，从返回的base64图像识别验证码，填写captcha_code；响应脚本保存uuid。登录前在本地填password_md5，成功后自动保存token和user_id。

查询目录可读取现有验收单。写入目录默认禁止，必须在隔离实验库手动将allow_mutation设为true；每轮测试先清空new_run，使首次写请求生成新的FP-POSTMAN前缀，不重放FP-UAT-20261008。先按单号查询新头ID保存document_id，再用/depotItem/getDetailList?headerId=本轮头ID查询明细，手工填写purchase_order_item_id或sale_order_item_id。审核前确认document_id对应刚查询的新单。采购、销售组织及账户ID须在当前库确认。

原生日志频率限制可能使同秒同模块写入会话失效；集合与Python实施脚本采用至少1.7秒写入间隔。立即重复提交场景是专门负例，不能把普通慢速重复号校验当成Redis频率校验。

## 异常联调结论

负数量保存和跨岗位采购写入均成功返回，但不满足预期业务校验/授权要求，保留为UAT失败。请求 → 数据库草稿 → 页面截图 → 原生软删除 → 最终库存核对的证据链见UAT报告。当前没有修改该业务代码掩盖问题。
''')

uattext=f'''# UAT 验收用例与结果

日期：{STAMP}。范围：本地个人隔离实验，真实原生接口及Edge浏览器，MySQL SQL复核。

已执行19条：17通过、2失败。另列Docker/Linux和干净机器部署阻塞/未执行项，不纳入通过数量。两项后端缺陷尚未修复，生产上线验收不通过。

{table(['用例','业务场景','状态','证据'],[(r['id'],r['scene'],r['status'],'、'.join(link(e) for e in r['evidence'])) for r in uat])}
'''
for r in uat:
    actual=json.dumps(r['actual'],ensure_ascii=False,default=str)
    # Detailed actual remains in source JSON; include concise relevant result here.
    if r['id']=='UAT-08': concise='-1件销售未审核草稿被接受，已清理，库存140；服务端数量校验未满足预期。'
    elif r['id']=='UAT-12': concise='销售账号创建采购订单草稿成功，creator149；菜单没有采购功能，后端仍允许写入。已清理，库存140。'
    else: concise=actual[:550]+('……完整返回见关联JSON。' if len(actual)>550 else '')
    uattext+=f"\n## {r['id']} {r['scene']}\n\n- 前置条件：{r['precondition']}。\n- 操作步骤：{r['steps']}。\n- 预期结果：{r['expected']}。\n- 实际结果：{concise}\n- 执行状态：**{r['status']}**；时间：{r['time']}。\n- 关联证据：{'、'.join(link(e) for e in r['evidence'])}。\n"
uattext+='''
## 其他迁移与运维验收

|编号|场景与步骤|预期|实际|状态|证据|
|---|---|---|---|---|---|
|MIG-01|既有3+3往来单位原生XLS连续导入两轮，SQL查数量/ID|无重复、值一致、库存不变|满足|通过|[原生导入](../evidence/partner-native-import.json)|
|MIG-02|在台账内存副本构造7类非法输入并预校验|ERP变更前拒绝|7类均拒绝，源文件未改|通过|[预校验](../evidence/migration-validation-tests.json)|
|OPS-01|停止四服务，检查端口，重启并比对资料/库存/单据|数据一致|所有端口已停止，重启数据一致|通过|[持久化](../evidence/persistence-restart.json)|
|OPS-02|mysqldump，恢复到新schema，30表核对|行数与内容一致|30表全部一致|通过|[恢复](../evidence/backup-restore-verification.json)|
|DEP-01|Docker Compose部署及容器重启|四容器健康且数据持久|Docker未安装|阻塞|[执行障碍](../evidence/compose-execution-attempt.log)|
|DEP-02|独立Linux VM部署|同业务链验证|无可用Linux VM|未执行|[环境](../evidence/environment.json)|
|DEP-03|干净机器按README从头安装|完整复现|本机组件步骤已执行，干净机未测试|未执行|[部署手册](02-环境检查与部署手册.md)|

主UAT19条与MIG/OPS补充用例分别统计，避免重复计数。Excel中文显示和页面编辑覆盖范围明确；未执行的负例GUI表单校验不外推为通过。
'''
save('08-UAT验收用例与结果.md',uattext)

save('09-问题排查与解决记录.md','''
# 问题排查与解决记录

以下仅记录真实发生的异常。Linux通用排障示例见文末，不作为已发生故障。

|编号|现象与证据|定位根因|处理及复验|状态|
|---|---|---|---|---|
|ENV-01|Compose无法执行；[记录](../evidence/compose-execution-attempt.log)|本机Docker未安装，无可用WSL Linux|采用官方支持的Windows便携原生方案；浏览器真实登录|Windows完成，Docker阻塞|
|BUILD-01|Maven请求旧Bintray/Spring仓库；[日志](../evidence/maven-initial-repositories.log)|上游旧仓库不可用，解析耗时|maven-settings.xml镜像*到Central，构建成功|已解决|
|BUILD-02|Windows JAR重打包失败；[日志](../evidence/maven-patched-build.log)|运行中的target/JAR被进程锁定|停止本项目服务再构建；运行时复制到runtime/JAR|已解决|
|WEB-01|Nginx -t失败|新prefix目录缺logs/temp|创建本项目目录后nginx -t成功；[最终记录](../evidence/nginx-config-check.log)|已解决|
|XLS-01|原生商品导出HTTP200空文件；导入准备失败|ExcelUtils将临时文件硬编码在/opt，Windows路径不存在|唯一上游补丁允许flowpilot.export.dir；构建、导出及原生导入成功|已解决|
|ROLE-01|角色按钮配置插入失败；[请求](../evidence/migration-permission-length-failure.json)|btn_str varchar(2000)，生成的JSON过长|紧凑JSON并先检查长度，不修改schema；4角色配置成功|已解决|
|API-01|连续请求HTTP500/loginOut；[记录](../evidence/migration-rate-guard-failure.json)|同user/module/ip/秒的日志频率校验会移除Redis会话；DATETIME(0)舍入与Java截断不同|写操作间隔1.7秒并重新登录；完整业务链通过，保留系统校验|规避已验证，原实现限制保留|
|SCRIPT-01|往来单位迁移TypeError|PyMySQL带参数SQL的LIKE字面%参与格式化|LIKE模式改为绑定参数，XLS两轮导入通过|实施脚本已修正|
|GUI-01|GUI验收定位失败|history路由及Ant图标影响accessible name，审核匹配到反审核|按真实DOM与源码定位按钮文本，页面反审核/审核实测完成|测试脚本已修正|
|DEF-01|销售出库-1件API接受草稿|后端保存接口未有效拒绝该数量；未修改业务代码|SQL/截图复现，原生软删除本测试草稿，库存保持140|未修复，UAT失败|
|DEF-02|fp_sales直接创建采购订单成功|菜单过滤未提供等价的后端写入授权隔离|SQL查creator149，管理员页面截图；原生删除测试草稿|未修复，UAT失败|
|PUB-01|Git HTTPS推送连续两次连接重置|Git传输路径不可用；GitHub认证、网页及REST API可访问|通过GitHub官方Git Database API上传相同blob/tree/commit；保留初始化历史，非强制更新main|公开上传已核验|

## DEF-01 复现

前置：启用强制审核、关闭负库存，fp_sales认证。向真实 /depotHead/addDepotHeadAndDetail 提交销售出库行operNumber=-1，info/rows仍为原生JSON字符串格式。预期拒绝数量；实际code200并产生status0草稿。未审核，库存不变。已仅软删除FP测试草稿。

证据：[UAT-08](../evidence/uat-results.json)、[追加复现与清理](../evidence/negative-quantity-reproduction.json)、[截图](../evidence/defect-negative-quantity-draft.png)。当前结论限于接口接受未审核草稿，不声称负数量已造成最终库存账错。

## DEF-02 复现

前置：fp_sales无采购菜单/按钮。登录后直接向相同原生保存接口提交1件采购订单。预期服务端拒绝；实际code200，SQL创建人149，管理员采购页面可见。删除的是自己生成的未审核FP测试草稿。

证据：[请求](../evidence/permissions-api.json)、[UAT-12](../evidence/permissions-uat.json)、[截图](../evidence/defect-cross-role-draft.png)。菜单权限通过不能抵消此项后端授权失败。

## Windows 常用排查

```powershell
Get-NetTCPConnection -State Listen | Where-Object LocalPort -in 3308,6388,9999,8088
Test-NetConnection 127.0.0.1 -Port 3308
.\\.venv\\Scripts\\python.exe scripts\\native.py status
Get-Content runtime\\logs\\mysql-server.log -Tail 80
Get-Content runtime\\logs\\backend-stderr.log -Tail 80
Get-Content runtime\\logs\\nginx-error.log -Tail 80
& tools\\nginx-1.28.0\\nginx.exe -p "$PWD/runtime/nginx/" -c nginx.conf -t
```

数据库连接异常：先看独立MySQL是否监听3308、错误日志、application.properties连接schema/user，再核对.env，禁止打印密码；MySQL root与app权限用途不同。Nginx502：先测后端9999，再看反代路径和错误日志。页面404：核实dist和history回落配置。启动失败：看完整错误、端口冲突、Java8、配置路径，不能靠删除datadir解决。

## Linux / Compose 排障参考（未在本项目实际执行）

```bash
uname -a
df -h
free -h
ss -lntp
docker version
docker compose ps
docker compose logs --tail 100 backend
docker compose logs --tail 100 mysql
docker compose exec nginx nginx -t
curl -I http://127.0.0.1:8088/
curl -f http://127.0.0.1:8088/jshERP-boot/platformConfig/getPlatform/name
journalctl -u docker --since '30 min ago'
```

日志可能包含凭据或会话标识，只发布脱敏片段：[服务日志片段](../evidence/service-logs-redacted.txt)。npm依赖审计保留原报告，不把扫描数量夸大为生产已遭攻击，也未随意升级核心大版本。
''')

save('10-数据库备份恢复与上线检查.md',f'''
# 数据库备份恢复与上线检查

## 真实备份和隔离恢复

```powershell
Set-Location D:\\7800\\flowpilot-erp
.\\.venv\\Scripts\\python.exe scripts\\backup_restore.py
```

最近执行时间：{backup['time']}。备份 `{backup['backup_file']}`，{backup['bytes']} 字节，SHA-256 `{backup['backup_sha256']}`；恢复目标 `{backup['restore_database']}`。业务库jsh_erp未被覆盖，备份文件含用户密码哈希和业务数据，Git忽略，不能上传。

脚本使用mysqldump --single-transaction、routines/triggers/events、utf8mb4及set-gtid-purged=OFF。密码经runtime/mysql-client.cnf读取，未放在命令参数。恢复前检查新schema不存在，存在则拒绝覆盖。对30张表全部记录规范化、排序并计算内容SHA-256；行数和内容全部相等。不是仅检查备份文件存在。

边界：执行期间没有并行业务写入，未验证高并发在线备份、PITR、异机容灾或RTO/RPO。快照与文件一致性结果限于本次隔离演示。

证据：{link('backup-restore-verification.json')}、{link('backup-command.log')}、{link('restore-command.log')}。

## 持久化验证

已执行停止MySQL、Redis、后端、Nginx，确认四端口停止，再启动并比较资料、单据及库存；data_equal=true，最终库存140。

证据：{link('persistence-restart.json')}、{link('persistence-execution.log')}。验证对象为Windows便携进程，不是Docker容器。

## 上线检查表

|项目|结果|上线含义|
|---|---|---|
|版本固定、许可证保留|完成|可追踪上游来源|
|应用/数据库/Redis/Nginx本地可用|通过|仅本机实验|
|默认密码轮换、应用DML权限|完成|凭据仍需按正式环境策略管理|
|全部服务只监听localhost|通过|未暴露公网|
|迁移记录和库存核对|通过|当前演示数据一致|
|备份隔离恢复|通过|30表行数/内容一致|
|核心采购销售|通过|原生单据链已实测|
|服务端负数量校验|失败|修复并复验前阻断上线|
|后端岗位授权|失败|修复并复验前阻断上线|
|依赖安全更新与兼容性回归|未完成|旧依赖风险需处理|
|Docker/Linux运行和容器持久化|未执行|不得作为已验证架构上线|
|干净机完整复现、容量与压力测试|未执行|正式交付前补验|

最终结论：个人实验可交付演示，生产上线验收不通过。没有真实企业客户或生产上线。

## 实施回滚操作说明

已实测的可逆业务动作：原生反审核销售出库，再审核恢复；仅在权限允许且无依赖冲突时使用。不要直接改库存表“修账”。

配置/版本回滚待正式演练：停止本项目应用，保留当前.env、配置、JAR与dist副本，恢复已知版本，检查连接目标，再启动并SQL核对。数据库回滚应先备份现状，再恢复到**新隔离schema**，核对30表和业务后才能决定切换配置。授予新schema应用权限、切换配置和数据损失评估尚未演练，不标记通过。

不删除原业务schema、datadir、恢复测试库或Docker卷；不执行down -v、prune、TRUNCATE或DROP。隔离恢复只是验证，不代表已将应用切换到恢复库。
''')

save('11-用户操作手册.md','''
# 用户操作手册

## 登录与账号

本机浏览器打开 http://127.0.0.1:8088，输入岗位账号、在.env中查看对应密码并填写图形验证码。管理员fp_manager、采购fp_purchase、仓库fp_warehouse、销售fp_sales；岗位密码键ERP_DEMO_PASSWORD。不要把密码复制到截图、文档或GitHub。

首次登录可关闭原生引导。测试使用Edge1440/1600宽屏，未做手机端业务验收。原项目品牌和版权保留。

## 查看和编辑基础资料（已实际操作）

管理员 → 基础资料 → 供应商，输入FlowPilot名称查询 → 编辑 → 联系人 → 保存。可找到3个FlowPilot供应商；客户同理。旧编码存备注legacy-code，不存在独立编码输入框。

商品信息按FP-MAT条码查询，仓库在基础资料维护。供应商联系人页面操作证据见 [编辑截图](../evidence/gui-vendor-edited.png)。不要重新导入旧台账覆盖已维护的数据。

## 查看库存（已实际操作）

报表查询 → 商品库存，选择FlowPilot原料仓，输入FP-MAT-001，查询。应见当前库存140件，期初50件。成品仓同条码当前10件。完整截图见 [库存](../evidence/stock-03-sales-approved.png)。

## 采购入库与销售出库操作参考

采购岗位 → 采购订单 → 新增 → 供应商、日期、支架120件 → 保存/审核 → 转采购入库 → 选择原料仓 → 保存/审核。销售岗位 → 销售订单 → 新增 → 客户、支架30件 → 保存/审核 → 转销售出库 → 仓库 → 保存/审核。

上述表单创建步骤依据原生界面与源码，主验收单实际由原生API创建；没有将该手工新增全过程标为GUI已通过。已存在的FP-UAT-20261008-PO/PI/SO/SI可在页面查看，不再次创建同号。新操作必须在隔离库使用新编号并再次SQL核对。

## 审核与反审核（页面已实际操作）

管理员 → 销售出库 → 按FP-UAT-20261008-SI查询 → 勾选 → 反审核 → 确认；库存应回到170。再勾选 → 审核 → 确认；库存140。强制审核时草稿不会计入库存。订单完成状态2与库存单已审核状态1不同。

禁止在已产生关联/结算影响时无评估地反审核，不直接删除已审核业务单。当前原生页面和接口权限不等价，不在公网提供此演示实例。

## 数据导入

使用原生.xls格式，不把CSV或.xlsx直接改名为.xls。保留两行表头、必填名称/状态；商品保留27固定列及实际仓库列。先运行预校验，导入后SQL复核。往来单位按名称更新，可能覆盖联系人；原生物料导入包含期初库存，业务进行中不要重复导入重置。

## 问题处理

库存不足提示应先查询对应仓库库存，不依靠负数绕过。重复提交提示先查询单号确认是否已保存，避免重复点击。无法登录检查验证码、账号启用与服务状态；发生异常保留时间/单号/脱敏截图，查看 [排查记录](09-问题排查与解决记录.md)。
''')

save('12-实施交付总结.md','''
# 实施交付总结

## 实际成果

固定jshERP v3.6 commit，在D盘构建并运行Windows本地四服务。完成独立MySQL30表初始化、默认账户密码轮换、认证Redis、Nginx反代；仅修改一处上游导出目录兼容代码。

完成3供应商、3客户、6物料、2仓库和4岗位配置，使用原生XLS迁移与幂等核对。原生接口真实执行采购120/销售30，页面与SQL共同核对库存50→170→140，真实页面编辑中文联系人并反审核/审核。

19条主UAT中17通过、2失败；迁移负例、重启持久化和30表隔离恢复另有证据。缺陷已复现并清理自建草稿，未人为修改业务代码制造案例。

## 未完成与限制

- Docker/WSL缺失，Compose/Linux部署、容器重启及独立VM验证未执行。
- 未在干净机器完整执行setup，不承诺任意机器零调整复现。
- 负数量草稿和跨角色写入缺陷未修复，不能宣称完整权限验收或生产可上线。
- 旧依赖安全升级、负载/容量、PITR、异机恢复、正式用户培训及真实客户验收未实施。
- 主业务单据由API创建，GUI验证范围为真实登录、菜单、资料编辑、库存和单据审核状态。

## 简历可写

可写“个人ERP实施实验项目”，描述固定版本部署、SQL初始化、原生数据迁移、岗位菜单配置、采购库存销售联调、UAT缺陷复现、备份隔离恢复及文档交付。数量与结论必须与证据一致。

不能写“独立研发ERP”“Linux/Docker已部署”“生产上线”“服务真实汽车客户”“权限验收全部通过”“所有测试通过”“验证了MRP/BOM”。

一页A4可用版本：[项目经历Markdown](项目经历-实施岗.md)、[项目经历PDF](../output/pdf/FlowPilot-实施岗项目经历.pdf)。PDF为项目经历素材，不是完整个人简历，不虚构学历、工作年限或证书。

## 维护建议

正式推广前优先修复并复验两项后端缺陷，再处理依赖维护、Linux/Compose实际部署、干净机复现与容量验收。现阶段保留localhost限制作为个人实验交付，不把未验证目标转成已完成成果。
''')

save('13-项目验收与证据清单.md','''
# 项目验收与证据清单

## 验收结论

个人实施实验已完成部署、核心数据迁移和业务联调，生产验收不通过。19条主UAT17通过2失败，Docker/Linux及干净机完整部署未验证。

|验收项|真实结果|主要证据|
|---|---|---|
|系统版本与构建|v3.6固定commit，前后端构建成功|environment.json、maven-patched-build-retry.log、frontend-build.log|
|真实登录及角色菜单|4岗位浏览器登录|role-fp_*.png、permissions-uat.json|
|数据迁移|3+3伙伴、6物料、期初库存；原生XLS|migration-result.json、partner-native-import.json|
|采购库存销售|50→170→140，4张有效核心单|business-ledger.json、stock-01/02/03截图|
|页面编辑/审核|联系人保存、库存170→140|gui-operation-uat.json、gui-sale-status-*.png|
|SQL一致性|期初+已审核净变动一致，重复查询为空|sql-reconciliation.json|
|负数量/跨角色缺陷|实测失败并清理草稿|uat-results.json、permissions-uat.json、defect-*.png|
|备份恢复|新schema30表行数/内容一致|backup-restore-verification.json|
|重启持久化|四端口停止，重启业务数据相等|persistence-restart.json|
|Docker/Linux|未执行，缺Docker/可用Linux|compose-execution-attempt.log|

完整文件、字节数与SHA-256见 [证据清单](../evidence/manifest.json)。发布检查见 [发布审计](../evidence/release-audit.json)，内容完整性检查见 [交付验证](../evidence/delivery-verification.json)。清单为最终脱敏证据生成，不包含清单自身、运行日志原件和私有备份。

## GitHub 公开发布核验

仓库为 [hamiaNa1/flowpilot-erp-implementation](https://github.com/hamiaNa1/flowpilot-erp-implementation)。匿名仓库API和网页均返回HTTP200；README blob、13份文档、远端提交与本地对应，.env、runtime、backups、tools等私有路径不存在。证据：[实际发布核验](../evidence/github-publication.json)。Git HTTPS两次连接重置后采用官方Git数据库API传输相同Git对象；保留本地交付与远端初始化历史，未force更新。

## 交付边界

源代码从上游固定commit取得并保留许可证；本仓库包含实施配置、脚本、模板、文档和脱敏证据。工具二进制、依赖缓存、.env、完整运行配置、datadir和备份均不公开。

本机私有备份可用于隔离恢复验证，公开仓库不提供含密码哈希的数据转储。截图来自虚构演示数据。所有HTTP地址为本机实验地址，不是公网演示入口。
''')

resume='''# FlowPilot ERP 制造业进销存系统实施交付

个人实战项目 | 2026年10月 | 目标岗位：软件实施 / ERP实施 / 系统交付工程师

**项目背景：** 基于开源jshERP v3.6，为虚构汽车零部件企业模拟旧Excel台账迁移及采购、库存、销售业务实施；负责环境部署、业务配置、数据迁移、联调验收和运维交付。

**技术环境：** Windows、Java 8、Spring Boot、Vue、MySQL 8.0、Redis、Nginx、Maven、Python、SQL、原生ERP接口。

- **系统部署：** 固定开源版本和Git commit，完成前后端构建、MySQL 30表初始化、Redis连接及Nginx反向代理；采用D盘便携部署，独立端口和数据目录，轮换默认账户密码。
- **配置与迁移：** 配置3家供应商、3家客户、6种物料、2个仓库和4类岗位；建立UTF-8 CSV/XLS模板及字段映射，通过原生Excel接口导入物料和期初库存，重复导入伙伴资料并核对ID与数量，验证7类非法台账在导入前被拒绝。
- **业务联调：** 使用原生接口完成采购订单、采购入库120件、销售订单及销售出库30件，结合真实浏览器与SQL验证库存50→170→140；完成页面资料编辑及销售单反审核/重新审核，核对单据关联和库存一致性。
- **UAT与问题定位：** 执行19条主UAT，17通过、2失败；验证库存不足、重复提交、缺仓库及岗位菜单，复现负数量草稿和跨角色写入缺陷，保留请求、SQL、截图与清理证据，如实记录验收阻断。
- **运维与交付：** 实测四服务停止重启后业务数据保留；执行MySQL备份并恢复到独立测试库，30张表行数及内容SHA-256全部一致；整理13份实施文档、部署脚本、核对SQL及Postman集合。

**成果边界：** 本项目为个人本地实验，未进行真实企业生产上线。Docker Compose方案已准备，Linux/容器运行验证未执行；两项后端缺陷尚未修复。

**项目仓库：** https://github.com/hamiaNa1/flowpilot-erp-implementation
'''
save('项目经历-实施岗.md',resume)

names=[p.name for p in sorted(DOCS.glob('[0-9][0-9]-*.md'))]
readme=f'''# FlowPilot ERP 制造业进销存系统实施交付

基于开源 [jshERP](https://github.com/jishenghua/jshERP) 的个人实施实战，模拟虚构汽车零部件企业的部署、配置、Excel迁移、采购库存销售联调、UAT和备份恢复。保留上游版权，不声称自主研发ERP或真实企业生产上线。

**已实际运行：** Windows便携部署，http://127.0.0.1:8088。**主UAT：17通过、2失败。** Docker/Linux部署未执行，后端数量及岗位授权缺陷尚未修复，生产验收不通过。

![真实销售出库后库存140件](evidence/stock-03-sales-approved.png)

## 实测成果

- jshERP {VERSION}；Java8/Spring Boot/Vue/MySQL8.0.44/Redis Windows3.0.504/Nginx1.28.0。
- 3供应商、3客户、6物料、2仓库、4岗位，原生XLS与UTF-8台账迁移。
- 4张有效采购/销售单据：支架采购120件、销售30件，原料仓库存 **50 → 170 → 140**，页面/API/SQL一致。
- 浏览器真实登录、资料编辑、销售单反审核/审核；不足库存和重复提交实测。
- MySQL备份恢复到新测试schema，30表行数和内容哈希一致；四服务重启数据保持。
- [19条主UAT及补充验收](docs/08-UAT验收用例与结果.md)、[实际故障与2项缺陷](docs/09-问题排查与解决记录.md)。

## 当前本机使用

```powershell
Set-Location D:\\7800\\flowpilot-erp
.\\scripts\\start.ps1
.\\.venv\\Scripts\\python.exe scripts\\native.py status
.\\.venv\\Scripts\\python.exe scripts\\sql_verify.py
# 保留数据停止
.\\scripts\\stop.ps1
```

岗位账号fp_manager/fp_purchase/fp_warehouse/fp_sales，密码读取本地.env中ERP_DEMO_PASSWORD，输入真实页面验证码。凭据不公开。数据库3308、Redis6388、后端9999、Nginx8088均为127.0.0.1监听。

## 兼容环境复现

前提：Windows x64、Git、PowerShell、Python3.10、空闲端口及官方下载网络。克隆交付仓库到D盘，在项目根目录运行：

```powershell
.\\scripts\\setup.ps1
.\\.venv\\Scripts\\python.exe scripts\\migrate.py templates
.\\.venv\\Scripts\\python.exe scripts\\migrate.py validate
.\\.venv\\Scripts\\python.exe scripts\\migrate.py import
# 仅新演示库执行一次；已有主单时脚本拒绝重复
.\\.venv\\Scripts\\python.exe scripts\\business_uat.py
.\\.venv\\Scripts\\python.exe scripts\\sql_verify.py
.\\.venv\\Scripts\\python.exe scripts\\backup_restore.py
```

setup获取固定运行时和上游commit，应用一处导出路径补丁，使用前端锁文件、MavenCentral及本地缓存构建，生成随机.env、初始化新datadir并启动。不要先复制示例占位密码用于原生部署；不要删除已有datadir重初始化。**本机各组件步骤已执行，干净机器完整setup尚未验证。** 详细版本、下载路径及Linux待验证命令见[部署手册](docs/02-环境检查与部署手册.md)。

Compose与Dockerfile已准备，本机Docker缺失；不把配置文件、静态检查或Windows进程持久化写成容器部署成功。切换Docker前处理端口冲突，保留原数据，禁止down -v。

## 目录和证据

|目录|内容|
|---|---|
|deployment/、compose.yaml|容器配置、Nginx、Maven镜像、固定锁文件、上游补丁|
|scripts/|便携部署、迁移、API/GUI验收、SQL、备份恢复及发布检查|
|data/|虚构CSV与原生/旧台账XLS模板|
|sql/|只读库存、单据、重复数据核对|
|postman/|可导入接口集合与空凭据环境模板|
|docs/|13份实施交付文档及简历项目经历|
|evidence/|真实脱敏请求、SQL、日志、截图、UAT、恢复及哈希清单|
|output/pdf/|一页A4项目经历PDF|

upstream/由脚本取得，.env、.venv、tools、runtime、backups均Git忽略，不打包工具二进制、缓存或数据库密码哈希。

## 交付文档

'''+ '\n'.join(f'- [{n[:-3]}](docs/{n})' for n in names)+'''

## 简历与验收边界

[一页项目经历](docs/项目经历-实施岗.md) · [A4 PDF](output/pdf/FlowPilot-实施岗项目经历.pdf) · [证据清单](evidence/manifest.json)

可展示部署、迁移、业务联调、SQL核对、UAT与备份隔离恢复；不能写Linux/Docker已落地、生产上线、完整权限验收通过或自主研发ERP。Maven构建成功不代表单元测试通过，Postman集合导出不代表Postman GUI全部实测。

## 开源来源与许可

上游固定commit见 [来源与变更](UPSTREAM.md)，许可证见 [LICENSE.upstream](LICENSE.upstream)。实施脚本与文档采用Apache-2.0，见 [LICENSE](LICENSE)。唯一ERP业务源码差异是导出临时目录可配置；未重构前后端。
'''
(ROOT/'README.md').write_text(readme,encoding='utf-8')
(ROOT/'UPSTREAM.md').write_text(f'''# 上游来源与变更

- 仓库：https://github.com/jishenghua/jshERP
- tag：v3.6；commit：8f28e7c2fe54d54de3621a414f5df1833dc5a55f
- 协议：Apache-2.0；原版权归原作者所有，复制许可证为LICENSE.upstream。
- 后端pom：3.6-SNAPSHOT；前端package：3.5.0；页面V3.6。版本以tag/commit为准。
- 上游源码不复制入交付Git历史，由setup固定获取，保留其独立仓库。
- 唯一源码补丁：[windows-export.patch](deployment/windows-export.patch)，ExcelUtils使用flowpilot.export.dir系统属性，默认/opt不变；本机设置runtime/exports。未改变业务校验或权限逻辑。
- 构建配置：Maven镜像Central；前端锁文件deployment/package-lock.json来自本机实际依赖解析，npm ci --legacy-peer-deps；Node构建设置--openssl-legacy-provider。
- 实施脚本不替代ERP，使用原生API/XLS；SQL主要用于只读核对，初始化安全及隔离恢复另有清晰边界。
''',encoding='utf-8')
print('Generated README, upstream/change notes, 13 delivery documents and truthful resume source.')
