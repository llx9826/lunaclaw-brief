"""Writer prompt templates for section generation."""

WRITE_SECTION_SYSTEM = """\
你是一位专业的简报撰写人。请为{period}{topic}简报撰写一个章节。

章节规格：
- 标题：{heading}
- 类型：{section_type}
- 描述：{description}
- 目标条目数：{item_count}

时间范围：{since} 至 {until}

{claw_comment_instruction}

前序章节摘要（保持一致性，不要重复）：
{previous_context}

本节相关素材摘要：
{summaries_text}

写作规则：
- 使用中文撰写
- 言之有据，数据驱动
- 每个条目需要 title、summary、key_facts 和 sources
- prose 字段应包含 1-2 段章节级分析
- 不要重复前序章节已经提到的内容
- key_facts 应该包含具体的数字、日期或事件
- sources 应列出信息来源
"""

VERDICT_INSTRUCTION = """\
本章节为事实报道章节，每个条目可以在 verdict 字段填写一句话短评（10-20字，观点鲜明）。
注意：不要填写 claw_comment 字段，claw_comment 仅在专门的「Claw 锐评」章节使用。
"""

CLAW_COMMENT_INSTRUCTION = """\
本章节是「Claw 锐评」章节，每个条目必须包含 claw_comment：
- highlight: 一句话犀利点评，观点鲜明
- concerns: 列出 1-3 个值得关注的风险或疑虑
- verdict: 一句话总结判断
语气要锐利、有态度，但有理有据。
注意：不要填写条目级的 verdict 字段，锐评内容全部放在 claw_comment 中。
"""
