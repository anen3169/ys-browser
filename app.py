from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re, urllib.parse

app = Flask(__name__, template_folder='.')

def hesapla(sorgu):
    try:
        sorgu = sorgu.strip()
        if re.match(r'^[\d\s\+\-\*\/\(\)\.]+$', sorgu) and sorgu:
            return eval(sorgu), True
    except:
        pass
    return None, False

def url_mi(sorgu):
    return re.match(r'^https?://', sorgu) is not None

def site_cek(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 YS-Browser/1.0'}
        r = requests.get(url, headers=headers, timeout=8)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')

        title = soup.title.string.strip() if soup.title else url
        meta = soup.find('meta', attrs={'name': 'description'})
        desc = meta['content'].strip() if meta and meta.get('content') else 'Açıklama yok'

        results = [{'url': url, 'title': title, 'desc': desc[:200]}]

        for a in soup.find_all('a', href=True)[:8]:
            link = a['href']
            if link.startswith('http'):
                text = a.get_text(strip=True)
                if text and 10 < len(text) < 100:
                    results.append({'url': link, 'title': text, 'desc': ''})
        return results, None
    except:
        return None, "Siteye ulaşılamadı"

def web_ara(query):
    # SearXNG public instance'ları - sırayla dener
    instances = [
        'https://searx.be',
        'https://search.bus-hit.me',
        'https://baresearch.org',
        'https://searx.work'
    ]
    
    headers = {'User-Agent': 'Mozilla/5.0 YS-Browser/1.0'}
    
    for instance in instances:
        try:
            url = f"{instance}/search?q={urllib.parse.quote(query)}&format=json&language=tr-TR"
            r = requests.get(url, headers=headers, timeout=7)
            if r.status_code == 200:
                data = r.json()
                results = []
                for res in data.get('results', [])[:8]:
                    results.append({
                        'url': res.get('url', ''),
                        'title': res.get('title', query),
                        'desc': res.get('content', '')[:200]
                    })
                if results:
                    return results, None
        except:
            continue
    
    return None, "Arama motoruna bağlanılamadı. İnterneti kontrol et"

@app.route('/', methods=['GET'])
def index():
    query = request.args.get('q', '').strip()
    results = []
    is_math = False
    math_result = None
    error = None

    if query:
        math_result, is_math = hesapla(query)
        if not is_math:
            if url_mi(query):
                results, error = site_cek(query)
            else:
                results, error = web_ara(query)

    return render_template('index.html',
                         query=query,
                         results=results or [],
                         is_math=is_math,
                         result=math_result,
                         error=error)

app = app