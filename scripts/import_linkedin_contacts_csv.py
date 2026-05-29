import os, re, hashlib
import pandas as pd
from storage import get_client

sb = get_client()
CSV_PATH = os.getenv("LINKEDIN_IMPORT_CSV_PATH", "data/linkedin_contacts_import_ready.csv")

HIGH = ["président","president","fondateur","fondatrice","ceo","dg","directeur général","directrice générale","directeur general","directrice generale","gérant","gerant","directeur commercial","directrice commerciale","directeur développement","directrice développement","responsable foncier","responsable programmes","partenariats","partenaires"]
MEDIUM = ["responsable commercial","business developer","business development","chargé de développement","charge de developpement","commercialisation","immobilier neuf","directeur agence","manager"]
LOW = ["assistant","assistante","alternant","alternante","stagiaire","étudiant","etudiant","rh","communication","marketing"]
REJECT = ["étudiant","etudiant","recherche alternance","recherche emploi","coach","formateur","architecte d'intérieur","mobilier","décoration","decoration"]

def norm(v): return "" if pd.isna(v) else str(v).strip()
def lower(v): return norm(v).lower()

def normalize_company_name(v):
    v = lower(v).replace("&"," et ").replace("'"," ").replace("-"," ")
    v = re.sub(r"[^a-z0-9àâçéèêëîïôöùûüÿñæœ ]+", " ", v)
    for stop in ["sas","sasu","sarl","sa","sci","sccv","snc","scp","scpi","societe","société","groupe","immobilier","promotion","immo","fonciere","foncière","habitat"]:
        v = re.sub(rf"\b{re.escape(stop)}\b", " ", v)
    return re.sub(r"\s+"," ",v).strip()

def source_hash(row):
    raw = "|".join([lower(row.get("linkedin_url")), lower(row.get("sales_navigator_id")), lower(row.get("full_name")), lower(row.get("company_name"))])
    return hashlib.sha256(raw.encode()).hexdigest()

def split_name(full_name):
    parts = norm(full_name).split()
    if len(parts) == 0: return "", ""
    if len(parts) == 1: return parts[0], ""
    return parts[0], " ".join(parts[1:])

def calibrate(row):
    text = lower(" ".join([row.get("job_title",""), row.get("occupation",""), row.get("company_name","")]))
    if any(k in text for k in REJECT): return "D_a_revoir",20,False,"Rôle/profil hors cible."
    if any(k in text for k in HIGH): return "A_tres_prioritaire",90,True,"Décideur ou rôle directement exploitable."
    if any(k in text for k in MEDIUM): return "B_prioritaire",70,True,"Rôle commercial/développement exploitable."
    if any(k in text for k in LOW): return "C_secondaire",45,False,"Rôle secondaire."
    if row.get("linkedin_url"): return "C_secondaire",50,False,"LinkedIn présent mais rôle insuffisamment qualifié."
    return "D_a_revoir",25,False,"Données insuffisantes."

def fetch_all_companies():
    rows=[]; start=0; page=1000
    while True:
        batch = sb.table("companies").select("id,name").range(start,start+page-1).execute().data or []
        if not batch: break
        rows.extend(batch)
        if len(batch)<page: break
        start += page
    return rows

def build_index(companies):
    exact={}; tokens=[]
    for c in companies:
        n = normalize_company_name(c.get("name"))
        if n: exact[n]=c
        tokens.append((c,n,set(t for t in n.split() if len(t)>=4)))
    return exact,tokens

def match_company(row, exact, token_index):
    n = normalize_company_name(row.get("company_name"))
    if not n: return None,0,"Société absente"
    if n in exact: return exact[n],100,"Match exact"
    rt = set(t for t in n.split() if len(t)>=4)
    best=None
    for c, cn, ct in token_index:
        ov = rt.intersection(ct)
        if not ov: continue
        score = int((len(ov)/max(len(rt),1))*100)
        if cn in n: score += 20
        if n in cn: score += 20
        score = min(score,95)
        if not best or score > best[0]: best=(score,c,ov)
    if best and best[0]>=70: return best[1],best[0],f"Tokens {sorted(list(best[2]))}"
    return None,best[0] if best else 0,"Aucun match fiable"

def exists_hash(h):
    return bool(sb.table("linkedin_contacts_import").select("id").eq("source_hash", h).limit(1).execute().data or [])

def duplicate_contact(linkedin_url):
    if not linkedin_url: return None
    rows = sb.table("contacts").select("id").eq("linkedin_url", linkedin_url).limit(1).execute().data or []
    return rows[0]["id"] if rows else None

def run():
    print("[START] Import LinkedIn contacts CSV", flush=True)
    if not os.path.exists(CSV_PATH):
        raise FileNotFoundError(CSV_PATH)
    df = pd.read_csv(CSV_PATH)
    for col in ["full_name","first_name","last_name","job_title","occupation","company_name","linkedin_url","sales_navigator_id","company_website","company_linkedin_url","location","premium","profile_status","profile_picture_url","source_file"]:
        if col not in df.columns: df[col]=""
    exact, token_index = build_index(fetch_all_companies())
    batch=[]; inserted=0; matched=0; ready=0; skipped=0
    for _, r in df.iterrows():
        row={col:norm(r.get(col)) for col in df.columns}
        full = row.get("full_name") or f"{row.get('first_name','')} {row.get('last_name','')}".strip()
        first,last = row.get("first_name"), row.get("last_name")
        if not first or not last: first,last = split_name(full)
        row["full_name"]=full; row["first_name"]=first; row["last_name"]=last
        h=source_hash(row)
        if exists_hash(h): skipped += 1; continue
        level,score,walaxy,reason = calibrate(row)
        company,match_score,match_reason = match_company(row,exact,token_index)
        dup = duplicate_contact(row.get("linkedin_url"))
        if company: matched += 1
        status = "matched" if company else "company_to_review"
        if score < 45: status = "rejected"
        if dup: status = "duplicate"
        walaxy_ready = bool(walaxy and company and score >= 65 and match_score >= 70 and not dup)
        if walaxy_ready: ready += 1
        batch.append({
            "full_name":full,"first_name":first,"last_name":last,"job_title":row.get("job_title"),"occupation":row.get("occupation"),
            "company_name":row.get("company_name"),"normalized_company_name":normalize_company_name(row.get("company_name")),
            "matched_company_id":company.get("id") if company else None,"matched_company_name":company.get("name") if company else None,
            "match_confidence":match_score,"match_reason":match_reason,"linkedin_url":row.get("linkedin_url"),"sales_navigator_id":row.get("sales_navigator_id"),
            "company_website":row.get("company_website"),"company_linkedin_url":row.get("company_linkedin_url"),"location":row.get("location"),"premium":row.get("premium"),
            "profile_status":row.get("profile_status"),"profile_picture_url":row.get("profile_picture_url"),"decision_level":level,"contact_score":score,
            "walaxy_ready_candidate":walaxy_ready,"calibration_reason":reason,"import_status":status,"promotion_status":"not_promoted",
            "is_duplicate": bool(dup), "duplicate_contact_id": dup,
            "source_file":row.get("source_file") or os.path.basename(CSV_PATH),"source_hash":h,"calibrated_at":"now()"
        })
        if len(batch)>=200:
            sb.table("linkedin_contacts_import").insert(batch).execute(); inserted += len(batch); batch=[]
    if batch:
        sb.table("linkedin_contacts_import").insert(batch).execute(); inserted += len(batch)
    print(f"[FINISH] Lignes insérées staging : {inserted}", flush=True)
    print(f"[FINISH] Doublons ignorés : {skipped}", flush=True)
    print(f"[FINISH] Lignes matchées société : {matched}", flush=True)
    print(f"[FINISH] Candidats Walaxy ready : {ready}", flush=True)

if __name__ == "__main__":
    run()
