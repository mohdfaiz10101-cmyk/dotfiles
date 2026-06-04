- [ ] [OP] [2026-06-04 06:18] AI配置告警(自愈失败): 🔴 AGENTS.md 处理后仍缺: FALSE_POSITIVE_GUARD 只能由 CC dev.*模式

### [SELF-IMPROVE 2026-06-04] GLM 自动代码审查
- [ ] [SELF-IMPROVE] brain.py: TokenBucket类的status方法缺失右括号导致语法错误，且类末尾代码不完整需补全。
- [ ] [SELF-IMPROVE] think.py: 截断的SYSTEM_P变量及缺失的模块导出与核心调用逻辑，导致文件不完整且无法实际运行。
- [ ] [SELF-IMPROVE] kanban.html: 修复截断的CSS代码（`.wip-bar`的`background`属性不完整），确保样式正常渲染。
- [ ] [SELF-IMPROVE] launcher-server.py: `translate_path` 方法未完整实现目录遍历防御，且存在命令注入风险，应在启动进程时严格使用参数列表而非拼接字符串，并补全路径校验逻辑。
- [ ] [SELF-IMPROVE] hub-api.py: 存在SQL注入风险，应将f-string拼接的SQL语句改为参数化查询，并将表名通过白名单校验后再动态插入。
- [x] [2026-06-04 13:30] Termix 外部访问修复 — ENABLE_SSL=false + socat 9443→9080 + FRP 链路通过
