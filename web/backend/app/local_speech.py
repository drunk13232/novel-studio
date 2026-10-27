"""One owned SAPI5 COM apartment. System synthesizer, offline, no voice models."""
import queue,threading,time,uuid
from concurrent.futures import Future
from fastapi import APIRouter
from pydantic import BaseModel,Field,ConfigDict
from app.errors import ConsoleError

class SpeechRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    text:str=Field(default='',max_length=200000)
    voice:str=''
    rate:int=Field(default=0,ge=-10,le=10)
    volume:int=Field(default=100,ge=0,le=100)
    owner:str=Field(default='',max_length=180)
    path:str=''
    revision:str=''
    project:str=''
class RecognitionRequest(BaseModel):
    model_config=ConfigDict(extra='forbid')
    owner:str=Field(min_length=1,max_length=180)
    language:str=Field(default='zh-CN',pattern=r'^(zh-CN|en-US|ja-JP)$')
    duration:int=Field(default=25,ge=5,le=45)
class RecognitionOwner(BaseModel):
    model_config=ConfigDict(extra='forbid')
    owner:str=Field(min_length=1,max_length=180)
    id:str=Field(min_length=32,max_length=32,pattern=r'^[0-9a-f]{32}$')
class LocalSpeech:
    def __init__(self):
        self.recognition={'available':False,'engines':[],'state':'IDLE','owner':'','id':'','text':'','error':None}
        self.commands=queue.Queue();self.lock=threading.RLock();self.thread=None;self.active_stream=None;self.info={'available':False,'voices':[],'state':'STOPPED','paragraph':-1,'error':None,'project':'','path':'','revision':'','owner':'','mouth':0.0,'viseme':0,'viseme_events':0,'visemes_available':False}
    def start(self):
        if not self.thread:
            self.thread=threading.Thread(target=self.worker,name='NovelStudio-SAPI5',daemon=True);self.thread.start()
    def status(self):
        self.start()
        with self.lock:return {**self.info,'recognition':dict(self.recognition)}
    def command(self,action,body=None):
        self.start();future=Future();self.commands.put((action,body or {},future))
        try:return future.result(timeout=10)
        except TimeoutError:raise ConsoleError('系统朗读暂未响应，请稍后重试',503)
    def worker(self):
        voice=None;events=None;paragraphs=[];current=-1;paused=False
        recognizer=reco_context=grammar=reco_events=audio_stream=None;reco_deadline=0
        def release_recognition():
            nonlocal recognizer,reco_context,grammar,reco_events,audio_stream
            if grammar:
                try:grammar.DictationSetState(0)
                except Exception:pass
            if recognizer:
                try:recognizer.State=3
                except Exception:pass
            if reco_events:reco_events.disconnect()
            reco_events=grammar=reco_context=recognizer=None
            if audio_stream:
                try:audio_stream.Close()
                except Exception:pass
            audio_stream=None

        try:
            import comtypes
            from comtypes.client import CreateObject
            from comtypes.messageloop import PeekMessage,TranslateMessage,DispatchMessage
            from ctypes import byref
            from ctypes.wintypes import MSG
            message=MSG()
            comtypes.CoInitialize();voice=CreateObject('SAPI.SpVoice');tokens=voice.GetVoices();voices=[]
            from comtypes.client import GetEvents
            from comtypes.gen import SpeechLib
            parent=self
            class VoiceEvents:
                def _ISpeechVoiceEvents_Viseme(self,*args):
                    code=int(args[-1]);opening={0:0,1:.5,2:.75,3:.7,4:.55,5:.5,6:.65,7:.4,8:.5,9:.55,10:.6,11:.7,12:.1,13:.25,14:.3,15:.15,16:.4,17:.3,18:.25,19:.2,20:.25,21:.05}.get(code,0)
                    with parent.lock:
                        if parent.info['state']=='PLAYING' and args[0]==parent.active_stream:parent.info.update(viseme=code,mouth=opening,viseme_events=parent.info['viseme_events']+1,visemes_available=True)
                def _ISpeechVoiceEvents_EndStream(self,*args):
                    with parent.lock:
                        if args[0]==parent.active_stream:parent.info.update(mouth=0.0,viseme=0)
            try:
                events=GetEvents(voice,VoiceEvents());voice.EventInterests=voice.EventInterests|256|4
                self.info['events_connected']=True
            except Exception:
                self.info['visemes_available']=False
            for i in range(tokens.Count):
                token=tokens.Item(i);languages=token.GetAttribute('Language');codes=[x.lower() for x in languages.split(';')];voices.append({'id':token.Id,'name':token.GetDescription(),'language':languages,'chinese':any(x in {'804','404','c04','1004','1404'} for x in codes)})
            with self.lock:self.info.update(available=True,voices=voices,error=None,output=voice.AudioOutput.GetDescription())
            try:
                probe=CreateObject('SAPI.SpInprocRecognizer');engines=probe.GetRecognizers();installed=[]
                for i in range(engines.Count):
                    token=engines.Item(i);installed.append({'id':token.Id,'name':token.GetDescription(),'language':token.GetAttribute('Language')})
                self.recognition.update(available=bool(installed),engines=installed);del probe
            except Exception:self.recognition.update(error='系统离线识别引擎不可用；可继续文字输入')
        except Exception as e:
            with self.lock:self.info.update(error='Windows SAPI5 不可用：'+str(e),available=False)
        while True:
            try:action,body,future=self.commands.get(timeout=.03)
            except queue.Empty:action=None
            if action:
                try:
                    if action=='close':
                        release_recognition()
                        if voice:
                            if paused:voice.Resume()
                            self.active_stream=None;voice.Speak('',3)
                        future.set_result({'stopped':True});break
                    if not voice:raise ConsoleError(self.info['error'] or '系统语音不可用',503)
                    if action.startswith('recognition_'):
                        if action=='recognition_start':
                            if self.recognition['state']=='LISTENING':raise ConsoleError('麦克风正由另一轮识别使用，请先停止',409)
                            if self.info['state'] in {'PLAYING','PAUSED'}:
                                if self.info.get('owner')!=body['owner']:raise ConsoleError('其他任务正在朗读，请先停止它以避免回声',409)
                                if paused:voice.Resume();paused=False
                                voice.Speak('',3);paragraphs=[];self.active_stream=None;self.info.update(state='STOPPED',mouth=0.0)
                            release_recognition();recognizer=CreateObject('SAPI.SpInprocRecognizer');engines=recognizer.GetRecognizers()
                            code={'zh-CN':'804','en-US':'409','ja-JP':'411'}[body.get('language','zh-CN')]
                            engine=next((engines.Item(i) for i in range(engines.Count) if code in engines.Item(i).GetAttribute('Language').lower().split(';')),None)
                            if not engine:raise ConsoleError('没有此语言的离线识别引擎，可在 Windows 中安装语言语音组件；文字输入可继续',503)
                            recognizer.Recognizer=engine
                            if body.get('audio_file'):
                                # Internal verification only; HTTP schema never accepts file paths.
                                audio_stream=CreateObject('SAPI.SpFileStream');audio_stream.Open(body['audio_file'],0);recognizer.AudioInputStream=audio_stream
                            reco_context=recognizer.CreateRecoContext();identifier=uuid.uuid4().hex
                            class RecognitionEvents:
                                def _ISpeechRecoContextEvents_Recognition(self,*args):
                                    if parent.recognition['id']!=identifier or parent.recognition['state']!='LISTENING':return
                                    result=args[-1];text=result.PhraseInfo.GetText()
                                    with parent.lock:parent.recognition.update(state='FINISHED',text=text[:4000],confidence=float(result.PhraseInfo.Rule.EngineConfidence),elapsed_ms=round((time.monotonic()-rec_started)*1000,1))
                                def _ISpeechRecoContextEvents_FalseRecognition(self,*args):
                                    if parent.recognition['id']==identifier and parent.recognition['state']=='LISTENING':
                                        parent.recognition.update(state='NO_MATCH',error='未识别到清晰语音，请重试或使用文字输入')
                            rec_started=time.monotonic();reco_events=GetEvents(reco_context,RecognitionEvents(),interface=SpeechLib._ISpeechRecoContextEvents);reco_context.EventInterests=16|512
                            grammar=reco_context.CreateGrammar(1);grammar.DictationLoad();self.recognition.update(state='LISTENING',owner=body['owner'],id=identifier,text='',error=None,confidence=None)
                            grammar.DictationSetState(1);recognizer.State=1;reco_deadline=time.monotonic()+body.get('duration',25)
                        elif action=='recognition_stop':
                            if body.get('owner')!=self.recognition['owner'] or body.get('id')!=self.recognition['id']:raise ConsoleError('识别请求已更换，未停止其他会话麦克风',409)
                            self.recognition.update(state='CANCELLED',text='');release_recognition()
                        elif action!='recognition_status':raise ConsoleError('未知语音识别操作',422)
                        future.set_result(dict(self.recognition));continue
                    if action in {'pause','resume','stop'} and body.get('owner') and self.info.get('owner')!=body['owner']:raise ConsoleError('当前朗读属于另一项任务，未停止或修改它',409)
                    if action=='start':
                        token=next((tokens.Item(i) for i in range(tokens.Count) if tokens.Item(i).Id==body.get('voice')),None)
                        if token is None:raise ConsoleError('请选择可用的本地声音',422)
                        if self.recognition['state']=='LISTENING':
                            if body.get('owner')!=self.recognition['owner']:raise ConsoleError('其他会话正在使用麦克风',409)
                            self.recognition.update(state='CANCELLED',text='');release_recognition()
                        if body.get('owner') and self.info['state'] in {'PLAYING','PAUSED'} and self.info.get('owner')!=body['owner']:raise ConsoleError('正在朗读其他任务，请先由原任务停止',409)
                        if paused:voice.Resume();paused=False
                        self.active_stream=None;voice.Speak('',3)
                        voice.Voice=token;voice.Rate=body.get('rate',0);voice.Volume=body.get('volume',100);paragraphs=[x for x in body['text'].splitlines() if x.strip()];current=-1
                        with self.lock:self.info.update(state='PLAYING',owner=body.get('owner',''),mouth=0.0,viseme=0,project=body.get('project',''),path=body.get('path',''),revision=body.get('revision',''),paragraph=-1,error=None)
                    elif action=='pause':
                        if self.info['state']=='PLAYING':voice.Pause();paused=True;self.info.update(state='PAUSED',mouth=0.0)
                    elif action=='resume':
                        if paused:voice.Resume();paused=False;self.info['state']='PLAYING'
                    elif action=='stop':
                        if paused:voice.Resume();paused=False
                        self.active_stream=None;voice.Speak('',3);paragraphs=[];self.info.update(state='STOPPED',paragraph=-1,mouth=0.0,viseme=0)
                    elif action=='rate':voice.Rate=body['rate']
                    else:raise ConsoleError('未知朗读操作',422)
                    future.set_result(self.status())
                except Exception as e:
                    if action and action.startswith('recognition_') and action!='recognition_stop':
                        self.recognition.update(state='ERROR',error='语音识别未启动或中断，请检查麦克风、语言组件和 Windows 权限；仍可使用文字输入');release_recognition()
                    future.set_exception(e)
            if voice:
                try:
                    while PeekMessage(byref(message),None,0,0,1):
                        TranslateMessage(byref(message));DispatchMessage(byref(message))
                    if recognizer and self.recognition['state']=='LISTENING' and time.monotonic()>reco_deadline:self.recognition.update(state='TIMEOUT',error='未收到完整语音，已释放麦克风；可重试或改用文字')
                    if recognizer and self.recognition['state']!='LISTENING':release_recognition()
                    if self.info['state']=='PLAYING' and not paused and voice.Status.RunningState==1:
                        current+=1
                        if current<len(paragraphs):self.active_stream=voice.Speak(paragraphs[current],1);self.info['paragraph']=current
                        else:self.info.update(state='STOPPED',paragraph=-1,mouth=0.0,viseme=0)
                except Exception as e:
                    self.info.update(state='STOPPED',mouth=0.0,viseme=0,error=str(e));paragraphs=[]
        release_recognition()
        if events:events.disconnect()
        if voice:
            del voice
            comtypes.CoUninitialize()
    def close(self):
        if self.thread:
            try:self.command('close')
            except Exception:pass
            self.thread.join(timeout=3)
def speech_routes(service):
    router=APIRouter(prefix='/api/studio/speech')
    @router.get('')
    def status():return service.status()
    @router.get('/recognition/status')
    def recognition_status():return service.command('recognition_status')
    @router.post('/recognition/start')
    def recognize(b:RecognitionRequest):return service.command('recognition_start',b.model_dump())
    @router.post('/recognition/stop')
    def stop_recognition(b:RecognitionOwner):return service.command('recognition_stop',b.model_dump())
    @router.post('/{action}')
    def command(action:str,b:SpeechRequest):return service.command(action,b.model_dump())
    return router
