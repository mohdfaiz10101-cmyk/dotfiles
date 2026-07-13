# MCP Policy

> Generated: 2026-07-13T13:19:15

| MCP | Kind | Policy | Enabled | Agent | Triggers |
|---|---|---|---:|---|---|
| `baidu-netdisk` | data | on_demand | false | `tech-researcher` | 数据库, sqlite, 查询, 表 |
| `claude-knowledge` | general | on_demand | false | `sisyphus` | claude-knowledge |
| `codegraph` | code-intelligence | core | true | `sisyphus` | 源码, 代码, 函数, 调用链, 重构 |
| `context7` | research-ui | core | true | `tech-researcher` | 网页, 浏览器, 截图, 爬取, 文档, 搜索 |
| `fetch` | research-ui | core | true | `tech-researcher` | 网页, 浏览器, 截图, 爬取, 文档, 搜索 |
| `firecrawl` | research-ui | on_demand | false | `tech-researcher` | 网页, 浏览器, 截图, 爬取, 文档, 搜索 |
| `grep_app` | general | on_demand | false | `sisyphus` | grep_app |
| `haven` | device | on_demand | false | `ops-dispatcher` | 手机, 设备, adb, windows, haven, 平板 |
| `hermes` | general | on_demand | false | `sisyphus` | hermes |
| `ios-connect` | device | on_demand | false | `ops-dispatcher` | 手机, 设备, adb, windows, haven, 平板 |
| `khoj` | memory | on_demand | false | `sisyphus` | 历史, 记忆, 偏好, 以前, 召回 |
| `letta` | memory | core | true | `sisyphus` | 历史, 记忆, 偏好, 以前, 召回 |
| `memory-engine` | memory | core | true | `sisyphus` | 历史, 记忆, 偏好, 以前, 召回 |
| `ntfy` | messaging | on_demand | false | `ops-dispatcher` | 发送, 通知, telegram, wechat, ntfy, 消息 |
| `phone-connect` | device | core | true | `ops-dispatcher` | 手机, 设备, adb, windows, haven, 平板 |
| `playwright` | research-ui | on_demand | false | `tech-researcher` | 网页, 浏览器, 截图, 爬取, 文档, 搜索 |
| `server-memory` | memory | on_demand | false | `sisyphus` | 历史, 记忆, 偏好, 以前, 召回 |
| `sqlite` | data | on_demand | false | `tech-researcher` | 数据库, sqlite, 查询, 表 |
| `sys-info` | general | core | true | `sisyphus` | sys-info |
| `tablet` | device | on_demand | false | `ops-dispatcher` | 手机, 设备, adb, windows, haven, 平板 |
| `vision` | research-ui | on_demand | false | `tech-researcher` | 网页, 浏览器, 截图, 爬取, 文档, 搜索 |
| `wechat` | messaging | on_demand | false | `ops-dispatcher` | 发送, 通知, telegram, wechat, ntfy, 消息 |
| `win` | device | core | true | `ops-dispatcher` | 手机, 设备, adb, windows, haven, 平板 |

## Rules

- New MCPs are classified automatically from name, command, URL, and capability keywords.
- New MCPs default to on-demand behavior until verified.
- Heavy/UI/external-write MCPs should not remain enabled by default.
- Agents should request enabling a disabled MCP only when the task trigger matches.
