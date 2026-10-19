# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Tag DOCX text using the owner's Engine and required rebuilt scraper WASM."""
from __future__ import annotations
import argparse
from collections import Counter
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
from xml.etree import ElementTree as ET
from zipfile import ZipFile, ZIP_DEFLATED
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parent
W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'

def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest() if hasattr(hashlib, 'file_digest') else hashlib.sha256(stream.read()).hexdigest()

def atomic_copy(source, destination):
    fd, temporary = tempfile.mkstemp(prefix='.tagged-', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as out, Path(source).open('rb') as stream:
            shutil.copyfileobj(stream, out)
        os.replace(temporary, destination)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)

def extract(docx, text_path, index_path, limit):
    counts = Counter()
    char_offset = byte_offset = 0
    pdf_page = None
    with ZipFile(docx) as archive, archive.open('word/document.xml') as xml, text_path.open('w', encoding='utf-8', newline='\n') as text_out, index_path.open('w', encoding='utf-8') as index_out:
        for _, element in ET.iterparse(xml, events=('end',)):
            if element.tag != W+'p': continue
            counts['xml_paragraphs'] += 1
            parts = []
            for node in element.iter():
                if node.tag == W+'t': parts.append(node.text or '')
                elif node.tag in (W+'br', W+'cr'): parts.append('\n')
                elif node.tag == W+'tab': parts.append('\t')
            value = ''.join(parts)
            element.clear()
            if not value.strip(): continue
            counts['nonempty_paragraphs_seen'] += 1
            stripped = value.strip()
            page = re.fullmatch(r'--- Page (\d+) ---', stripped)
            if page:
                pdf_page = int(page[1]); counts['page_wrappers_removed'] += 1; continue
            if stripped.startswith(('# Source:', '# Pages:', '# Detection:')) or re.fullmatch(r'#+', stripped):
                counts['metadata_wrappers_removed'] += 1; continue
            if re.fullmatch(r'[-\s]{4,}', value):
                counts['separator_wrappers_removed'] += 1; continue
            if limit is not None and counts['prose_paragraphs'] >= limit: break
            encoded = value.encode('utf-8')
            record = {'docx_paragraph':counts['xml_paragraphs'], 'pdf_page':pdf_page,
                'char_start':char_offset, 'char_end':char_offset+len(value),
                'byte_start':byte_offset, 'byte_end':byte_offset+len(encoded)}
            text_out.write(value+'\n')
            index_out.write(json.dumps(record, ensure_ascii=False)+'\n')
            counts['prose_paragraphs'] += 1
            char_offset += len(value)+1
            byte_offset += len(encoded)+1
    if not counts['prose_paragraphs']: raise ValueError('DOCX contains no nonempty prose')
    return dict(counts)

def tagged_docx(template, raw_text, target):
    """New OOXML companion; raw tagger units become paragraphs, not source layout."""
    font = None
    with ZipFile(template) as original, original.open('word/document.xml') as stream:
        for _, node in ET.iterparse(stream, events=('end',)):
            if node.tag == W+'rFonts':
                font = dict(node.attrib)
                break
    ET.register_namespace('w', W[1:-1])
    props = ET.Element(W+'rPr')
    if font:
        ET.SubElement(props, W+'rFonts', font)
    run_properties = ET.tostring(props, encoding='utf-8')
    count = 0
    with ZipFile(template) as original, ZipFile(target, 'w', compression=ZIP_DEFLATED) as tagged:
        for info in original.infolist():
            if info.filename != 'word/document.xml':
                tagged.writestr(info, original.read(info.filename))
                continue
            with tagged.open(info, 'w') as xml, Path(raw_text).open(encoding='utf-8') as lines:
                xml.write(('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
                    '<w:document xmlns:w="'+W[1:-1]+'"><w:body>').encode())
                for line in lines:
                    value = line.removesuffix('\n')
                    xml.write(b'<w:p><w:r>'+run_properties+b'<w:t xml:space="preserve">')
                    xml.write(escape(value).encode('utf-8'))
                    xml.write(b'</w:t></w:r></w:p>')
                    count += 1
                xml.write(b'<w:sectPr/></w:body></w:document>')
    # Verify ZIP integrity and exact text round-trip against the tagged stream.
    with ZipFile(target) as package:
        if package.testzip() is not None: raise ValueError('Generated tagged DOCX ZIP failed integrity check')
        with package.open('word/document.xml') as stream, Path(raw_text).open(encoding='utf-8') as expected:
            for _, node in ET.iterparse(stream, events=('end',)):
                if node.tag != W+'p': continue
                value = ''.join(n.text or '' for n in node.iter() if n.tag == W+'t')
                if value != next(expected).removesuffix('\n'): raise ValueError('Tagged DOCX text round-trip failed')
                node.clear()
            if next(expected, None) is not None: raise ValueError('Tagged DOCX is truncated')
    return count

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path)
    parser.add_argument('--output-dir', type=Path, default=ROOT/'output/tagger')
    parser.add_argument('--max-paragraphs', type=int, help='Explicit small pilot; uses a separate output name')
    args = parser.parse_args()
    if args.max_paragraphs is not None and args.max_paragraphs <= 0: parser.error('--max-paragraphs must be positive')
    docx = args.input
    if docx is None:
        candidates = list((ROOT/'input').glob('*.docx'))
        if len(candidates) != 1: parser.error('Specify --input (there is not exactly one DOCX in input/)')
        docx = candidates[0]
    docx = docx.resolve()
    if not docx.is_file(): parser.error(f'Input does not exist: {docx}')
    if shutil.which('node') is None: parser.error('Node 22+ is required for the supplied Engine/WASM')
    out = args.output_dir.resolve(); out.mkdir(parents=True, exist_ok=True)
    stem = docx.stem + (f'-first-{args.max_paragraphs}' if args.max_paragraphs else '')
    work = out/'.work'/stem; work.mkdir(parents=True, exist_ok=True)
    source = work/'source.txt'; index = work/'paragraphs.jsonl'; result = work/'result.json'
    original_hash = digest(docx)
    counts = extract(docx, source, index, args.max_paragraphs)
    print(f'[docx] {counts["prose_paragraphs"]:,} paragraphs extracted; original DOCX unchanged', flush=True)
    subprocess.run(['node', str(ROOT/'engine/tag-text.mjs'), str(source), str(work), str(result)], cwd=ROOT, check=True)
    stats = json.loads(result.read_text())
    if digest(docx) != original_hash: raise ValueError('Original DOCX was modified')
    outputs = {'source':out/f'{stem}.source.txt', 'paragraphs':out/f'{stem}.paragraphs.jsonl', 'raw_pos':out/f'{stem}.raw_pos.txt'}
    for key, origin in [('source',source),('paragraphs',index),('raw_pos',Path(stats.pop('raw_pos_path')))]:
        atomic_copy(origin, outputs[key])
    word_work = work/'tagged.docx'
    word_paragraphs = tagged_docx(docx, outputs['raw_pos'], word_work)
    outputs['tagged_docx'] = out/f'{stem}.tagged.docx'
    atomic_copy(word_work, outputs['tagged_docx'])
    rejected = work/'tree/pos-fail.txt'
    if rejected.exists():
        outputs['rejected_dictionary'] = out/f'{stem}.pos-rejected.txt'
        atomic_copy(rejected, outputs['rejected_dictionary'])
    report = {**stats, 'input_docx':str(docx.relative_to(ROOT)) if docx.is_relative_to(ROOT) else str(docx),
        'docx_sha256':original_hash, 'original_docx_unchanged':True,
        'tagged_docx_sha256':digest(outputs['tagged_docx']), 'tagged_docx_text_roundtrip':True,
        'tagged_docx_paragraphs':word_paragraphs,
        'tagged_docx_layout':'raw tagger units, not the original DOCX paragraph/page layout; Word rendering not tested',
        'extraction':counts, 'partial_pilot':args.max_paragraphs is not None,
        'paragraph_offsets':'Python Unicode code points and UTF-8 bytes in .source.txt, before WASM normalization; not tagged-text offsets',
        'outputs':{key:str(value.relative_to(out)) for key,value in outputs.items() if key not in ('source','paragraphs')},
        'generated_local_support':{key:str(value.relative_to(out)) for key,value in outputs.items() if key in ('source','paragraphs')}}
    report_work = work/'report.json'; report_work.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    report_path = out/f'{stem}.report.json'; atomic_copy(report_work, report_path)
    print(f'[done] {outputs["raw_pos"]}', flush=True)
    print(f'[report] {report_path}', flush=True)

if __name__ == '__main__':
    try: main()
    except (OSError, ValueError, KeyError, subprocess.CalledProcessError) as error:
        raise SystemExit(f'error: {error}') from error
