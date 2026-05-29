import streamlit as st
from storage import get_client
from programs_page import render_programs_page

st.set_page_config(page_title="Octave Radar", page_icon="🎯", layout="wide")
sb = get_client()

def count(table, filters=None):
    try:
        q = sb.table(table).select("id", count="exact")
        if filters:
            for f in filters:
                q = f(q)
        return q.limit(1).execute().count or 0
    except Exception:
        return 0

def fetch(table, columns="*", limit=200, order=None):
    q = sb.table(table).select(columns)
    if order:
        q = q.order(order, desc=True)
    return q.limit(limit).execute().data or []

st.title("🎯 Octave Radar")
st.caption("CRM de prospection B2B : comptes promoteurs, contacts LinkedIn, programmes, signaux et priorités commerciales.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🔥 Comptes prioritaires", "🏗️ Programmes", "👥 Contacts LinkedIn", "📡 Signaux", "⚙️ Debug"])

with tab1:
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    c1.metric("Sociétés", count("companies"))
    c2.metric("Contacts", count("contacts"))
    c3.metric("LinkedIn", count("contacts", [lambda q: q.eq("external_source", "linkedin_file")]))
    c4.metric("Walaxy ready", count("contacts", [lambda q: q.eq("walaxy_ready", True)]))
    c5.metric("Programmes", count("programs"))
    c6.metric("Signaux", count("enrichment_signals"))

    st.subheader("Comptes actionnables")
    f1, f2, f3, f4 = st.columns([1, 1, 1, 1])
    with f1:
        min_score = st.slider("Hot score min.", 0, 100, 50)
    with f2:
        only_linkedin = st.checkbox("Avec contacts LinkedIn")
    with f3:
        only_programs = st.checkbox("Avec programmes")
    with f4:
        limit = st.slider("Nombre", 20, 300, 120)

    q = sb.table("companies").select(
        "id,name,region,city,company_type,hot_score,fit_octave_score,website,website_status,"
        "programs_count,linkedin_contacts_count,walaxy_ready_contacts_count,"
        "top_linkedin_contact_name,top_linkedin_contact_role,top_linkedin_contact_url"
    ).gte("hot_score", min_score)

    if only_linkedin:
        q = q.gte("linkedin_contacts_count", 1)
    if only_programs:
        q = q.gte("programs_count", 1)

    rows = q.order("hot_score", desc=True).limit(limit).execute().data or []
    for c in rows:
        with st.container(border=True):
            left, right = st.columns([3, 1])
            with left:
                st.markdown(f"### {c.get('name')}")
                st.caption(f"{c.get('company_type') or '-'} · {c.get('region') or '-'} · {c.get('city') or '-'} · site {c.get('website_status') or '-'}")
                links = []
                if c.get("website"):
                    links.append(f"[Site]({c.get('website')})")
                if c.get("top_linkedin_contact_url"):
                    links.append(f"[Top contact : {c.get('top_linkedin_contact_name')}]({c.get('top_linkedin_contact_url')}) · {c.get('top_linkedin_contact_role')}")
                if links:
                    st.markdown(" · ".join(links))
            with right:
                st.metric("Hot score", c.get("hot_score") or 0)
                st.metric("Contacts LI", c.get("linkedin_contacts_count") or 0)
                st.metric("Programmes", c.get("programs_count") or 0)

with tab2:
    render_programs_page()

with tab3:
    st.subheader("Contacts exploitables")
    f1, f2, f3, f4 = st.columns([1, 1, 1, 1])
    with f1:
        source = st.selectbox("Source", ["Toutes", "linkedin_file", "public_registry", "official_site"])
    with f2:
        only_walaxy = st.checkbox("Walaxy ready uniquement", value=True)
    with f3:
        min_confidence = st.slider("Score contact min.", 0, 100, 60)
    with f4:
        limit = st.slider("Contacts", 50, 1000, 300)

    q = sb.table("contacts").select("*").gte("confidence", min_confidence).order("confidence", desc=True).limit(limit)
    if source != "Toutes":
        q = q.eq("external_source", source)
    if only_walaxy:
        q = q.eq("walaxy_ready", True)

    contacts = q.execute().data or []
    st.write(f"{len(contacts)} contacts affichés")
    for c in contacts:
        with st.container(border=True):
            st.markdown(f"### {c.get('full_name') or 'Contact à identifier'}")
            st.caption(f"{c.get('role') or '-'} · {c.get('source_name') or '-'} · score {c.get('confidence') or 0}")
            if c.get("linkedin_url"):
                st.markdown(f"[LinkedIn]({c.get('linkedin_url')})")
            if c.get("salesnav_query"):
                st.caption(f"SalesNav : {c.get('salesnav_query')}")
            if c.get("notes"):
                st.info(c.get("notes"))

with tab4:
    st.subheader("Signaux ciblés")
    signals = fetch("enrichment_signals", "*", 400, "detected_at")
    for s in signals:
        with st.container(border=True):
            st.markdown(f"**{s.get('company_name') or '-'}** · {s.get('signal_type') or '-'} · score {s.get('confidence') or 0}")
            if s.get("source_url"):
                st.markdown(f"[{s.get('title') or 'Source'}]({s.get('source_url')})")
            else:
                st.write(s.get("title") or "")
            if s.get("commercial_pain"):
                st.info(s.get("commercial_pain"))

with tab5:
    st.subheader("Contrôle")
    st.write("Compteurs techniques")
    debug = {
        "linkedin staging": count("linkedin_contacts_import"),
        "staging matched": count("linkedin_contacts_import", [lambda q: q.not_.is_("matched_company_id", "null")]),
        "staging promoted": count("linkedin_contacts_import", [lambda q: q.eq("promotion_status", "promoted")]),
        "contacts linkedin_file": count("contacts", [lambda q: q.eq("external_source", "linkedin_file")]),
        "programs detail": count("programs", [lambda q: q.eq("is_program_detail", True)]),
    }
    st.json(debug)
