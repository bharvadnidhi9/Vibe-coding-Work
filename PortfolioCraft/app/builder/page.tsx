"use client";
import { useEffect, useState } from "react";import Link from "next/link";
import Portfolio,{TEMPLATES} from "@/components/Portfolio";
import { PortfolioData,SAMPLE,TemplateKey,DEFAULT_ACCENT,uid,Item } from "@/lib/data";
const KEY="portfoliocraft:draft:v1";const W={desktop:"100%",tablet:"768px",mobile:"390px"} as const;
type Dev=keyof typeof W;
export default function Builder(){
 const [d,setD]=useState<PortfolioData>(SAMPLE);const [ready,setReady]=useState(false);
 const [status,setStatus]=useState("Saved locally");const [dev,setDev]=useState<Dev>("desktop");
 const [dark,setDark]=useState(false);const [prev,setPrev]=useState(false);const [tab,setTab]=useState<"edit"|"preview">("edit");
 useEffect(()=>{try{const s=localStorage.getItem(KEY);if(s)setD({...SAMPLE,...JSON.parse(s)});}catch{}
  const t=new URLSearchParams(location.search).get("template") as TemplateKey|null;
  if(t&&t in TEMPLATES)setD(x=>({...x,template:t}));
  setDark(localStorage.getItem("pc:dark")==="1");setReady(true);},[]);
 useEffect(()=>{document.documentElement.classList.toggle("dark",dark);try{localStorage.setItem("pc:dark",dark?"1":"0")}catch{}},[dark]);
 useEffect(()=>{if(!ready)return;setStatus("Saving…");const h=setTimeout(()=>{try{localStorage.setItem(KEY,JSON.stringify(d));setStatus("Saved locally")}catch{setStatus("Save failed – browser storage is full or unavailable")}},400);return()=>clearTimeout(h)},[d,ready]);
 const set=<K extends keyof PortfolioData>(k:K,v:PortfolioData[K])=>setD(x=>({...x,[k]:v}));
 const move=(i:number,n:number)=>{const s=[...d.sections];if(n<0||n>=s.length)return;[s[i],s[n]]=[s[n],s[i]];set("sections",s)};
 const img=(f:File|undefined,cb:(u:string)=>void)=>{if(!f)return;if(!/^image\/(jpeg|png|webp)$/.test(f.type)){alert("Use JPG, PNG or WebP.");return}if(f.size>5*1024*1024){alert("Image must be under 5 MB.");return}
  const r=new FileReader();r.onload=()=>{const im=new Image();im.onload=()=>{const c=document.createElement("canvas");const sc=Math.min(1,800/im.width);c.width=im.width*sc;c.height=im.height*sc;c.getContext("2d")!.drawImage(im,0,0,c.width,c.height);cb(c.toDataURL("image/jpeg",.8))};im.src=r.result as string};r.readAsDataURL(f)};
 const itemEd=(key:"experience"|"education"|"achievements",label:string)=>(<fieldset className="space-y-2"><legend className="font-semibold">{label}</legend>{d[key].map((it,i)=>(<div key={it.id} className="space-y-1 rounded-lg border border-neutral-200 dark:border-neutral-800 p-2">{(["title","org","detail"] as (keyof Item)[]).filter(f=>f!=="id").map(f=>(<input key={f} className="inp" aria-label={label+" "+f} placeholder={f==="org"?"Organization":f==="detail"?"Dates / details":"Title"} value={it[f]} onChange={e=>set(key,d[key].map((x,j)=>j===i?{...x,[f]:e.target.value}:x))}/>))}<button className="btn-s" onClick={()=>set(key,d[key].filter((_,j)=>j!==i))}>Remove</button></div>))}<button className="btn-s" onClick={()=>set(key,[...d[key],{id:uid(),title:"",org:"",detail:""}])}>+ Add</button></fieldset>);
 const L=({t,children}:{t:string;children:React.ReactNode})=><label className="block text-sm"><span className="font-medium">{t}</span>{children}</label>;
 const editor=(<div className="space-y-6 p-4">
  <p className="rounded-lg bg-amber-100 p-2 text-xs text-amber-900">Guest draft: stored only in this browser and may be lost if you clear site data. Cloud save arrives with accounts.</p>
  <L t="Template"><select className="inp" value={d.template} onChange={e=>set("template",e.target.value as TemplateKey)}>{(Object.keys(TEMPLATES) as TemplateKey[]).map(k=><option key={k} value={k}>{TEMPLATES[k].name}</option>)}</select></L>
  <fieldset className="space-y-2"><legend className="font-semibold">Profile</legend>
   <L t="Display name"><input className="inp" value={d.name} onChange={e=>set("name",e.target.value)}/></L>
   <L t="Headline"><input className="inp" value={d.headline} onChange={e=>set("headline",e.target.value)}/></L>
   <L t="Intro"><input className="inp" value={d.intro} onChange={e=>set("intro",e.target.value)}/></L>
   <L t="About"><textarea className="inp" rows={4} value={d.about} onChange={e=>set("about",e.target.value)}/></L>
   <L t="Skills (comma separated)"><input className="inp" value={d.skills} onChange={e=>set("skills",e.target.value)}/></L></fieldset>
  <fieldset className="space-y-2"><legend className="font-semibold">Projects ({d.projects.length}/12)</legend>
   {d.projects.map((p,i)=>{const up=(k:string,v:string)=>set("projects",d.projects.map((x,j)=>j===i?{...x,[k]:v}:x));return(<div key={p.id} className="space-y-1 rounded-lg border border-neutral-200 dark:border-neutral-800 p-2">
    <input className="inp" aria-label="Project name" placeholder="Name" value={p.name} onChange={e=>up("name",e.target.value)}/>
    <textarea className="inp" aria-label="Project description" placeholder="Description" value={p.description} onChange={e=>up("description",e.target.value)}/>
    <input className="inp" aria-label="Tags" placeholder="Tags, comma separated" value={p.tags} onChange={e=>up("tags",e.target.value)}/>
    {(["repo","demo"] as const).map(f=>(<div key={f}><input className="inp" aria-label={f==="repo"?"Repository URL":"Live demo URL"} placeholder={f==="repo"?"Repository URL":"Live demo URL"} value={p[f]} onChange={e=>up(f,e.target.value)}/>{p[f]&&!/^https?:\/\//i.test(p[f])&&<p className="text-xs text-red-600">Must start with http:// or https://</p>}</div>))}
    <input type="file" aria-label="Project image" accept="image/jpeg,image/png,image/webp" onChange={e=>img(e.target.files?.[0],u=>up("image",u))}/>
    <div className="flex gap-2"><button className="btn-s" disabled={i===0} onClick={()=>{const a=[...d.projects];[a[i-1],a[i]]=[a[i],a[i-1]];set("projects",a)}}>↑</button><button className="btn-s" disabled={i===d.projects.length-1} onClick={()=>{const a=[...d.projects];[a[i+1],a[i]]=[a[i],a[i+1]];set("projects",a)}}>↓</button><button className="btn-s" onClick={()=>set("projects",d.projects.filter((_,j)=>j!==i))}>Delete</button></div></div>)})}
   <button className="btn-s" disabled={d.projects.length>=12} onClick={()=>set("projects",[...d.projects,{id:uid(),name:"",description:"",tags:"",repo:"",demo:"",image:""}])}>+ Add project</button></fieldset>
  {itemEd("experience","Experience")}{itemEd("education","Education")}{itemEd("achievements","Achievements")}
  <fieldset className="space-y-2"><legend className="font-semibold">Contact</legend>
   <L t="Email"><input type="email" className="inp" value={d.email} onChange={e=>set("email",e.target.value)}/></L>
   <L t="GitHub URL"><input className="inp" value={d.github} onChange={e=>set("github",e.target.value)}/></L>
   <L t="LinkedIn URL"><input className="inp" value={d.linkedin} onChange={e=>set("linkedin",e.target.value)}/></L></fieldset>
  <fieldset className="space-y-2"><legend className="font-semibold">Sections</legend>{d.sections.map((s,i)=>(<div key={s.id} className="flex items-center gap-2"><input type="checkbox" id={"s-"+s.id} checked={s.visible} onChange={()=>set("sections",d.sections.map((x,j)=>j===i?{...x,visible:!x.visible}:x))}/><label htmlFor={"s-"+s.id} className="flex-1 capitalize text-sm">{s.id}</label><button className="btn-s" aria-label={"Move "+s.id+" up"} onClick={()=>move(i,i-1)}>↑</button><button className="btn-s" aria-label={"Move "+s.id+" down"} onClick={()=>move(i,i+1)}>↓</button></div>))}</fieldset>
  <fieldset className="space-y-2"><legend className="font-semibold">Design</legend><L t="Accent color"><input type="color" value={d.accent} onChange={e=>set("accent",e.target.value)}/></L><button className="btn-s" onClick={()=>set("accent",DEFAULT_ACCENT)}>Reset design (keeps content)</button></fieldset>
  <button className="btn-s" onClick={()=>{if(confirm("Clear all content and start from a blank draft?"))setD({...SAMPLE,name:"",headline:"",intro:"",about:"",skills:"",projects:[],experience:[],education:[],achievements:[]})}}>Clear all content</button>
 </div>);
 const pane=(<div className="flex-1 overflow-auto bg-neutral-200 dark:bg-neutral-800 p-4"><div className="mx-auto h-full overflow-auto rounded-lg shadow transition-all" style={{maxWidth:W[dev]}}><Portfolio d={d}/></div></div>);
 if(prev)return(<div className="h-screen flex flex-col"><div className="p-2 flex gap-2 border-b"><button className="btn-s" onClick={()=>setPrev(false)}>← Exit preview</button></div><div className="flex-1 overflow-auto"><Portfolio d={d}/></div></div>);
 return(<div className="h-screen flex flex-col"><header className="flex flex-wrap items-center gap-2 border-b border-neutral-200 dark:border-neutral-800 px-4 py-2"><Link href="/" className="font-bold">PortfolioCraft</Link><span className="text-xs text-neutral-500" role="status">{status}</span><div className="ml-auto flex flex-wrap gap-2">
  <div className="hidden md:flex gap-1" role="group" aria-label="Device preview">{(Object.keys(W) as Dev[]).map(k=><button key={k} className={dev===k?"btn-p":"btn-s"} aria-pressed={dev===k} onClick={()=>setDev(k)}>{k}</button>)}</div>
  <button className="btn-s" onClick={()=>setPrev(true)}>Preview</button><button className="btn-s" onClick={()=>setDark(!dark)} aria-pressed={dark}>{dark?"Light":"Dark"} mode</button>
  <button className="btn-p" disabled title="Publishing requires an account – coming in the next phase">Publish</button></div></header>
  <div className="md:hidden flex border-b" role="tablist">{(["edit","preview"] as const).map(t=><button key={t} role="tab" aria-selected={tab===t} className={"flex-1 py-2 "+(tab===t?"font-bold border-b-2 border-indigo-500":"")} onClick={()=>setTab(t)}>{t}</button>)}</div>
  <div className="flex-1 flex min-h-0"><aside className={"md:block md:w-96 md:border-r border-neutral-200 dark:border-neutral-800 overflow-auto w-full "+(tab==="edit"?"block":"hidden")}>{editor}</aside><div className={"md:flex flex-1 min-w-0 "+(tab==="preview"?"flex":"hidden")}>{pane}</div></div></div>);
}
