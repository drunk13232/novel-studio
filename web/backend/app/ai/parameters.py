"""Explicit protocol mappings. Unknown or ineffective controls fail visibly."""
from urllib.parse import urlsplit
from app.errors import ConsoleError

SAMPLING=['temperature','top_p','top_k','frequency_penalty','presence_penalty','seed','stop']
def request_arguments(provider,model,params):
    cap=model.capabilities;args={'model':model.id,'stream':params.streaming and cap.get('streaming') is not False}
    deepseek=provider.provider_type=='deepseek' and urlsplit(provider.base_url).hostname=='api.deepseek.com'
    thinking=params.thinking=='enabled' or params.reasoning_effort not in {None,'none'}
    if params.reasoning_effort is not None:
        if cap.get('reasoning') is not True:raise ConsoleError('此模型的推理控制不受支持或尚未核实；请求未发送',422)
        if params.reasoning_effort not in model.reasoning_levels:raise ConsoleError('所选思考强度不在此模型已确认的档位中；未静默降级',422)
        args['reasoning' if model.protocol=='responses' else 'reasoning_effort']={'effort':params.reasoning_effort} if model.protocol=='responses' else params.reasoning_effort
    if params.thinking is not None:
        if not deepseek:raise ConsoleError('此协议没有已核实的独立 Thinking 开关；请使用支持的推理档位',422)
        if params.thinking=='disabled' and params.reasoning_effort not in {None,'none'}:raise ConsoleError('关闭思考与非空推理强度冲突，请只选择有效组合',422)
        if model.protocol=='responses':
            if params.thinking=='disabled':args['reasoning']={'effort':'none'}
            elif params.reasoning_effort is None:raise ConsoleError('Responses 开启思考时请选择已确认的强度',422)
        else:args['extra_body']={'thinking':{'type':params.thinking}}
    if deepseek and params.reasoning_effort is not None and model.protocol=='chat':
        args['extra_body']={'thinking':{'type':'disabled' if params.reasoning_effort=='none' else 'enabled'}}
    for name in SAMPLING:
        value=getattr(params,name)
        if value is None:continue
        if cap.get(name) is not True:raise ConsoleError(name+' 支持情况未确认或不支持；清除此设置后重试',422)
        rule=model.parameter_rules.get(name,{})
        if deepseek and thinking and name in {'temperature','presence_penalty','frequency_penalty'}:raise ConsoleError('DeepSeek 思考模式会忽略 '+name+'，请清除此无效设置',422)
        if rule.get('disabled_when_thinking') and thinking:raise ConsoleError('当前思考模式下 '+name+' 不生效，请清除此设置',422)
        if isinstance(value,(int,float)) and (value<rule.get('minimum',float('-inf')) or value>rule.get('maximum',float('inf'))):raise ConsoleError(name+' 超出此模型确认的参数范围',422)
        if name=='top_k':
            args.setdefault('extra_body',{})['top_k']=value
        else:args[name]=value
    if model.protocol=='responses' and any(k in args for k in ['stop','frequency_penalty','presence_penalty','seed']):raise ConsoleError('当前 Responses 适配未提供这些采样字段；请清除后重试',422)
    if params.max_output_tokens:
        if model.output_limit and params.max_output_tokens>model.output_limit:raise ConsoleError('输出上限超过模型已知限制',422)
        if model.protocol=='responses':args['max_output_tokens']=params.max_output_tokens
        elif model.chat_token_parameter:args[model.chat_token_parameter]=params.max_output_tokens
        else:raise ConsoleError('尚未配置此 Chat 模型支持的输出长度参数，请在模型设置中确认后再使用上限',422)
    return args
