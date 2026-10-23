# Count ZH vs MY segments and find chapter boundaries
zh_count = sum(1 for p in paras if p.startswith('[ZH]'))
my_count = sum(1 for p in paras if p.startswith('[MY]'))
print(f"ZH segments: {zh_count}")
print(f"MY segments: {my_count}")

# Find all chapter markers
import re
chapters = []
for i, p in enumerate(paras):
    m = re.match(r'\[ZH\] 第(.+?)章：(.+?) — page', p)
    if m:
        chapters.append((i, m.group(1), m.group(2)))

print(f"\nTotal chapters found: {len(chapters)}")
for idx, num, title in chapters[:15]:
    print(f"  Line {idx}: 第{num}章 {title}")
print("  ...")
for idx, num, title in chapters[-5:]:
    print(f"  Line {idx}: 第{num}章 {title}")