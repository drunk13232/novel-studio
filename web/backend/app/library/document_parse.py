"""Bounded adapters to pypdf/python-docx; never execute uploaded content."""
import ctypes
import json
import os
import re
import zipfile
from pathlib import Path

MAX_UPLOAD = 64 * 1024 * 1024
MAX_TEXT = 8 * 1024 * 1024
MAX_UNITS = 8000


def file_type(blob, name):
    ext = Path(name).suffix.lower()
    if ext == '.pdf' and blob[:1024].lstrip().startswith(b'%PDF-'): return 'pdf'
    if ext == '.docx' and blob.startswith(b'PK'):
        import io
        with zipfile.ZipFile(io.BytesIO(blob)) as z:
            rows = z.infolist()
            if len(rows) > 2000 or sum(r.file_size for r in rows) > 128 * 1024 * 1024: raise ValueError('DOCX 解压规模超过限制')
            if any(r.flag_bits & 1 or r.file_size > 32 * 1024 * 1024 or r.file_size > max(1, r.compress_size) * 300 for r in rows): raise ValueError('DOCX 加密或压缩比例异常')
            names = {r.filename for r in rows}
            if {'word/document.xml', '[Content_Types].xml'} <= names and not any('vbaProject' in n for n in names): return 'docx'
        raise ValueError('不是受支持的无宏 DOCX 文件')
    if ext in {'.txt', '.md', '.markdown'} and not blob.startswith((b'MZ', b'PK', b'%PDF-')):
        decode(blob)  # binary pretending to be text is refused
        return 'md' if ext != '.txt' else 'txt'
    from .document_formats import file_type as extra_type
    extra=extra_type(blob,name,decode)
    if extra:return extra
    raise ValueError('文件类型不匹配；支持 PDF、DOCX、TXT、Markdown、HTML、EPUB、JSON、YAML、CSV')


def decode(blob):
    for encoding in ['utf-8-sig', 'utf-16' if blob.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8']:
        try:
            text = blob.decode(encoding)
            if '\x00' in text: raise ValueError('文本含二进制内容')
            return text, encoding
        except UnicodeError: pass
    from charset_normalizer import from_bytes
    match = from_bytes(blob).best()
    if not match or match.chaos > .2: raise ValueError('无法可靠识别文本编码')
    text = str(match)
    if '\x00' in text: raise ValueError('文本含二进制内容')
    return text, match.encoding


def memory_limit():
    if os.name != 'nt':
        import resource
        resource.setrlimit(resource.RLIMIT_AS, (512 * 1024 * 1024, 512 * 1024 * 1024))
        return
    from ctypes import wintypes as w
    class Basic(ctypes.Structure):
        _fields_ = [('per_process', ctypes.c_int64), ('per_job', ctypes.c_int64), ('flags', w.DWORD), ('min_working', ctypes.c_size_t), ('max_working', ctypes.c_size_t), ('active', w.DWORD), ('affinity', ctypes.c_size_t), ('priority', w.DWORD), ('scheduling', w.DWORD)]
    class IO(ctypes.Structure):
        _fields_ = [(name, ctypes.c_uint64) for name in ['read_op','write_op','other_op','read_bytes','write_bytes','other_bytes']]
    class Extended(ctypes.Structure):
        _fields_ = [('basic', Basic), ('io', IO), ('process_memory', ctypes.c_size_t), ('job_memory', ctypes.c_size_t), ('peak_process', ctypes.c_size_t), ('peak_job', ctypes.c_size_t)]
    k = ctypes.WinDLL('kernel32', use_last_error=True)
    k.CreateJobObjectW.restype = w.HANDLE
    k.SetInformationJobObject.argtypes = [w.HANDLE, ctypes.c_int, ctypes.c_void_p, w.DWORD]
    k.AssignProcessToJobObject.argtypes = [w.HANDLE, w.HANDLE]
    k.GetCurrentProcess.restype = w.HANDLE
    handle = k.CreateJobObjectW(None, None)
    limits = Extended(); limits.basic.flags = 0x100; limits.process_memory = 512 * 1024 * 1024
    if not handle or not k.SetInformationJobObject(handle, 9, ctypes.byref(limits), ctypes.sizeof(limits)) or not k.AssignProcessToJobObject(handle, k.GetCurrentProcess()): raise OSError('无法建立解析内存限制')
    # This worker exits after parsing; the OS closes the handle then.


def extract_worker(filename, kind, output):
    result = {'units': [], 'status': 'FAILED', 'error': '', 'encoding': '', 'warnings': []}
    try:
        memory_limit()
        used = 0
        def add(text, number, label, heading=False,locator=None):
            nonlocal used
            if len(result['units']) >= MAX_UNITS or used + len(text.encode('utf8')) > MAX_TEXT:
                result['warnings'].append('达到提取上限，仅保留前部内容'); return False
            used += len(text.encode('utf8'))
            number=number if number is not None else len(result['units'])+1
            result['units'].append({'id': str(len(result['units'])+1), 'number': number, 'label': label, 'text': text, 'heading': heading,'locator':locator or {'format':kind,'page' if kind=='pdf' else 'paragraph' if kind=='docx' else 'line':number}})
            return True
        if kind == 'pdf':
            from pypdf import PdfReader
            reader = PdfReader(filename)
            if reader.is_encrypted: raise ValueError('加密 PDF 需先在本地解密后上传')
            if len(reader.pages) > 2000: raise ValueError('PDF 超过 2000 页解析限制')
            for number, page in enumerate(reader.pages, 1):
                try:
                    stream = page.get_contents()
                    if stream and len(stream.get_data()) > 16 * 1024 * 1024: raise ValueError('页面内容流超过限制')
                    if not add(page.extract_text() or '', number, f'第 {number} 页'): break
                except Exception as error:
                    result['warnings'].append(f'第 {number} 页未提取：{str(error)[:160]}'); add('', number, f'第 {number} 页')
            result['total_pages'] = len(reader.pages)
            if any(not u['text'].strip() for u in result['units']) and any(u['text'].strip() for u in result['units']):result['warnings'].append('部分页面没有文字层，可能需要 OCR')
            if not any(u['text'].strip() for u in result['units']):
                result.update(status='UNSEARCHABLE', error='需要 OCR 才能搜索正文；原始页面仍可阅读')
        elif kind == 'docx':
            from docx import Document
            from docx.text.paragraph import Paragraph
            from docx.table import Table
            number = 0
            for block in Document(filename).iter_inner_content():
                paragraphs = [block] if isinstance(block, Paragraph) else [p for row in block.rows for cell in row.cells for p in cell.paragraphs] if isinstance(block, Table) else []
                for paragraph in paragraphs:
                    number += 1
                    if not add(paragraph.text, number, f'第 {number} 段', paragraph.style.name.startswith('Heading')): break
                if result['warnings']: break
        elif kind in {'html','epub','json','yaml','csv'}:
            from .document_formats import extract
            extract(filename,kind,decode,add,result)
        else:
            text, result['encoding'] = decode(Path(filename).read_bytes())
            for number, line in enumerate(text.splitlines(), 1):
                if not add(line, number, f'第 {number} 行', bool(re.match(r'^#{1,6}\s', line)) if kind == 'md' else False): break
        if result['status'] != 'UNSEARCHABLE': result['status'] = 'PARTIAL' if result['warnings'] else 'READY'
        if not result['units']: result.update(status='UNSEARCHABLE', error='未提取到正文，原始文件已保留')
    except Exception as error: result.update(status='FAILED', error=str(error)[:1000])
    Path(output).write_text(json.dumps(result, ensure_ascii=False), encoding='utf8')
