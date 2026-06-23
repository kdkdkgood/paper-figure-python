<!-- 条件读取：仅在需要默认样式/字体/DPI/配色基线时读取此文件 -->

# Global Core Params（Skill 默认参数基线）

以下参数作为 Skill 侧默认基线，优先于一般参考文档；当用户明确切换期刊风格时可按期刊要求覆盖。

## 字体与字号

- `font_family`（默认）: `Times New Roman`
- `xlabel/ylabel`: `10 pt`
- `tick_label`: `8.5 pt`
- `legend`: `8.5 pt`
- `legend_title`: `9.0 pt`
- 图内标题：禁用

## 线条与图例

- `line_width`: `1.2 pt`
- `axes_linewidth`: `0.8 pt`
- `marker_size`: `4.5 pt`
- `legend.handlelength`: `1.8`
- `legend.handletextpad`: `0.5`
- `legend.borderpad`: `0.3`
- `legend.labelspacing`: `0.3`
- `legend.markerscale`: `0.9`

## 输出

- 输出格式：`PNG`
- `dpi(line)=1000`
- `dpi(photo)=600`
- `dpi(combo)=600`

## 坐标轴文本规则

- 轴标签必须带单位（如 `Time (s)`、`Response (a.u.)`）
- 变量斜体、单位正体
- `ylabel pad = 1.8`
- `xlabel pad = 1.8`
- `ytick pad = 3.0`

## 颜色与可读性

- 推荐 Okabe-Ito 色盘
- 禁止仅靠颜色区分系列，必须叠加线型/点型/纹理
