"""Only complete, unambiguous single UI commands use the existing local Action path."""
import re

def exact_action(text):
    text=text.strip().rstrip('。.!！')
    match=re.fullmatch(r'(?:请|帮我)?(?:切换(?:到|为)?|使用)(月白纸笺|月白|青岚书房|青岚|夜墨星河|芳乃|蕾姆|静蓝夜写|古典手稿|远山水墨|星图观测室|哥特藏书馆|赛博霓虹|森林温室|留白编辑室)(?:主题)?',text)
    if match:return 'set_theme',{'theme':{'月白纸笺':'moon','月白':'moon','青岚书房':'mist','青岚':'mist','夜墨星河':'night','芳乃':'yoshino','蕾姆':'rem','静蓝夜写':'rem-night','古典手稿':'manuscript','远山水墨':'ink','星图观测室':'observatory','哥特藏书馆':'gothic','赛博霓虹':'cyber','森林温室':'greenhouse','留白编辑室':'minimal'}[match[1]]}
    match=re.fullmatch(r'(?:请|帮我)?(?:把|将)?(?:正文)?字号(?:调到|改为|设置为|设为)(1[4-9]|2\d|3[0-2])(?:号|px)?',text)
    if match:return 'set_editor_font_size',{'size':int(match[1])}
    match=re.fullmatch(r'(?:请|帮我)?(?:打开|跳转到|跳到)第([0-9一二三四五六七八九十百零两]{1,6})章',text)
    if match:
        value=match[1]
        if value.isascii() and value.isdecimal():number=int(value)
        elif '百' not in value and '十' in value:
            parts=value.split('十')
            if len(parts)!=2:return None
            tens,ones=parts;digits={'一':1,'二':2,'两':2,'三':3,'四':4,'五':5,'六':6,'七':7,'八':8,'九':9};number=digits.get(tens,1)*10+digits.get(ones,0)
            if tens and tens not in digits or ones and ones not in digits:return None
        elif value in '一二三四五六七八九':number='一二三四五六七八九'.index(value)+1
        else:return None
        if 0<=number<=99999:return 'open_chapter',{'number':number}
    match=re.fullmatch(r'(?:请|帮我)?打开(人物|世界观|时间线|文献库|文风库|大纲|灵感箱|世界逻辑实验室|文学评审|角色工作台)(?:页面|面板)?',text)
    if match:return 'navigate_to_page',{'page':{'人物':'characters','世界观':'world','时间线':'timeline','文献库':'references','文风库':'styles','大纲':'outline','灵感箱':'notes','世界逻辑实验室':'worldlogic','文学评审':'literary','角色工作台':'roleplay'}[match[1]]}
    match=re.fullmatch(r'(?:请|帮我)?打开(通用|外观|写作|AI接口|模型分配|AI助手|生图|存储|备份|快捷键|帮助)设置',text,re.I)
    if match:return 'open_settings_section',{'section':{'通用':'general','外观':'appearance','写作':'writing','ai接口':'api','模型分配':'models','ai助手':'assistant','生图':'images','存储':'storage','备份':'backup','快捷键':'keys','帮助':'help'}[match[1].lower()]}
    return None
