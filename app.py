from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re, urllib.parse, time

app = Flask(__name__, template_folder='.')

# Başlangıç cache'i
cache_data = {
    "wikipedia-tr": [],
    "wikipedia-ua": [],
    "wikipedia-eu": [],
    "webtekno": []
}
cache_loaded = False

def init_cache():
    """Vercel cold start'ta çalışır"""
    global cache_data, cache_loaded
    if cache_loaded:
        return

    headers = {'User-Agent': 'Mozilla/5.0 YS-Browser/1.0'}
    
    # Wikipedia TR - 1500 başlık
    try:
        url = "https://tr.wikipedia.org/w/api.php?action=query&list=allpages&aplimit=500&format=json"
        for _ in range(3): # 3x500 = 1500
            r = requests.get(url, headers=headers, timeout=8)
            pages = r.json().get('query', {}).get('allpages', [])
            for p in pages:
                cache_data["wikipedia-tr"].append({
                    'title': p['title'],
                    'url': f"https://tr.wikipedia.org/wiki/{urllib.parse.quote(p['title'].replace(' ', '_'))}"
                })
            if 'continue' in r.json():
                url = f"https://tr.wikipedia.org/w/api.php?action=query&list=allpages&aplimit=500&apfrom={pages[-1]['title']}&format=json"
            time.sleep(0.5)
    except:
        pass

    # Wikipedia UA - 500 başlık
    try:
        url = "https://uk.wikipedia.org/w/api.php?action=query&list=allpages&aplimit=500&format=json"
        r = requests.get(url, headers=headers, timeout=8)
        pages = r.json().get('query', {}).get('allpages', [])
        for p in pages[:500]:
            cache_data["wikipedia-ua"].append({
                'title': p['title'],
                'url': f"https://uk.wikipedia.org/wiki/{urllib.parse.quote(p['title'].replace(' ', '_'))}"
            })
    except:
        pass

    # Wikipedia EU - 200 başlık
    try:
        url = "https://eu.wikipedia.org/w/api.php?action=query&list=allpages&aplimit=200&format=json"
        r = requests.get(url, headers=headers, timeout=8)
        pages = r.json().get('query', {}).get('allpages', [])
        for p in pages[:200]:
            cache_data["wikipedia-eu"].append({
                'title': p['title'],
                'url': f"https://eu.wikipedia.org/wiki/{urllib.parse.quote(p['title'].replace(' ', '_'))}"
            })
    except:
        pass

    # Webtekno - 300 haber başlığı
    try:
        r = requests.get("https://www.webtekno.com", headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        count = 0
        for a in soup.find_all('a', href=True):
            link = a['href']
            text = a.get_text(strip=True)
            if 'webtekno.com' in link and '/haber/' in link and text and len(text) > 15:
                cache_data["webtekno"].append({'title': text, 'url': link})
                count += 1
                if count >= 300:
                    break
    except:
        pass

    cache_loaded = True

init_cache()

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

def sayfa_tara(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 YS-Browser/1.0'}
        r = requests.get(url, headers=headers, timeout=8)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else url
        meta = soup.find('meta', attrs={'name': 'description'})
        desc = meta['content'].strip() if meta and meta.get('content') else 'Açıklama yok'
        links = []
        for a in soup.find_all('a', href=True)[:20]:
            link = a['href']
            text = a.get_text(strip=True)
            if link.startswith('http') and text and 5 < len(text) < 80:
                links.append({'url': link, 'title': text})
        return {'url': url, 'title': title, 'desc': desc[:250], 'links': links}, None
    except:
        return None, "Site taranamadı"

def cache_ara(query):
    query_lower = query.lower()
    results = []
    
    for site, items in cache_data.items():
        for item in items:
            if query_lower in item['title'].lower():
                results.append({
                    'url': item['url'],
                    'title': item['title'],
                    'desc': f"Önbellek: {site}"
                })
            if len(results) >= 12:
                break
        if len(results) >= 12:
            break
    
    if results:
        return results, None
    
    # Cache'de yoksa Wikipedia API'den çek
    try:
        search_term = query.replace(' ', '_')
        wiki_url = f"https://tr.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(search_term)}"
        headers = {'User-Agent': 'YS-Browser/1.0'}
        r = requests.get(wiki_url, headers=headers, timeout=8)
        if r.status_code == 200:
            data = r.json()
            return [{
                'url': data.get('content_urls', {}).get('desktop', {}).get('page'),
                'title': data.get('title', query),
                'desc': data.get('extract', 'Açıklama yok')[:250]
            }], None
    except:
        pass
    return None, "Sonuç bulunamadı"

@app.route('/', methods=['GET'])
def index():
    query = request.args.get('q', '').strip()
    result = None
    results = []
    is_math = False
    math_result = None
    error = None

    if query:
        math_result, is_math = hesapla(query)
        if not is_math:
            if url_mi(query):
                result, error = sayfa_tara(query)
            else:
                results, error = cache_ara(query)

    return render_template('index.html',
                         query=query,
                         result=result,
                         results=results or [],
                         is_math=is_math,
                         math_result=math_result,
                         error=error,
                         cache_stats={
                             'tr': len(cache_data['wikipedia-tr']),
                             'ua': len(cache_data['wikipedia-ua']),
                             'eu': len(cache_data['wikipedia-eu']),
                             'webtekno': len(cache_data['webtekno'])
                         })

app = app