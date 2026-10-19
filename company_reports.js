(()=>{'use strict';
function value(m,overrides={}){
 const p={...m.parameters,...overrides};let price;
 if(!Object.values(p).every(Number.isFinite))return null;
 if(m.kind==='earnings')price=p.eps*p.factor*p.pe/Math.pow(1+p.discount,p.years);
 else if(m.kind==='growth_profit')price=p.revenue*Math.pow(1+p.growth,p.years)*p.margin/(p.shares*p.dilution)*p.pe/Math.pow(1+p.discount,p.years);
 else if(m.kind==='circle'){
  const reserve=p.reserve_income*Math.pow(1+p.balance_growth,p.years)*p.yield_factor;
  const other=p.other_income*Math.pow(1+p.other_growth,p.years);
  const profit=Math.max(0,(reserve+other)*p.retention-p.opex*Math.pow(1+p.opex_growth,p.years))*(1-p.tax);
  price=profit/(p.shares*p.dilution)*p.pe/Math.pow(1+p.discount,p.years);
 }else if(m.kind==='adr')price=p.local_price/p.fx*p.ordinary_per_ads*(1+p.premium);
 else return null;
 return Number.isFinite(price)?price:null;
}
function reverse(m,price,overrides={}){
 const key=m.reverse.key;let [lo,hi]=m.reverse.range;
 const f=x=>value(m,{...overrides,[key]:x});
 if(f(lo)>price||f(hi)<price)return null;
 for(let i=0;i<90;i++){const mid=(lo+hi)/2;if(f(mid)<price)lo=mid;else hi=mid}return (lo+hi)/2;
}
const fmt=(x,unit)=>unit==='%'?(x*100).toFixed(1)+'%':x.toFixed(2)+unit;
document.querySelectorAll('.study').forEach(article=>{
 const data=JSON.parse(article.querySelector('.study-data').textContent),model=data.profile.model;
 const fields=[...article.querySelectorAll('[data-key]')];
 function calculate(){
  const edits=Object.fromEntries(fields.map(x=>[x.dataset.key,Number(x.value)/Number(x.dataset.scale)]));
  for(const c of model.controls)article.querySelector('[data-label="'+c.key+'"]').textContent=fmt(edits[c.key],c.unit);
  const v=value(model,edits);article.querySelector('[data-study-value]').textContent=v===null?'参数无效':'$'+v.toFixed(2);
  article.querySelector('[data-study-change]').textContent=v===null?'请核对参数。':'相对观察报价 '+((v/data.quote.price-1)*100).toFixed(1)+'%（条件结果）';
  const implied=reverse(model,data.quote.price,edits);
  article.querySelector('[data-study-reverse]').textContent=model.reverse.label+'：'+(implied===null?'给定范围无可靠解':fmt(implied,model.reverse.unit));
 }
 fields.forEach(x=>x.addEventListener('input',calculate));
 article.querySelector('[data-reset-study]').addEventListener('click',()=>{fields.forEach(x=>{x.value=model.parameters[x.dataset.key]*Number(x.dataset.scale)});calculate()});
 article.querySelector('[data-download-study]').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=data.symbol+'-research-'+data.profile.editorial_as_of+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
 calculate();
});
window.companyModels={value,reverse};
})();
