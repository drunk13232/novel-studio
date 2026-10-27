"""Small integration entry for existing narrative/reader services, no AI engine."""
from fastapi import APIRouter, Query
from .narrative_curve import NarrativeCurve
from .reader_personas import ReaderPersonas
from .insight_models import CurveAnalyze,CurveOverride,CurveSettings,PersonaSave,PersonaRemove,ReaderPrepare,ReaderApprove,ReaderNext,ReaderRetry

class CreativeInsights:
    def __init__(self,tools,matrix,reviews):
        self.curve=NarrativeCurve(tools,matrix)
        self.readers=ReaderPersonas(reviews,self.curve)

def routes(service):
    router=APIRouter(prefix='/api/projects/{p}/creative-insights')
    @router.get('/curve')
    def curve(p:str):return service.curve.index(p)
    @router.post('/curve/analyze')
    def analyze(p:str,b:CurveAnalyze):return service.curve.analyze(p,b)
    @router.put('/curve/override')
    def override(p:str,b:CurveOverride):return service.curve.override(p,b)
    @router.put('/curve/settings')
    def settings(p:str,b:CurveSettings):return service.curve.settings(p,b)
    @router.get('/readers')
    def readers(p:str):return service.readers.index(p)
    @router.put('/readers/personas')
    def save(p:str,b:PersonaSave):return service.readers.save(p,b)
    @router.delete('/readers/personas/{id}')
    def remove(p:str,id:str,b:PersonaRemove):return service.readers.remove(p,id,b)
    @router.post('/readers/prepare')
    def prepare(p:str,b:ReaderPrepare):return service.readers.prepare(p,b)
    @router.get('/readers/panels/{id}')
    def panel(p:str,id:str,chunk:int=Query(default=0,ge=0,le=1000)):return service.readers.get(p,id,chunk)
    @router.post('/readers/panels/{id}/approve')
    def approve(p:str,id:str,b:ReaderApprove):return service.readers.approve(p,id,b)
    @router.post('/readers/panels/{id}/next',status_code=202)
    async def next_(p:str,id:str,b:ReaderNext):return await service.readers.next(p,id,b)
    @router.post('/readers/panels/{id}/retry')
    def retry(p:str,id:str,b:ReaderRetry):return service.readers.retry(p,id,b)
    return router
