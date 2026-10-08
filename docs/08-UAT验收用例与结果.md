# UAT 验收用例与结果

日期：2026-10-08（Asia/Hong_Kong，个人实验）。范围：本地个人隔离实验，真实原生接口及Edge浏览器，MySQL SQL复核。

已执行19条：17通过、2失败。另列Docker/Linux和干净机器部署阻塞/未执行项，不纳入通过数量。两项后端缺陷尚未修复，生产上线验收不通过。

| 用例 | 业务场景 | 状态 | 证据 |
| --- | --- | --- | --- |
| UAT-01 | 基础资料和期初库存 | 通过 | [migration-result.json](../evidence/migration-result.json)、[stock-01-initial.png](../evidence/stock-01-initial.png) |
| UAT-02 | 采购订单 | 通过 | [business-api.json](../evidence/business-api.json) |
| UAT-03 | 采购入库与审核 | 通过 | [stock-02-purchase-approved.png](../evidence/stock-02-purchase-approved.png)、[business-stock-snapshots.json](../evidence/business-stock-snapshots.json) |
| UAT-04 | 销售订单与出库 | 通过 | [stock-03-sales-approved.png](../evidence/stock-03-sales-approved.png)、[business-api.json](../evidence/business-api.json) |
| UAT-05 | 库存不足 | 通过 | [business-api.json](../evidence/business-api.json) |
| UAT-06 | 同号重复提交 | 通过 | [business-api.json](../evidence/business-api.json) |
| UAT-07 | 必填仓库校验 | 通过 | [business-api.json](../evidence/business-api.json) |
| UAT-08 | 接口负数量校验 | 失败 | [business-api.json](../evidence/business-api.json) |
| UAT-09 | 反审核与重新审核 | 通过 | [business-api.json](../evidence/business-api.json) |
| UAT-10 | 单据和库存一致性 | 通过 | [business-ledger.json](../evidence/business-ledger.json) |
| UAT-11-fp_manager | 岗位菜单权限 fp_manager | 通过 | [role-fp_manager.png](../evidence/role-fp_manager.png)、[permissions-api.json](../evidence/permissions-api.json) |
| UAT-11-fp_purchase | 岗位菜单权限 fp_purchase | 通过 | [role-fp_purchase.png](../evidence/role-fp_purchase.png)、[permissions-api.json](../evidence/permissions-api.json) |
| UAT-11-fp_warehouse | 岗位菜单权限 fp_warehouse | 通过 | [role-fp_warehouse.png](../evidence/role-fp_warehouse.png)、[permissions-api.json](../evidence/permissions-api.json) |
| UAT-11-fp_sales | 岗位菜单权限 fp_sales | 通过 | [role-fp_sales.png](../evidence/role-fp_sales.png)、[permissions-api.json](../evidence/permissions-api.json) |
| UAT-12 | 销售岗位调用采购写入接口 | 失败 | [permissions-api.json](../evidence/permissions-api.json)、[defect-cross-role-draft.png](../evidence/defect-cross-role-draft.png) |
| UAT-13 | 立即重复提交 | 通过 | [permissions-api.json](../evidence/permissions-api.json) |
| UAT-14 | 真实页面编辑中文供应商联系人 | 通过 | [gui-vendor-edit-dialog.png](../evidence/gui-vendor-edit-dialog.png)、[gui-vendor-edited.png](../evidence/gui-vendor-edited.png)、[gui-operation-api.json](../evidence/gui-operation-api.json) |
| UAT-15-0 | 页面销售出库反审核 | 通过 | [gui-sale-status-0.png](../evidence/gui-sale-status-0.png)、[gui-operation-api.json](../evidence/gui-operation-api.json) |
| UAT-15-1 | 页面销售出库审核 | 通过 | [gui-sale-status-1.png](../evidence/gui-sale-status-1.png)、[gui-operation-api.json](../evidence/gui-operation-api.json) |

## UAT-01 基础资料和期初库存

- 前置条件：基础数据已迁移；启用强制审核，关闭负库存。
- 操作步骤：读取真实基础资料接口、查询SQL、在库存页面筛选仓库与物料。
- 预期结果：6个往来单位、6个物料；原料仓支架50件。
- 实际结果：{"partners": 6, "materials": 6, "raw_stock": "50.000000"}
- 执行状态：**通过**；时间：2026-10-08T16:38:36.018031+08:00。
- 关联证据：[migration-result.json](../evidence/migration-result.json)、[stock-01-initial.png](../evidence/stock-01-initial.png)。

## UAT-02 采购订单

- 前置条件：基础数据已迁移；启用强制审核，关闭负库存。
- 操作步骤：采购账号保存采购订单120件并审核。
- 预期结果：订单审核后不改变库存。
- 实际结果：{"order": [{"id": 277, "number": "FP-UAT-20261008-PO", "type": "其它", "sub_type": "采购订单", "status": "1", "purchase_status": "0", "creator": 147, "link_number": "", "total_price": "-8160.000000"}], "stock": "50.000000"}
- 执行状态：**通过**；时间：2026-10-08T16:38:37.885370+08:00。
- 关联证据：[business-api.json](../evidence/business-api.json)。

## UAT-03 采购入库与审核

- 前置条件：基础数据已迁移；启用强制审核，关闭负库存。
- 操作步骤：按采购订单关联保存采购入库，审核，在页面和SQL核实。
- 预期结果：草稿不计库存；审核后50+120=170。
- 实际结果：{"pending_stock": "50.000000", "approved_stock": "170.000000", "document": [{"id": 278, "number": "FP-UAT-20261008-PI", "type": "入库", "sub_type": "采购", "status": "1", "purchase_status": "0", "creator": 147, "link_number": "FP-UAT-20261008-PO", "total_price": "-8160.000000"}], "browser_cells": ["1", "流水分布", "FP-MAT-001", "FlowPilot制动支架", "BRK-01", "", "", "", "", "件", "68", "50", "170", "11560", "0"]}
- 执行状态：**通过**；时间：2026-10-08T16:38:43.101099+08:00。
- 关联证据：[stock-02-purchase-approved.png](../evidence/stock-02-purchase-approved.png)、[business-stock-snapshots.json](../evidence/business-stock-snapshots.json)。

## UAT-04 销售订单与出库

- 前置条件：基础数据已迁移；启用强制审核，关闭负库存。
- 操作步骤：销售账号保存销售订单30件并审核，关联出库并审核，页面和SQL核实。
- 预期结果：170-30=140件；单据关联完整。
- 实际结果：{"stock": "140.000000", "order": [{"id": 279, "number": "FP-UAT-20261008-SO", "type": "其它", "sub_type": "销售订单", "status": "2", "purchase_status": "0", "creator": 149, "link_number": "", "total_price": "2850.000000"}], "outbound": [{"id": 280, "number": "FP-UAT-20261008-SI", "type": "出库", "sub_type": "销售", "status": "1", "purchase_status": "0", "creator": 149, "link_number": "FP-UAT-20261008-SO", "total_price": "2850.000000"}], "browser_cells": ["1", "流水分布", "FP-MAT-001", "FlowPilot制动支架", "BRK-01", "", "", "", "", "件", "68", "50", "140", "9520",……完整返回见关联JSON。
- 执行状态：**通过**；时间：2026-10-08T16:38:50.032220+08:00。
- 关联证据：[stock-03-sales-approved.png](../evidence/stock-03-sales-approved.png)、[business-api.json](../evidence/business-api.json)。

## UAT-05 库存不足

- 前置条件：基础数据已迁移；启用强制审核，关闭负库存。
- 操作步骤：销售账号尝试141件出库，SQL查询头表和库存。
- 预期结果：141件出库被拒绝；整单事务回滚，库存仍140。
- 实际结果：{"response": {"code": 8000004, "data": {"message": "商品:FlowPilot制动支架-FP-MAT-001库存不足"}}, "bill_count": 0, "stock": "140.000000"}
- 执行状态：**通过**；时间：2026-10-08T16:38:50.107741+08:00。
- 关联证据：[business-api.json](../evidence/business-api.json)。

## UAT-06 同号重复提交

- 前置条件：基础数据已迁移；启用强制审核，关闭负库存。
- 操作步骤：重放已成功采购入库的相同请求。
- 预期结果：拒绝同号单据，仅1个采购入库头、库存保持140。
- 实际结果：{"response": {"code": 8500022, "data": {"message": "抱歉，单据编号已经存在"}}, "count": 1, "stock": "140.000000"}
- 执行状态：**通过**；时间：2026-10-08T16:38:52.283282+08:00。
- 关联证据：[business-api.json](../evidence/business-api.json)。

## UAT-07 必填仓库校验

- 前置条件：基础数据已迁移；启用强制审核，关闭负库存。
- 操作步骤：用原生接口提交缺少仓库的销售出库。
- 预期结果：缺少仓库被拒绝，头表回滚。
- 实际结果：{"response": {"code": 8500004, "data": {"message": "仓库不能为空"}}, "bill_count": 0}
- 执行状态：**通过**；时间：2026-10-08T16:38:52.377154+08:00。
- 关联证据：[business-api.json](../evidence/business-api.json)。

## UAT-08 接口负数量校验

- 前置条件：基础数据已迁移；启用强制审核，关闭负库存。
- 操作步骤：提交-1件的未审核测试单；如果原生接口接受，保留证据并仅清理该测试草稿。
- 预期结果：出库数量必须大于0；服务端拒绝负数。
- 实际结果：-1件销售未审核草稿被接受，已清理，库存140；服务端数量校验未满足预期。
- 执行状态：**失败**；时间：2026-10-08T16:38:55.933544+08:00。
- 关联证据：[business-api.json](../evidence/business-api.json)。

## UAT-09 反审核与重新审核

- 前置条件：基础数据已迁移；启用强制审核，关闭负库存。
- 操作步骤：通过原生batchSetStatus反审核销售出库，再审核。
- 预期结果：销售反审核库存恢复170，再审核回到140。
- 实际结果：{"unapprove": {"code": 200, "data": {"message": "成功"}}, "stock_unapproved": "170.000000", "reapprove": {"code": 200, "data": {"message": "成功"}}, "stock_reapproved": "140.000000"}
- 执行状态：**通过**；时间：2026-10-08T16:38:59.399476+08:00。
- 关联证据：[business-api.json](../evidence/business-api.json)。

## UAT-10 单据和库存一致性

- 前置条件：基础数据已迁移；启用强制审核，关闭负库存。
- 操作步骤：SQL核对头表、行表、状态、关联单号、库存。
- 预期结果：4张有效主业务单据，订单完成，采购120销售30，原料仓140。
- 实际结果：{"ledger": [{"number": "FP-UAT-20261008-PO", "type": "其它", "sub_type": "采购订单", "status": "2", "creator": 147, "link_number": "", "oper_number": "120.000000", "basic_number": "120.000000", "depot_id": null, "link_id": null}, {"number": "FP-UAT-20261008-PI", "type": "入库", "sub_type": "采购", "status": "1", "creator": 147, "link_number": "FP-UAT-20261008-PO", "oper_number": "120.000000", "basic_number": "120.000000", "depot_id": 19, "link_id": 334}, {"number": "FP-UAT-20261008-SO", "type": "其它", "sub_type": "销售订单", "status": "2", "creator": 149, "li……完整返回见关联JSON。
- 执行状态：**通过**；时间：2026-10-08T16:38:59.461661+08:00。
- 关联证据：[business-ledger.json](../evidence/business-ledger.json)。

## UAT-11-fp_manager 岗位菜单权限 fp_manager

- 前置条件：原生角色和用户关系已配置。
- 操作步骤：使用岗位账号真实浏览器登录，读取原生菜单接口。
- 预期结果：采购、销售、仓库菜单按岗位可见。
- 实际结果：{"paths": ["/dashboard/analysis", "/billC", "/bill/retail_out", "/bill/retail_back", "/bill", "/bill/purchase_apply", "/bill/purchase_order", "/bill/purchase_in", "/bill/purchase_back", "/billB", "/bill/sale_order", "/bill/sale_out", "/bill/sale_back", "/billD", "/bill/other_in", "/bill/other_out", "/bill/allocation_out", "/bill/assemble", "/bill/disassemble", "/financial", "/financial/item_in", "/financial/item_out", "/financial/money_in", "/financial/money_out", "/financial/giro", "/financial/advance_in", "/report", "/report/material_stock", ……完整返回见关联JSON。
- 执行状态：**通过**；时间：2026-10-08T16:43:14.530254+08:00。
- 关联证据：[role-fp_manager.png](../evidence/role-fp_manager.png)、[permissions-api.json](../evidence/permissions-api.json)。

## UAT-11-fp_purchase 岗位菜单权限 fp_purchase

- 前置条件：原生角色和用户关系已配置。
- 操作步骤：使用岗位账号真实浏览器登录，读取原生菜单接口。
- 预期结果：采购、销售、仓库菜单按岗位可见。
- 实际结果：{"paths": ["/dashboard/analysis", "/bill", "/bill/purchase_order", "/bill/purchase_in", "/report", "/report/material_stock", "/material", "/material/material", "/systemA", "/system/vendor"], "visible_text": "管伊佳ERP\n首页\n采购管理\n报表查询\n商品管理\n基础资料\nFlowPilot汽车零部件有限公司（虚构演示企业）\n欢迎您，FlowPilot采购员 退出登录\n首页\n今日销售\n\n￥2850\n\n今日零售\n\n￥0\n\n今日采购\n\n￥8160\n\n本月累计销售\n\n￥2850\n\n本月累计零售\n\n￥0\n\n本月累计采购\n\n￥8160\n\n昨日销售\n\n￥0\n\n昨日零售\n\n￥0\n\n昨日采购\n\n￥0\n\n今年累计销售\n\n￥2850\n\n今年累计零售\n\n￥0\n\n今年累计采购\n\n￥8160\n\n销售统计\n零售统计\n采购统计\n© 2015-2030 管伊佳ERP V3.6\n服务到期：2099-……完整返回见关联JSON。
- 执行状态：**通过**；时间：2026-10-08T16:43:18.275107+08:00。
- 关联证据：[role-fp_purchase.png](../evidence/role-fp_purchase.png)、[permissions-api.json](../evidence/permissions-api.json)。

## UAT-11-fp_warehouse 岗位菜单权限 fp_warehouse

- 前置条件：原生角色和用户关系已配置。
- 操作步骤：使用岗位账号真实浏览器登录，读取原生菜单接口。
- 预期结果：采购、销售、仓库菜单按岗位可见。
- 实际结果：{"paths": ["/dashboard/analysis", "/billD", "/bill/other_in", "/bill/other_out", "/report", "/report/material_stock", "/report/in_detail", "/report/out_detail", "/material", "/material/material"], "visible_text": "管伊佳ERP\n首页\n仓库管理\n报表查询\n商品管理\nFlowPilot汽车零部件有限公司（虚构演示企业）\n欢迎您，FlowPilot仓库员 退出登录\n首页\n今日销售\n\n￥2850\n\n今日零售\n\n￥0\n\n今日采购\n\n￥8160\n\n本月累计销售\n\n￥2850\n\n本月累计零售\n\n￥0\n\n本月累计采购\n\n￥8160\n\n昨日销售\n\n￥0\n\n昨日零售\n\n￥0\n\n昨日采购\n\n￥0\n\n今年累计销售\n\n￥2850\n\n今年累计零售\n\n￥0\n\n今年累计采购\n\n￥8160\n\n销售统计\n零售统计\n采购统计\n© 2015-2030 管伊佳ERP V3.6\n服务到期：2099-……完整返回见关联JSON。
- 执行状态：**通过**；时间：2026-10-08T16:43:22.388822+08:00。
- 关联证据：[role-fp_warehouse.png](../evidence/role-fp_warehouse.png)、[permissions-api.json](../evidence/permissions-api.json)。

## UAT-11-fp_sales 岗位菜单权限 fp_sales

- 前置条件：原生角色和用户关系已配置。
- 操作步骤：使用岗位账号真实浏览器登录，读取原生菜单接口。
- 预期结果：采购、销售、仓库菜单按岗位可见。
- 实际结果：{"paths": ["/dashboard/analysis", "/billB", "/bill/sale_order", "/bill/sale_out", "/report", "/report/material_stock", "/material", "/material/material", "/systemA", "/system/customer"], "visible_text": "管伊佳ERP\n首页\n销售管理\n报表查询\n商品管理\n基础资料\nFlowPilot汽车零部件有限公司（虚构演示企业）\n欢迎您，FlowPilot销售员 退出登录\n首页\n今日销售\n\n￥2850\n\n今日零售\n\n￥0\n\n今日采购\n\n￥8160\n\n本月累计销售\n\n￥2850\n\n本月累计零售\n\n￥0\n\n本月累计采购\n\n￥8160\n\n昨日销售\n\n￥0\n\n昨日零售\n\n￥0\n\n昨日采购\n\n￥0\n\n今年累计销售\n\n￥2850\n\n今年累计零售\n\n￥0\n\n今年累计采购\n\n￥8160\n\n销售统计\n零售统计\n采购统计\n© 2015-2030 管伊佳ERP V3.6\n服务到期：2099-02-1……完整返回见关联JSON。
- 执行状态：**通过**；时间：2026-10-08T16:43:26.106385+08:00。
- 关联证据：[role-fp_sales.png](../evidence/role-fp_sales.png)、[permissions-api.json](../evidence/permissions-api.json)。

## UAT-12 销售岗位调用采购写入接口

- 前置条件：fp_sales没有采购菜单和采购按钮。
- 操作步骤：销售账号直接提交采购订单1件，查询SQL并截图；仅清理本测试草稿。
- 预期结果：后端拒绝未经授权的采购写入。
- 实际结果：销售账号创建采购订单草稿成功，creator149；菜单没有采购功能，后端仍允许写入。已清理，库存140。
- 执行状态：**失败**；时间：2026-10-08T16:43:31.062302+08:00。
- 关联证据：[permissions-api.json](../evidence/permissions-api.json)、[defect-cross-role-draft.png](../evidence/defect-cross-role-draft.png)。

## UAT-13 立即重复提交

- 前置条件：成功保存本测试销售订单，Redis防重复TTL为2秒。
- 操作步骤：立即重放相同请求，SQL核对仅一个头；清理本测试草稿。
- 预期结果：Redis防重复拒绝第二次提交。
- 实际结果：{"first": {"msg": "操作成功", "code": 200}, "second": {"code": 8500032, "data": {"message": "抱歉，请不要频繁提交单据"}}, "count": 1, "cleanup": {"code": 200, "data": {"message": "成功"}}}
- 执行状态：**通过**；时间：2026-10-08T16:43:36.477171+08:00。
- 关联证据：[permissions-api.json](../evidence/permissions-api.json)。

## UAT-14 真实页面编辑中文供应商联系人

- 前置条件：fp_manager真实登录且拥有基础资料编辑按钮。
- 操作步骤：供应商页面查询旧编码对应名称，点击编辑，修改联系人并保存，SQL核对。
- 预期结果：原记录联系人更新，ID和旧编码保留。
- 实际结果：{"before": {"id": 90, "supplier": "FlowPilot精密钢材供应商（虚构）", "contacts": "供应联系人甲（页面验收）", "description": "legacy-code:SUP-FP-001"}, "after": {"id": 90, "supplier": "FlowPilot精密钢材供应商（虚构）", "contacts": "供应联系人甲（页面验收）", "description": "legacy-code:SUP-FP-001"}}
- 执行状态：**通过**；时间：2026-10-08T16:53:12.916797+08:00。
- 关联证据：[gui-vendor-edit-dialog.png](../evidence/gui-vendor-edit-dialog.png)、[gui-vendor-edited.png](../evidence/gui-vendor-edited.png)、[gui-operation-api.json](../evidence/gui-operation-api.json)。

## UAT-15-0 页面销售出库反审核

- 前置条件：已保存真实销售出库30件。
- 操作步骤：销售出库页面按单号查询，勾选，点击反审核并确认，SQL核对。
- 预期结果：状态0，原料仓170件。
- 实际结果：{"document": [{"id": 280, "number": "FP-UAT-20261008-SI", "type": "出库", "sub_type": "销售", "status": "0", "purchase_status": "0", "creator": 149, "link_number": "FP-UAT-20261008-SO", "total_price": "2850.000000"}], "stock": "170.000000"}
- 执行状态：**通过**；时间：2026-10-08T16:53:14.004899+08:00。
- 关联证据：[gui-sale-status-0.png](../evidence/gui-sale-status-0.png)、[gui-operation-api.json](../evidence/gui-operation-api.json)。

## UAT-15-1 页面销售出库审核

- 前置条件：已保存真实销售出库30件。
- 操作步骤：销售出库页面按单号查询，勾选，点击审核并确认，SQL核对。
- 预期结果：状态1，原料仓140件。
- 实际结果：{"document": [{"id": 280, "number": "FP-UAT-20261008-SI", "type": "出库", "sub_type": "销售", "status": "1", "purchase_status": "0", "creator": 149, "link_number": "FP-UAT-20261008-SO", "total_price": "2850.000000"}], "stock": "140.000000"}
- 执行状态：**通过**；时间：2026-10-08T16:54:14.567882+08:00。
- 关联证据：[gui-sale-status-1.png](../evidence/gui-sale-status-1.png)、[gui-operation-api.json](../evidence/gui-operation-api.json)。

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
