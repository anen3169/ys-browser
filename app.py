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
    except Exception as e:
        return None, f"Site hatası: {str(e)[:30]}"

def web_ara(query):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Accept': 'text/html,application/xhtml+xml'
    }
    q = urllib.parse.quote_plus(query)
    
    # 1. Deneme: Bing HTML - Vercel'de en stabil olanı
    try:
        url = f"https://www.bing.com/search?q={q}&count=8"
        r = requests.get(url, headers=headers, timeout=7)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            results = []
            for li in soup.find_all('li', class_='b_algo')[:8]:
                a = li.find('a', href=True)
                h2 = li.find('h2')
                p = li.find('p')
                if a and h2:
                    results.append({
                        'url': a['href'],
                        'title': h2.get_text(strip=True),
                        'desc': p.get_text(strip=True)[:200] if p else ''
                    })
            if results:
                return results, None
    except Exception as e:
        print(f"Bing hata: {e}")

    # 2. Fallback: DuckDuckGo Lite - en hafif sürüm
    try:
        url = f"https://duckgo.com/lite/?q={q}"
        r = requests.get(url, headers=headers, timeout=7)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            results = []
            for a in soup.find_all('a', class_='result-link')[:8]:
                results.append({
                    'url': a['href'],
                    'title': a.get_text(strip=True),
                    'desc': ''
                })
            if results:
                return results, None
    except Exception as e:
        print(f"DDG Lite hata: {e}")

    return None, "Arama başarısız. Vercel IP engeli olabilir"

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