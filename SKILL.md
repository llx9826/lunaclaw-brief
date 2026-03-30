# ClawCat Brief — AI 简报引擎 Skill

本项目提供两种使用模式。请根据你的角色选择：

## 宿主 AI 模式（推荐）

如果你是 Cursor / OpenClaw 等宿主 AI，请阅读：

**[clawcat_skill/SKILL.md](clawcat_skill/SKILL.md)**

该模式提供三个工具函数（`plan_report` / `fetch_data` / `render_report`），
你只需调用工具获取数据和渲染，内容撰写由你完成，无需额外 LLM API Key。

```python
from clawcat_skill import plan_report, fetch_data, render_report
```

## 独立运行模式

如果你想独立运行完整 pipeline（自带 LLM），使用 CLI：

```bash
python -m clawcat.cli "做个每日 AI 新闻"
python -m clawcat.cli "OCR 技术周报"
python -m clawcat.cli "今天 A 股怎么样"
```

此模式需要在 `config.yaml` 或 `config.local.yaml` 中配置 LLM API Key。

---

*ClawCat Brief · Built by llx & Luna*
