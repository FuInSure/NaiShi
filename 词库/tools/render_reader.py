from pathlib import Path
import json
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'tools/reader.html').read_text(encoding='utf8')
for placeholder,filename in [('__VOCAB__','vocabulary.json'),('__SENTENCES__','sentences.json'),('__MANIFEST__','manifest.json')]:
    payload=json.dumps(json.loads((ROOT/filename).read_text(encoding='utf8')),ensure_ascii=False,separators=(',',':')).replace('<','\\u003c').replace('>','\\u003e').replace('&','\\u0026')
    s=s.replace(placeholder,payload)
s=s.replace('__JS__',(ROOT/'tools/reader.js').read_text(encoding='utf8')+'\n'+(ROOT/'tools/study.js').read_text(encoding='utf8'))
(ROOT/'打开词库.html').write_text(s,encoding='utf8')
print('Reader generated:',len(s.encode('utf8')),'bytes')
