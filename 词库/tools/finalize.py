from pathlib import Path
import json, sqlite3, hashlib, collections, re
from build import ROOT, norm, raw_norm, CORRECTIONS

def write_json(path,data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf8')

data=json.loads((ROOT/'vocabulary.json').read_text(encoding='utf8'))
cards=data['cards']; by_key={c['normalized_term']:c for c in cards}
enrich=json.loads((ROOT/'tools/enrichment.json').read_text(encoding='utf8'))
for c in cards:
    if c['origin']=='adapted_aitd':
        # Canonical-key corrections also cover alias rows used as the source representative.
        correction=CORRECTIONS.get(raw_norm(c['term']),CORRECTIONS.get(c['normalized_term'],{}))
        if correction:
            c.setdefault('original_source_text',{'term':c['term'],'meaning_zh':c['meaning_zh']})
            c.update(correction)
            c['editorial_correction']=correction
    c['review_scope']='编辑释义与搭配；未经过独立专家复核' if c['origin']=='original_editorial' else '来源可追溯，已筛选与抽查；未逐条对照教材复核'
    c['source_accessed_at']='2026-10-27' if c['source_url'] else None
    c['senses']=[{'domain':c['module'],'meaning_zh':c['meaning_zh']}]
    c['pronunciation']=None
    c['confusion_group_ids']=[]

for line in (ROOT/'tools/examples.txt').read_text(encoding='utf8').splitlines():
    if not line.strip() or line.startswith('#'):continue
    term,en,zh,note=line.split('|')
    c=by_key[norm(term)]
    c['examples']=[{'en':en,'zh':zh,'kind':'original_teaching_example','source_url':None}]
    c['notes_zh']=note
    c['part_of_speech']=enrich['pos'].get(term,'noun phrase' if ' ' in term else 'noun')
    c['content_gaps']=[x for x in c['content_gaps'] if x not in ['bilingual_example','part_of_speech']]

for term,ipa in enrich['ipa_us'].items():
    c=by_key[norm(term)];c['ipa']=ipa
    c['pronunciation']={'dialect':'US','notation':'IPA','value':ipa,'origin':'editorial_transcription','review_status':'not_dictionary_cross_checked'}
    c['content_gaps']=[x for x in c['content_gaps'] if x!='ipa']

for term,abbr in enrich['abbreviations'].items():
    if norm(term) in by_key:by_key[norm(term)]['abbreviations']=sorted(set(by_key[norm(term)]['abbreviations']+abbr))

from pronunciation import enrich_pronunciations
enrich_pronunciations(cards)

groups=[]
for i,g in enumerate(enrich['confusion_groups'],1):
    group={'id':f'cg_{i:02d}','note_zh':g['note'],'card_ids':[by_key[norm(t)]['id'] for t in g['terms'] if norm(t) in by_key]}
    assert len(group['card_ids'])==len(g['terms']),g
    for term in g['terms']:
        c=by_key[norm(term)];c['confusion_group_ids'].append(group['id'])
        c['related_ids']=sorted(set(c['related_ids']+[x for x in group['card_ids'] if x!=c['id']]))
    groups.append(group)

# Learning tags are multi-label; module counts remain mutually exclusive.
for c in cards:
    t=c['normalized_term']
    if re.search(r'graph|spatial|temporal|forecast|time series|recurrent|convolution|attention',t):c['tags'].append('时空预测相关')
    if re.search(r'probabil|uncertaint|bayes|likelihood|posterior|prior|distribution|quantile|conformal|calibration|variance',t):c['tags'].append('概率建模相关')
    if re.search(r'neural|network|fusion|hybrid|ensemble|expert|gate|attention',t):c['tags'].append('混合架构相关')
    c['tags']=list(dict.fromkeys(c['tags']))
    c['content_depth']='example_and_usage' if c['examples'] else 'gloss_and_collocation' if c['collocations'] else 'basic_bilingual_gloss'
    c['difficulty_basis']='编辑建议，不是基于用户测评或语料频率的等级'

sentences=[]
for line in (ROOT/'tools/papers.txt').read_text(encoding='utf8').splitlines():
    if not line.strip() or line.startswith('#'):continue
    url,title,year,module,en,zh,structure,context,terms=line.split('|')
    words=len(en.split())
    assert words<=25,(title,words)
    sentence={'id':'s_'+hashlib.sha256(url.encode()).hexdigest()[:12], 'module':module,'en':en,'reference_translation_zh':zh,'structure_zh':structure,'context_zh':context,'level':1 if words<=16 else 2,'kind':'paper_quote','source':{'title':title,'url':url,'year':int(year),'year_basis':'conference_year' if 'nips.cc' in url else 'first_arxiv_submission','location':'Abstract','verification':'exact_text_checked_on_source_page','accessed_at':'2026-10-27','rights':'copyright_retained_by_original_rightsholder; short_attributed_excerpt'},'word_count':words,'target_terms':[t for t in terms.split(',') if norm(t) in by_key],'target_card_ids':[by_key[norm(t)]['id'] for t in terms.split(',') if norm(t) in by_key],'answer_hidden_by_default':True,'translation_status':'editorial_reference_not_author_translation'}
    sentences.append(sentence)

# Include independently sourced expansion records; preserve machine-review labels.
addition_path=ROOT/'sentence_additions.json'
if addition_path.exists():
    additions=json.loads(addition_path.read_text(encoding='utf8'))
    known={s['en'].lower() for s in sentences}
    for s in additions:
        s['source']['url']=re.sub(r'v\d+$','',s['source']['url'])
        s['source']['version_note']='核对访问当日的摘要页面；未固定历史版本'
        s['id']='s_'+hashlib.sha256(s['source']['url'].encode()).hexdigest()[:12]
        if s['en'].lower() not in known:
            sentences.append(s);known.add(s['en'].lower())
    assert len(sentences)<=365

# Recommended sequence blends general words and specialty terms every day.
core=[c for c in cards if c['origin']=='original_editorial']
modules=list(dict.fromkeys(c['module'] for c in core))
queues={m:sorted([c for c in core if c['module']==m],key=lambda c:(not bool(c['examples']),c['level'])) for m in modules}
order=[]
while any(queues.values()):
    for m in modules:
        if queues[m]:order.append(queues[m].pop(0)['id'])
order += [c['id'] for c in cards if c['origin']!='original_editorial']
order=data.get('learning_order',order)
days=[{'lesson':i//10+1,'card_ids':order[i:i+10]} for i in range(0,len(order),10)]
data.update(confusion_groups=groups,learning_order=order,selection_note='1156 个编辑核心条目优先；扩展条目从 AITD 经过别名归并、领域筛选和词条长度排序选入。非词频排名，未宣称覆盖所有必要词汇。')
write_json(ROOT/'vocabulary.json',data)
write_json(ROOT/'sentences.json',{'schema_version':'1.0.0','content_version':'2026-10-27.1','count':len(sentences),'planned_count':365,'remaining_count':365-len(sentences),'sentences':sentences})
write_json(ROOT/'learning_plan.json',{'schema_version':'1.0.0','new_cards_per_lesson':10,'total_lessons':len(days),'lessons':days,'review_note':'这里只提供词条顺序；复习算法与学习记录应在 APP 层实现，不把完成一课标记为掌握。','sentence_note':'论文句子按学习日使用；新增机器初译与自动结构提示待审校，未创建定时提醒。'})

counts={
    'vocabulary_cards':len(cards), 'original_editorial_cards':len(core), 'source_adapted_cards':len(cards)-len(core),
    'cards_with_collocations':sum(bool(c['collocations']) for c in cards),
    'cards_with_bilingual_examples':sum(bool(c['examples']) for c in cards),
    'cards_with_ipa':sum(bool(c['ipa']) for c in cards),
    'cards_with_part_of_speech':sum(bool(c['part_of_speech']) for c in cards),
    'paper_sentences':len(sentences), 'paper_sentences_remaining':365-len(sentences),
    'confusion_groups':len(groups), 'modules':dict(collections.Counter(c['module'] for c in cards)),
    'quality_status':'基础词库已建立；词卡字段仍有缺口。句库包含编辑译文与待审校机器初译，实际数量见统计。'
}
write_json(ROOT/'manifest.json',{'schema_version':'1.0.0','created_at':'2026-10-27','counts':counts,'content_gaps':dict(collections.Counter(x for c in cards for x in c['content_gaps']))})

# Only replace a generated staging database, then atomically publish it.
db=ROOT/'vocabulary.build.sqlite'
if db.exists():db.unlink()
con=sqlite3.connect(db)
con.executescript('''
CREATE TABLE metadata(key TEXT PRIMARY KEY,value TEXT NOT NULL);
CREATE TABLE cards(id TEXT PRIMARY KEY,term TEXT NOT NULL,meaning_zh TEXT NOT NULL,module TEXT NOT NULL,priority TEXT NOT NULL,content_depth TEXT NOT NULL,payload TEXT NOT NULL);
CREATE INDEX cards_module ON cards(module);
CREATE TABLE sentences(id TEXT PRIMARY KEY,en TEXT NOT NULL,reference_translation_zh TEXT NOT NULL,source_url TEXT NOT NULL,payload TEXT NOT NULL);
''')
con.executemany('INSERT INTO cards VALUES(?,?,?,?,?,?,?)',[(c['id'],c['term'],c['meaning_zh'],c['module'],c['priority'],c['content_depth'],json.dumps(c,ensure_ascii=False)) for c in cards])
con.executemany('INSERT INTO sentences VALUES(?,?,?,?,?)',[(s['id'],s['en'],s['reference_translation_zh'],s['source']['url'],json.dumps(s,ensure_ascii=False)) for s in sentences])
con.executemany('INSERT INTO metadata VALUES(?,?)',[('schema_version','1.0.0'),('content_version','2026-10-27.1'),('counts',json.dumps(counts,ensure_ascii=False))])
con.commit()
assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
con.close();db.replace(ROOT/'vocabulary.sqlite')
print(json.dumps(counts,ensure_ascii=False,indent=2))
