---
path: fix://font/cjk-font-songti-sc-default
scope: global
type: fix
status: active
weight: 0.82
hits: 1
misses: 0
trigger: 含中文标签/标题的图出现 "Glyph ... missing from font(s) Times New Roman" 警告
hook: 中文绘图默认字体使用 Songti SC（macOS 系统宋体），与 Times New Roman 同为衬线体；创建时 CONFIG font_family=Songti SC，代码中统一用 style['font_family'] 引用
created: 2026-06-23
updated: 2026-06-23
last_hit: 2026-06-23
evidence_count: 1
superseded_by:
---

## 触发条件
雷达图、柱状图、热力图等任何含中文标签/标题的图使用 Times New Roman 导致 tofu（方框/缺失字形）。

## 做法
1. 创建新图时，CONFIG 中 `style_spec.font_family` 设为 `Songti SC`
2. 所有 `ax.text()` / `set_xticklabels()` / `set_xlabel()` 等 API 中 `fontfamily=style['font_family']`
3. Songti SC 是 macOS 系统自带宋体（衬线），与 Times New Roman 风格匹配，适合论文正文
4. 不要硬编码字体名，始终从 `style['font_family']` 读取

## 为什么不是其他字体
- Heiti SC / PingFang SC：无衬线黑体，与 Times New Roman 混排违和
- Arial Unicode MS：字形偏大、字重偏重，破坏论文版面灰度
- Songti SC：宋体衬线，灰度与 TNR 一致，macOS 默认安装，无需额外下载
