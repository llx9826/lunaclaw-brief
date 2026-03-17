"""LunaClaw Brief — Markdown → Structured Section Parser

Converts raw Markdown (from LLM) into a list of section dicts that
Jinja2 templates can render with icons, CSS classes, and HTML content.

Supports the unified Markdown Schema:
  ## Section Title  →  section boundary
  ### N. Item Title →  numbered item card
  **Label**：text   →  key-value row (.kv-row)
  **🦞 Claw 锐评**  →  claw review card
  - item            →  bullet list
  everything else   →  paragraph
"""

import re


SECTION_STYLES = {
    # Tech sections
    "核心结论": {"css_class": "section-core", "icon": "💡", "gradient": "from-amber-400 to-orange-500"},
    "重点事件": {"css_class": "section-events", "icon": "🔥", "gradient": "from-blue-400 to-indigo-500"},
    "开源项目": {"css_class": "section-projects", "icon": "🚀", "gradient": "from-green-400 to-emerald-500"},
    "论文推荐": {"css_class": "section-papers", "icon": "📄", "gradient": "from-cyan-400 to-blue-500"},
    "论文": {"css_class": "section-papers", "icon": "📄", "gradient": "from-cyan-400 to-blue-500"},
    "趋势分析": {"css_class": "section-trends", "icon": "📈", "gradient": "from-purple-400 to-pink-500"},
    "趋势": {"css_class": "section-trends", "icon": "📈", "gradient": "from-purple-400 to-pink-500"},
    "复盘": {"css_class": "section-review", "icon": "🦞", "gradient": "from-orange-400 to-red-500"},
    "Claw 复盘": {"css_class": "section-review", "icon": "🦞", "gradient": "from-orange-400 to-red-500"},
    "今日必看": {"css_class": "section-core", "icon": "⚡", "gradient": "from-amber-400 to-orange-500"},
    "快评": {"css_class": "section-review", "icon": "🦞", "gradient": "from-orange-400 to-red-500"},
    # Finance sections
    "核心判断": {"css_class": "section-core", "icon": "🎯", "gradient": "from-amber-400 to-orange-500"},
    "市场核心判断": {"css_class": "section-core", "icon": "🎯", "gradient": "from-amber-400 to-orange-500"},
    "宏观": {"css_class": "section-finance-macro", "icon": "🏛️", "gradient": "from-blue-400 to-indigo-500"},
    "政策": {"css_class": "section-finance-macro", "icon": "🏛️", "gradient": "from-blue-400 to-indigo-500"},
    "行业热点": {"css_class": "section-events", "icon": "🔥", "gradient": "from-orange-400 to-red-500"},
    "公司事件": {"css_class": "section-events", "icon": "🏢", "gradient": "from-orange-400 to-red-500"},
    "科技": {"css_class": "section-projects", "icon": "💻", "gradient": "from-cyan-400 to-blue-500"},
    "金融交叉": {"css_class": "section-projects", "icon": "💻", "gradient": "from-cyan-400 to-blue-500"},
    "投资策略": {"css_class": "section-finance-strategy", "icon": "📊", "gradient": "from-green-400 to-emerald-500"},
    "策略建议": {"css_class": "section-finance-strategy", "icon": "📊", "gradient": "from-green-400 to-emerald-500"},
    "风险提示": {"css_class": "section-finance-risk", "icon": "⚠️", "gradient": "from-red-400 to-rose-500"},
    "Claw 风险": {"css_class": "section-finance-risk", "icon": "🦞", "gradient": "from-red-400 to-rose-500"},
    "市场要闻": {"css_class": "section-core", "icon": "📰", "gradient": "from-amber-400 to-orange-500"},
    "投资信号": {"css_class": "section-finance-strategy", "icon": "📡", "gradient": "from-green-400 to-emerald-500"},
    # Stock market sections
    "A 股": {"css_class": "section-core", "icon": "🇨🇳", "gradient": "from-red-400 to-rose-500"},
    "A股": {"css_class": "section-core", "icon": "🇨🇳", "gradient": "from-red-400 to-rose-500"},
    "大盘走势": {"css_class": "section-core", "icon": "📈", "gradient": "from-blue-400 to-indigo-500"},
    "港股": {"css_class": "section-core", "icon": "🇭🇰", "gradient": "from-red-400 to-pink-500"},
    "美股": {"css_class": "section-core", "icon": "🇺🇸", "gradient": "from-blue-400 to-indigo-500"},
    "板块": {"css_class": "section-events", "icon": "🔥", "gradient": "from-orange-400 to-red-500"},
    "个股": {"css_class": "section-events", "icon": "📈", "gradient": "from-green-400 to-emerald-500"},
    "热门": {"css_class": "section-events", "icon": "🔥", "gradient": "from-orange-400 to-red-500"},
    "资金面": {"css_class": "section-finance-macro", "icon": "💰", "gradient": "from-amber-400 to-yellow-500"},
    "资金流": {"css_class": "section-finance-macro", "icon": "💰", "gradient": "from-amber-400 to-yellow-500"},
    "情绪": {"css_class": "section-finance-macro", "icon": "🌡️", "gradient": "from-purple-400 to-pink-500"},
    "跨市场": {"css_class": "section-projects", "icon": "🔄", "gradient": "from-cyan-400 to-blue-500"},
    "联动": {"css_class": "section-projects", "icon": "🔄", "gradient": "from-cyan-400 to-blue-500"},
    "科技巨头": {"css_class": "section-events", "icon": "💻", "gradient": "from-cyan-400 to-blue-500"},
    "热点个股": {"css_class": "section-events", "icon": "🔥", "gradient": "from-orange-400 to-red-500"},
    "新股": {"css_class": "section-events", "icon": "🆕", "gradient": "from-green-400 to-teal-500"},
    "异动": {"css_class": "section-finance-risk", "icon": "⚡", "gradient": "from-yellow-400 to-orange-500"},
    "IPO": {"css_class": "section-events", "icon": "🆕", "gradient": "from-green-400 to-teal-500"},
    "Claw 策略": {"css_class": "section-finance-risk", "icon": "🦞", "gradient": "from-orange-400 to-red-500"},
}

DEFAULT_STYLE = {"css_class": "section-default", "icon": "📝", "gradient": "from-gray-400 to-gray-500"}

# Pattern to match **Label**：text or **Label**: text (Chinese/English colon)
_KV_PATTERN = re.compile(r"^\*\*(.+?)\*\*\s*[:：]\s*(.+)")
_CLAW_START = re.compile(r"\*\*🦞\s*Claw\s*(锐评|风险)")
_CLAW_FULL = re.compile(r"\*\*🦞\s*Claw\s*(?:锐评|风险提示?)\*\*\s*[:：]?\s*(.*)")
_NUM_HEADING = re.compile(r"^(\d+)\.\s*(.*)")


def parse_sections(markdown: str) -> list[dict]:
    """Split Markdown on ## headings into section list."""
    sections: list[dict] = []
    lines = markdown.split("\n")
    current_title = None
    content_lines: list[str] = []

    for line in lines:
        if line.startswith("## "):
            if current_title:
                sections.append(_make_section(current_title, content_lines))
            raw_title = line[3:].strip()
            raw_title = re.sub(r"\*\*", "", raw_title)
            raw_title = re.sub(r"🦞\s*", "", raw_title)
            current_title = raw_title.strip()
            content_lines = []
        elif line.strip() or content_lines:
            content_lines.append(line)

    if current_title:
        sections.append(_make_section(current_title, content_lines))

    return sections


def _make_section(title: str, content_lines: list[str]) -> dict:
    style = _match_style(title)
    content_html = _render_content("\n".join(content_lines))
    return {"title": title, "content": content_html, **style}


def _match_style(title: str) -> dict:
    clean = title.strip()
    for keyword, style in SECTION_STYLES.items():
        if keyword in clean:
            return style
    return DEFAULT_STYLE


def _render_content(content: str) -> str:
    """Convert Markdown content block to HTML."""
    content = re.sub(r"(?:^|\n+)---+\s*(?:\n|$)", "\n\n", content)

    if "### " in content:
        blocks = re.split(r"\n+(?=### )", content.strip())
        parts = []
        for b in blocks:
            b = b.strip()
            if not b:
                continue
            if b.startswith("### "):
                parts.append(_render_block(b))
            else:
                parts.append(_render_block(b))
        return "\n".join(parts)
    return _render_block(content.strip())


def _render_block(content: str) -> str:
    lines = content.split("\n")
    html: list[str] = []
    in_claw = False
    claw_lines: list[str] = []
    in_item_block = False
    i = 0

    while i < len(lines):
        stripped = lines[i].strip()
        clean = _strip_list_marker(stripped)

        # ### heading → item block
        if stripped.startswith("### "):
            if in_claw:
                _flush_claw(html, claw_lines)
                in_claw = False
                claw_lines = []
            if in_item_block:
                html.append("</div>")
            h3_text = stripped[4:]
            num_html = ""
            m_num = _NUM_HEADING.match(h3_text)
            if m_num:
                num_html = f'<div class="item-num">{int(m_num.group(1)):02d}</div>'
                h3_text = m_num.group(2)
            html.append(f'<div class="item-block">{num_html}<h3>{h3_text}</h3>')
            in_item_block = True
            i += 1
            continue

        # #### sub-heading
        if stripped.startswith("#### "):
            html.append(f"<h4>{stripped[5:]}</h4>")
            i += 1
            continue

        # Claw review start
        if _CLAW_START.match(clean):
            if in_claw:
                _flush_claw(html, claw_lines)
            in_claw = True
            claw_lines = []
            m = _CLAW_FULL.match(clean)
            if m and m.group(1).strip():
                claw_lines.append(m.group(1).strip())
            i += 1
            continue

        # Inside claw review — keep collecting until a structural break
        if in_claw:
            if stripped.startswith("### ") or stripped.startswith("## "):
                _flush_claw(html, claw_lines)
                in_claw = False
                claw_lines = []
                continue

            # Blank line: look ahead to see if next non-blank line is still review text
            if not stripped:
                next_idx = i + 1
                while next_idx < len(lines) and not lines[next_idx].strip():
                    next_idx += 1
                if next_idx < len(lines):
                    next_line = lines[next_idx].strip()
                    next_clean = _strip_list_marker(next_line)
                    is_structural = (
                        next_line.startswith("### ")
                        or next_line.startswith("## ")
                        or _KV_PATTERN.match(next_clean)
                        or _CLAW_START.match(next_clean)
                        or (next_line.startswith("| ") and "|" in next_line[1:])
                    )
                    if is_structural:
                        _flush_claw(html, claw_lines)
                        in_claw = False
                        claw_lines = []
                        i += 1
                        continue
                # Not a structural break — continue collecting as same Claw block
                i += 1
                continue

            if clean:
                claw_lines.append(clean)
            i += 1
            continue

        # **Label**：text → key-value row
        kv_match = _KV_PATTERN.match(clean)
        if kv_match:
            label = kv_match.group(1)
            value = kv_match.group(2).strip()
            # Skip if label looks like a Claw review (already handled above)
            if "🦞" not in label:
                html.append(
                    f'<div class="kv-row"><span class="kv-label">{_inline(label)}</span>'
                    f'<span class="kv-value">{_inline(value)}</span></div>'
                )
                i += 1
                continue

        # Markdown table (| col | col |)
        if stripped.startswith("|") and "|" in stripped[1:]:
            table_lines = [stripped]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("|"):
                table_lines.append(lines[i].strip())
                i += 1
            html.append(_render_table(table_lines))
            continue

        # Dash-style list items
        if stripped.startswith("- ") and not stripped.startswith("---"):
            list_items = [stripped[2:]]
            i += 1
            while i < len(lines) and lines[i].strip().startswith("- "):
                list_items.append(lines[i].strip()[2:])
                i += 1
            html.append("<ul>" + "".join(f"<li>{_inline(li)}</li>" for li in list_items) + "</ul>")
            continue

        # Regular content
        display = clean if clean != stripped else stripped
        if display:
            html.append(f"<p>{_inline(display)}</p>")
        i += 1

    if in_claw and claw_lines:
        _flush_claw(html, claw_lines)

    if in_item_block:
        html.append("</div>")

    return "\n".join(html)


def _strip_list_marker(s: str) -> str:
    """Strip leading markdown list markers (* or numbered) and indentation."""
    return re.sub(r"^\s*(?:[\*\-]\s+|\d+\.\s+)", "", s).strip()


def _flush_claw(html: list[str], claw_lines: list[str]):
    """Render collected Claw review lines into a styled card."""
    if not claw_lines:
        return
    items_html = "".join(f"<p>{_inline(cl)}</p>" for cl in claw_lines)
    html.append(
        f'<div class="claw-card"><div class="claw-label">🦞 Claw 锐评</div>{items_html}</div>'
    )


def _render_table(table_lines: list[str]) -> str:
    """Convert markdown table lines to HTML <table>."""
    rows: list[list[str]] = []
    separator_idx = -1
    for idx, line in enumerate(table_lines):
        cells = [c.strip() for c in line.strip("|").split("|")]
        if all(re.match(r"^[-:]+$", c) for c in cells if c):
            separator_idx = idx
            continue
        rows.append(cells)

    if not rows:
        return ""

    html_parts = ['<div class="table-wrapper"><table>']

    if separator_idx == 1 and len(rows) >= 1:
        header = rows[0]
        html_parts.append("<thead><tr>")
        for cell in header:
            html_parts.append(f"<th>{_inline(cell)}</th>")
        html_parts.append("</tr></thead>")
        body_rows = rows[1:]
    else:
        body_rows = rows

    html_parts.append("<tbody>")
    for row in body_rows:
        html_parts.append("<tr>")
        for cell in row:
            html_parts.append(f"<td>{_inline(cell)}</td>")
        html_parts.append("</tr>")
    html_parts.append("</tbody></table></div>")

    return "".join(html_parts)


def _inline(text: str) -> str:
    """Inline formatting: bold / italic / link."""
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"\*(.+?)\*", r"<em>\1</em>", text)
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    return text
