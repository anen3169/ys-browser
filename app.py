from flask import Flask, render_template, request
import requests
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
        from bs4 import BeautifulSoup
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
    # 1. DuckDuckGo Instant Answer API - Vercel'de ban yok
    try:
        api_url = f"https://api.duckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        r = requests.get(api_url, timeout=8)
        data = r.json()

        results = []

        # Özet varsa
        if data.get('AbstractURL') and data.get('AbstractText'):
            results.append({
                'url': data['AbstractURL'],
                'title': data.get('Heading', query),
                'desc': data['AbstractText'][:250]
            })

        # İlgili konular
        for topic in data.get('RelatedTopics', [])[:7]:
            if isinstance(topic, dict) and 'FirstURL' in topic:
                results.append({
                    'url': topic['FirstURL'],
                    'title': topic.get('Text', '').split(' - ')[0][:80],
                    'desc': topic.get('Text', '')[:200]
                })

        if results:
            return results, None
    except:
        pass

    # 2. Fallback: Wikipedia API - Türkçe
    try:
        wiki_url = f"https://tr.wikipedia.org/api/rest_v1/page/summary/{urllib.parse.quote(query)}"
        r = requests.get(wiki_url, timeout=6)
        if r.status_code == 200:
            data = r.json()
            return [{
                'url': data.get('content_urls', {}).get('desktop', {}).get('page', f'https://tr.wikipedia.org/wiki/{query}'),
                'title': data.get('title', query),
                'desc': data.get('extract', '')[:250]
            }], None
    except:
        pass

    return None, "Sonuç bulunamadı. Başka kelime dene"

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