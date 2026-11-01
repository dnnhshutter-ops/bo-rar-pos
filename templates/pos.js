let products=[], cart=[], exchangeRate=3.2;
async function loadProducts(){
 const sel=document.getElementById('product'); if(!sel)return;
 const data=await (await fetch('/api/products')).json(); products=data.products||[]; exchangeRate=data.rate||3.2;
 sel.innerHTML='<option value="">ပစ္စည်းရွေးပါ</option>'+products.map(p=>`<option value="${p.id}">${p.name} · ${Number(p.price).toLocaleString()} ကျပ် · လက်ကျန် ${p.stock}</option>`).join('');
}
function currency(){return document.getElementById('currency')?.value||'MMK'}
function priceFor(p){return currency()==='KRW'?p.krw_price:p.price}
function money(n){return currency()==='KRW'?'₩'+Number(n||0).toLocaleString('en-US',{maximumFractionDigits:2}):Number(n||0).toLocaleString('en-US')+' ကျပ်'}
function renderCart(){
 const t=document.getElementById('cart'); if(!t)return;
 t.innerHTML='<tr><th>ပစ္စည်း</th><th>အရေအတွက်</th><th>တစ်ခုဈေး</th><th>စုစုပေါင်း</th><th></th></tr>';
 cart.forEach((x,i)=>{let tr=t.insertRow();let unit= x.priceMMK!==undefined?(currency()==='KRW'?x.priceMMK/exchangeRate:x.priceMMK):x.cost;
 tr.innerHTML=`<td>${x.name}</td><td>${x.qty}</td><td>${money(unit)}</td><td>${money(x.qty*unit)}</td><td><button class="danger" type="button" onclick="removeItem(${i})">ဖယ်</button></td>`});
 let total=cart.reduce((a,x)=>a+x.qty*(x.priceMMK!==undefined?(currency()==='KRW'?x.priceMMK/exchangeRate:x.priceMMK):x.cost),0);
 let discount=Number(document.getElementById('discount')?.value||0);
 if(document.getElementById('total'))document.getElementById('total').textContent=money(Math.max(0,total-discount));
}
function addItem(){let id=Number(document.getElementById('product').value),qty=Number(document.getElementById('qty').value),p=products.find(x=>x.id===id);if(!p||qty<=0)return alert('ပစ္စည်းနှင့် အရေအတွက် ရွေးပါ');let old=cart.find(x=>x.id===id);if(old)old.qty+=qty;else cart.push({id,name:p.name,qty,priceMMK:p.price});renderCart()}
function addPurchaseItem(){let id=Number(document.getElementById('product').value),qty=Number(document.getElementById('qty').value),cost=Number(document.getElementById('cost').value),p=products.find(x=>x.id===id);if(!p||qty<=0||cost<0)return alert('အချက်အလက် ဖြည့်ပါ');cart.push({id,name:p.name,qty,cost});renderCart()}
function removeItem(i){cart.splice(i,1);renderCart()}
function submitSale(){if(!cart.length)return alert('ပစ္စည်းထည့်ပါ'),false;document.getElementById('items').value=JSON.stringify(cart.map(x=>({id:x.id,qty:x.qty})));return true}
function submitPurchase(){if(!cart.length)return alert('ပစ္စည်းထည့်ပါ'),false;document.getElementById('items').value=JSON.stringify(cart.map(x=>({id:x.id,qty:x.qty,cost:x.cost})));return true}
document.addEventListener('DOMContentLoaded',()=>{loadProducts();document.getElementById('discount')?.addEventListener('input',renderCart);document.getElementById('currency')?.addEventListener('change',renderCart)});
