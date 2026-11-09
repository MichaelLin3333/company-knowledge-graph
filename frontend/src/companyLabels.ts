import type { Company } from './api';

// Short labels are presentation only. Records retain the full sourced legal name.
const familiarNames:Record<string,string>={
 AAPL:'Apple',MSFT:'Microsoft',AMZN:'Amazon',NVDA:'NVIDIA',TSMC:'TSMC',CRM:'Salesforce',
 NORDIC:'Nordic Semiconductor',NANOFILM:'Nanofilm Technologies',NANYAPCB:'Nan Ya PCB',
 JDI:'Japan Display',JXADVANCED:'JX Advanced Metals',DONGSHAN:'Dongshan Precision',
 ANJIE:'Suzhou Anjie',KERSEN:'Kersen',SHENZHENBSC:'Shenzhen BSC',
 SONY:'Sony Group',SONY_CORP:'Sony Corporation',AVGO:'Broadcom Inc.',
 BROADCOM_SG:'Broadcom Singapore',NOK:'NOK Corporation',NOK_GROUP:'NOK Group',
};

export function companyNodeLabel(company:Company,root=false):string {
 const name=familiarNames[company.id]||company.name
  .replace(/,?\s+\b(?:(?:Company|Co\.?)[,]?\s*)?(?:Incorporated|Corporation|Corp\.?|Limited|Ltd\.?)\s*$/i,'')
  .replace(/\s+/g,' ').trim()||company.name;
 const words=name.split(' '),lines:string[]=[];let line='';
 const width=root?23:20;
 for(const word of words){
  if(line&&line.length+word.length+1>width){lines.push(line);line=word;}else line+=(line?' ':'')+word;
 }
 if(line)lines.push(line);
 let label=lines.slice(0,2).map(value=>value.length>width?value.slice(0,width-1)+'…':value).join('\n');
 if(lines.length>2)label=label.replace(/…?$/,'…');
 return label+(company.primary_ticker?'\n'+company.primary_ticker:'');
}
