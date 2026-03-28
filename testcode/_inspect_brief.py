"""Quick inspector for generated Brief JSON."""
import json, sys

path = sys.argv[1] if len(sys.argv) > 1 else "output/2026-03-29_brief.json"
with open(path, "r", encoding="utf-8") as f:
    d = json.load(f)

print(f"Title: {d['title']}")
print(f"Type: {d['report_type']}")
tr = d["time_range"]
print(f"Time: {tr['resolved_start'][:10]} ~ {tr['resolved_end'][:10]}")
print(f"Summary: {d['executive_summary'][:200]}")
print()
for i, s in enumerate(d["sections"]):
    items = s.get("items", [])
    has_claw = sum(1 for it in items if it.get("claw_comment"))
    print(f"Section {i+1}: {s['heading']} ({s['section_type']}) - {len(items)} items, {has_claw} with claw_comment")
    for it in items[:3]:
        print(f"  - {it['title']}")
        if it.get("key_facts"):
            for kf in it["key_facts"][:2]:
                print(f"    * {kf}")
        if it.get("claw_comment"):
            cc = it["claw_comment"]
            print(f"    [claw] {cc.get('highlight', '')[:80]}")
print()
m = d["metadata"]
print(f"Model: {m.get('llm_model')}")
print(f"Sources: {', '.join(m.get('sources_used', []))}")
print(f"Items: {m.get('items_fetched')} fetched, {m.get('items_selected')} selected")
