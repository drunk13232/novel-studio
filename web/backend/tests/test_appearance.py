"""Bounded visual preferences; all HTTP writes use a temporary application root."""
import hashlib,json
from types import SimpleNamespace
from pathlib import Path
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fastapi.responses import JSONResponse
from pydantic import ValidationError
from app.appearance import THEME_IDS,DARK_THEMES,ThemeCustomization
from app.assistant.models import Theme,Context
from app.studio import Preferences,studio_routes,scoped_preferences
from app.errors import ConsoleError


def client_for(tmp_path,monkeypatch,registry=None):
    workspace=tmp_path/'engine';workspace.mkdir()
    data=tmp_path/'data';monkeypatch.setenv('NOVEL_STUDIO_DATA',str(data))
    app=FastAPI();app.include_router(studio_routes(registry or SimpleNamespace(),None,SimpleNamespace(workspace=workspace)))
    @app.exception_handler(ConsoleError)
    async def console_error(_request,error):
        return JSONResponse(error.payload(),status_code=error.status)
    namespace=hashlib.sha256(str(workspace.resolve()).casefold().encode()).hexdigest()[:20]
    return TestClient(app),data/namespace/'preferences.json'


@pytest.mark.parametrize('theme',THEME_IDS)
def test_existing_action_and_context_accept_exact_theme_id(theme):
    assert Theme(theme=theme).theme==theme
    assert Context(theme=theme).theme==theme
    assert Preferences(appearance=theme).appearance==theme


def test_preview_is_not_persisted_and_theme_roundtrip_preserves_other_preferences(tmp_path,monkeypatch):
    client,path=client_for(tmp_path,monkeypatch)
    original=Preferences(font_family='KaiTi',font_size=22,line_height=2.1,appearance='rem-night').model_dump()
    assert client.put('/api/studio/preferences',json=original).status_code==200
    before=path.read_bytes()
    # Only explicit Apply uses the existing preferences endpoint. A read cannot
    # commit a frontend preview or mutate author font/save settings.
    assert client.get('/api/studio/preferences').json()['preferences']['appearance']=='rem-night'
    assert path.read_bytes()==before
    changed={**original,'appearance':'gothic','previous_appearance':'rem-night','theme_favorites':['gothic','ink'],'theme_customizations':{'gothic':{'accent':'#d8ba94','radius':8,'decoration':40,'motion':0,'density':'compact'}}}
    assert client.put('/api/studio/preferences',json=changed).status_code==200
    restored=client.get('/api/studio/preferences').json()['preferences']
    assert restored['appearance']=='gothic' and restored['theme']=='dark'
    assert restored['font_family']=='KaiTi' and restored['font_size']==22 and restored['line_height']==2.1
    assert restored['theme_favorites']==['gothic','ink']
    assert restored['theme_customizations']['gothic']['motion']==0
    assert scoped_preferences(restored,'public')['theme_customizations']==restored['theme_customizations']


def test_unknown_saved_skin_falls_back_without_rewriting_disk(tmp_path,monkeypatch):
    client,path=client_for(tmp_path,monkeypatch);path.parent.mkdir(parents=True)
    original={'appearance':'unavailable-old-skin','theme':'dark','font_family':'SimSun'}
    path.write_text(json.dumps(original),'utf8');before=path.read_bytes()
    assert client.get('/api/studio/preferences').json()['preferences']['appearance']=='night'
    assert path.read_bytes()==before


@pytest.mark.parametrize('bad',[{'accent':'url(https://example.org/private)'},{'background':'red;display:none'},{'radius':500},{'motion':-1},{'asset_url':'https://example.org/model'},{'script':'alert(1)'},{'name':'bad\nname'},{'density':'invisible'}])
def test_untrusted_customization_is_rejected(bad):
    with pytest.raises(ValidationError):ThemeCustomization.model_validate(bad)


def test_unknown_theme_and_oversized_map_rejected():
    with pytest.raises(ValidationError):Preferences(appearance='url(https://example.org)')
    with pytest.raises(ValidationError):Preferences(theme_customizations={'unknown':{}})
    assert {'observatory','gothic','cyber'}<=DARK_THEMES


def test_project_theme_roundtrip_and_backup_scope(tmp_path,monkeypatch):
    registry=SimpleNamespace(get=lambda project: {'id':project})
    client,path=client_for(tmp_path,monkeypatch,registry)
    original=Preferences(appearance='moon',font_family='KaiTi',workspaces={
        'draft-a':{'appearance':'ink','appearance_customizations':{'ink':{'accent':'#123456','radius':2}},'tabs':[],'closed':[],'layout':{'manuscript':65,'reference':35}},
        'draft-b':{'appearance':'gothic','tabs':[],'simple_navigation':False},
    }).model_dump()
    assert client.put('/api/studio/preferences',json=original).status_code==200
    restored=client.get('/api/studio/preferences').json()['preferences']
    assert restored['appearance']=='moon' and restored['font_family']=='KaiTi'
    assert restored['workspaces']['draft-a']['appearance']=='ink'
    assert restored['workspaces']['draft-a']['appearance_customizations']['ink']['accent']=='#123456'
    assert restored['theme_customizations']=={}
    assert restored['workspaces']['draft-b']['appearance']=='gothic'
    scoped=scoped_preferences(restored,'draft-a')
    assert set(scoped['workspaces'])=={'draft-a'}
    assert scoped['workspaces']['draft-a']['appearance']=='ink'
    # Removing the optional override follows the global theme without moving data.
    del restored['workspaces']['draft-a']['appearance']
    assert client.put('/api/studio/preferences',json=restored).status_code==200
    persisted=json.loads(path.read_text('utf8'))['workspaces']['draft-a']
    assert 'appearance' not in persisted
    assert persisted['appearance_customizations']['ink']['accent']=='#123456'
    assert client.get('/api/studio/preferences').json()['preferences']['workspaces']['draft-b']['appearance']=='gothic'


@pytest.mark.parametrize('bad',['not-a-theme','url(https://example.org)',{'script':'run'},None])
def test_invalid_project_theme_does_not_overwrite_preferences(tmp_path,monkeypatch,bad):
    client,path=client_for(tmp_path,monkeypatch,SimpleNamespace(get=lambda project:{'id':project}))
    original=Preferences().model_dump()
    assert client.put('/api/studio/preferences',json=original).status_code==200
    before=path.read_bytes()
    candidate={**original,'workspaces':{'draft-a':{'appearance':bad}}}
    assert client.put('/api/studio/preferences',json=candidate).status_code==422
    assert path.read_bytes()==before


@pytest.mark.parametrize('bad',[{'ink':{'script':'run'}},{'unknown':{}},{'ink':{'background':'url(https://example.org)'}},None])
def test_untrusted_project_customization_rejected_without_write(tmp_path,monkeypatch,bad):
    client,path=client_for(tmp_path,monkeypatch,SimpleNamespace(get=lambda project:{'id':project}))
    original=Preferences().model_dump()
    assert client.put('/api/studio/preferences',json=original).status_code==200
    before=path.read_bytes()
    candidate={**original,'workspaces':{'draft-a':{'appearance':'ink','appearance_customizations':bad}}}
    assert client.put('/api/studio/preferences',json=candidate).status_code==422
    assert path.read_bytes()==before


def test_backup_and_model_validation_cannot_bypass_project_theme_whitelist():
    candidate={'workspaces':{'draft-a':{'appearance':'ink','appearance_customizations':{'ink':{'background':'url(https://invalid.example)'}}}}}
    with pytest.raises(ValidationError):Preferences.model_validate(candidate)
    with pytest.raises(ValidationError):scoped_preferences(candidate,'draft-a')


def test_unknown_saved_project_theme_falls_back_without_disk_rewrite(tmp_path,monkeypatch):
    client,path=client_for(tmp_path,monkeypatch);path.parent.mkdir(parents=True)
    value={'appearance':'moon','workspaces':{'draft-a':{'appearance':'future-skin','appearance_customizations':{'future-skin':{'radius':2},'ink':{'motion':0}}}}}
    path.write_text(json.dumps(value),'utf8');before=path.read_bytes()
    restored=client.get('/api/studio/preferences').json()['preferences']
    assert 'appearance' not in restored['workspaces']['draft-a']
    assert restored['workspaces']['draft-a']['appearance_customizations']=={'ink':{'motion':0}}
    assert path.read_bytes()==before
