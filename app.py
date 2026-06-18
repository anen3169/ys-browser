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
    try:
        # 1. Deneme: DuckDuckGo Instant Answer API - bedava, limit yok
        api_url = f"https://api.duckgo.com/?q={urllib.parse.quote(query)}&format=json&no_html=1&skip_disambig=1"
        r = requests.get(api_url, timeout=6)
        data = r.json()

        results = []

        # Abstract varsa en üste koy
        if data.get('AbstractURL') and data.get('AbstractText'):
            results.append({
                'url': data['AbstractURL'],
                'title': data.get('Heading', query),
                'desc': data['AbstractText'][:200]
            })

        # İlgili konular
        for topic in data.get('RelatedTopics', [])[:7]:
            if 'FirstURL' in topic and 'Text' in topic:
                results.append({
                    'url': topic['FirstURL'],
                    'title': topic['Text'].split(' - ')[0][:80],
                    'desc': topic['Text'][:200]
                })

        if results:
            return results, None

        # 2. Fallback: HTML sonuç sayfası
        html_url = f"https://html.duckgo.com/html/?q={urllib.parse.quote(query)}"
        headers = {'User-Agent': 'Mozilla/5.0'}
        r = requests.get(html_url, headers=headers, timeout=6)
        soup = BeautifulSoup(r.text, 'html.parser')

        for res in soup.find_all('div', class_='result')[:8]:
            a = res.find('a', class_='result__a')
            if a:
                title = a.get_text(strip=True)
                link = a['href']
                desc_div = res.find('a', class_='result__snippet')
                desc = desc_div.get_text(strip=True) if desc_div else ''
                results.append({'url': link, 'title': title, 'desc': desc[:200]})

        if not results:
            return None, "Sonuç bulunamadı"
        return results, None

    except Exception as e:
        return None, "Arama sunucusu yanıt vermedi"

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