import {ResponsiveContainer,LineChart,Line,CartesianGrid,XAxis,YAxis,Tooltip,BarChart,Bar,Cell,ReferenceLine} from 'recharts';
import {t,useUiTranslation} from './i18n';

export default function WritingChart({rows,type,animate,valueName}:{rows:Record<string,any>[];type:'line'|'bar';animate:boolean;valueName?:string}) {
 useUiTranslation('dashboard');
 const name = valueName || t('dashboard:writingDashboard.netCharacters');
 const grid = <CartesianGrid stroke="var(--line)" vertical={false}/>;
 const axis = <YAxis stroke="var(--muted)" width={50}/>;
 const tooltip = <Tooltip contentStyle={{background:'var(--panel)',color:'var(--ink)',borderColor:'var(--line)',borderRadius:8}} labelStyle={{color:'var(--ink)'}}/>;
 return <div className="wd-chart" role="img" aria-label={name}>
  <ResponsiveContainer width="100%" height={230}>{type === 'line' ? <LineChart data={rows} accessibilityLayer>{grid}<XAxis dataKey="date" tickFormatter={value => value.slice(5)} stroke="var(--muted)"/>{axis}{tooltip}<ReferenceLine y={0} stroke="var(--line)"/><Line isAnimationActive={animate} type="monotone" dataKey="han" name={name} stroke="var(--accent)" strokeWidth={2} dot={false}/></LineChart> : <BarChart data={rows} accessibilityLayer>{grid}<XAxis dataKey="label" stroke="var(--muted)" minTickGap={20}/>{axis}{tooltip}<ReferenceLine y={0} stroke="var(--line)"/><Bar isAnimationActive={animate} dataKey="han" name={name} radius={[3,3,0,0]}>{rows.map((row,index) => <Cell key={index} fill={row.han < 0 ? 'var(--wd-negative,var(--gold))' : 'var(--accent)'}/>)}</Bar></BarChart>}</ResponsiveContainer>
 </div>;
}
