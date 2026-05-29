import os
from storage import get_client
sb = get_client()
MIN_CONTACT_SCORE=int(os.getenv("LINKEDIN_PROMOTE_MIN_SCORE","65"))
MIN_MATCH_CONFIDENCE=int(os.getenv("LINKEDIN_PROMOTE_MIN_MATCH","70"))
LIMIT=int(os.getenv("LINKEDIN_PROMOTE_LIMIT","1000"))

def existing(linkedin_url=None, company_id=None, full_name=None):
    if linkedin_url:
        rows=sb.table("contacts").select("id").eq("linkedin_url",linkedin_url).limit(1).execute().data or []
        if rows: return rows[0]["id"]
    if company_id and full_name:
        rows=sb.table("contacts").select("id").eq("company_id",company_id).ilike("full_name",full_name).limit(1).execute().data or []
        if rows: return rows[0]["id"]
    return None

def update_company_stats(company_id):
    rows=sb.table("contacts").select("id,full_name,role,linkedin_url,confidence").eq("company_id",company_id).eq("external_source","linkedin_file").order("confidence",desc=True).execute().data or []
    walaxy=[r for r in rows if r.get("linkedin_url")]
    payload={"linkedin_contacts_count":len(rows),"walaxy_ready_contacts_count":len(walaxy),"updated_at":"now()"}
    if walaxy:
        payload.update({"top_linkedin_contact_name":walaxy[0].get("full_name"),"top_linkedin_contact_role":walaxy[0].get("role"),"top_linkedin_contact_url":walaxy[0].get("linkedin_url")})
    sb.table("companies").update(payload).eq("id",company_id).execute()

def quality(score):
    if score>=85: return "fiable"
    if score>=65: return "a_verifier"
    return "a_identifier"

def run():
    print("[START] Promote LinkedIn import", flush=True)
    rows=sb.table("linkedin_contacts_import").select("*").eq("promotion_status","not_promoted").eq("walaxy_ready_candidate",True).gte("contact_score",MIN_CONTACT_SCORE).gte("match_confidence",MIN_MATCH_CONFIDENCE).limit(LIMIT).execute().data or []
    print(f"[INFO] Candidats à promouvoir : {len(rows)}", flush=True)
    promoted=duplicates=errors=0
    for r in rows:
        try:
            dup=existing(r.get("linkedin_url"),r.get("matched_company_id"),r.get("full_name"))
            if dup:
                sb.table("linkedin_contacts_import").update({"promotion_status":"duplicate","is_duplicate":True,"duplicate_contact_id":dup}).eq("id",r["id"]).execute()
                duplicates += 1
                continue
            payload={
                "company_id":r.get("matched_company_id"),"full_name":r.get("full_name"),"first_name":r.get("first_name"),"last_name":r.get("last_name"),
                "role":r.get("job_title") or r.get("occupation"),"seniority":"decision_maker" if r.get("decision_level")=="A_tres_prioritaire" else "influencer",
                "linkedin_url":r.get("linkedin_url"),"sales_navigator_id":r.get("sales_navigator_id"),"profile_picture_url":r.get("profile_picture_url"),
                "source_url":r.get("linkedin_url"),"source_name":"linkedin_import","confidence":r.get("contact_score") or 0,
                "contact_status":"identifie","is_decision_maker":r.get("decision_level")=="A_tres_prioritaire","is_generic":False,
                "salesnav_query":f'{r.get("full_name")} {r.get("matched_company_name")}',"google_query":f'site:linkedin.com/in "{r.get("full_name")}" "{r.get("matched_company_name")}"',
                "walaxy_ready":True,"notes":r.get("calibration_reason"),"contact_quality_status":quality(r.get("contact_score") or 0),
                "contact_quality_reason":r.get("calibration_reason"),"is_suspect":False,"external_source":"linkedin_file","external_id":r.get("source_hash"),
                "imported_at":"now()","last_verified_at":"now()","walaxy_status":"ready","enrichment_channel":"linkedin_import",
                "linkedin_import_id":r.get("id"),"linkedin_import_score":r.get("contact_score") or 0,"linkedin_import_decision_level":r.get("decision_level")
            }
            inserted=sb.table("contacts").insert(payload).execute().data or []
            contact_id=inserted[0]["id"] if inserted else None
            sb.table("linkedin_contacts_import").update({"promotion_status":"promoted","promoted_at":"now()","duplicate_contact_id":contact_id}).eq("id",r["id"]).execute()
            update_company_stats(r.get("matched_company_id"))
            promoted += 1
            print(f"[PROMOTED] {r.get('full_name')} | {r.get('matched_company_name')}", flush=True)
        except Exception as e:
            errors += 1
            print(f"[ERROR] {r.get('full_name')} | {e}", flush=True)
    print(f"[FINISH] Contacts promus : {promoted}", flush=True)
    print(f"[FINISH] Doublons détectés : {duplicates}", flush=True)
    print(f"[FINISH] Erreurs : {errors}", flush=True)

if __name__ == "__main__":
    run()
