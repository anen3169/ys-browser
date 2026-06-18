from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re, urllib.parse

app = Flask(__name__, template_folder='.')

# Geçici hafıza - Vercel'de kalıcı değil, istek bazlı
trained_data = {"url": "", "content": ""}

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

def site_egit(url):
    global trained_data
    try:
        headers = {'User-Agent': 'Mozilla/5.0 YS-Browser/1.0'}
        r = requests.get(url, headers=headers, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Sadece önemli text'leri al
        for tag in soup(['script', 'style', 'nav', 'footer', 'header']):
            tag.decompose()
            
        text = soup.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)[:8000]  # 8000 karakter limit
        
        trained_data = {"url": url, "content": text}
        title = soup.title.string.strip() if soup.title else url
        return f"AI eğitildi: {title}", None
    except Exception as e:
        return None, f"Eğitilemedi: {str(e)[:50]}"

def ai_sor(soru):
    global trained_data
    if not trained_data["content"]:
        return None, "Önce AI'ı eğit. Örnek: https://tr.wikipedia.org/wiki/TÜBİTAK"
    
    # Basit arama: sorudaki kelimeleri içerikte ara
    soru_kelimeler = [k.lower() for k in re.findall(r'\w+', soru) if len(k) > 3]
    content_lower = trained_data["content"].lower()
    
    bulunan_cumleler = []
    for cumle in trained_data["content"].split('. '):
        if any(k in cumle.lower() for k in soru_kelimeler):
            bulunan_cumleler.append(cumle.strip())
        if len(bulunan_cumleler) >= 3:
            break
    
    if bulunan_cumleler:
        cevap = '.join(bulunan_cumleler[:3])
        return f"[{trained_data['url']} kaynağından] {cevap}...", None
    else:
        return None, "Eğitilen sitede bu konu hakkında bilgi bulamadım"

def web_ara(query):
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
    return None, "Wikipedia'da bulunamadı"

@app.route('/', methods=['GET'])
def index():
    query = request.args.get('q', '').strip()
    results = []
    is_math = False
    math_result = None
    error = None
    ai_mode = False
    ai_message = ""

    if query:
        # AI Eğitme komutu: "egit https://site.com" veya direkt link
        if query.startswith('egit ') or (url_mi(query) and 'egit' in request.args):
            url = query.replace('egit ', '').strip()
            msg, error = site_egit(url)
            if msg:
                ai_mode = True
                ai_message = msg
        # AI Sorma: "ai: soru" formatı
        elif query.startswith('ai:'):
            ai_mode = True
            soru = query.replace('ai:', '').strip()
            msg, error = ai_sor(soru)
            if msg:
                ai_message = msg
        else:
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
                         error=error,
                         ai_mode=ai_mode,
                         ai_message=ai_message,
                         trained_url=trained_data["url"])

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
        return results, None
    except:
        return None, "Siteye ulaşılamadı"

app = app