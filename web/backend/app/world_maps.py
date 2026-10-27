"""Project-local map annotations; Bible and asset services remain authoritative."""
import json, re, threading
from typing import Literal
from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field, model_validator
from app.errors import ConsoleError
from app.library.storage import safe, read, write, digest, uid, now, checkpoint, write_guard

class Strict(BaseModel):
    model_config=ConfigDict(extra='forbid',allow_inf_nan=False)
class Point(Strict):
    x:float=Field(ge=0,le=1000)
    y:float=Field(ge=0,le=1000)
class Pin(Point):
    id:str=Field(pattern=r'^pin_[0-9a-f]{32}$')
    entity_id:str=Field(pattern=r'^entity_[0-9a-f]{32}$')
    label:str=Field(default='',max_length=100)
    child_map:str=Field(default='',pattern=r'^(?:map_[0-9a-f]{32})?$')
class Shape(Strict):
    id:str=Field(pattern=r'^shape_[0-9a-f]{32}$')
    name:str=Field(min_length=1,max_length=100)
    kind:Literal['route','region']='route'
    points:list[Point]=Field(min_length=2,max_length=200)
    @model_validator(mode='after')
    def polygon(self):
        if self.kind=='region' and len(self.points)<3:raise ValueError('A region needs three points')
        return self
class MapDefinition(Strict):
    id:str=Field(pattern=r'^map_[0-9a-f]{32}$')
    name:str=Field(min_length=1,max_length=100)
    parent_id:str=Field(default='',pattern=r'^(?:map_[0-9a-f]{32})?$')
    background:str=Field(default='',pattern=r'^(?:asset_[0-9a-f]{32})?$')
    scale_label:str=Field(default='',max_length=150)
    coordinate_label:str=Field(default='',max_length=150)
    pins:list[Pin]=Field(default_factory=list,max_length=500)
    shapes:list[Shape]=Field(default_factory=list,max_length=100)
class MapSave(Strict):
    etag:str=Field(max_length=64)
    maps:list[MapDefinition]=Field(default_factory=list,max_length=30)

class WorldMaps:
    def __init__(self,registry,bible,assets):self.registry=registry;self.bible=bible;self.assets=assets;self.lock=threading.RLock()
    def path(self,p):return safe(self.registry.workspace(p).root,'metadata/studio/world-maps.json')
    def get(self,p):
        target=self.path(p);raw=target.read_bytes() if target.exists() else b''
        try:
            stored=json.loads(raw.decode('utf-8-sig')) if raw else {'maps':[]}
            if not isinstance(stored,dict) or stored.get('schema_version',1)!=1:raise ValueError('unsupported map schema')
            MapSave(etag='',maps=stored.get('maps',[]))
        except (ValueError,TypeError):raise ConsoleError('地图文件损坏或版本不受支持；原文件保留，请从历史恢复',422,code='MAP_DAMAGED')
        entities={e['id']:e for e in self.bible.list(p)}
        return {**stored,'etag':digest(raw),'locations':[{'id':e['id'],'name':e['name'],'summary':e['summary'],'category':e['category'],'status':e['status']} for e in entities.values() if e['category'] in {'continent','region','city','town','building','location','geography'}], 'images':[{'id':a['id'],'name':a['name'],'width':a['width'],'height':a['height']} for a in self.assets.list(p)],'authority':'AUTHOR_MAP_NOT_STORY_FACT'}
    def save(self,p,body):
        with self.lock: # HTTP middleware already owns the shared OS mutation lease.
            target=self.path(p);current=self.get(p)
            if body.etag!=current['etag']:raise ConsoleError('地图已变化，请保留编辑并重新读取',409,code='MAP_STALE')
            ids=[m.id for m in body.maps]
            if len(ids)!=len(set(ids)):raise ConsoleError('地图 ID 重复',422,code='MAP_DUPLICATE')
            locations={e['id'] for e in current['locations']}
            parents={m.id:m.parent_id for m in body.maps}
            for item in body.maps:
                if item.background:self.assets.get(p,item.background)
                if item.parent_id and item.parent_id not in ids:raise ConsoleError('上级地图不存在',422,code='MAP_PARENT')
                seen=set();cursor=item.id
                while cursor:
                    if cursor in seen:raise ConsoleError('地图层级不能成环',422,code='MAP_CYCLE')
                    seen.add(cursor);cursor=parents.get(cursor,'')
                if len({pin.id for pin in item.pins})!=len(item.pins):raise ConsoleError('标记 ID 重复',422,code='MAP_PIN_ID')
                for pin in item.pins:
                    if pin.entity_id not in locations:raise ConsoleError('地点已移除或不属于本项目',409,code='MAP_LOCATION')
                    if pin.child_map==item.id:raise ConsoleError('地点不能链接回同一张地图作为子图',422,code='MAP_SELF_LINK')
                    if pin.child_map and pin.child_map not in ids:raise ConsoleError('标记的子地图不存在',422,code='MAP_CHILD')
                if len({shape.id for shape in item.shapes})!=len(item.shapes):raise ConsoleError('路线区域 ID 重复',422,code='MAP_SHAPE_ID')
            value={'schema_version':1,'maps':[m.model_dump() for m in body.maps],'updated_at':now()}
            if len(json.dumps(value,ensure_ascii=False).encode())>2*1024*1024:raise ConsoleError('地图数据超过 2 MiB',413,code='MAP_LIMIT')
            checkpoint(self.registry.workspace(p).root,'metadata/studio/world-maps.json','MAP_EDIT')
            write(target,value)
            return self.get(p)

def routes(service):
    router=APIRouter(prefix='/api/projects/{p}/world-maps')
    @router.get('')
    def get(p:str):return service.get(p)
    @router.put('')
    def put(p:str,body:MapSave):return service.save(p,body)
    return router
