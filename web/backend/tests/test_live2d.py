from pathlib import Path
from types import SimpleNamespace
import io,json,zipfile,stat
import pytest
from PIL import Image
from app.live2d import ModelResources,ImportInfo,CompanionSettings,Profile,LiveCompanion,PrivateRegistry,decode,data_file
from app.errors import ConsoleError

def model(tmp):
    b=tmp/'models'/'test';b.mkdir(parents=True)
    (b/'slot.json').write_text(json.dumps({'model':'test.model3.json','character':'haru','sample':True}))
    (b/'test.moc3').write_bytes(b'MOC3'+bytes(16))
    Image.new('RGBA',(32,32)).save(b/'test.png')
    body={'Version':3,'FileReferences':{'Moc':'test.moc3','Textures':['test.png'],'Expressions':[],'Motions':{}}}
    (b/'test.model3.json').write_text(json.dumps(body));return b,body,ModelResources(tmp)

def test_real_data_signature_and_plain_png_rejected(tmp_path):
    b,v,s=model(tmp_path);assert s.model('test')['character']=='haru'
    (b/'test.moc3').write_bytes(b'PNG!')
    with pytest.raises(ConsoleError):s.model('test')

@pytest.mark.parametrize('name',['../secret.json','https://host/a.json','x\\a.json','/secret.json','a:ads','%2e%2e/a'])
def test_reference_traversal_rejected(tmp_path,name):
    with pytest.raises(ConsoleError):data_file(tmp_path,name)

def test_nonfinite_and_deep_json_rejected(tmp_path):
    p=tmp_path/'a.json';p.write_text('{"value":1e999}')
    with pytest.raises(ConsoleError):decode(p)
    p.write_text('['*100+'0'+']'*100)
    with pytest.raises(ConsoleError):decode(p)

@pytest.mark.parametrize('name',['../outside.model3.json','code.js','voice.wav'])
def test_untrusted_zip_never_executes_or_escapes(tmp_path,name):
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:z.writestr(name,'{}')
    with pytest.raises(ConsoleError):ModelResources(tmp_path).import_zip(stream.getvalue(),ImportInfo(character='rem',name='test',license_note='test only',confirm_rights=True))
    assert not (tmp_path/'models').exists()

def test_model_identity_cannot_fake_named_character(tmp_path):
    b,v,s=model(tmp_path)
    c=LiveCompanion.__new__(LiveCompanion);c.resources=s
    with pytest.raises(ConsoleError,match='Haru'):c.save_settings(CompanionSettings(profiles={'rem':Profile(model_id='test')}))

def test_private_scope_does_not_read_canon(tmp_path):
    calls=[]
    real=SimpleNamespace(engine=tmp_path,get=lambda p:calls.append(p))
    reg=PrivateRegistry(tmp_path,real)
    a='novel_'+'a'*32;b='novel_'+'b'*32
    first=reg.workspace('companion-yoshino-'+a);second=reg.workspace('companion-rem-'+a);third=reg.workspace('companion-yoshino-'+b)
    assert len({first.root,second.root,third.root})==3
    with pytest.raises(ConsoleError):reg.workspace('../Canon')
    assert calls==[a,a,b]

def test_public_runtime_is_not_in_frontend_build():
    root=Path(__file__).resolve().parents[3]
    assert {p.name for p in (root/'web/frontend/public/live2d').iterdir()}=={'frame.html','frame.mjs'}
    assert 'import(\'/api/studio/live2d/runtime/l2d.js\')' in (root/'web/frontend/public/live2d/frame.mjs').read_text()


@pytest.mark.parametrize('ratio',[0,-1,True,11,'portrait'])
def test_invalid_canvas_aspect_rejected(tmp_path,ratio):
    b,v,s=model(tmp_path)
    (b/'slot.json').write_text(json.dumps({'model':'test.model3.json','character':'haru','canvas_aspect':ratio}))
    with pytest.raises(ConsoleError):s.model('test')


def test_private_import_preserves_only_safe_display_metadata(tmp_path):
    b,v,s=model(tmp_path/'source')
    slot={'model':'test.model3.json','character':'haru','canvas_aspect':2/3}
    stream=io.BytesIO()
    with zipfile.ZipFile(stream,'w') as z:
        for file in b.iterdir():
            if file.name!='slot.json':z.writestr(file.name,file.read_bytes())
        z.writestr('slot.json',json.dumps(slot))
    result=ModelResources(tmp_path/'target').import_zip(stream.getvalue(),ImportInfo(character='rem',name='Author choice',license_note='Private test',confirm_rights=True))
    assert result['canvas_aspect']==2/3 and result['character']=='rem' and result['name']=='Author choice'


def test_pet_placement_keeps_previous_companion_settings_compatible(tmp_path):
    import threading
    c=LiveCompanion.__new__(LiveCompanion);c.home=tmp_path;c.lock=threading.RLock()
    c.save_settings(CompanionSettings(pet_x=.25,pet_y=.6,pet_passthrough=True))
    persisted=json.loads((tmp_path/'companion-settings.json').read_text('utf8'))
    assert not {'pet_x','pet_y','pet_passthrough'}.intersection(persisted)
    assert persisted['character']=='yoshino' and persisted['profiles']['rem']['model_id']==''
    settings=c.settings();assert settings.pet_x==.25 and settings.pet_y==.6 and settings.pet_passthrough
    from pydantic import ValidationError
    with pytest.raises(ValidationError):CompanionSettings(pet_x=2)


def test_behavior_mapping_must_reference_real_motion(tmp_path):
    b,v,s=model(tmp_path)
    meta=json.loads((b/'slot.json').read_text())
    meta['behaviors']={'nod':{'group':'Invented','index':0}}
    (b/'slot.json').write_text(json.dumps(meta))
    with pytest.raises(ConsoleError,match='绑定已有动作'):s.model('test')
    meta['behaviors']={'shell':{'group':'Anything','index':0}}
    (b/'slot.json').write_text(json.dumps(meta))
    with pytest.raises(ConsoleError,match='白名单'):s.model('test')


def test_duet_scope_is_separate_from_private_conversations(tmp_path):
    real=SimpleNamespace(engine=tmp_path,get=lambda p:None)
    reg=PrivateRegistry(tmp_path,real)
    paths=[reg.workspace('companion-'+char).root for char in ['duet','yoshino','rem']]
    assert len(set(paths))==3
    with pytest.raises(ConsoleError):reg.workspace('companion-duet-other-project')


def test_behavior_settings_do_not_break_previous_release(tmp_path):
    import threading
    c=LiveCompanion.__new__(LiveCompanion);c.home=tmp_path;c.lock=threading.RLock()
    c.save_settings(CompanionSettings(duet=True,quiet=True,autonomous=False,partner_x=.3))
    assert c.settings().duet and c.settings().quiet and not c.settings().autonomous
    stored=json.loads((tmp_path/'companion-settings.json').read_text())
    assert not {'duet','quiet','autonomous','partner_x'}.intersection(stored)
