export type TemplateKey = "minimal"|"midnight"|"studio"|"professional"|"editorial"|"gallery";
export type SectionId = "hero"|"about"|"work"|"skills"|"experience"|"education"|"achievements"|"contact";
export interface Project { id:string; name:string; description:string; tags:string; repo:string; demo:string; image:string }
export interface Item { id:string; title:string; org:string; detail:string }
export interface PortfolioData {
  template:TemplateKey; name:string; headline:string; intro:string; about:string; skills:string;
  projects:Project[]; experience:Item[]; education:Item[]; achievements:Item[];
  email:string; github:string; linkedin:string; accent:string;
  sections:{id:SectionId;visible:boolean}[];
}
export const DEFAULT_ACCENT="#6d5efc";
export const uid=()=>Math.random().toString(36).slice(2,9);
export const SAMPLE:PortfolioData={
  template:"minimal",name:"Alex Rivera",headline:"Full-stack developer & designer",
  intro:"I build clear, fast web products.",about:"I'm a developer who loves turning ideas into polished interfaces. Currently open to new opportunities.",
  skills:"TypeScript, React, Node.js, Figma, PostgreSQL",
  projects:[{id:"p1",name:"TaskFlow",description:"A kanban app with real-time sync.",tags:"React, Node",repo:"https://github.com",demo:"",image:""}],
  experience:[{id:"e1",title:"Frontend Developer",org:"Acme Co.",detail:"2022 – Present · Built the design system."}],
  education:[{id:"d1",title:"B.Sc. Computer Science",org:"State University",detail:"2018 – 2022"}],
  achievements:[{id:"a1",title:"Hackathon Winner",org:"DevFest",detail:"2023"}],
  email:"",github:"",linkedin:"",accent:DEFAULT_ACCENT,
  sections:(["hero","about","work","skills","experience","education","achievements","contact"] as SectionId[]).map(id=>({id,visible:true})),
};
export const safeUrl=(u:string)=>/^https?:\/\//i.test(u)?u:"";
