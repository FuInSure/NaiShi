from pathlib import Path
import urllib.request,urllib.parse,json,re,html,time,concurrent.futures,hashlib
ROOT=Path(__file__).resolve().parents[1]
CACHE=ROOT/'source'/'sentence_expansion';CACHE.mkdir(exist_ok=True)
def get(url):
    for i in range(3):
        try:
            return urllib.request.urlopen(urllib.request.Request(url,headers={'User-Agent':'ResearchEnglishStudy/1.0'}),timeout=25).read().decode('utf8')
        except Exception:
            if i==2:raise
            time.sleep(2+i)
def clean(s):return re.sub(r'\s+',' ',html.unescape(re.sub('<[^>]+>',' ',s))).strip()
existing=json.loads((ROOT/'sentences.json').read_text(encoding='utf8'))['sentences']
used=set(re.findall(r'\d{4}\.\d{4,5}', ' '.join(s['source']['url'] for s in existing)))
lists=['https://raw.githubusercontent.com/ddz16/TSFpaper/master/README.md','https://raw.githubusercontent.com/ddz16/TSFpaper/main/README.md','https://github.com/ddz16/TSFpaper','https://github.com/TSCenter/awesome-time-series-papers']
ids=[]
for url in lists:
    try:
        raw=get(url)
        ids+=re.findall(r'(?:abs/|pdf/|arxiv.org%2Fabs%2F)(\d{4}\.\d{4,5})',raw)
        (CACHE/('list_'+hashlib.sha256(url.encode()).hexdigest()[:8]+'.txt')).write_text(raw,encoding='utf8')
        if len(set(ids))>650:break
    except Exception as e:print('LIST',type(e).__name__,flush=True)
ids=list(dict.fromkeys(i for i in ids if i not in used))
print('CANDIDATES',len(ids),flush=True)
cards=json.loads((ROOT/'vocabulary.json').read_text(encoding='utf8'))['cards']
def process(pid):
    f=CACHE/(pid+'.json')
    if f.exists():return json.loads(f.read_text(encoding='utf8'))
    try:
        raw=get('https://arxiv.org/abs/'+pid)
        abstract=clean(re.search(r'<blockquote[^>]*class="abstract[^"]*"[^>]*>(.*?)</blockquote>',raw,re.S)[1])
        abstract=re.sub(r'^Abstract:\s*','',abstract)
        title=html.unescape(re.search(r'<meta name="citation_title" content="([^"]+)"',raw)[1])
        version=re.search(re.escape(pid)+r'v(\d+)',raw)
        url='https://arxiv.org/abs/'+pid+('v'+version[1] if version else '')
        candidates=[s.strip() for s in re.split(r'(?<=[.!?])\s+(?=[A-Z])',abstract) if 10<=len(s.split())<=25 and not re.search(r'https|www\.|code is|repository|\$|\\',s,re.I)]
        if not candidates:return None
        candidates.sort(key=lambda s:('we ' not in s.lower(),bool(re.search(r'\d|%|state.of.the.art',s,re.I)),len(s.split())))
        en=candidates[0]
        response=json.loads(get('https://translate.googleapis.com/translate_a/single?'+urllib.parse.urlencode({'client':'gtx','sl':'en','tl':'zh-CN','dt':'t','q':en})))
        zh=''.join(x[0] for x in response[0] if x[0])
        if not re.search('[\u4e00-\u9fff]',zh):return None
        module='概率建模' if re.search('probabil|uncertaint|bayes|quantile|diffusion|distribution|conformal',title,re.I) else '混合神经网络' if re.search('hybrid|fusion|graph|network|transformer|attention',title,re.I) else '时空序列预测'
        matched=[c for c in cards if re.search(r'\b'+re.escape(c['term'])+r'\b',en,re.I)]
        matched.sort(key=lambda c:-len(c['term']))
        structures=[]
        if re.search(r'\b(we|We)\s+(propose|present|introduce|develop|evaluate|show|demonstrate|study|investigate)',en):
            m=re.search(r'\b(we|We)\s+(\w+)',en);structures.append('主句以 We '+m[2]+' 开头：作者作主语，后接研究动作和对象。')
        if re.search(r'\bthat\b',en):structures.append('注意 that 后的从句：结合前面的名词或动词判断它是修饰成分还是宾语内容。')
        if re.search(r'\b(which|where|while|although|because)\b',en):structures.append('注意连接词 '+', '.join(re.findall(r'\b(which|where|while|although|because)\b',en))+' 所引出的修饰、对比或因果关系。')
        if re.search(r'\b(is|are|was|were|be)\s+\w+(?:ed|en)\b',en):structures.append('句中出现可能的被动结构，先识别动作承受者，再判断是否需要译出施事。')
        if not structures:structures.append('先找主语与限定动词，再将介词短语等修饰成分放回主干；保留原句的范围和比较条件。')
        s={'id':'s_'+hashlib.sha256(url.encode()).hexdigest()[:12],'module':module,'en':en,'reference_translation_zh':zh,'structure_zh':' '.join(structures),'context_zh':'来自该论文摘要。若涉及方法优越性或性能，限于作者所述实验条件；指代与限定条件请结合来源摘要阅读。新增译文为机器初译，结构提示为规则生成，均待逐句人工审校。','level':1 if len(en.split())<=16 else 2,'kind':'paper_quote','source':{'title':title,'url':url,'year':2000+int(pid[:2]),'year_basis':'first_arxiv_submission','location':'Abstract','verification':'exact_text_extracted_from_source_html','accessed_at':'2026-10-28','rights':'copyright_retained_by_original_rightsholder; short_attributed_excerpt'},'word_count':len(en.split()),'target_terms':[c['term'] for c in matched[:6]],'target_card_ids':[c['id'] for c in matched[:6]],'answer_hidden_by_default':True,'translation_status':'machine_translation_pending_editorial_review','analysis_status':'rule_based_reading_hint_pending_review'}
        f.write_text(json.dumps(s,ensure_ascii=False,indent=2),encoding='utf8')
        return s
    except Exception as e:
        print('SKIP',pid,type(e).__name__,flush=True);return None
result=[];seen={s['en'].lower() for s in existing}
with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
    # Limited batches preserve partial progress without launching every request at once.
    for start in range(0,len(ids),12):
        for s in pool.map(process,ids[start:start+12]):
            if s and s['en'].lower() not in seen:
                result.append(s);seen.add(s['en'].lower())
                if len(result)==365-len(existing):break
        print('READY',len(result),'/',365-len(existing),flush=True)
        (ROOT/'sentence_additions.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf8')
        if len(result)>=365-len(existing):break
        time.sleep(1)
print('FINISHED',len(result),flush=True)
