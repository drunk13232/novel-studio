import {t as translateUI,useUiTranslation} from './i18n';
import {ResponsiveContainer,LineChart,Line,CartesianGrid,XAxis,YAxis,Tooltip} from 'recharts';
import {ReactFlow,Background,Controls,type Node,type Edge} from '@xyflow/react';
import dagre from '@dagrejs/dagre';
import '@xyflow/react/dist/style.css';
type D=Record<string,any>;
export function SensitivityChart({analysis}:{analysis:D}){
 useUiTranslation(["experiments"]);
const key=analysis.samples.find((v:D)=>v.outputs?.some((o:D)=>typeof o.value==='number'))?.outputs.find((o:D)=>typeof o.value==='number');if(!key)return <p>{translateUI("experiments:noPlottableNumericResults")}</p>;const rows=analysis.samples.map((v:D)=>({x:v.parameter,value:v.outputs.find((o:D)=>o.id===key.id)?.value??null}));return <div className="wll-chart"><p>{analysis.variable} → {key.name}（{key.unit}）</p><ResponsiveContainer width="100%" height={230}><LineChart data={rows}><CartesianGrid stroke="var(--line)"/><XAxis dataKey="x" type="number" domain={['dataMin','dataMax']} stroke="var(--muted)"/><YAxis stroke="var(--muted)"/><Tooltip contentStyle={{background:'var(--surface)',borderColor:'var(--line)',color:'var(--ink)'}}/><Line dataKey="value" name={key.name} type="linear" connectNulls={false} stroke="var(--accent)" isAnimationActive={false}/></LineChart></ResponsiveContainer><small>{analysis.interpretation}</small></div>;}
export function DependencyGraph({graph}:{graph:D}){
 useUiTranslation(["experiments"]);
const g=new dagre.graphlib.Graph();g.setGraph({rankdir:'LR'});g.setDefaultEdgeLabel(()=>({}));graph.nodes.forEach((v:D)=>g.setNode(v.id,{width:155,height:48}));graph.edges.forEach((v:D)=>g.setEdge(v.before,v.after));dagre.layout(g);const nodes:Node[]=graph.nodes.map((v:D)=>({id:v.id,position:{x:g.node(v.id).x-77,y:g.node(v.id).y-24},data:{label:v.id},style:{background:'var(--surface)',color:'var(--ink)',borderColor:'var(--line)',width:155}}));const edges:Edge[]=graph.edges.map((v:D)=>({id:v.id,source:v.before,target:v.after,label:v.meaning,style:{stroke:graph.conflicting_dependencies.includes(v.id)?'#b14b44':'var(--accent)'},labelStyle:{fill:'var(--ink)'}}));return <div className="wll-graph"><ReactFlow nodes={nodes} edges={edges} fitView nodesDraggable={false} nodesConnectable={false} deleteKeyCode={null}><Background color="var(--line)"/><Controls showInteractive={false}/></ReactFlow></div>;}
