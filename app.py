from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__, template_folder='.')

def hesapla(sorgu):
    try:
        if re.match(r'^[\d\s\+\-\*\/\(\)\.]+$', sorgu):
            return eval(sorgu), True
    except:
        pass
    return None, False

def url_mi(sorgu):
    return re.match(r'^https?://', sorgu) is not None

def site_cek(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 YS-Browser Mobile/1.0'}
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
        return None, f"Site çekilemedi"

def web_ara(query):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 YS-Browser Mobile/1.0'}
        url = f"https://html.duckgo.com/html/?q={query}"
        r = requests.get(url, headers=headers, timeout=8)
        soup = BeautifulSoup(r.text, 'html.parser')
        
        results = []
        for res in soup.find_all('div', class_='result')[:8]:
            a = res.find('a', class_='result__a')
            if a:
                title = a.get_text(strip=True)
                link = a['href']
                desc_div = res.find('div', class_='result__snippet')
                desc = desc_div.get_text(strip=True) if desc_div else ''
                results.append({'url': link, 'title': title, 'desc': desc[:200]})
        return results, None
    except Exception as e:
        return None, "Arama yapılamadı"

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
                         results=results, 
                         is_math=is_math,
                         result=math_result,
                         error=error)

app = app