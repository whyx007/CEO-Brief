# -*- coding: utf-8 -*-
from urllib.request import Request,urlopen
from urllib.parse import quote
from pathlib import Path
q='上海拜安传感技术有限公司 官网'
url='https://search.whyx.site:8444/search?q='+quote(q)
html=urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=20).read().decode('utf-8','ignore')
i=html.find('baiantek.com')
Path(r'C:\Users\Administrator\.openclaw\workspace\finance-postinvest-ai-platform\ceo-brief\_whyx_snippet.html').write_text(html[i-500:i+2000], encoding='utf-8')
print(i)
