# Bo Rar POS – Myanmar / Dual Currency Edition

မြန်မာဘာသာသုံး ကုန်စုံဆိုင် POS starter project။ MMK နှင့် KRW ငွေကြေးရွေးချယ်မှု၊ ဆိုင် Admin က သတ်မှတ်သော ငွေလဲနှုန်း၊ online hosting အတွက် Render configuration ပါဝင်သည်။

## Local Mac / Windows
Python 3.10+ လိုအပ်သည်။

```bash
python -m venv .venv
# Mac/Linux
source .venv/bin/activate
# Windows PowerShell
# .venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```
Browser: http://127.0.0.1:5000

Initial login: `admin` / `admin123`။ ပထမဆုံးအသုံးပြုချိန်တွင် မဖြစ်မနေ password ပြောင်းပါ။ Starter version တွင် password-change UI မပါသေးသဖြင့် အများပြည်သူသုံး Internet ပေါ် မတင်မီ developer ဖြင့် password-management နှင့် security hardening ပြီးစီးစေရန်လိုအပ်သည်။

## ငွေကြေးနှင့် ငွေလဲနှုန်း
- ကုန်ပစ္စည်း၏ အရင်း/အရောင်းဈေးကို MMK အခြေခံဖြင့် မှတ်တမ်းတင်သည်။
- အရောင်းတွင် MMK သို့မဟုတ် KRW ရွေးနိုင်သည်။ KRW ရွေးလျှင် ကုန်ပစ္စည်း MMK ဈေးကို သတ်မှတ်ထားသော rate ဖြင့် ပြောင်းတွက်သည်။
- အဝယ်တွင် ရွေးထားသောငွေကြေးဖြင့် unit cost ထည့်နိုင်သည်။ KRW ဝယ်ယူမှု၏ cost ကို stock valuation အတွက် MMK သို့ပြောင်းသိမ်းသည်။
- Admin > ဆက်တင်တွင် `1 KRW = ? MMK` ကို သတ်မှတ်ပါ။ ဥပမာ 3.2 သည် ဥပမာတန်ဖိုးသာဖြစ်ပြီး live exchange rate မဟုတ်ပါ။ ဆိုင်၏ လက်တွေ့နှုန်းကို ထည့်ပါ။
- အရောင်း/အဝယ်/အကြွေး/အသုံးစရိတ်/အစီရင်ခံစာများတွင် currency ကို ခွဲပြသည်။ မတူညီသောငွေကြေးများကို တစ်ခုတည်းအဖြစ် မပေါင်းထားပါ။

## Render အွန်လိုင်းတင်ရန်
1. Project ကို GitHub repository အသစ်သို့ upload လုပ်ပါ။
2. Render တွင် **New > Blueprint** ကိုရွေးပြီး repository ချိတ်ပါ။
3. `render.yaml` ကိုဖတ်ပြီး Web Service တည်ဆောက်ပါ။
4. ဒီ configuration သည် `/var/data` persistent disk သုံးထားသည်။ Render persistent disk ပါဝင်သော paid plan လိုအပ်နိုင်သည်။ Free ephemeral filesystem ပေါ်တွင် SQLite သုံးပါက redeploy/restart ပြီး data ပျောက်နိုင်သည်။
5. Deploy ပြီးရင် Render ကပေးသော HTTPS URL ဖြင့် ဖုန်း/ကွန်ပျူတာမှ ဝင်ပါ။
6. Admin password ကို ချက်ချင်းပြောင်းပြီး မျှဝေမထားပါနှင့်။

## လက်ရှိအခြေအနေနှင့် ကန့်သတ်ချက်များ
- Flask + SQLite; Render deployment blueprint နှင့် persistent disk path ပါဝင်သည်.
- Starter/MVP ဖြစ်သည်။ Production အသုံးပြုမီ CSRF protection, password change/reset, rate limiting, staff permissions, database backup/restore UI, audit logs, refund/returns, cash drawer and Bluetooth printer testing တို့ကို ထပ်ဖြည့်စစ်ဆေးရန်လိုသည်။
- SQLite သည် ဆိုင်တစ်ဆိုင်/အသုံးပြုသူအနည်းငယ်အတွက် စတင်ရန်ဖြစ်သည်။ ဆိုင်ခွဲများ၊ တစ်ပြိုင်နက်အသုံးပြုသူများများလာပါက PostgreSQL သို့ပြောင်းရန် အကြံပြုသည်။
