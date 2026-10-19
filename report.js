(()=>{
'use strict';
const data=JSON.parse(document.getElementById('case-data').textContent);
const model=(cash,debt,shares,growth,wacc,g)=>{
 if(![cash,debt,shares,growth,wacc,g].every(Number.isFinite)||wacc<=g||shares<=0)return null;
 let pv=0,last=cash;
 for(let i=1;i<=5;i++){last=cash*Math.pow(1+growth,i);pv+=last/Math.pow(1+wacc,i)}
 const tv=last*(1+g)/(wacc-g)/Math.pow(1+wacc,5);
 return Math.max(0,pv+tv-debt)/shares;
};
const reverse=(cash,debt,shares,price,wacc,g)=>{
 let lo=-.5,hi=1;
 const f=x=>model(cash,debt,shares,x,wacc,g);
 if(f(lo)>price||f(hi)<price)return null;
 for(let i=0;i<80;i++){const mid=(lo+hi)/2;if(f(mid)<price)lo=mid;else hi=mid}
 return (lo+hi)/2;
};
function tab(name,company=document.getElementById('company-'+data.symbol)){
 company.querySelectorAll('[data-panel]').forEach(x=>{const selected=x.dataset.panel===name;x.classList.toggle('active',selected);x.setAttribute('aria-selected',String(selected))});
 company.querySelectorAll('[data-content]').forEach(x=>{x.hidden=x.dataset.content!==name;x.classList.toggle('active',!x.hidden)});
}
document.querySelectorAll('[data-panel]').forEach(x=>x.addEventListener('click',()=>tab(x.dataset.panel,x.closest('.company'))));
document.querySelectorAll('[data-goto]').forEach(x=>x.addEventListener('click',()=>{const company=x.closest('.company');tab(x.dataset.goto,company);company.querySelector('.tabs').scrollIntoView({block:'start'})}));
function selectCompany(id){
 const found=document.getElementById('company-'+id);if(!found)return;
 document.querySelectorAll('.company').forEach(x=>{x.hidden=x!==found});
 document.querySelectorAll('[data-company]').forEach(x=>{x.classList.toggle('selected',x.dataset.company===id);if(x.dataset.company===id)x.setAttribute('aria-current','page');else x.removeAttribute('aria-current')});
}
document.querySelectorAll('[data-company]').forEach(x=>x.addEventListener('click',ev=>{ev.preventDefault();selectCompany(x.dataset.company);history.replaceState(null,'','#company-'+x.dataset.company);window.scrollTo({top:0})}));
if(location.hash.startsWith('#company-'))selectCompany(location.hash.slice(9));
const growth=document.getElementById('growth'),wacc=document.getElementById('wacc'),terminal=document.getElementById('terminal'),start=document.getElementById('cash-start');
function calculate(){
 const g=Number(growth.value)/100,w=Number(wacc.value)/100,t=Number(terminal.value)/100;
 const cash=start.value==='runrate'?data.runrate_sensitivity.cash_proxy:data.bridge.fcff_proxy;
 document.getElementById('growth-label').textContent=(g*100).toFixed(1)+'%';
 document.getElementById('wacc-label').textContent=(w*100).toFixed(2)+'%';
 document.getElementById('terminal-label').textContent=(t*100).toFixed(1)+'%';
 const value=model(cash,data.balance.net_debt,data.balance.shares,g,w,t);
 document.getElementById('live-value').textContent=value===null?'参数无效':'$'+value.toFixed(2);
 document.getElementById('live-change').textContent=value===null?'WACC必须高于永续增长率。':'相对当前报价 '+((value/data.quote.price-1)*100).toFixed(1)+'%（条件结果，不是收益预测）';
 const required=value===null?null:reverse(cash,data.balance.net_debt,data.balance.shares,data.quote.price,w,t);
 document.getElementById('live-growth').textContent=required===null?'在求解范围内无可靠的隐含增长结果。':'固定此起点与折现假设，支持当前价格所需的五年增长约 '+(required*100).toFixed(1)+'%。';
}
[growth,wacc,terminal,start].forEach(x=>x.addEventListener('input',calculate));
document.getElementById('reset-model').addEventListener('click',()=>{growth.value=data.profile.growth.base*100;wacc.value=data.assumptions.base_wacc*100;terminal.value=data.profile.terminal_growth*100;start.value='ttm';calculate()});
document.getElementById('download-case').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(data,null,2)],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download=data.symbol+'-research-'+data.as_of+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)});
calculate();
// Exposed for deterministic browser/Python reconciliation, not external network use.
window.researchModel={value:model,reverse};
})();
