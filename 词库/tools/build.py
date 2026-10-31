"""Build local, reproducible vocabulary assets. Standard library only."""
from pathlib import Path
import re, json, hashlib, unicodedata, collections, html

ROOT = Path(__file__).resolve().parents[1]
SOURCE_URL = 'https://github.com/jiqizhixin/Artificial-Intelligence-Terminology-Database'

ALIASES = {
    'back propagation':'backpropagation',
    'back propagation algorithm':'backpropagation',
    'back propagation through time':'backpropagation through time',
    'bayes theorem':"bayes' theorem",
    'bayes inference':'bayesian inference',
    'bayes network':'bayesian network',
    'bayes net':'bayesian network',
    'bayesian net':'bayesian network',
    'long short term memory network':'long short term memory',
    'long short term memory networks':'long short term memory',
    'gaussian':'gaussian distribution',
    'normal distribution':'gaussian distribution',
    'gaussian mixture':'gaussian mixture model',
    'kullback leibler divergence':'kullback leibler divergence',
    'kl divergence':'kullback leibler divergence',
    'maximum likelihood':'maximum likelihood estimation',
    'maximum a posteriori':'maximum a posteriori estimation',
    'maximum posterior estimation':'maximum a posteriori estimation',
    'multi layer perceptron':'multilayer perceptron',
    'multi layer perceptrons':'multilayer perceptron',
    'multilayer perceptrons':'multilayer perceptron',
    'multi layer perception':'multilayer perceptron',
    'multi layer neural network':'multilayer neural network',
    'normalization layer':'normalization layer',
    'probability density':'probability density function',
    'probability mass':'probability mass function',
    'rectified linear units':'rectified linear unit',
    'rectified linear unit relu':'rectified linear unit',
    'mean square error':'mean squared error',
    'root mean square error':'root mean squared error',
    'mean absolute errors':'mean absolute error',
    'conditional random fields':'conditional random field',
    'gaussian processes':'gaussian process',
    'hidden markov models':'hidden markov model',
    'monte carlo method':'monte carlo estimation',
    'monte carlo methods':'monte carlo estimation',
    'monte carlo algorithm':'monte carlo estimation',
    'self attention mechanism':'self attention',
    'convolution neural network':'convolutional neural network',
    'convolutional neural networks':'convolutional neural network',
    'recurrent neural networks':'recurrent neural network',
    'recurrent network':'recurrent neural network',
    'neural networks':'neural network',
    'artificial neural network':'neural network',
    'batch normalisation':'batch normalization',
    'tied weight':'weight tying',
    'tied weights':'weight tying',
    'weight sharing':'parameter sharing',
    'prediction':'prediction',
    'student t distribution':"student's t distribution",
    'student s t distribution':"student's t distribution",
    't distribution':"student's t distribution",
    'exponentially weighted moving average':'exponential moving average',
    'dilated causal convolution':'dilated causal convolution',
}

def raw_norm(s):
    s=unicodedata.normalize('NFKC',s).lower().strip().replace('’',"'")
    s=re.sub(r'[-–—_/]+',' ',s)
    s=re.sub(r'\s+',' ',s)
    return s

for line in (ROOT/'tools/aliases.txt').read_text(encoding='utf8').splitlines():
    if line.strip() and not line.startswith('#'):
        alt,canon=line.split('|')
        ALIASES[raw_norm(alt)]=raw_norm(canon)

def norm(s):
    s=raw_norm(s)
    visited=set()
    while s in ALIASES and s not in visited:
        visited.add(s)
        s=raw_norm(ALIASES[s])
    return s

CORRECTIONS={raw_norm(k):v for k,v in json.loads((ROOT/'tools/corrections.json').read_text(encoding='utf8')).items()}
EXCLUDED={norm(x) for x in (ROOT/'tools/exclude.txt').read_text(encoding='utf8').splitlines() if x.strip() and not x.startswith('#')}

def clean(s):
    s=re.sub(r'<[^>]+>','',s)
    s=re.sub(r'\[([^]]+)\]\([^)]*\)',r'\1',s)
    return html.unescape(s).strip().strip('*').strip()

def read_source():
    records={}
    for p in sorted((ROOT/'source').glob('*.md')):
        for ln,line in enumerate(p.read_text(encoding='utf8').splitlines(),1):
            if not line.startswith('AITD-'):continue
            cells=line.split('|')
            if len(cells)<3:continue
            sid,en,zh=map(clean,cells[:3])
            if not en or not zh:continue
            correction=CORRECTIONS.get(raw_norm(en),{})
            original_en,original_zh=en,zh
            en=correction.get('term',en)
            zh=correction.get('meaning_zh',zh)
            key=norm(en)
            display=key if raw_norm(en)!=key else en
            entry=records.setdefault(key,{'term':display,'meaning_zh':zh,'source_ids':[], 'abbreviations':[], 'source_locations':[], 'in_ml_section':False})
            if raw_norm(en)==key:entry.update(term=en,meaning_zh=zh)
            if correction:entry['editorial_correction']=correction
            if original_en!=en or original_zh!=zh:entry['original_source_text']={'term':original_en,'meaning_zh':original_zh}
            entry['source_ids'].append(sid)
            entry['source_locations'].append({'file':'source/'+p.name,'line':ln})
            if p.name.startswith('section_'):entry['in_ml_section']=True
            if len(cells)>3:
                abbr=clean(cells[3])
                if abbr:entry['abbreviations'].append(abbr)
    return records

def category(term):
    t=norm(term)
    if re.search(r'bayes|probab|likelihood|posterior|prior|variational|markov|monte carlo|gibbs|sampling|distribution|gaussian|entropy|stochastic|random variable|random field|random process|uncertaint|covariance|copula|bernoulli|binomial|poisson|dirichlet|quantile|density|inference|kalman|particle filter|state space|normalizing flow|expectation maximization',t):return '概率建模'
    if re.search(r'time series|temporal|forecast|spatial|seasonal|autoregress|autocorrel|time step|time delay|wavelet|fourier|signal|spectr|frequency|smoothing|moving average|stationar|trend|lagged',t):return '时空序列预测'
    if re.search(r'neural|network|convol|recurrent|attention|encoder|decoder|perceptron|embedding|residual|gating|gated|gate|fusion|graph|lstm|pooling|hidden state|hidden layer|activation|rectif|sigmoid|tanh|softmax|skip connection',t):return '混合神经网络'
    if re.search(r'matrix|vector|tensor|scalar|derivative|gradient|hessian|jacobian|eigen|singular|norm\b|integral|calculus|convex|concave|theorem|lemma|proof|inequality|distance|metric|inner product|outer product|orthogonal|euclid|algebra|lagrange|taylor|differential|polynomial|function|constraint|optimi|descent|saddle|minimum|maximum|variance|correlation|statistic|confidence|hypothesis|estimato|regress|test\b|square|absolute|least|error|bias|median|mean\b|moment\b',t):return '数学与训练基础'
    return '机器学习基础与扩展'

EXCLUDE = re.compile(r'acoustic|speech|phonem|phonetic|phonolog|morphem|tokeniz|word2vec|wordnet|word sense|word segmentation|bag of words|bag of word|part.of.speech|parse tree|parsing|parser|syntactic|syntactic|syntax|n gram|bigram|trigram|unigram|language model|machine translation|translation model|question answering|text summar|named entity|entity linking|coreference|co reference|sentiment|document retrieval|topic document|topic model|topic vector|term frequency|inverse document|tf idf|natural language|linguistic|vocabulary|lexical|lexicon|word vector|word embedding|token\b|chatbot|dialogue|dialog\b|recognition of speech|speaker|speech synthesis|acquisition of language|corpus|corpora|bleu|rouge|annotation scheme|semantic role|semantic parsing|image caption|object detection|object recognition|face recognition|facial|image segmentation|instance segmentation|semantic segmentation|bounding box|optical flow|optical character|image retrieval|image classification|object localization|object tracking|super resolution|style transfer|pixel|voxel|video game|chess|game tree|alpha beta|alphago|alpha go|go game|minimax search|robot|slam|lidar|point cloud|pose estimation|kinemat|inverse kinematic|servo|actuator|reinforcement learning|actor critic|q learning|sarsa|bellman|temporal difference|policy gradient|policy iteration|value iteration|markov decision|reward|action value|state value|bandit|epsilon greedy|exploration exploitation|monte carlo tree|rollout|roll out|behaviorism|behaviourism|actionism|symbolism|connectionism|cognitive architecture|turing test|strong ai|weak ai|artificial general|expert system|knowledge base|knowledge graph|ontology|ontolog|first order logic|propositional logic|predicate logic|description logic|resolution principle|unification|theorem prover|fuzzy control|fuzzy logic|genetic algorithm|genetic programming|evolutionary|ant colony|particle swarm|simulated annealing|tabu|hill climbing|constraint satisfaction|heuristic search|breadth first|depth first|best first|beam search|a star|a\*|search tree|backward search|forward search|backward induction|alpha beta|hardware|chip|processing unit|bitrate|cuda|mapreduce|map reduce|hadoop|spark\b|database|sql\b|blockchain|internet of things|cloud computing|computer vision|computer graphics|virtual reality|augmented reality|knowledge representation',re.I)

def build():
    sources=read_source()
    cards={}
    for line in (ROOT/'tools/curated.txt').read_text(encoding='utf8').splitlines():
        if not line.strip():continue
        if line.startswith('#'):
            module,level=line[1:].strip().split('|');continue
        term,meaning,collocation=[x.strip() for x in line.split('|')]
        key=norm(term)
        if key in cards:raise ValueError('duplicate curated '+term)
        cards[key]={'term':term,'meaning_zh':meaning,'module':module,'level':int(level),'priority':'核心','collocations':[collocation],'origin':'original_editorial','review_status':'editorial_draft','aliases':[],'source_ids':[],'source_locations':[],'abbreviations':[]}
    candidates=[]; rejected=[]
    for key,s in sources.items():
        if key in cards:
            c=cards[key]
            for field in ['source_ids','source_locations','abbreviations']:c[field]=s[field]
            if s['term'].lower()!=c['term'].lower():c['aliases'].append(s['term'])
            c['source_meaning_zh']=s['meaning_zh']
            continue
        if key in EXCLUDED or EXCLUDE.search(key):rejected.append({'term':s['term'],'reason':'outside_primary_learning_scope_or_unreliable_fragment'});continue
        if not re.search(r'[\u4e00-\u9fff]',s['meaning_zh']):rejected.append({'term':s['term'],'reason':'no_chinese_gloss'});continue
        if len(key)<3:rejected.append({'term':s['term'],'reason':'ambiguous_short_label'});continue
        module=s.get('editorial_correction',{}).get('module',category(key))
        score=(100 if s['in_ml_section'] else 0)+(30 if module in ['概率建模','时空序列预测','混合神经网络','数学与训练基础'] else 10)
        score+=max(0,6-len(key.split()))
        candidates.append((score,key,s,module))
    # Hash tie-break avoids alphabetic A-D selection bias; no claim of corpus frequency.
    candidates.sort(key=lambda x:(-x[0],hashlib.sha256(x[1].encode()).hexdigest()))
    limit=1900-len(cards)
    for score,key,s,module in candidates[:limit]:
        cards[key]={**s,'module':module,'level':2 if s['in_ml_section'] else 3,'priority':'进阶' if s['in_ml_section'] else '扩展','collocations':[],'origin':'adapted_aitd','review_status':'source_imported_not_individually_reviewed','aliases':[]}
    for score,key,s,module in candidates[limit:]:rejected.append({'term':s['term'],'reason':'reserve_not_selected'})
    out=[]
    for key,c in cards.items():
        c['id']='v_'+hashlib.sha256(key.encode()).hexdigest()[:12]
        c['normalized_term']=key
        c['part_of_speech']=None
        c['ipa']=None
        c['examples']=[]
        c['notes_zh']=None
        c['related_ids']=[]
        c['source_ids']=sorted(set(c['source_ids']))
        c['abbreviations']=sorted(set(c['abbreviations']))
        c['source_url']=SOURCE_URL if c['source_ids'] else None
        c['license']='CC-BY-NC-SA-4.0' if c['origin']=='adapted_aitd' else 'original_project_content'
        c['card_type']='word' if ' ' not in c['term'].strip() else 'phrase_or_term'
        c['tags']=[c['module']]
        c['content_gaps']=['ipa','part_of_speech','bilingual_example']+([] if c['collocations'] else ['collocation'])
        c.pop('in_ml_section',None)
        out.append(c)
    (ROOT/'vocabulary.json').write_text(json.dumps({'schema_version':'1.0.0','content_version':'2026-10-27.1','count':len(out),'cards':out},ensure_ascii=False,indent=2),encoding='utf8')
    (ROOT/'source/selection_log.json').write_text(json.dumps(rejected,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps({'cards':len(out),'curated':sum(c['origin']=='original_editorial' for c in out),'source_unique':len(sources),'eligible_additions':len(candidates),'modules':dict(collections.Counter(c['module'] for c in out))},ensure_ascii=False,indent=2))

if __name__=='__main__':build()
