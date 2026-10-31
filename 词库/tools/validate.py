from pathlib import Path
import json, sqlite3, collections, re, hashlib
from build import ROOT,norm

def read(name):return json.loads((ROOT/name).read_text(encoding='utf8'))
v=read('vocabulary.json');s=read('sentences.json');m=read('manifest.json');p=read('learning_plan.json')
cards=v['cards'];sentences=s['sentences'];ids={c['id'] for c in cards}
assert len(cards)==1900==v['count']==m['counts']['vocabulary_cards']
assert len(ids)==len(cards)
assert all(c['ipa'] and c['pronunciation']['components'] and not c['examples'] for c in cards)
assert m['counts']['cards_with_ipa']==1900 and m['counts']['cards_with_bilingual_examples']==0
assert len({norm(c['term']) for c in cards})==len(cards)
assert len(sentences)==s['count']==m['counts']['paper_sentences']
assert len({x['source']['url'] for x in sentences})==len(sentences)
assert len({x['en'] for x in sentences})==len(sentences)
assert collections.Counter(c['module'] for c in cards)==m['counts']['modules']
for c in cards:
    assert c['term'].strip() and c['meaning_zh'].strip()
    assert '\ufffd' not in json.dumps(c,ensure_ascii=False)
    assert set(c['related_ids']) <= ids
    assert c['id'] not in c['related_ids']
    expected={name for name,value in [('ipa',c['ipa']),('part_of_speech',c['part_of_speech']),('collocation',c['collocations'])] if not value}
    assert set(c['content_gaps'])==expected,(c['term'],expected,c['content_gaps'])
    if c['origin']=='adapted_aitd':
        assert c['source_ids'] and c['source_locations'] and c['license']=='CC-BY-NC-SA-4.0'
    for loc in c['source_locations']:
        raw=(ROOT/loc['file']).read_text(encoding='utf8').splitlines()[loc['line']-1]
        assert raw.split('|')[0] in c['source_ids']
    for e in c['examples']:
        assert e['en'] and e['zh'] and e['kind']=='original_teaching_example'
for x in sentences:
    assert 0<x['word_count']<=25
    assert x['source']['url'].startswith('https://')
    assert x['source']['location']=='Abstract'
    assert set(x['target_card_ids'])<=ids
    assert x['reference_translation_zh'] and x['structure_zh'] and x['context_zh']
    assert x['answer_hidden_by_default']
plan_ids=[i for lesson in p['lessons'] for i in lesson['card_ids']]
assert len(plan_ids)==1900 and set(plan_ids)==ids
assert len(p['lessons'])==190
con=sqlite3.connect(ROOT/'vocabulary.sqlite')
assert con.execute('PRAGMA integrity_check').fetchone()[0]=='ok'
assert con.execute('SELECT count(*) FROM cards').fetchone()[0]==1900
assert con.execute('SELECT count(*) FROM sentences').fetchone()[0]==len(sentences)
for cid,payload in con.execute('SELECT id,payload FROM cards'):
    assert json.loads(payload)==next(c for c in cards if c['id']==cid)
con.close()
reader=(ROOT/'打开词库.html').read_text(encoding='utf8')
embedded=json.loads(re.search(r'<script id="vocab-data" type="application/json">(.*?)</script>',reader,re.S)[1])
assert embedded==v
for marker in ['__VOCAB__','__SENTENCES__','__MANIFEST__','__JS__']:assert marker not in reader
assert not re.search(r'[A-Z]:[\\/]',reader)
checks=['1900 个词条与唯一 ID','别名归并后的英文唯一性','模块统计与清单一致','所有缺口与实际字段一致','原始来源行号可定位','论文句子来源与关联词 ID','190 课学习顺序完整且不重复','SQLite 完整性与 JSON 逐条一致','阅读版内嵌数据与主文件一致','前端未嵌入本机绝对路径']
report={'result':'pass','checked_at':'2026-10-28','checks':checks,'scope_note':'结构与一致性验证；不等于所有释义、编辑音标和参考译文已获独立专家核验。'}
(ROOT/'validation.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf8')
for name in ['vocabulary.json','vocabulary.sqlite','sentences.json','learning_plan.json','manifest.json','打开词库.html']:
    print(name,hashlib.sha256((ROOT/name).read_bytes()).hexdigest())
(ROOT/'SHA256SUMS.txt').write_text('\n'.join(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()+'  '+n for n in ['vocabulary.json','vocabulary.sqlite','sentences.json','learning_plan.json','manifest.json','打开词库.html'])+'\n',encoding='utf8')
print('PASS:',len(checks),'integrity checks')
