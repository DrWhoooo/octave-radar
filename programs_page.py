import pandas as pd
import streamlit as st
from storage import get_client

sb = get_client()

def fetch_all(table, columns="*", page_size=1000, max_rows=30000):
    rows = []
    start = 0
    while start < max_rows:
        batch = sb.table(table).select(columns).range(start, start + page_size - 1).execute().data or []
        if not batch:
            break
        rows.extend(batch)
        if len(batch) < page_size:
            break
        start += page_size
    return rows

@st.cache_data(ttl=120)
def load_programs():
    programs = fetch_all("programs", "*")
    companies = fetch_all("companies", "id,name,company_type,entity_role,group_detection_status,parent_company_name")
    dfp = pd.DataFrame(programs)
    dfc = pd.DataFrame(companies)
    if dfp.empty:
        return pd.DataFrame()
    if not dfc.empty:
        dfc = dfc.rename(columns={
            "id": "company_id",
            "name": "company_record_name",
            "company_type": "company_record_type",
            "entity_role": "company_entity_role",
            "group_detection_status": "company_group_status",
        })
        dfp = dfp.merge(dfc, on="company_id", how="left")
    for col in ["program_name","company_name","program_city","program_postal_code","fiscality","program_url","image_url","price_from","delivery_date","typology","lots_summary","commercial_status","source_name","confidence","detected_at","is_program_detail","extraction_quality_reason","company_record_type","company_entity_role","company_group_status"]:
        if col not in dfp.columns:
            dfp[col] = None
    dfp["confidence"] = pd.to_numeric(dfp["confidence"], errors="coerce").fillna(0).astype(int)
    dfp["price_from"] = pd.to_numeric(dfp["price_from"], errors="coerce")
    dfp["is_program_detail"] = dfp["is_program_detail"].fillna(False)
    return dfp

def clean(v, default="-"):
    if v is None:
        return default
    v = str(v).strip()
    return default if not v or v.lower() in ["none", "nan", "null"] else v

def price(v):
    if v is None or pd.isna(v):
        return "Prix NC"
    return f"{float(v):,.0f} €".replace(",", " ")

def entity_segment(row):
    company_type = str(row.get("company_record_type") or "").lower()
    entity_role = str(row.get("company_entity_role") or "").lower()
    group_status = str(row.get("company_group_status") or "").lower()
    company_name = str(row.get("company_name") or "").lower()
    markers = ["sci", "sccv", "snc", "scp", "scpi", "societe_projet"]
    if entity_role == "project_company" or group_status in ["a_rattacher", "a_verifier", "attached"]:
        return "Sociétés projet"
    if any(m in company_type for m in markers) or any(company_name.startswith(m + " ") for m in markers):
        return "Sociétés projet"
    return "Promoteurs / opérateurs"

def card(row):
    with st.container(border=True):
        image = clean(row.get("image_url"), "")
        if image.startswith("http"):
            st.image(image, use_container_width=True)
        else:
            st.info("🏗️ Visuel à enrichir")
        st.markdown(f"### {clean(row.get('program_name'), 'Programme détecté')}")
        st.caption(clean(row.get("company_name"), "Promoteur non renseigné"))
        c1, c2 = st.columns(2)
        c1.metric("Score", f"{int(row.get('confidence') or 0)}%")
        c2.metric("Prix", price(row.get("price_from")))
        loc = " · ".join([x for x in [clean(row.get("program_city"), ""), clean(row.get("program_postal_code"), "")] if x])
        st.write(f"**Localisation :** {loc or 'NC'}")
        st.write(f"**Fiscalité :** {clean(row.get('fiscality'), 'NC')}")
        details = []
        for label, col in [("Lots", "lots_summary"), ("Livraison", "delivery_date"), ("Typologie", "typology")]:
            val = clean(row.get(col), "")
            if val:
                details.append(f"{label} : {val}")
        if details:
            st.caption(" · ".join(details))
        url = clean(row.get("program_url"), "")
        if url.startswith("http"):
            st.link_button("Ouvrir", url, use_container_width=True)

def render_programs_page():
    st.subheader("Programmes")
    df = load_programs()
    if df.empty:
        st.warning("Aucun programme.")
        return
    df["entity_segment"] = df.apply(entity_segment, axis=1)
    df["search_blob"] = df.apply(lambda r: " ".join(str(r.get(c) or "") for c in ["program_name","company_name","program_city","fiscality","extraction_quality_reason"]).lower(), axis=1)

    k1, k2, k3, k4 = st.columns(4)
    k1.metric("Total", len(df))
    k2.metric("Fiches détaillées", len(df[df["is_program_detail"] == True]))
    k3.metric("Promoteurs", df["company_id"].nunique() if "company_id" in df else 0)
    k4.metric("Score ≥ 75", len(df[df["confidence"] >= 75]))

    f1, f2, f3, f4 = st.columns([1.4, 1, 1, 1])
    with f1:
        search = st.text_input("Recherche programme / ville / promoteur")
    with f2:
        quality = st.selectbox("Qualité", ["Fiches détaillées", "Toutes", "Pages génériques"])
    with f3:
        min_score = st.slider("Score min", 0, 100, 55, 5)
    with f4:
        view = st.radio("Vue", ["Vignettes", "Table"], horizontal=True)

    filtered = df.copy()
    if search:
        filtered = filtered[filtered["search_blob"].str.contains(search.lower(), regex=False, na=False)]
    if quality == "Fiches détaillées":
        filtered = filtered[filtered["is_program_detail"] == True]
    elif quality == "Pages génériques":
        filtered = filtered[filtered["is_program_detail"] != True]
    filtered = filtered[filtered["confidence"] >= min_score].sort_values(["confidence","company_name"], ascending=[False, True])
    st.caption(f"{len(filtered)} programme(s) affiché(s) sur {len(df)}.")

    if view == "Table":
        cols = [c for c in ["company_name","program_name","program_city","fiscality","price_from","lots_summary","confidence","is_program_detail","program_url"] if c in filtered.columns]
        st.dataframe(filtered[cols], use_container_width=True, hide_index=True)
        return

    rows = filtered.head(150).reset_index(drop=True)
    for i in range(0, len(rows), 3):
        cols = st.columns(3)
        for j, col in enumerate(cols):
            if i + j < len(rows):
                with col:
                    card(rows.iloc[i+j])
