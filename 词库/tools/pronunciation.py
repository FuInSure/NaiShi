"""Dictionary-backed IPA with explicitly labelled editorial supplements."""
from pathlib import Path
import re, json, hashlib, collections
ROOT=Path(__file__).resolve().parents[1]
SOURCE=ROOT/'source/pronunciation'
dictionary={line.split('\t')[0]:re.findall(r'/([^/]+)/',line.split('\t')[1]) for line in (SOURCE/'en_US.txt').read_text(encoding='utf-8').splitlines() if '\t' in line}
editorial={line.split('|')[0]:line.split('|')[1] for line in (ROOT/'tools/ipa_editorial.txt').read_text(encoding='utf-8-sig').splitlines() if line and not line.startswith('#')}
letters=dict(zip('abcdefghijklmnopqrstuvwxyz',['eɪ','biː','siː','diː','iː','ɛf','dʒiː','eɪtʃ','aɪ','dʒeɪ','keɪ','ɛl','ɛm','ɛn','oʊ','piː','kjuː','ɑr','ɛs','tiː','juː','viː','ˈdʌbəljuː','ɛks','waɪ','ziː']))
initialisms={'lstm','kl','kpss','rnn','pca','rbm','em'}
def component(word):
    key=word.lower()
    if key in initialisms:return {'word':word,'ipa':' '.join(letters[x] for x in key),'origin':'letter_names','note':'逐字母读法'}
    if key in ['0','1']:key={'0':'zero','1':'one'}[key]
    if key in editorial:return {'word':word,'ipa':editorial[key],'origin':'editorial','note':'编辑参考读音，未独立核验；人名可能有不同英语化读法'}
    if key not in dictionary:raise ValueError('Missing pronunciation: '+word)
    variants=dictionary[key]
    preferred={'present':'prɪˈzɛnt','lead':'liːd','read':'riːd','attribute':'ˈætrɪbjuːt'}
    if key in preferred:return {'word':word,'ipa':preferred[key],'variants':variants,'origin':'editorial','note':'依科研语境选读；未独立核验'}
    return {'word':word,'ipa':variants[0],'variants':variants,'origin':'ipa_dict','source_url':'https://github.com/open-dict-data/ipa-dict/blob/master/data/en_US.txt'}
def enrich_pronunciations(cards):
    report=collections.Counter()
    for c in cards:
        term=c['term'];key=term.lower()
        # Keep original editorial readings rather than silently replacing them.
        old=json.loads((ROOT/'tools/enrichment.json').read_text(encoding='utf-8'))['ipa_us']
        if key in old:
            parts=[{'word':term,'ipa':old[key],'origin':'editorial','note':'编辑参考读音，未独立核验'}]
        elif key in dictionary and key not in editorial and key not in initialisms:
            parts=[component(term)]
        else:
            tokens=re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?|[0-9]+",term)
            assert tokens,term
            parts=[component(t) for t in tokens]
        has_editorial=any(p['origin']=='editorial' for p in parts)
        c['ipa']=' '.join(p['ipa'] for p in parts)
        c['pronunciation']={'notation':'IPA','dialect':'US-oriented; names may use anglicized readings','value':c['ipa'],'origin':'component_readings' if len(parts)>1 else parts[0]['origin'],'review_status':'contains_editorial_pending_review' if has_editorial else 'dictionary_or_letter_names','components':parts,'note':('分词参考读音；未标注短语连读与句重音。' if len(parts)>1 else '')+('含编辑补充，未独立核验。' if has_editorial else '词典读音或字母名称。'),'accessed_at':'2026-10-30'}
        c['content_gaps']=[x for x in c['content_gaps'] if x not in ['ipa','bilingual_example']]
        c['examples']=[]
        report['total']+=1;report['with_editorial' if has_editorial else 'dictionary_or_letters']+=1
    (SOURCE/'coverage.json').write_text(json.dumps(dict(report),ensure_ascii=False,indent=2),encoding='utf-8')
