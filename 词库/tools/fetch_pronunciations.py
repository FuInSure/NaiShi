from pathlib import Path
import json,urllib.request,re,concurrent.futures,html,time
root=Path('词库/source/pronunciation');missing=json.loads((root/'missing.json').read_text(encoding='utf-8')); cache=root/'wiktionary';cache.mkdir(exist_ok=True)
words=sorted(set(x.lower() for x in missing if not x.isupper() and not x.isdigit()))
def fetch(word):
 p=cache/(word.replace("'",'_')+'.json')
 if p.exists():return
 url='https://en.wiktionary.org/wiki/'+urllib.parse.quote(word)
 try:
  req=urllib.request.Request(url,headers={'User-Agent':'NaiShiPronunciation/1.0 (educational dictionary lookup)'})
  raw=urllib.request.urlopen(req,timeout=25).read().decode()
  # Limit to English section, stopping before the next language.
  start=re.search(r'id="English"',raw)
  section=raw[start.start():] if start else ''
  end=re.search(r'<div class="mw-heading mw-heading2"',section[50:])
  if end:section=section[:50+end.start()]
  ipas=[html.unescape(re.sub('<[^>]+>','',x)) for x in re.findall(r'<span[^>]*class="IPA"[^>]*>(.*?)</span>',section,re.S)]
  out={'word':word,'url':url,'ipa':list(dict.fromkeys(ipas)),'accessed':'2026-10-30'}
 except Exception as e:out={'word':word,'url':url,'ipa':[],'error':str(e)}
 p.write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as ex:list(ex.map(fetch,words))
print('cached',len(words))
