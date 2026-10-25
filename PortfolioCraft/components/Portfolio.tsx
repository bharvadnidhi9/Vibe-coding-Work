import { PortfolioData, TemplateKey, safeUrl } from "@/lib/data";
export const TEMPLATES:Record<TemplateKey,{name:string;desc:string;bg:string;fg:string;font:string;wrap:string;hero:string;grid:string;card:string}>={
 minimal:{name:"Minimal",desc:"Whitespace and quiet typography.",bg:"#ffffff",fg:"#171717",font:"system-ui,sans-serif",wrap:"max-w-2xl px-6 py-16 space-y-14",hero:"text-left",grid:"grid gap-4",card:"border-b pb-4"},
 midnight:{name:"Midnight",desc:"Dark surfaces, technical accents.",bg:"#0b1020",fg:"#e6e9f5",font:"ui-monospace,monospace",wrap:"max-w-3xl px-6 py-16 space-y-12",hero:"text-left",grid:"grid gap-4 sm:grid-cols-2",card:"rounded-xl border border-white/10 bg-white/5 p-4"},
 studio:{name:"Studio",desc:"Expressive, creative composition.",bg:"#fff7ed",fg:"#1c1917",font:"Georgia,serif",wrap:"max-w-4xl px-6 py-16 space-y-16",hero:"text-center",grid:"grid gap-6 sm:grid-cols-3",card:"rounded-3xl bg-white p-5 shadow-lg -rotate-1"},
 professional:{name:"Professional",desc:"Structured, career-focused.",bg:"#f8fafc",fg:"#0f172a",font:"system-ui,sans-serif",wrap:"max-w-3xl px-6 py-12 space-y-8",hero:"text-left",grid:"grid gap-3",card:"rounded-md border bg-white p-4 shadow-sm"},
 editorial:{name:"Editorial",desc:"Magazine-style, type-led.",bg:"#fbfaf7",fg:"#222",font:"Georgia,serif",wrap:"max-w-3xl px-6 py-20 space-y-16",hero:"text-left",grid:"grid gap-8",card:"border-t-2 pt-3"},
 gallery:{name:"Visual Gallery",desc:"Image-forward work cards.",bg:"#111111",fg:"#f5f5f5",font:"system-ui,sans-serif",wrap:"max-w-5xl px-6 py-14 space-y-12",hero:"text-center",grid:"grid gap-4 sm:grid-cols-2 lg:grid-cols-3",card:"overflow-hidden rounded-2xl bg-neutral-900"},
};
const tags=(s:string)=>s.split(",").map(t=>t.trim()).filter(Boolean);
export default function Portfolio({d}:{d:PortfolioData}){
  const t=TEMPLATES[d.template]; const a=d.accent;
  const Head=({children}:{children:string})=><h2 className="text-xl font-bold mb-4" style={{color:a}}>{children}</h2>;
  const list=(items:PortfolioData["experience"],title:string)=>items.some(i=>i.title)?(<section key={title}><Head>{title}</Head><div className={t.grid}>{items.filter(i=>i.title).map(i=>(<div key={i.id} className={t.card} style={{borderColor:a+"55"}}><b>{i.title}</b>{i.org&&<> · {i.org}</>}<p className="opacity-75 text-sm">{i.detail}</p></div>))}</div></section>):null;
  const render=(id:string)=>{switch(id){
    case "hero":return(<header key={id} className={t.hero}><h1 className="text-4xl sm:text-5xl font-extrabold">{d.name||"Your Name"}</h1><p className="text-lg mt-2" style={{color:a}}>{d.headline||"Your headline"}</p>{d.intro&&<p className="mt-3 opacity-80">{d.intro}</p>}</header>);
    case "about":return d.about?(<section key={id}><Head>About</Head><p className="whitespace-pre-line opacity-90">{d.about}</p></section>):null;
    case "work":return d.projects.some(p=>p.name)?(<section key={id}><Head>Work</Head><div className={t.grid}>{d.projects.filter(p=>p.name).map(p=>(<article key={p.id} className={t.card} style={{borderColor:a+"55"}}>{p.image&&<img src={p.image} alt={p.name} loading="lazy" className="w-full h-36 object-cover"/>}<div className={d.template==="gallery"?"p-4":""}><h3 className="font-semibold">{p.name}</h3><p className="text-sm opacity-80">{p.description}</p><p className="text-xs mt-1 opacity-60">{tags(p.tags).join(" · ")}</p><div className="mt-2 flex gap-3 text-sm">{safeUrl(p.repo)&&<a href={safeUrl(p.repo)} style={{color:a}} className="underline" target="_blank" rel="noopener noreferrer">Code</a>}{safeUrl(p.demo)&&<a href={safeUrl(p.demo)} style={{color:a}} className="underline" target="_blank" rel="noopener noreferrer">Live</a>}</div></div></article>))}</div></section>):null;
    case "skills":return tags(d.skills).length?(<section key={id}><Head>Skills</Head><div className="flex flex-wrap gap-2">{tags(d.skills).map(s=><span key={s} className="rounded-full px-3 py-1 text-sm" style={{background:a+"22",color:a}}>{s}</span>)}</div></section>):null;
    case "experience":return list(d.experience,"Experience");
    case "education":return list(d.education,"Education");
    case "achievements":return list(d.achievements,"Achievements");
    case "contact":return(d.email||safeUrl(d.github)||safeUrl(d.linkedin))?(<section key={id}><Head>Contact</Head><div className="flex flex-wrap gap-4">{d.email&&<a className="underline" href={"mailto:"+d.email}>{d.email}</a>}{safeUrl(d.github)&&<a className="underline" href={safeUrl(d.github)} target="_blank" rel="noopener noreferrer">GitHub</a>}{safeUrl(d.linkedin)&&<a className="underline" href={safeUrl(d.linkedin)} target="_blank" rel="noopener noreferrer">LinkedIn</a>}</div></section>):null;
  }return null;};
  return(<div style={{background:t.bg,color:t.fg,fontFamily:t.font,minHeight:"100%"}}><main className={"mx-auto "+t.wrap}>{d.sections.filter(s=>s.visible).map(s=>render(s.id))}</main></div>);
}
