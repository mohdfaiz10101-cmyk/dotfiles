---
name: ai-office-control
description: "AI文档控制：openpyxl/python-docx CLI操作 + LibreOffice GUI预览，office-agent:9810 + CLI模式"
user-invocable: false
version: "2.1.0"
category: productivity
tags: [libreoffice, docx, xlsx, openpyxl, python-docx, cli, office]
effort: medium
created: 2026-04-22
updated: 2026-04-25
---

# AI Office Control (v2.1)

## 概述
office-agent.py — AI 文档控制引擎，支持 .docx/.xlsx/.odt/.ods
- **HTTP 模式**: POST :9810/command（自然语言→GLM意图→执行）
- **CLI 模式**: `python3 ~/hub/office-agent.py --cli "指令"`
- **预览模式**: xdg-open → LibreOffice GUI

## API 端点
| 端点 | 方法 | 说明 |
|------|------|------|
| /health | GET | 服务状态+版本 |
| /command | POST | 自然语言指令执行 |
| /execute | POST | 直接执行已解析的 intent JSON |
| /current-file | GET | 获取当前文件路径 |
| /set-file | POST | 设置当前文件 |
| /history | GET | 操作历史 |

## 支持的 action

### Writer (.docx)
| action | 参数 | 说明 |
|--------|------|------|
| bold/italic/underline | target, all/last/paragraph_N | 格式化段落 |
| font_size | target, size | 字体大小(磅) |
| color | target, color(十六进制) | 字体颜色 |
| set_align | target, align | 对齐(left/center/right/justify) |
| set_line_spacing | target, spacing | 行间距(倍数) |
| insert_text | content | 末尾插入文字 |
| insert_table | rows, cols | 插入表格 |
| find_replace | find, replace | 查找替换 |
| delete_paragraph | target | 删除段落 |
| set_heading | target, level(1-6) | 设置标题级别 |
| add_paragraph | content | 新增段落 |
| get_content | - | 获取全文 |
| page_break | - | 插入分页符 |
| **insert_image** | image_path, width(cm), height(cm) | 插入图片 |
| **header_footer** | header, footer | 设置页眉页脚 |
| export_pdf | path | 导出PDF |
| save | - | 保存 |
| open | filepath | LibreOffice打开预览 |
| new_doc | filepath | 新建文档 |

### Calc (.xlsx)
| action | 参数 | 说明 |
|--------|------|------|
| read_cell | sheet, cell | 读取单元格 |
| write_cell | sheet, cell, value | 写入单元格 |
| write_row | sheet, row, values | 写入一行 |
| get_sheet_summary | - | 获取表格摘要 |
| **read_range** | range("A1:C5") | 读取范围 |
| **find_replace** | find, replace | 查找替换 |
| **batch_write** | cells=[{cell,value}] | 批量写入 |
| **delete_row** | row | 删除行 |
| **insert_row** | row, values | 插入行 |
| **format_cell** | cell, format, bold, color, size | 格式化单元格 |
| **auto_fit** | - | 自动调整列宽 |

### CLI 用法
```bash
# 直接执行指令（无需HTTP）
python3 ~/hub/office-agent.py --cli "打开 ~/Desktop/report.xlsx"
python3 ~/hub/office-agent.py --cli "A1写入Hello"
python3 ~/hub/office-agent.py --cli "读取A1到C5"

# 管道输入
echo "B2写入100" | python3 ~/hub/office-agent.py --cli

# HTTP 模式（默认）
python3 ~/hub/office-agent.py
```

## 架构
```
用户指令 → GLM CLI意图解析 → openpyxl/python-docx执行 → 保存
                                                  ↓
                                          notify-send 通知
                                                  ↓
                                         LibreOffice GUI 自动检测变更
```

## 注意事项
- 意图解析用 GLM CLI（`/home/charlie/.local/bin/glm`），不走 LiteLLM
- 修改文件后自动 notify-send 桌面通知
- LibreOffice 需手动打开文件预览，修改后 LO 自动检测磁盘变更
