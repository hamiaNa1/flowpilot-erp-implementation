# Excel 数据迁移与 SQL 核对

## 输入与原生模板

`data/` 包含 suppliers.csv、customers.csv、materials.csv、initial-stock.csv（UTF-8 BOM），及对应旧台账 XLS、原生 suppliers-native.xls、customers-native.xls、materials-native.xls。供应商3行、客户3行、物料6行、期初仓库输入12行。CSV不是ERP直接导入格式，由脚本预校验后转换为原生XLS。

供应商/客户必须两行表头，第三行开始，15列。物料前27列为原生固定合同，后续列按当前真实仓库顺序追加；模板依据实际导出及 MaterialService / SupplierService，不按主观猜测填写。

## 字段映射

| 源字段 | 原生输入/目标表字段 | 约束与转换 |
| --- | --- | --- |
| code（往来单位） | jsh_supplier.description | 原系统没有独立旧编码字段；存 legacy-code:SUP-FP-001 / CUS-FP-001 |
| name / type | supplier / type | 供应商或客户；同租户同名称同类型原生更新，脚本先查编码冲突 |
| contact / address | contacts / address | 中文原值；XLS联系人列1、地址列11、备注列12 |
| effective_date | 仅迁移来源审计 | YYYY-MM-DD预校验，不虚构目标生效日字段 |
| barcode | jsh_material_extend.bar_code | FP-MAT-001～006；唯一性预检查，原生基本条码列10 |
| name / specification / unit | jsh_material.name / standard / unit | 原生列0/1/8；必填名称和基本单位 |
| purchase_price / sale_price | material_extend.purchase_decimal / wholesale_decimal | 原生采购价列14，零售/销售价列15/16 |
| raw_stock / finished_stock | jsh_material_initial_stock.number | 按仓库列定位，非负有限数；与独立库存台账一致 |
| warehouse | jsh_depot.id → depot_id | 按已配置真实仓库名解析，不硬写跨环境ID |

物料完整27列合同和生成逻辑见 [迁移脚本](../scripts/migrate.py)。期初库存通过商品原生XLS的仓库列一起导入，未采用直接INSERT业务库存表。

## 执行与复核

```powershell
.\.venv\Scripts\python.exe scripts\migrate.py validate
# 新库初始化时执行；已有业务后不反复覆盖期初
.\.venv\Scripts\python.exe scripts\migrate.py import
.\.venv\Scripts\python.exe scripts\sql_verify.py
```

首次资料创建：往来单位最初通过原生 /supplier/add；之后查明原生 importVendor/importCustomer，补充用XLS真实导入两轮，ID和数量均保持3+3，所有映射值SQL核对一致。最终迁移脚本已优先调用原生XLS接口。物料和期初库存首次已通过 /material/importExcel 成功导入，随后角色配置失败不否定此前成功导入的事实，原始成功请求保留于 migration-permission-length-failure.json。

重复保护：往来单位先检查名称和旧编码冲突，再用原生名称+type更新；物料已存在全套FP条码时跳过，部分存在则阻止自动继续，避免覆盖进行中的库存。business_uat.py 检测既有验收单号后拒绝重复运行。

7类负例在源数据内存副本上执行：必填名称、重复编码、负数量、非法数字、日期格式、未知物料、未知仓库，均在修改ERP前拒绝；没有改坏有效台账制造故障经历。

中文保存经原生XLS读回、接口返回、数据库和页面截图验证。服务器 utf8mb4/utf8mb4_unicode_ci，客户端 utf8mb4；PowerShell控制台的编码表现不能替代文件和页面数据判断。另有真实XLS读回渲染预览：[模板截图](../evidence/xls-template-preview.png)、[检查记录](../evidence/xls-template-verification.json)；没有宣称Microsoft Excel GUI验收。

核对SQL见 [reconciliation.sql](../sql/reconciliation.sql)，包含迁移量、库存期初+已审核净变动、单据关联、重复条码/旧编码/单号。最终差异为0，三类重复查询均空。

证据：[migration-precheck.json](../evidence/migration-precheck.json)、[migration-result.json](../evidence/migration-result.json)、[migration-permission-length-failure.json](../evidence/migration-permission-length-failure.json)、[partner-native-import.json](../evidence/partner-native-import.json)、[partner-native-api.json](../evidence/partner-native-api.json)、[migration-validation-tests.json](../evidence/migration-validation-tests.json)、[sql-reconciliation.json](../evidence/sql-reconciliation.json)。
