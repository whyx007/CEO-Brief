# -*- coding: utf-8 -*-
from urllib.request import Request, urlopen
from urllib.parse import quote
import re

q = '上海拜安传感技术有限公司 官网'
url = 'https://search.whyx.site:8444/search?q=' + quote(q)
html = urlopen(Request(url, headers={'User-Agent':'Mozilla/5.0'}), timeout=20).read().decode('utf-8', 'ignore')
for m in re.finditer(r'<a[^>]+href="(https?://[^"]+)"[^>]*>\s*<h3[^>]*>(.*?)</h3>', html, re.S):
    print('URL:', m.group(1))
    print('TITLE:', re.sub(r'<.*?>', '', m.group(2)).strip())
    print('---')
