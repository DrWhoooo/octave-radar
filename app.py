import streamlit as st
from storage import get_client
from programs_page import render_programs_page

sb = get_client()

def count(table, filters=None):
    try:
        q = sb.table(table).select("id", count="exact")
        if filters:
            for f in filters: q = f(q)
        return q.limit(1).execute().count or 0
    except: return 0

SIGNAL_COLORS = {
    "partner_space":   ("#7C3AED", "🤝 Partenaires"),
    "program_launch":  ("#059669", "🏗️ Programme"),
    "rehabilitation":  ("#DC2626", "🔨 Réhab"),
    "foncier":         ("#D97706", "🌍 Foncier"),
    "recruitment":     ("#2563EB", "👥 Recrutement"),
    "program_page":    ("#059669", "📋 Programmes"),
}

def signal_badge(signal_type):
    color, label = SIGNAL_COLORS.get(signal_type, ("#6B7280", signal_type))
    return f'<span style="background:{color};color:white;padding:2px 8px;border-radius:12px;font-size:11px;font-weight:600;margin:2px">{label}</span>'

def score_color(score):
    if score >= 80: return "#10B981"
    if score >= 60: return "#F59E0B"
    return "#6B7280"

st.markdown("""
<style>
    .stApp { background: #0F172A; color: #E2E8F0; }
    h1,h2,h3 { color: #F8FAFC !important; }
    .metric-card { background:#1E293B; border:1px solid #334155; border-radius:12px; padding:16px; text-align:center; }
    .metric-value { font-size:28px; font-weight:700; color:#38BDF8; }
    .metric-label { font-size:11px; color:#94A3B8; text-transform:uppercase; letter-spacing:1px; }
    .account-card { background:#1E293B; border:1px solid #334155; border-radius:16px; padding:20px; margin:8px 0; }
    .account-name { font-size:18px; font-weight:700; color:#F8FAFC; margin-bottom:4px; }
    .account-meta { font-size:12px; color:#64748B; margin-bottom:10px; }
    .score-badge { display:inline-block; border-radius:8px; padding:4px 12px; font-weight:700; font-size:18px; color:white; }
    .signal-card { background:#1E293B; border-radius:10px; padding:14px 16px; margin:6px 0; }
    .insight-card { background:linear-gradient(135deg,#1E293B 0%,#0F2437 100%); border:1px solid #1D4ED8; border-radius:16px; padding:20px; margin:10px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="padding:20px 0 8px">
    <h1 style="font-size:30px;margin:0">🎯 Octave Radar</h1>
    <p style="color:#64748B;margin:4px 0 0">Agent de prospection B2B — Promoteurs immobiliers</p>
</div>
""", unsafe_allow_html=True)

cols = st.columns(6)
metrics = [
    ("Sociétés", count("companies")),
    ("Contacts", count("contacts")),
    ("LinkedIn", count("contacts", [lambda q: q.eq("external_source","linkedin_file")])),
    ("Walaxy ✓", count("contacts", [lambda q: q.eq("walaxy_ready",True)])),
    ("Programmes", count("programs")),
    ("Signaux", count("enrichment_signals")),
]
for col, (label, value) in zip(cols, metrics):
    col.markdown(f'<div class="metric-card"><div class="metric-value">{value}</div><div class="metric-label">{label}</div></div>', unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

tab0, tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🚀 Mission du jour", "🔥 Comptes", "🏗️ Programmes", "👥 Contacts", "📡 Signaux", "⚙️ Debug"
])

with tab0:
    st.markdown("### 🚀 Mission du jour")
    st.caption("Comptes à traiter maintenant — signal, contexte, angle.")

    insights = sb.table("prospect_insights")\
        .select("company_id,icp_score,intent_score,rationale,pain_points,approach_angle,outreach_message,priority_level,target_roles")\
        .eq("is_active", True).order("intent_score", desc=True).limit(15).execute().data or []

    ids = list({i["company_id"] for i in insights})
    cmap = {}
    if ids:
        rows = sb.table("companies").select(
            "id,name,region,city,company_type,hot_score,website,"
            "top_linkedin_contact_name,top_linkedin_contact_role,top_linkedin_contact_url,"
            "programs_count,linkedin_contacts_count"
        ).in_("id", ids).execute().data or []
        cmap = {r["id"]: r for r in rows}

    smap = {}
    if ids:
        sigs = sb.table("enrichment_signals").select("company_id,signal_type,confidence")\
            .in_("company_id", ids).gte("confidence", 60).execute().data or []
        for s in sigs: smap.setdefault(s["company_id"], []).append(s)

    if not insights:
        st.warning("Aucun insight disponible.")
    else:
        for ins in insights:
            c = cmap.get(ins["company_id"])
            if not c: continue
            score = ins.get("intent_score", 0)
            sc = score_color(score)
            sigs = smap.get(ins["company_id"], [])
            badges = ''.join(signal_badge(s['signal_type']) for s in sigs[:4])

            st.markdown(f"""<div class="insight-card">
                <div style="display:flex;justify-content:space-between;align-items:flex-start">
                    <div>
                        <div class="account-name">{c.get('name','')}</div>
                        <div class="account-meta">{c.get('company_type','-')} · {c.get('region','-')} · {c.get('city','-')}</div>
                        {badges}
                    </div>
                    <div style="text-align:right">
                        <div class="score-badge" style="background:{sc}">{score}</div>
                        <div style="font-size:11px;color:#64748B;margin-top:4px">Intent Score</div>
                    </div>
                </div>
            </div>""", unsafe_allow_html=True)

            c1, c2 = st.columns([2,1])
            with c1:
                if ins.get("rationale"): st.info(f"**Pourquoi maintenant :** {ins['rationale']}")
                if ins.get("pain_points"): st.warning(f"**Douleur :** {ins['pain_points']}")
                if ins.get("approach_angle"): st.success(f"**Angle :** {ins['approach_angle']}")
                if ins.get("outreach_message"):
                    with st.expander("📝 Message suggéré"):
                        st.write(ins["outreach_message"])
            with c2:
                links = []
                if c.get("website"): links.append(f"[🌐 Site]({c['website']})")
                if c.get("top_linkedin_contact_url"):
                    links.append(f"[💼 {c.get('top_linkedin_contact_name','Contact')}]({c['top_linkedin_contact_url']})")
                if links: st.markdown("  \n".join(links))
                if c.get("top_linkedin_contact_role"): st.caption(c["top_linkedin_contact_role"])
                st.metric("Contacts LI", c.get("linkedin_contacts_count",0))
                st.metric("Programmes", c.get("programs_count",0))
            st.markdown("---")

with tab1:
    st.markdown("### 🔥 Comptes prioritaires")
    f1,f2,f3,f4 = st.columns(4)
    with f1: min_score = st.slider("Hot score min.", 0, 100, 50)
    with f2: only_li = st.checkbox("Avec contacts LinkedIn")
    with f3: only_prog = st.checkbox("Avec programmes")
    with f4: limit = st.slider("Nombre", 20, 300, 60)

    q = sb.table("companies").select(
        "id,name,region,city,company_type,hot_score,website,website_status,"
        "programs_count,linkedin_contacts_count,walaxy_ready_contacts_count,"
        "top_linkedin_contact_name,top_linkedin_contact_role,top_linkedin_contact_url"
    ).gte("hot_score", min_score)
    if only_li: q = q.gte("linkedin_contacts_count", 1)
    if only_prog: q = q.gte("programs_count", 1)
    rows = q.order("hot_score", desc=True).limit(limit).execute().data or []

    rids = [r["id"] for r in rows]
    rsigs = {}
    if rids:
        ss = sb.table("enrichment_signals").select("company_id,signal_type,confidence")\
            .in_("company_id", rids).gte("confidence",60).execute().data or []
        for s in ss: rsigs.setdefault(s["company_id"],[]).append(s)

    for c in rows:
        sc = score_color(c.get("hot_score",0))
        sigs = rsigs.get(c["id"],[])
        badges = ''.join(signal_badge(s['signal_type']) for s in sigs[:3])

        st.markdown(f"""<div class="account-card">
            <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div style="flex:1">
                    <div class="account-name">{c.get('name','')}</div>
                    <div class="account-meta">{c.get('company_type','-')} · {c.get('region','-')} · {c.get('city','-')} · site {c.get('website_status','-')}</div>
                    {badges}
                </div>
                <div style="text-align:right;min-width:80px">
                    <div class="score-badge" style="background:{sc}">{c.get('hot_score',0)}</div>
                    <div style="font-size:11px;color:#64748B;margin-top:4px">Hot Score</div>
                </div>
            </div>
        </div>""", unsafe_allow_html=True)

        l1,l2 = st.columns([3,1])
        with l1:
            links = []
            if c.get("website"): links.append(f"[🌐 Site]({c['website']})")
            if c.get("top_linkedin_contact_url"):
                links.append(f"[💼 {c.get('top_linkedin_contact_name','Contact')}]({c['top_linkedin_contact_url']}) · {c.get('top_linkedin_contact_role','')}")
            if links: st.markdown("  \n".join(links))
        with l2:
            st.caption(f"LI: {c.get('linkedin_contacts_count',0)} · Prog: {c.get('programs_count',0)} · Walaxy: {c.get('walaxy_ready_contacts_count',0)}")

with tab2:
    render_programs_page()

with tab3:
    st.markdown("### 👥 Contacts exploitables")
    f1,f2,f3,f4 = st.columns(4)
    with f1: source = st.selectbox("Source", ["Toutes","linkedin_file","public_registry","official_site"])
    with f2: only_w = st.checkbox("Walaxy ready", value=True)
    with f3: min_conf = st.slider("Score min.", 0, 100, 60)
    with f4: climit = st.slider("Contacts", 50, 500, 100)

    q2 = sb.table("contacts").select(
        "full_name,role,linkedin_url,confidence,walaxy_ready,external_source"
    ).gte("confidence", min_conf).order("confidence", desc=True).limit(climit)
    if source != "Toutes": q2 = q2.eq("external_source", source)
    if only_w: q2 = q2.eq("walaxy_ready", True)
    contacts = q2.execute().data or []

    st.caption(f"{len(contacts)} contacts")
    for c in contacts:
        sc = score_color(c.get("confidence",0))
        li_link = f'<a href="{c["linkedin_url"]}" target="_blank" style="color:#38BDF8;font-size:12px">💼 LinkedIn</a>' if c.get("linkedin_url") else ""
        st.markdown(f"""<div class="account-card" style="padding:14px">
            <div style="display:flex;justify-content:space-between;align-items:center">
                <div>
                    <div style="font-weight:600;color:#F8FAFC">{c.get('full_name') or '—'}</div>
                    <div style="font-size:12px;color:#64748B">{c.get('role') or '-'}</div>
                    {li_link}
                </div>
                <div class="score-badge" style="background:{sc};font-size:14px">{c.get('confidence',0)}</div>
            </div>
        </div>""", unsafe_allow_html=True)

with tab4:
    st.markdown("### 📡 Signaux commerciaux")
    f1,f2 = st.columns(2)
    with f1:
        sig_filter = st.multiselect("Types de signaux", list(SIGNAL_COLORS.keys()), default=[])
    with f2:
        min_sig = st.slider("Score min.", 0, 100, 45)

    q3 = sb.table("enrichment_signals").select("*").gte("confidence", min_sig).order("confidence", desc=True).limit(200)
    if sig_filter: q3 = q3.in_("signal_type", sig_filter)
    signals = q3.execute().data or []

    st.caption(f"{len(signals)} signaux")
    for s in signals:
        color, _ = SIGNAL_COLORS.get(s.get("signal_type",""), ("#6B7280","Signal"))
        sc = score_color(s.get("confidence",0))
        src = f'<a href="{s["source_url"]}" target="_blank" style="color:#38BDF8;font-size:12px">🔗 Source</a>' if s.get("source_url") else ""
        st.markdown(f"""<div class="signal-card" style="border-left:4px solid {color}">
            <div style="display:flex;justify-content:space-between;align-items:flex-start">
                <div>
                    <div style="font-weight:600;color:#F8FAFC">{s.get('company_name','-')}</div>
                    {signal_badge(s.get('signal_type',''))}
                    <div style="font-size:12px;color:#94A3B8;margin-top:6px">{s.get('commercial_pain','')}</div>
                    {src}
                </div>
                <div class="score-badge" style="background:{sc};font-size:14px">{s.get('confidence',0)}</div>
            </div>
        </div>""", unsafe_allow_html=True)

with tab5:
    st.markdown("### ⚙️ Debug")
    debug = {
        "societes_total": count("companies"),
        "avec_site": count("companies", [lambda q: q.not_.is_("website","null")]),
        "linkedin_promus": count("contacts", [lambda q: q.eq("external_source","linkedin_file")]),
        "walaxy_ready": count("contacts", [lambda q: q.eq("walaxy_ready",True)]),
        "signaux_total": count("enrichment_signals"),
        "programmes_detail": count("programs", [lambda q: q.eq("is_program_detail",True)]),
        "insights_actifs": count("prospect_insights", [lambda q: q.eq("is_active",True)]),
    }
    st.json(debug)
