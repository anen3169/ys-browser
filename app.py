from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re

app = Flask(__name__, template_folder='.')

def hesapla(sorgu):
    try:
        # Videodaki "15*20+30 = 330" olayı
        if re.match(r'^[\d\s\+\-\*\/\(\)\.]+$', sorgu):
            return eval(sorgu), True
    except:
        pass
    return None, False

def site_cek(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 YS-Browser Vercel/1.0'}
        r = requests.get(url, headers=headers, timeout=8)  # Vercel 10sn limit
        r.raise_for_status()
        r.encoding = r.apparent_encoding
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
        return None, f"Site çekilemedi: {str(e)}"

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
            if query.startswith('http'):
                results, error = site_cek(query)
            else:
                error = "URL gir veya hesap yap: 15*20+30"
    
    return render_template('index.html', 
                         query=query, 
                         results=results, 
                         is_math=is_math,
                         result=math_result,
                         error=error)

# Vercel için şart
app = app