"""Synthetic, project-isolated organization checks; no real AI or user-data access."""
import copy,json
import pytest
from pydantic import ValidationError
from test_writing_assist import service
from app.library.data_organization import Create,Review,Definition,Confirm,Source
from app.library.bible import Category
from app.library.world_templates import compatible
from app.errors import ConsoleError

def setup(service):
    writing,p,root=service;return writing.world_studio.data_organization,p,root

def definition():
    return Definition(name='国家资料',templates=[{'key':'nations','name':'国家数值','fields':[{'id':'population','name':'人口','type':'number'},{'id':'stock','name':'库存','type':'quantity','unit':'吨'},{'id':'history','name':'历年记录','type':'table','columns':[{'id':'year','name':'纪年','type':'text'},{'id':'value','name':'数值','type':'number'}]}]}],records=[{'key':'north','name':'虚构北国','template_key':'nations','values':[{'id':'population','value_json':'5000000','basis':'AUTHOR_INPUT'},{'id':'stock','value_json':'null','basis':'UNKNOWN'},{'id':'history','value_json':'[{"year":"元年","value":12},{"year":"次年","value":null}]','basis':'AUTHOR_INPUT'}]}],views=[{'key':'numbers','name':'国家对比','template_key':'nations','columns':['population','stock']}])

def draft(s,p,d=None,**kw):
    r=s.create(p,Create(goal='按资料组织，不补造人口或军费',**kw));return s.review(p,r['id'],Review(etag=r['etag'],definition=d or definition()))
def apply(s,p,r):
    preview=s.preview(p,r['id']);return s.apply(p,r['id'],Confirm(etag=r['etag'],preview_sha256=preview['preview_sha256'],confirm=True))
def protected(root):
    return {f:f.read_bytes() for name in ['chapters','characters','state','settings','outlines'] for f in (root/name).rglob('*') if f.is_file()}

def test_empty_create_preview_and_idempotent_apply_preserve_real_authorities(service):
    s,p,root=setup(service);before=protected(root);count=len(s.bible.list(p));r=draft(s,p);assert len(s.bible.list(p))==count
    v=s.preview(p,r['id']);assert v['new_records']==1 and v['existing_records_modified']==0 and not v['canon_changed'];a=apply(s,p,r);e=s.bible.get(p,a['entities'][0]['id']);assert e['status']=='PENDING' and not e['writer_public'] and e['canon_level']=='REFERENCE';assert e['fields']['stock'] is None
    assert apply(s,p,r)['reused'] and len(s.bible.list(p))==count+1;assert before==protected(root)
    table=s.table(p,r['id'],'numbers');assert table['rows'][0]['fields']['population']==5000000 and table['single_source']
    assert not s.table(p,r['id'],'numbers',query='不存在')['rows']

def test_references_existing_entity_instead_of_copy_and_live_view_updates(service):
    s,p,_=setup(service);cat=s.bible.category(p,{'id':'org_test_source','name':'来源','fields':[{'id':'count','name':'数量','type':'number'}]});e=s.bible.save(p,{'name':'原条目','category':cat['id'],'fields':{'count':10}});r=s.create(p,Create(goal='按原字段展示',sources=[Source(kind='entity',id=e['id'])],reuse_templates=[cat['id']]));d=Definition(templates=[{'key':'same','name':'原分类','existing_id':cat['id']}],records=[{'key':'source','name':'原条目','template_key':'same','existing_id':e['id']}]);r=s.review(p,r['id'],Review(etag=r['etag'],definition=d));before=len(s.bible.list(p));a=apply(s,p,r);assert len(s.bible.list(p))==before and a['entities'][0]['id']==e['id']
    etag=e.pop('etag');e['fields']['count']=25;s.bible.save(p,e,etag);assert s.table(p,r['id'],'same')['rows'][0]['fields']['count']==25

def test_preview_token_and_source_staleness_reject_without_writes(service):
    s,p,_=setup(service);r=draft(s,p);n=len(s.bible.list(p))
    with pytest.raises(ConsoleError):s.apply(p,r['id'],Confirm(etag=r['etag'],preview_sha256='wrong',confirm=True))
    r2=s.review(p,r['id'],Review(etag=r['etag'],definition=definition()))
    with pytest.raises(ConsoleError):s.apply(p,r['id'],Confirm(etag=r['etag'],preview_sha256=s.preview(p,r['id'])['preview_sha256'],confirm=True))
    assert len(s.bible.list(p))==n
    e=s.bible.save(p,{'name':'原始','category':'overview'});r=draft(s,p,sources=[Source(kind='entity',id=e['id'])]);etag=e.pop('etag');e['summary']='外部新版本';s.bible.save(p,e,etag)
    with pytest.raises(ConsoleError):s.preview(p,r['id'])

def test_batch_failure_rolls_back_templates_records_and_receipt(service,monkeypatch):
    s,p,root=setup(service);r=draft(s,p);before={f:f.read_bytes() for f in (root/'bible').rglob('*') if f.is_file()};original=s.save
    def fail(p,row):
        saved=original(p,row)
        if row['status']=='APPLIED':raise OSError('synthetic receipt failure')
        return saved
    monkeypatch.setattr(s,'save',fail)
    with pytest.raises(OSError):apply(s,p,r)
    assert s.get(p,r['id'])['status']=='DRAFT' and s.get(p,r['id'])['receipt'] is None
    after={f:f.read_bytes() for f in (root/'bible').rglob('*') if f.is_file()};assert after==before

def test_unknown_fabricated_quote_duplicate_and_executable_schema_rejected(service):
    s,p,_=setup(service)
    for patch in ['unknown','quote','duplicate','code']:
        d=definition()
        if patch=='unknown':d.records[0].values[0].basis='UNKNOWN'
        if patch=='quote':d.records[0].values[0].basis='SOURCE_QUOTE';d.records[0].values[0].source_id='input';d.records[0].values[0].quote='并不存在的精确原文'
        if patch=='duplicate':d.templates.append(copy.deepcopy(d.templates[0]))
        if patch=='code':
            with pytest.raises(ValidationError):Definition.model_validate({**d.model_dump(),'script':'__import__("os")'})
            continue
        with pytest.raises(ConsoleError):draft(s,p,d,text='只有人口设定，来源不包含该句。')
    with pytest.raises(ValidationError):Definition.model_validate({'templates':[{'key':'bad','name':'恶意','fields':[{'id':'shell','name':'命令','type':'python'}]}]})

def test_table_types_units_references_nan_and_row_limits(service):
    s,p,_=setup(service);r=draft(s,p);_,cats=s.resolved(r,r['definition']);c=cats['nations'];s.bible.category(p,c)
    bad=[{'history':[{'year':'元年','value':'not numeric'}]},{'stock':{'value':3,'unit':''}},{'history':[{}]*201},{'population':float('nan')}]
    for fields in bad:
        with pytest.raises(ConsoleError):s.bible.save(p,{'name':'错误值','category':c['id'],'fields':fields})
    old=copy.deepcopy(c);new=copy.deepcopy(c);new['fields'][2]['children']=new['fields'][2]['children'][:1];assert not compatible(old,new)

def test_table_entity_references_are_validated_and_derived(service):
    s,p,_=setup(service);target=s.bible.save(p,{'name':'目标','category':'overview'});c=s.bible.category(p,{'id':'table_links','name':'表格关联','fields':[{'id':'links','name':'关联表','type':'table','children':[{'id':'target','name':'目标','type':'entity'}]}]})
    with pytest.raises(ConsoleError):s.bible.save(p,{'name':'越界','category':c['id'],'fields':{'links':[{'target':'entity_'+'f'*32}]}})
    e=s.bible.save(p,{'name':'有效','category':c['id'],'fields':{'links':[{'target':target['id']}]}});assert any(x['source_id']==e['id'] and x['target_id']==target['id'] for x in s.bible.relations(p))

def test_author_only_source_fields_and_nonselected_objects_are_not_sent(service):
    s,p,_=setup(service);c=s.bible.category(p,{'id':'source_scope','name':'来源','fields':[{'id':'public_value','name':'公开','type':'text'},{'id':'secret','name':'私密','type':'text','author_only':True},{'id':'rows','name':'表格','type':'table','children':[{'id':'visible','name':'可见','type':'text'},{'id':'hidden','name':'私密列','type':'text','author_only':True}]}]});e=s.bible.save(p,{'name':'所选','category':c['id'],'fields':{'public_value':'allowed','secret':'PRIVATE_MARKER','rows':[{'visible':'yes','hidden':'PRIVATE_COLUMN'}]}});s.bible.save(p,{'name':'未选','category':'overview','summary':'UNSELECTED_MARKER'});r=s.create(p,Create(goal='只整理所选字段',sources=[Source(kind='entity',id=e['id'])]));text=json.dumps(r['sources']);assert 'allowed' in text and 'PRIVATE_MARKER' not in text and 'PRIVATE_COLUMN' not in text and 'UNSELECTED_MARKER' not in text
    with pytest.raises(ConsoleError):s.get(p+'bad',r['id'])
    with pytest.raises(ConsoleError):s.get(p,'../outside')

def test_existing_template_change_invalidates_preview(service):
    s,p,_=setup(service);c=s.bible.category(p,{'id':'reuse_source','name':'固定模板','fields':[]});r=s.create(p,Create(goal='复用',reuse_templates=[c['id']]));r=s.review(p,r['id'],Review(etag=r['etag'],definition=Definition(templates=[{'key':'same','name':'固定模板','existing_id':c['id']}])));c['fields'].append({'id':'new_value','name':'新增','type':'number','options':[]});s.bible.category(p,c)
    with pytest.raises(ConsoleError):s.preview(p,r['id'])


def capture(s,p,monkeypatch):
    from types import SimpleNamespace
    from app.creative.tasks import adapter as original
    box={}
    def fake_adapter(*a,**kw):
        kw['preview']=True;v=original(*a,**kw);v.selected_ai['backend']='MOCK_NOT_REAL_AI';return v
    monkeypatch.setattr('app.library.data_organization.adapter',fake_adapter)
    task=SimpleNamespace(id='organization-fixture',private_text=False,status='RUNNING',error=None,public=lambda:{'id':'organization-fixture','status':'RUNNING'})
    def prepared(*a,**kw):box.update(prompt=a[1],schema=a[4],complete=a[5],kwargs=kw);return task
    monkeypatch.setattr(s.studio.manager(p),'prepared',prepared);return box

def test_context_preview_is_local_and_ai_completion_is_proposal_only(service,monkeypatch):
    from app.library.data_organization import Run
    s,p,root=setup(service);r=s.create(p,Create(goal='只整理输入',text='某国人口五百万，军费未知。'));box=capture(s,p,monkeypatch);before=protected(root);n=len(s.bible.list(p));preview=s.run(p,r['id'],Run(etag=r['etag'],confirm_send=True),preview=True);assert preview['local_only'] and not box and s.get(p,r['id'])['status']=='DRAFT'
    s.run(p,r['id'],Run(etag=r['etag'],confirm_send=True));assert '五百万' in box['prompt'] and 'No tools/files/code/SQL' in box['prompt'];box['complete'](definition().model_dump_json());row=s.get(p,r['id']);assert row['status']=='READY' and row['definition']['records'][0]['values'][0]['basis']=='AI_PROPOSED';assert len(s.bible.list(p))==n and before==protected(root)

def test_cancel_blocks_late_results_and_does_not_replace_previous_definition(service,monkeypatch):
    import asyncio
    from app.library.data_organization import Run
    s,p,_=setup(service);r=draft(s,p);box=capture(s,p,monkeypatch);s.run(p,r['id'],Run(etag=r['etag'],confirm_send=True));manager=s.studio.manager(p)
    async def cancel(id):assert id=='organization-fixture'
    monkeypatch.setattr(manager,'cancel',cancel);stopped=asyncio.run(s.cancel(p,r['id']));assert stopped['status']=='CANCELLED'
    with pytest.raises(ConsoleError):box['complete'](definition().model_dump_json())
    assert s.get(p,r['id'])['definition']==r['definition']

def test_malformed_ai_output_does_not_destroy_the_previous_editable_plan(service,monkeypatch):
    from app.library.data_organization import Run
    s,p,_=setup(service);r=draft(s,p);box=capture(s,p,monkeypatch);s.run(p,r['id'],Run(etag=r['etag'],confirm_send=True))
    with pytest.raises(ConsoleError):box['complete']('not valid JSON')
    assert s.get(p,r['id'])['definition']==r['definition']

def test_comparison_units_unknown_sort_and_deleted_records(service):
    s,p,_=setup(service);d=definition();d.records.append(copy.deepcopy(d.records[0]));d.records[1].key='south';d.records[1].name='虚构南国';d.records[1].values[0].value_json='null';d.records[1].values[0].basis='UNKNOWN';r=draft(s,p,d);a=apply(s,p,r);t=s.table(p,r['id'],'numbers',sort='population',descending=True);assert t['rows'][-1]['fields']['population'] is None
    for i,e in enumerate(a['entities']):
        v=s.bible.get(p,e['id']);etag=v.pop('etag');v['fields']['stock']={'value':i+1,'unit':'kg' if i else '吨'};s.bible.save(p,v,etag)
    with pytest.raises(ConsoleError):s.table(p,r['id'],'numbers',sort='stock')
    root=s.bible.root(p);(root/'bible/entities'/(a['entities'][0]['id']+'.json')).unlink();t=s.table(p,r['id'],'numbers');assert t['total']==1 and len(t['missing_records'])==1

def test_applied_source_quote_remains_locatable_via_existing_provenance_panel(service):
    s,p,_=setup(service);d=definition();f=d.records[0].values[0];f.basis='SOURCE_QUOTE';f.source_id='input';f.quote='人口5000000';r=draft(s,p,d,text='虚构国家人口5000000。');a=apply(s,p,r);v=s.studio.provenance(p,a['entities'][0]['id']);assert any(x.get('quote')=='人口5000000' and x['current']=='CURRENT' for x in v['sources'])


def test_manual_origin_and_reference_scope_are_honest(service):
    s,p,_=setup(service);r=draft(s,p);a=apply(s,p,r);assert s.bible.get(p,a['entities'][0]['id'])['source']=='USER'
    target=s.bible.save(p,{'name':'未选关联','category':'overview'})
    d=definition().model_dump();d['templates'][0]['fields'].append({'id':'ref','name':'关联','type':'entity'})
    # Build typed objects through model validation rather than mutating a model with dicts.
    d['records'][0]['values'].append({'id':'ref','value_json':json.dumps(target['id']),'basis':'AI_PROPOSED'})
    d=Definition.model_validate(d)
    r=draft(s,p,d)
    with pytest.raises(ConsoleError):s.preview(p,r['id'])
