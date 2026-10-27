from pathlib import Path
import json
import pytest
from PIL import Image
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.companion import companion_routes,assert_public_resources
from app.errors import ConsoleError
from fastapi.responses import JSONResponse

def setup(tmp_path):
    personal=tmp_path/'personal';public=tmp_path/'public'
    personal.mkdir();public.mkdir()
    (public/'manifest.json').write_text('{"schema_version":1,"yoshino":null,"rem":null}')
    (public/'README.txt').write_text('Resource slots')
    app=FastAPI();app.include_router(companion_routes(personal,public))
    @app.exception_handler(ConsoleError)
    async def error(req,err):return JSONResponse({'detail':str(err)},err.status)
    return personal,public,TestClient(app)

def test_real_raster_and_named_slots(tmp_path):
    personal,public,client=setup(tmp_path)
    Image.new('RGBA',(32,48),(40,60,80,180)).save(personal/'rem.png')
    (personal/'manifest.json').write_text(json.dumps({'schema_version':1,'rem':'rem.png'}))
    body=client.get('/api/studio/companion/manifest').json()
    assert body['assets']['rem']['source']=='personal'
    assert body['assets']['yoshino']['status']=='missing'
    image=client.get(body['assets']['rem']['url']);assert image.status_code==200
    assert image.headers['content-type']=='image/png'
    assert image.content==(personal/'rem.png').read_bytes()
    assert str(tmp_path) not in json.dumps(body)

@pytest.mark.parametrize('name',['../private.png','https://example.org/rem.png','secret.svg','bad.png'])
def test_unsafe_or_corrupt_resources_are_not_served(tmp_path,name):
    personal,public,client=setup(tmp_path)
    (personal/'bad.png').write_text('not an image')
    (personal/'manifest.json').write_text(json.dumps({'schema_version':1,'rem':name}))
    assert client.get('/api/studio/companion/manifest').json()['assets']['rem']['status']=='missing'
    assert client.get('/api/studio/companion/rem').status_code==404
    assert client.get('/api/studio/companion/auth.json').status_code==404

def test_reload_and_public_build_guard(tmp_path):
    personal,public,client=setup(tmp_path);assert_public_resources(public)
    (personal/'manifest.json').write_text(json.dumps({'schema_version':1,'rem':'rem.png'}))
    Image.new('RGBA',(32,48),(40,60,80,180)).save(personal/'rem.png')
    first=client.get('/api/studio/companion/manifest').json()['assets']['rem']['url']
    Image.new('RGBA',(32,48),(80,90,100,180)).save(personal/'rem.png')
    assert client.get('/api/studio/companion/manifest').json()['assets']['rem']['url']!=first
    (public/'personal.png').write_bytes((personal/'rem.png').read_bytes())
    with pytest.raises(RuntimeError):assert_public_resources(public)
