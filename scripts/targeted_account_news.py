import os, time, hashlib, feedparser
from urllib.parse import quote_plus, urlparse
from storage import get_client

sb = get_client()
LIMIT=int(os.getenv("TARGETED_NEWS_COMPANY_LIMIT","120"))
MAX_QUERIES=int(os.getenv("TARGETED_NEWS_MAX_QUERIES","3"))
MAX_ENTRIES=int(os.getenv("TARGETED_NEWS_MAX_ENTRIES","4"))

RELIABLE = ["businessimmo.com","lemoniteur.fr","batiactu.com","cfnewsimmo.net","immoweek.fr","lesechos.fr","actu.fr","ouest-france.fr","sudouest.fr","lejournaldesentreprises.com","mesinfos.fr"]
RULES = {
 "program_launch":["programme immobilier","lancement commercial","mise en commercialisation","logements neufs","résidence neuve"],
 "rehabilitation":["réhabilitation","rehabilitation","déficit foncier","deficit foncier","malraux","denormandie","monument historique"],
 "foncier":["permis de construire","acquisition foncière","acquisition fonciere","terrain"],
 "partnership":["prescripteurs","partenaires commerciaux","réseau de commercialisation","commercialisateurs"],
 "recruitment":["directeur commercial immobilier","responsable développement foncier","responsable programmes immobiliers"]
}

def domain(url):
    try: return urlparse(url).netloc.replace("www.","").lower()
    except Exception: return ""

def reliable(url): return any(d in domain(url) for d in RELIABLE)

def classify(text):
    t=text.lower()
    best=("news_article",25,[])
    for typ, kws in RULES.items():
        hits=[k for k in kws if k in t]
        if hits:
            score=min(50+len(hits)*15,95)
            if score>best[1]: best=(typ,score,hits)
    return best

def exists(h):
    return bool(sb.table("enrichment_signals").select("id").eq("signal_hash",h).limit(1).execute().data or [])

def hash_signal(company_id,title,url):
    return hashlib.sha256(f"{company_id}|{title}|{url}".encode()).hexdigest()

def fetch_companies():
    rows=sb.table("companies").select("id,name,hot_score,linkedin_contacts_count,programs_count").or_("linkedin_contacts_count.gte.1,programs_count.gte.1,hot_score.gte.70").order("hot_score",desc=True).limit(LIMIT).execute().data or []
    return rows

def run():
    print("[START] Targeted account news", flush=True)
    created=0
    for c in fetch_companies():
        name=c.get("name")
        queries=[f'"{name}" "programme immobilier"', f'"{name}" "permis de construire"', f'"{name}" réhabilitation immobilier', f'"{name}" prescripteurs immobilier'][:MAX_QUERIES]
        for query in queries:
            feed=feedparser.parse(f"https://news.google.com/rss/search?q={quote_plus(query)}&hl=fr&gl=FR&ceid=FR:fr")
            for entry in feed.entries[:MAX_ENTRIES]:
                title=entry.get("title","").strip()
                url=entry.get("link","").strip()
                summary=entry.get("summary","").strip()
                if not title or not url or not reliable(url): continue
                typ,score,hits=classify(f"{title} {summary}")
                if score < 55: continue
                h=hash_signal(c["id"],title,url)
                if exists(h): continue
                payload={"company_id":c["id"],"company_name":name,"signal_type":typ,"title":title,"summary":summary or ", ".join(hits),"source_url":url,"source_name":domain(url),"source_type":"targeted_news_rss","confidence":score,"reliability_score":85,"is_reliable":True,"is_actionable":typ!="news_article","signal_hash":h,"search_query":query,"detected_at":"now()"}
                sb.table("enrichment_signals").insert(payload).execute()
                created += 1
                print(f"[NEWS] {name} | {typ} | {score} | {title}", flush=True)
            time.sleep(0.2)
    print(f"[FINISH] Signaux ciblés créés : {created}", flush=True)

if __name__ == "__main__":
    run()
