# 上游来源与变更

- 仓库：https://github.com/jishenghua/jshERP
- tag：v3.6；commit：8f28e7c2fe54d54de3621a414f5df1833dc5a55f
- 协议：Apache-2.0；原版权归原作者所有，复制许可证为LICENSE.upstream。
- 后端pom：3.6-SNAPSHOT；前端package：3.5.0；页面V3.6。版本以tag/commit为准。
- 上游源码不复制入交付Git历史，由setup固定获取，保留其独立仓库。
- 唯一源码补丁：[windows-export.patch](deployment/windows-export.patch)，ExcelUtils使用flowpilot.export.dir系统属性，默认/opt不变；本机设置runtime/exports。未改变业务校验或权限逻辑。
- 构建配置：Maven镜像Central；前端锁文件deployment/package-lock.json来自本机实际依赖解析，npm ci --legacy-peer-deps；Node构建设置--openssl-legacy-provider。
- 实施脚本不替代ERP，使用原生API/XLS；SQL主要用于只读核对，初始化安全及隔离恢复另有清晰边界。
