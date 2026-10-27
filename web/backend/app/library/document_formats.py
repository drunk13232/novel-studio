"""Data-only format adapters used inside the existing bounded parser worker."""
import csv, io, json, posixpath, re, zipfile
from pathlib import Path
from urllib.parse import unquote

TEXT_FORMATS={'.json':'json','.yaml':'yaml','.yml':'yaml','.csv':'csv','.html':'html','.htm':'html'}

def archive(blob):
    z=zipfile.ZipFile(io.BytesIO(blob));rows=z.infolist()
    if len(rows)>2000 or sum(r.file_size for r in rows)>128*1024*1024:raise ValueError('文档压缩包解压规模超过限制')
    for r in rows:
        if r.flag_bits&1 or r.file_size>32*1024*1024 or r.file_size>max(1,r.compress_size)*300:raise ValueError('文档压缩包加密或压缩比例异常')
        if '\\' in r.filename or r.filename.startswith('/') or any(v in {'..','.'} for v in r.filename.split('/')):raise ValueError('文档压缩包路径不安全')
    return z

def file_type(blob,name,decode):
    ext=Path(name).suffix.lower()
    if ext=='.epub' and blob.startswith(b'PK'):
        with archive(blob) as z:
            if z.read('mimetype').strip()!=b'application/epub+zip' or 'META-INF/container.xml' not in z.namelist():raise ValueError('不是受支持的 EPUB 文件')
        return 'epub'
    if ext in TEXT_FORMATS and not blob.startswith((b'MZ',b'PK',b'%PDF-')):
        text,_=decode(blob)
        if len(text.encode('utf8'))>8*1024*1024:raise ValueError('结构化文献超过 8 MiB 解析上限')
        return TEXT_FORMATS[ext]
    return None

def xml(blob):
    from lxml import etree
    if b'<!DOCTYPE' in blob.upper() or b'<!ENTITY' in blob.upper():raise ValueError('文档不允许 DTD 或外部实体')
    return etree.fromstring(blob,parser=etree.XMLParser(resolve_entities=False,no_network=True,huge_tree=False))

def html_units(text,add,chapter=''):
    from lxml import html
    tree=html.fromstring(text,parser=html.HTMLParser(no_network=True,remove_comments=True,huge_tree=False))
    for node in tree.xpath('//script|//style|//iframe|//object|//embed|//noscript'):node.drop_tree()
    nodes=tree.xpath('//h1|//h2|//h3|//h4|//h5|//h6|//p|//li[not(.//p)]|//td[not(.//p)]|//pre')
    if not nodes:nodes=[tree]
    for number,node in enumerate(nodes,1):
        value=' '.join(node.text_content().split())
        if value and not add(value,None,(chapter+' · ' if chapter else '')+f'文本块 {number}',str(node.tag).lower() in {'h1','h2','h3','h4','h5','h6'},{'format':'epub' if chapter else 'html','chapter':chapter,'block':number}):break

def extract(filename,kind,decode,add,result):
    if kind=='epub':
        with archive(Path(filename).read_bytes()) as z:
            container=xml(z.read('META-INF/container.xml'))
            files=container.xpath('//*[local-name()="rootfile"]/@full-path')
            if not files:raise ValueError('EPUB 缺少阅读顺序')
            opf=files[0]
            if opf not in z.namelist():raise ValueError('EPUB 包入口不存在')
            root=xml(z.read(opf));items={v.get('id'):v.get('href') for v in root.xpath('//*[local-name()="manifest"]/*[local-name()="item"]') if v.get('media-type') in {'application/xhtml+xml','text/html'}}
            for ref in root.xpath('//*[local-name()="spine"]/*[local-name()="itemref"]'):
                href=items.get(ref.get('idref'))
                if not href:continue
                if re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:',href):raise ValueError('EPUB 不读取外部资源')
                path=posixpath.normpath(posixpath.join(posixpath.dirname(opf),unquote(href.split('#')[0])))
                if path.startswith(('../','/')) or path not in z.namelist():raise ValueError('EPUB 章节路径无效')
                body=z.read(path);xml(body) # Reject external entities before HTML text extraction.
                text,_=decode(body);html_units(text,add,path)
                if result['warnings']:break
        return
    text,result['encoding']=decode(Path(filename).read_bytes())
    if kind=='html':html_units(text,add);return
    if kind=='csv':
        csv.field_size_limit(256*1024)
        rows=csv.reader(io.StringIO(text,newline=''));headers=next(rows,[])
        if len(headers)>256:raise ValueError('CSV 超过 256 列')
        for row_number,row in enumerate(rows,2):
            if len(row)>256:raise ValueError('CSV 超过 256 列')
            for col,value in enumerate(row,1):
                label=headers[col-1] if col<=len(headers) else str(col)
                if not add(value,None,f'第 {row_number} 行 · {label}',False,{'format':'csv','row':row_number,'column':col,'field':label}):return
        return
    if kind=='json':
        def reject(v):raise ValueError('JSON 不允许非有限数值：'+v)
        def pairs(rows):
            d={}
            for k,v in rows:
                if k in d:raise ValueError('JSON 包含重复键，无法确定引用路径')
                d[k]=v
            return d
        value=json.loads(text,parse_constant=reject,object_pairs_hook=pairs)
    else:
        import yaml
        if any(isinstance(t,(yaml.tokens.TagToken,yaml.tokens.AliasToken,yaml.tokens.AnchorToken)) for t in yaml.scan(text)):raise ValueError('YAML 不允许标签、锚点或别名')
        class UniqueLoader(yaml.SafeLoader):pass
        def mapping(loader,node,deep=False):
            value={}
            for k,v in node.value:
                key=loader.construct_object(k,deep=deep)
                if not isinstance(key,str) or key in value:raise ValueError('YAML 引用要求唯一字符串键')
                value[key]=loader.construct_object(v,deep=deep)
            return value
        UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,mapping)
        value=yaml.load(text,Loader=UniqueLoader)
    seen=0
    def walk(v,path='',depth=0):
        nonlocal seen
        seen+=1
        if depth>24 or seen>20000:raise ValueError('结构化文献过深或节点过多')
        if isinstance(v,dict) and v:
            for k,item in v.items():walk(item,path+'/'+str(k).replace('~','~0').replace('/','~1'),depth+1)
        elif isinstance(v,list) and v:
            for i,item in enumerate(v):walk(item,path+'/'+str(i),depth+1)
        else:
            rendered=json.dumps(v,ensure_ascii=False,allow_nan=False,default=str)
            add(rendered,None,kind.upper()+' '+(path or '/'),False,{'format':kind,'pointer':path})
    walk(value)
