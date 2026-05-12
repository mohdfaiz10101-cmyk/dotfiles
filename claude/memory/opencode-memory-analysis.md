# OpenCode 记忆和索引问题分析报告

## 1. 边做边记功能状态

### 当前实现
- **macg 记忆工具**：`memory_write()` - 追加内容到 `memory/` 目录
- **Letta MCP**：`macg_letta_store()` - 写入 Letta archival memory
- **自动同步服务**：`opencode-letta-sync.service` - 监控 memory/ 变化 → Letta

### 检测结果
✅ **功能正常**
- `memory_write()` 可正常写入本地 memory 文件
- Letta 记忆可存储（已验证 `letta-search` 返回结果）
- 同步服务已启动并运行

### 问题
❌ **OpenCode 未调用记忆工具**
- 当前会话未触发 `memory_write()` 或 `letta_store()`
- 缺少自动记忆触发机制
- 依赖手动调用，非真正"边做边记"

---

## 2. 社区解决方案调研

### 2.1 opencode-mem 插件（主流方案）
**GitHub**: `tickernelz/opencode-mem`

**功能**：
- 本地向量数据库（SQLite + USearch）
- 自动捕获对话内容
- 智能记忆提取
- Web UI 界面（端口 4747）

**已知问题**（2026-03-29 Issue #73）：
- ❌ OpenCode v1.3.5+ 不兼容
- ❌ 插件 API 变更导致加载失败
- ❌ 静默失败，无错误日志

**根本原因**：
- OpenCode v1.3.x 插件加载契约变更
- `opencode-mem` 仍使用旧 API（默认导出函数）
- 新版本期望 `server()` 入口点

**社区状态**：
- 🔴 活跃维护，等待 PR 合并
- 🟡 临时方案：降级 OpenCode 或修改插件

### 2.2 LanceDB OpenCode Pro（企业级方案）
**GitHub**: `tryweb/lancedb-opencode-pro`

**功能**：
- LanceDB 向量存储
- 混合搜索（向量 + BM25）
- 学习仪表板
- KPI 管道

**已知问题**：
- ⚠️ OpenCode v1.3.8+ NAPI bug（Issue #20623）
- 🔴 需要额外依赖（Ollama 或 OpenAI Embedding）

**社区状态**：
- 🟢 文档完善
- 🟡 依赖复杂度高

### 2.3 DeepWiki MCP 插件（语义索引）
**功能**：
- 语义向量索引
- 知识库查询
- 代码语义理解

**优势**：
- ✅ 避免"每次索引"问题
- ✅ 适合大型项目（100k+ 行）
- ✅ 查询速度快

**适用场景**：
- 大型代码库
- 需要语义理解
- 减少重复索引开销

---

## 3. 最佳实践建议

### 3.1 短期方案（当前环境）
**已实施**：
- ✅ `memory/` 目录 + Letta 双向同步
- ✅ `code-indexer` FTS5 索引
- ✅ `opencode-letta-sync` 守护服务

**需优化**：
- 🟡 添加自动记忆触发（Hook 层）
- 🟡 集成到 OpenCode MCP
- 🟡 测试检索准确性

### 3.2 中期方案（社区成熟）
**推荐**：
1. 等待 `opencode-mem` PR 合并（兼容 OpenCode v1.3.5+）
2. 或降级到 OpenCode v1.3.4

**理由**：
- ✅ 社区活跃维护
- ✅ 功能完整（自动捕获 + 检索）
- ✅ 本地向量数据库，无外部依赖

### 3.3 长期方案（企业级）
**考虑**：
- `lancedb-opencode-pro`（需解决 NAPI bug）
- 自研 MCP 插件（参考 `opencode-mem`）

**理由**：
- ✅ 企业级功能（KPI、仪表板）
- ✅ 混合搜索（向量 + 全文）
- ⚠️ 依赖复杂度高

---

## 4. 当前配置是否最完美？

### 4.1 优势
✅ **成本控制**：
- MCP 从 5 个减至 3 个（-40% 负载）
- 禁用 subagent 描述注入（减少 token）

✅ **容错设计**：
- Letta 不可用时静默失败
- 本地 memory 作为 fallback

✅ **实时同步**：
- inotify 监控 memory/ 变化
- 自动同步到 Letta

### 4.2 不足
❌ **缺少自动记忆**：
- 未集成到 OpenCode Hook 层
- 依赖手动调用工具

❌ **检索未集成**：
- OpenCode 不会主动查询 Letta
- 依赖用户显式调用 `letta-search`

❌ **社区插件不兼容**：
- `opencode-mem` 与 OpenCode v1.3.5+ 不兼容
- 需等待 PR 合并

### 4.3 改进建议

#### 方案 A：集成自动记忆（推荐）
**实现**：
1. 修改 OpenCode Hook 层，在关键操作后自动调用 `memory_write()`
2. 添加检索前置检查：对话开始时查询 Letta 记忆
3. 记忆内容：完成任务、踩坑记录、架构决策

**代码示例**：
```python
# 在 OpenCode Hook 层添加
@opencode_hook("after_task_complete")
def auto_memory(event):
    if event.success:
        content = f"完成: {event.description}\n结果: {event.output}"
        memory_write("lessons-learned.md", content)
        letta_store(content, tags="auto-capture,task-complete")
```

#### 方案 B：使用 DeepWiki MCP（大型项目）
**实现**：
1. 安装 `deepwiki-mcp` 插件
2. 配置语义向量索引
3. 替换 `code-indexer` FTS5

**优势**：
- 语义理解更强
- 适合复杂代码库

#### 方案 C：降级 OpenCode（临时方案）
**实现**：
```bash
opencode upgrade v1.3.4
npm install opencode-mem@latest
```

**风险**：
- ❌ 丢失新功能
- ❌ 安全漏洞

---

## 5. 结论

### 当前状态
**配置评估**：🟡 **基本完善，但有改进空间**

- ✅ 成本优化已完成
- ✅ Letta 双向同步已实现
- ❌ 自动记忆未集成
- ❌ 检索未自动化

### 最优方案
**推荐顺序**：
1. **短期**：实现方案 A（自动记忆 Hook）
2. **中期**：等待 `opencode-mem` 兼容更新
3. **长期**：考虑 `lancedb-opencode-pro`（企业需求）

### 下一步行动
1. 编写 OpenCode Hook 层自动记忆脚本
2. 测试记忆检索准确性
3. 监控 `opencode-mem` PR 进度

---

**报告生成时间**：2026-05-12
**分析工具**：WebSearch + 代码审计
**参考来源**：
- opencode-mem Issue #73
- LanceDB OpenCode Pro 文档
- Facebook Antigravity Google 社区
