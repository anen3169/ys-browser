from flask import Flask, render_template, request
import requests
from bs4 import BeautifulSoup
import re, urllib.parse

app = Flask(__name__, template_folder='.')

# Geçici hafıza - Vercel'de kalıcı değil
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

        # Gereksiz tag'leri at
        for tag in soup(['script', 'style', 'nav', 'footer', 'header', 'aside']):
            tag.decompose()

        text = soup.get_text(separator=' ', strip=True)
        text = re.sub(r'\s+', ' ', text)[:10000] # 10k karakter limit

        trained_data = {"url": url, "content": text}
        title = soup.title.string.strip() if soup.title else url
        return f"AI eğitildi: {title}", None
    except Exception as e:
        return None, f"Eğitilemedi: Siteye erişilemedi"

def ai_sor(soru):
    global trained_data
    if not trained_data["content"]:
        return None, "Önce AI'ı eğit. Örnek: egit https://tr.wikipedia.org/wiki/TÜBİTAK"

    soru_kelimeler = [k.lower() for k in re.findall(r'\w+', soru) if len(k) > 2]
    content = trained_data["content"]

    # En alakalı 3 paragrafı bul
    paragraflar = [p.strip() for p in content.split('.') if len(p.strip()) > 40]
    bulunan = []

    for para in paragraflar:
        para_lower = para.lower()
        skor = sum(1 for k in soru_kelimeler if k in para_lower)
        if skor > 0:
            bulunan.append((skor, para))

    bulunan.sort(reverse=True, key=lambda x: x[0])

    if bulunan:
        cevap = '.join([p[1] for p in bulunan[:3]])
        return f"Kaynak: {trained_data['url']}\n\n{cevap}...", None
    else:
        return None, "Eğitilen sitede bu konu hakkında bilgi bulamadım"

def site_cek(url):
    try:
        headers = {'User-Agent': 'Mozilla/5.0 YS-Browser/1.0'}
        r = requests.get(url, headers=headers, timeout=8)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, 'html.parser')
        title = soup.title.string.strip() if soup.title else url
        meta = soup.find('meta', attrs={'name': 'description'})
        desc = meta['content'].strip() if meta and meta.get('content') else 'Açıklama yok'
        return [{'url': url, 'title': title, 'desc': desc[:200]}], None
    except:
        return None, "Siteye ulaşılamadı"

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
    return None, "Wikipedia'da bulunamadı. Başka kelime dene"

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
        # AI Eğitme: "egit https://site.com"
        if query.lower().startswith('egit '):
            url = query[5:].strip()
            msg, error = site_egit(url)
            if msg:
                ai_mode = True
                ai_message = msg
        # AI Sorma: "ai: soru"
        elif query.lower().startswith('ai:'):
            ai_mode = True
            soru = query[3:].strip()
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

app = app