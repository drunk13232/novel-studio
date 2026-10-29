"""Official MCP stdio protocol adapter; no files, prompts, resources or business IO."""
from app.version import release_info
import asyncio,json,os,sys,uuid
from urllib.parse import urlsplit
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types
async def serve():
    base=os.environ.pop('NOVEL_MCP_URL','');token=os.environ.pop('NOVEL_MCP_CAP','')
    url=urlsplit(base)
    if url.scheme!='http' or url.hostname!='127.0.0.1' or not url.port or url.path or url.query or url.username or len(token)<32:raise RuntimeError('Invalid scoped MCP bootstrap')
    async with httpx.AsyncClient(base_url=base,headers={'X-Novel-MCP':token},trust_env=False,follow_redirects=False,timeout=45) as client:
        response=await client.get('/tools');response.raise_for_status();definitions=response.json()['tools'];schemas={d['name']:d['parameters'] for d in definitions}
        async def listing(ctx,params):
            return types.ListToolsResult(tools=[types.Tool(name=d['name'],description=d['description'],inputSchema=d['parameters'],annotations=types.ToolAnnotations(readOnlyHint=d['name'] in {'list_projects','search_characters','get_project_status','read_chapter','read_chapter_candidate','read_creative_writing','get_approved_writing_context','list_chapters'},destructiveHint=False,openWorldHint=False)) for d in definitions])
        async def calling(ctx,params):
            if params.name not in schemas:return types.CallToolResult(isError=True,content=[types.TextContent(type='text',text='Unregistered application action')])
            try:
                context=await client.get('/context');context.raise_for_status()
                result=await client.post('/call',json={'session_id':context.json()['session_id'],'name':params.name,'arguments':params.arguments or {},'call_id':uuid.uuid4().hex});result.raise_for_status();value=result.json()
                return types.CallToolResult(isError=not (value.get('ok') or value.get('pending_confirmation')),content=[types.TextContent(type='text',text=json.dumps(value,ensure_ascii=False))],structuredContent=value)
            except Exception:return types.CallToolResult(isError=True,content=[types.TextContent(type='text',text='应用调用未完成；请检查会话状态，不自动重试草稿写入。')])
        server=Server('NovelStudio',version=release_info()['version'],on_list_tools=listing,on_call_tool=calling,get_tool_input_schema=schemas.get)
        async with stdio_server() as (reader,writer):await server.run(reader,writer,server.create_initialization_options())
def main():
    # Console-less PyInstaller workers still have inherited OS pipe handles.
    if sys.platform=='win32' and (sys.stdin is None or sys.stdout is None):
        # Windowed bootloaders leave Python streams None. Bind only the inherited
        # Win32 pipes, then let the official MCP SDK own protocol framing.
        import msvcrt,win32api
        if sys.stdin is None:sys.stdin=os.fdopen(msvcrt.open_osfhandle(win32api.GetStdHandle(win32api.STD_INPUT_HANDLE),os.O_RDONLY),'r',encoding='utf8')
        if sys.stdout is None:sys.stdout=os.fdopen(msvcrt.open_osfhandle(win32api.GetStdHandle(win32api.STD_OUTPUT_HANDLE),os.O_WRONLY),'w',encoding='utf8')
    if sys.stderr is None:sys.stderr=open(os.devnull,'w')
    asyncio.run(serve())
if __name__=='__main__':main()
