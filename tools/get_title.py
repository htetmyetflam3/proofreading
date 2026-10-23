# Get unique chapters (each chapter spans multiple pages)

import zipfile, re
from xml.etree import ElementTree as ET

path = '/mnt/agents/upload/episodes.docx'
with zipfile.ZipFile(path) as z:
    xml = z.read('word/document.xml')

ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
root = ET.fromstring(xml)
paras = []
for p in root.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
    texts = [t.text or '' for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t')]
    line = ''.join(texts)
    paras.append(line)

print(f"Total paragraphs: {len(paras)}")
print(f"Non-empty: {sum(1 for p in paras if p.strip())}")
print("---FIRST 60---")
for i, p in enumerate(paras[:60]):
    if p.strip():
        print(f"[{i}] {p[:150]}")

seen = set()
unique_chapters = []
for idx, num, title in chapters:
    key = num
    if key not in seen:
        seen.add(key)
        unique_chapters.append((idx, num, title))

print(f"Unique chapters: {len(unique_chapters)}")
for idx, num, title in unique_chapters:
    print(f"  第{num}章: {title}")

  # Build parallel segments: pair ZH pages with MY pages
# Structure: [ZH] header, ZH lines..., [MY] header, MY lines..., repeat

segments = []
i = 0
while i < len(paras):
    if paras[i].startswith('[ZH]'):
        zh_start = i
        # collect ZH until [MY]
        j = i + 1
        zh_lines = []
        while j < len(paras) and not paras[j].startswith('[MY]'):
            zh_lines.append(paras[j])
            j += 1
        # collect MY until next [ZH] or end
        my_lines = []
        if j < len(paras) and paras[j].startswith('[MY]'):
            k = j + 1
            while k < len(paras) and not paras[k].startswith('[ZH]'):
                my_lines.append(paras[k])
                k += 1
            segments.append({
                'zh_header': paras[zh_start],
                'zh_lines': zh_lines,
                'my_header': paras[j],
                'my_lines': my_lines
            })
            i = k
        else:
            i = j
    else:
        i += 1

print(f"Total parallel segments: {len(segments)}")

# Show structure of first segment
s = segments[0]
print(f"\nZH header: {s['zh_header']}")
print(f"ZH lines: {len(s['zh_lines'])}")
print(f"MY header: {s['my_header']}")
print(f"MY lines: {len(s['my_lines'])}")
print("\n--- ZH lines sample ---")
for l in s['zh_lines'][:10]:
    print(f"  {l[:100]}")
print("\n--- MY lines sample ---")
for l in s['my_lines'][:10]:
    print(f"  {l[:100]}")



  # Extract all chapter titles in both languages for the full mapping
# Extract all chapter titles in both languages for the full mapping
# MY headers use Burmese numerals - rebuild map with flexible MY regex
chapter_map = {}
for s in segments:
    m = re.match(r'\[ZH\] 第(.+?)章：(.+?) — page', s['zh_header'])
    if m:
        num_zh = m.group(1)
        num_int = zh_num_to_int(num_zh)
        title_zh = m.group(2)
        # MY header: just extract chapter number
        m2 = re.match(r'\[MY\] အခန်း\s*\(?(.+?)\)?\s*—', s['my_header'])
        if num_int not in chapter_map:
            chapter_map[num_int] = {'zh': title_zh, 'zh_num': num_zh}

print(f"Mapped: {len(chapter_map)} chapters")
for num in sorted(chapter_map.keys()):
    t = chapter_map[num]
    print(f"  {num:3d}. {t['zh']}")