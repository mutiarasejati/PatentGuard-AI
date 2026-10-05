"""
PatentGuard AI - Integrated Web Application (Streamlit)
Mendukung Modul Khusus Analisis Farmasi & Kimia (IUPAC, Eksipien, All-Elements Rule & Doctrine of Equivalents)
serta Modul Paten Rekayasa Umum.
"""

import streamlit as st
import os
import json
import io
import pandas as pd
from typing import List, Optional

from models import (
    PatentAnalysisRequest,
    InfringementReport,
    Claim,
    ClaimType,
    ElementMatchStatus,
    InfringementRiskLevel,
    PharmaAnalysisRequest,
    PharmaInfringementReport,
    PharmaClaimCategory,
    ExcipientFunctionType,
    EquivalenceTestStatus,
)
from claim_extractor import ClaimExtractor
from analyzer import InfringementAnalyzer
from pharma_engine import (
    pharma_engine,
    CHEMICAL_REGISTRY,
    EXCIPIENT_DATABASE,
    ChemicalResolver,
    ExcipientEvaluator,
)
from report_generator import FTOReportGenerator
from doc_parser import DocumentParser

# Page configuration
st.set_page_config(
    page_title="PatentGuard AI - Pharmaceutical Patent Intelligence & FTO Engine",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS for styling
st.markdown("""
<style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #3b82f6, #06b6d4, #a855f7);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.1rem;
    }
    .sub-title {
        color: #94a3b8;
        font-size: 0.95rem;
        margin-bottom: 1.2rem;
    }
    .metric-card {
        background-color: #1e293b;
        border-radius: 12px;
        padding: 16px;
        border: 1px solid #334155;
        text-align: center;
    }
    .badge-api { background-color: rgba(59, 130, 246, 0.2); color: #93c5fd; padding: 3px 8px; border-radius: 6px; font-weight: bold; }
    .badge-polymer { background-color: rgba(168, 85, 247, 0.2); color: #d8b4fe; padding: 3px 8px; border-radius: 6px; font-weight: bold; }
    .badge-diluent { background-color: rgba(34, 197, 94, 0.2); color: #86efac; padding: 3px 8px; border-radius: 6px; font-weight: bold; }
    .badge-lubricant { background-color: rgba(148, 163, 184, 0.2); color: #cbd5e1; padding: 3px 8px; border-radius: 6px; font-weight: bold; }
    .badge-disintegrant { background-color: rgba(249, 115, 22, 0.2); color: #fdba74; padding: 3px 8px; border-radius: 6px; font-weight: bold; }
</style>
""", unsafe_allow_html=True)


# Pharmaceutical Benchmark Cases
PHARMA_CASES = {
    "Metformin XR (High Risk / Literal Infringement)": {
        "title": "US654321 - Extended-Release Metformin Biguanide Matrix Formulation",
        "patent": """What is claimed is:
1. An extended-release pharmaceutical matrix tablet comprising:
    500 mg to 1000 mg of 1,1-dimethylbiguanide hydrochloride;
    20% to 40% by weight of hydroxypropyl methylcellulose having a viscosity of 100,000 mPa.s; and
    0.5% to 2.0% by weight of a lubricant,
    wherein the tablet is manufactured via wet granulation and releases at least 80% of the active ingredient over a 12-hour period.

2. The extended-release tablet according to claim 1, wherein the lubricant is magnesium stearate.""",
        "product_name": "Glucosafe XR 500mg Extended Release",
        "dosage_form": "Tablet Lepas Lambat (Hydrophilic Matrix)",
        "formula": """Spesifikasi Formula Tablet Glucosafe XR:
- Zat Aktif: 1,1-dimethylbiguanide monohydrochloride (Metformin HCl) = 500 mg/tablet
- Polimer Matriks: Hydroxypropyl Methylcellulose (HPMC K100M) = 28% w/w
- Pengisi/Pengikat: Microcrystalline Cellulose (Avicel PH 102) = 20% w/w
- Pelincir: Magnesium Stearate = 1.0% w/w
- Glidan: Colloidal Silicon Dioxide (Aerosil 200) = 0.5% w/w
Proses: High-shear wet granulation menggunakan larutan pengikat PVP K30, pengeringan fluid bed dryer, dan pencetakan tablet rotari.
Uji Disolusi: 85% terlarut pada jam ke-12 (buffer fosfat pH 6.8).""",
    },
    "Atorvastatin (Low Risk / Safe Design-Around)": {
        "title": "EP2198765 - Crystalline Atorvastatin Calcium Trihydrate Matrix Formulation",
        "patent": """What is claimed is:
1. A solid pharmaceutical dosage form comprising:
    crystalline atorvastatin calcium trihydrate Form I characterized by X-ray powder diffraction peaks at 2-theta of 11.9, 17.0, and 21.6 degrees;
    15% to 35% by weight of hydroxypropyl methylcellulose phthalate as an enteric erosion polymer; and
    a wetting surfactant selected from sodium lauryl sulfate,
    wherein the formulation is processed by hot melt extrusion.

2. The solid dosage form according to claim 1, further comprising a plasticizer.""",
        "product_name": "Atorva-Pure 40mg (Lipid Matrix Design-Around)",
        "dosage_form": "Tablet Kempa Langsung",
        "formula": """Spesifikasi Formula Rekayasa Bebas Paten (Design-Around):
- Zat Aktif: Atorvastatin free base amorf dalam bentuk Co-Crystal dengan Nikotinamid (1:1 molar ratio, BUKAN garam kalsium trihidrat kristalin Form I) = 40 mg
- Matriks Pelepasan: Glycerol Distearate (Precirol ATO 5) = 20% w/w (Matriks lipid hidrofobik erosi kanal pori, TIDAK MENGGUNAKAN HPMC Phthalate)
- Pengisi Deformasi Plastis: Microcrystalline Cellulose (Avicel PH 200) = 38% w/w
- Pelincir: Sodium Stearyl Fumarate (Pruv) = 1.5% w/w (Bebas dari Sodium Lauryl Sulfate)
- Metode Manufaktur: Kempa Langsung (Direct Compression) tanpa proses hot melt extrusion maupun wet granulation.
- Profil Disolusi: Pelepasan mandiri pH-independen melalui erosi lipid.""",
    },
    "Paracetamol Sustained-Release (Medium Risk / Doctrine of Equivalents)": {
        "title": "WO202109876 - Extended-Release Acetaminophen Formulation Using Polysaccharide Hydrogel",
        "patent": """What is claimed is:
1. A sustained-release oral caplet comprising:
    650 mg of N-(4-hydroxyphenyl)acetamide;
    15% to 30% by weight of xanthan gum as the primary hydrophilic swellable matrix agent; and
    microcrystalline cellulose as a dry binder,
    wherein upon ingestion the xanthan gum hydrates to form a viscous hydrogel barrier controlling diffusion of the active substance.

2. The caplet of claim 1, wherein the caplet exhibits zero-order release kinetics for 8 hours.""",
        "product_name": "Paramol Retard 650mg Caplets",
        "dosage_form": "Kaplet Lepas Lambat",
        "formula": """Formula Sediaan Lepas Lambat:
- Zat Aktif: Paracetamol (Acetaminophen / N-(4-hydroxyphenyl)acetamide) = 650 mg/kaplet
- Polimer Matriks: Polyethylene Oxide (Polyox WSR-303) = 22% w/w (Substitusi dari Xanthan Gum; keduanya merupakan polimer hidrofilik yang mengembang dan berdisolusi membentuk lapisan gel penahan difusi)
- Pengisi/Pengikat: Microcrystalline Cellulose (Avicel PH 101) = 18% w/w
- Pelincir: Magnesium Stearate = 0.8% w/w
- Proses: Roller compaction (granulasi kering) dan kompresi kaplet lonjong.""",
    },
}

# General Engineering Cases
GENERAL_CASES = {
    "Drone Surveillance (High Risk / Literal Infringement)": {
        "title": "US9876543 - Autonomous Aerial Surveillance System with Thermal Tracking",
        "patent": """What is claimed is:
1. An autonomous aerial surveillance system comprising:
    a multi-rotor unmanned aerial vehicle (UAV) frame;
    a thermal imaging sensor mounted on a 3-axis gimbal;
    an onboard processor coupled to the thermal imaging sensor, wherein the processor executes a convolutional neural network to classify living objects based on thermal signatures; and
    a wireless telemetry transmitter configured to stream real-time alert coordinates to a ground control station.
2. The system according to claim 1, further comprising an audible perimeter deterrence siren mounted to the UAV frame.""",
        "product_name": "AeroGuard Pro X",
        "product_desc": """AeroGuard Pro X adalah drone keamanan otomatis:
- Rangka drone serat karbon quadcopter (4-rotor).
- Kamera pencitraan termal pada gimbal 3-sumbu otomatis.
- Komputer onboard menjalankan CNN mendeteksi manusia/hewan secara instan.
- Modul pemancar nirkabel mengirim koordinat GPS langsung ke stasiun darat.""",
    },
    "Water Purifier (Low Risk / Safe - Missing Element)": {
        "title": "IDP0000456 - Sistem Dispenser Air Pintar dengan Sterilisasi UV dan Sensor Ultrasonik",
        "patent": """Klaim:
1. Suatu sistem dispenser air pintar terdiri dari:
    sebuah tangki penampung air berkapasitas ganda;
    sebuah lampu sterilisasi sinar ultraviolet (UV-C) yang dipasang di dalam tangki penampung;
    sebuah sensor level air berbasis ultrasonik yang terhubung ke mikrokontroler; dan
    sebuah katup solenoid elektromagnetik yang membuka aliran air secara otomatis saat wadah terdeteksi.""",
        "product_name": "AquaPure ECO (Design-Around)",
        "product_desc": """AquaPure ECO adalah inovasi dispenser air higienis:
- Menggunakan tangki penampung air tunggal berbahan stainless steel food grade.
- Filtrasi mekanis membran keramik dan karbon aktif biologis (TIDAK MENGGUNAKAN lampu sinar UV).
- Tatakan dengan sensor berat (load cell) untuk membatasi pengisian air.
- Katup tuas manual tekan mekanis tanpa elektromagnetik.""",
    },
}


# --- SIDEBAR CONFIGURATION ---
with st.sidebar:
    st.image("https://img.icons8.com/isometric/100/test-tube.png", width=60)
    st.markdown("### ⚙️ Pengaturan PatentGuard AI")

    app_module = st.radio(
        "Pilih Modul Analisis:",
        options=["💊 Farmasi & Kimia (IUPAC & Formulasi)", "🛠️ Paten Umum / Rekayasa"],
        index=0,
    )

    api_key_env = os.getenv("GEMINI_API_KEY", "")
    custom_api_key = st.text_input(
        "Gemini API Key (Opsional)",
        value=api_key_env,
        type="password",
        help="Google Gemini API Key untuk analisis AI tingkat lanjut. Jika kosong, sistem menggunakan mesin penalaran heuristik.",
    )

    st.markdown("---")
    st.markdown("### 📂 Muat Kasus Uji Benchmark")

    if "Farmasi" in app_module:
        selected_case_name = st.selectbox("Pilih Kasus Farmasi:", options=list(PHARMA_CASES.keys()))
        if st.button("📋 Muat Kasus Farmasi ke Form", use_container_width=True):
            chosen = PHARMA_CASES[selected_case_name]
            st.session_state["patent_title"] = chosen["title"]
            st.session_state["patent_text"] = chosen["patent"]
            st.session_state["product_name"] = chosen["product_name"]
            st.session_state["dosage_form"] = chosen["dosage_form"]
            st.session_state["formula_text"] = chosen["formula"]
            st.session_state["pharma_report"] = None
            st.success("Kasus farmasi berhasil dimuat!")
    else:
        selected_general = st.selectbox("Pilih Kasus Rekayasa:", options=list(GENERAL_CASES.keys()))
        if st.button("📋 Muat Kasus Rekayasa ke Form", use_container_width=True):
            chosen = GENERAL_CASES[selected_general]
            st.session_state["patent_title"] = chosen["title"]
            st.session_state["patent_text"] = chosen["patent"]
            st.session_state["product_name"] = chosen["product_name"]
            st.session_state["product_desc"] = chosen["product_desc"]
            st.session_state["general_report"] = None
            st.success("Kasus rekayasa berhasil dimuat!")

    st.markdown("---")
    st.markdown("""
    **Pedoman Analisis Paten Farmasi:**
    - **Identitas Kimia**: Pengenalan IUPAC, INN, sinonim, bentuk garam, ester, hidrat, dan polimorfik.
    - **All-Elements Rule**: Tidak ada pelanggaran literal jika ada elemen wajib paten yang hilang.
    - **Doctrine of Equivalents**: Uji *Function-Way-Result* (Graver Tank) untuk substitusi eksipien.
    """)


# --- MAIN HEADER ---
st.markdown('<div class="main-title">🛡️ PatentGuard AI</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-title">Sistem Intelijen Paten Farmasi & Kimia (IUPAC, Pemetaan Fungsi Eksipien, All-Elements Rule, & Doctrine of Equivalents)</div>', unsafe_allow_html=True)


# ==============================================================================
# MODE 1: PHARMACEUTICAL & CHEMICAL SPECIALIZED MODULE
# ==============================================================================
if "Farmasi" in app_module:
    st.info("💡 **Modul Farmasi & Kimia Aktif:** Mampu memvalidasi struktur molekul, tata nama IUPAC, garam, polimorf, serta peran fungsional eksipien (polimer retardant, superdisintegran, pengisi, pelincir).")

    col_pat, col_form = st.columns([1, 1], gap="medium")

    with col_pat:
        st.markdown("### 📄 Dokumen Paten Pembanding A")
        patent_title_in = st.text_input(
            "Judul / Nomor Paten",
            value=st.session_state.get("patent_title", "US654321 - Extended-Release Metformin Biguanide Matrix"),
        )
        
        tab_p_text, tab_p_file = st.tabs(["📝 Input Teks Klaim", "📁 Upload Dokumen Paten (PDF/TXT)"])
        with tab_p_text:
            patent_text_in = st.text_area(
                "Teks Klaim Paten Farmasi",
                value=st.session_state.get("patent_text", PHARMA_CASES["Metformin XR (High Risk / Literal Infringement)"]["patent"]),
                height=280,
            )
        with tab_p_file:
            up_p_file = st.file_uploader("Upload Dokumen Paten (PDF / DOCX / TXT)", type=["pdf", "txt", "docx"], key="up_pat")
            if up_p_file:
                bytes_data = up_p_file.read()
                txt = DocumentParser.extract_text_from_bytes(bytes_data, up_p_file.name)
                patent_text_in = txt
                st.session_state["patent_text"] = txt
                st.success(f"File paten berhasil dibaca ({len(txt)} karakter).")

    with col_form:
        st.markdown("### 🧪 Spesifikasi Formula Internal B")
        col_pname, col_pform = st.columns(2)
        with col_pname:
            product_name_in = st.text_input("Nama Produk", value=st.session_state.get("product_name", "Glucosafe XR 500mg"))
        with col_pform:
            dosage_form_in = st.text_input("Bentuk Sediaan", value=st.session_state.get("dosage_form", "Tablet Lepas Lambat"))

        tab_f_text, tab_f_file = st.tabs(["📝 Input Spesifikasi Formula", "📁 Upload Dokumen Formula (PDF/TXT)"])
        with tab_f_text:
            formula_text_in = st.text_area(
                "Rincian Komposisi & Tahapan Proses",
                value=st.session_state.get("formula_text", PHARMA_CASES["Metformin XR (High Risk / Literal Infringement)"]["formula"]),
                height=280,
            )
        with tab_f_file:
            up_f_file = st.file_uploader("Upload Formula Produk (PDF / DOCX / TXT)", type=["pdf", "txt", "docx"], key="up_form")
            if up_f_file:
                f_bytes = up_f_file.read()
                f_txt = DocumentParser.extract_text_from_bytes(f_bytes, up_f_file.name)
                formula_text_in = f_txt
                st.session_state["formula_text"] = f_txt
                st.success(f"File formula berhasil dibaca ({len(f_txt)} karakter).")

    # Run Analysis Button
    st.markdown("---")
    btn_c1, btn_c2, btn_c3 = st.columns([1, 2, 1])
    with btn_c2:
        run_pharma_btn = st.button(
            "🔬 Jalankan Analisis Paten Farmasi & FTO Claim Chart",
            use_container_width=True,
            type="primary",
            disabled=not (patent_text_in.strip() and formula_text_in.strip()),
        )

    if run_pharma_btn:
        with st.spinner("AI Principal Patent Analyst sedang memproses entitas kimia IUPAC dan uji kesetaraan eksipien..."):
            eff_key = custom_api_key.strip() if custom_api_key else None
            req = PharmaAnalysisRequest(
                patent_title=patent_title_in,
                patent_text=patent_text_in,
                product_name=product_name_in,
                product_formula_text=formula_text_in,
                dosage_form=dosage_form_in,
                api_key=eff_key,
            )
            try:
                rep = pharma_engine.analyze(req)
                st.session_state["pharma_report"] = rep
                st.toast("Analisis Paten Farmasi Selesai!", icon="✅")
            except Exception as e:
                st.error(f"Gagal melakukan analisis: {e}")

    # Display Report if available
    if st.session_state.get("pharma_report"):
        rep: PharmaInfringementReport = st.session_state["pharma_report"]

        st.markdown("---")
        st.markdown("## 📊 Dossier Analisis FTO & Claim Chart Farmasi")

        # Top Executive Banner
        if rep.overall_risk == InfringementRiskLevel.HIGH:
            st.error(f"### 🚨 KESIMPULAN FTO: TIDAK LAYAK (HIGH INFRINGEMENT RISK - {rep.risk_score_numeric}%)\n**{rep.fto_verdict}**\n\n{rep.executive_summary}")
        elif rep.overall_risk == InfringementRiskLevel.MEDIUM:
            st.warning(f"### ⚠️ KESIMPULAN FTO: RISIKO SEDANG (DOCTRINE OF EQUIVALENTS - {rep.risk_score_numeric}%)\n**{rep.fto_verdict}**\n\n{rep.executive_summary}")
        else:
            st.success(f"### ✅ KESIMPULAN FTO: LAYAK (BEBAS PATEN / LOW RISK - {rep.risk_score_numeric}%)\n**{rep.fto_verdict}**\n\n{rep.executive_summary}")

        # Metrics
        met1, met2, met3, met4 = st.columns(4)
        with met1:
            st.metric("Skor Risiko Pelanggaran", f"{rep.risk_score_numeric}%")
        with met2:
            st.metric("All-Elements Rule", "Terpenuhi (Literal)" if rep.all_elements_rule_met else "Lolos (Element Missing)")
        with met3:
            st.metric("Doctrine of Equivalents", "Terpicu (DoE Risk)" if rep.doctrine_of_equivalents_triggered else "Tidak Terpicu")
        with met4:
            st.metric("Total Klaim Dianalisis", len(rep.claim_results))

        # Dossier Tabs
        t_chem, t_exc, t_chart, t_da = st.tabs([
            "🧪 1. Dossier Kimia & IUPAC",
            "🧩 2. Pemetaan Fungsi Eksipien (FWR)",
            "📋 3. Matriks Claim Chart Farmasi",
            "💡 4. Rekomendasi Design-Around & Ekspor"
        ])

        # TAB 1: CHEMICAL
        with t_chem:
            st.markdown("### 🧪 Verifikasi Tata Nama Kimia IUPAC & Zat Aktif")
            if rep.chemical_entities:
                for chem in rep.chemical_entities:
                    with st.container(border=True):
                        c_col1, c_col2 = st.columns([3, 1])
                        with c_col1:
                            st.markdown(f"#### {chem.inn_name} `API`")
                            st.caption(f"Nama Dagang: {', '.join(chem.trade_names)}")
                            st.code(f"Nama IUPAC: {chem.iupac_name}", language="text")
                        with c_col2:
                            if chem.is_equivalent_entity:
                                st.error("⚠️ Zat Identik / Ekuivalen")
                            else:
                                st.success("✅ Zat Berbeda")
                            st.write(f"**Bentuk:** {chem.chemical_form}")

                        st.markdown(f"""
                        - **Rumus Molekul:** `{chem.molecular_formula or '-'}` | **Berat Molekul:** `{chem.molecular_weight or '-'}` | **CAS:** `{chem.cas_number or '-'}`
                        - *Catatan Farmasetik:* {chem.equivalence_note or '-'}
                        """)
            else:
                st.info("Tidak terdeteksi zat aktif farmasi standar dalam teks.")

        # TAB 2: EXCIPIENTS
        with t_exc:
            st.markdown("### 🧩 Pemetaan Peran Fungsional Bahan Baku (Excipient Mapping & FWR Test)")
            if rep.excipient_evaluations:
                exc_rows = []
                for e in rep.excipient_evaluations:
                    fwr_summary = e.fwr_test.legal_doctrine_summary if e.fwr_test else "Identik dengan klaim paten"
                    exc_rows.append({
                        "Bahan Baku": e.ingredient_name,
                        "Kadar": e.unit_dosage_amount or "-",
                        "Kategori Fungsional": e.functional_category.value,
                        "Komponen Paten": e.claimed_counterpart or "Tidak diklaim langsung",
                        "Status": e.equivalence_status.value,
                        "Uji FWR / Justifikasi": fwr_summary,
                    })
                st.dataframe(pd.DataFrame(exc_rows), use_container_width=True, hide_index=True)
            else:
                st.info("Belum ada pemetaan eksipien yang diidentifikasi.")

        # TAB 3: CLAIM CHART
        with t_chart:
            st.markdown("### 📋 Matriks Perbandingan Klaim Farmasi Elemen-demi-Elemen")
            for cr in rep.claim_results:
                with st.expander(f"📌 Klaim {cr.claim_number} [{cr.claim_type.value}] — Risiko: {cr.risk_level.value}", expanded=True):
                    st.caption(f"Ringkasan: {cr.summary}")
                    chart_rows = []
                    for elem in cr.elements:
                        chart_rows.append({
                            "#": elem.element_index,
                            "Pilar Farmasi": elem.category.value,
                            "Limitasi Klaim Paten": elem.claim_limitation,
                            "Fitur Formula Produk": elem.formula_feature or "(Tidak ada)",
                            "Status": elem.status.value,
                            "Justifikasi Sains & Hukum": f"{elem.scientific_justification} [{elem.legal_doctrine}]"
                        })
                    st.dataframe(pd.DataFrame(chart_rows), use_container_width=True, hide_index=True)

        # TAB 4: DESIGN-AROUND & EXPORT
        with t_da:
            st.markdown("### 💡 Rekomendasi Rekayasa Bebas Paten (Pharmaceutical Design-Around)")
            if rep.design_around_recommendations:
                for idx, da in enumerate(rep.design_around_recommendations, start=1):
                    with st.container(border=True):
                        st.markdown(f"#### Strategi {idx}: {da.title} `[{da.strategy_type}]`")
                        st.write(da.description)
                        st.markdown("**Langkah-langkah Reformulasi Konkret:**")
                        for step in da.reformulation_steps:
                            st.markdown(f"- {step}")
                        st.caption(f"**Dasar Ilmiah FTO:** {da.scientific_rationale}")

            st.markdown("---")
            st.markdown("### 📥 Unduh Laporan FTO Resmi")
            d_col1, d_col2, d_col3 = st.columns(3)

            with d_col1:
                pdf_bytes = FTOReportGenerator.generate_pdf(rep)
                st.download_button(
                    label="📄 Unduh Laporan PDF (ReportLab)",
                    data=pdf_bytes,
                    file_name=f"FTO_Report_{rep.product_name.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )

            with d_col2:
                docx_bytes = FTOReportGenerator.generate_docx(rep)
                st.download_button(
                    label="📝 Unduh Laporan Word (.docx)",
                    data=docx_bytes,
                    file_name=f"FTO_Report_{rep.product_name.replace(' ', '_')}.docx",
                    mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    use_container_width=True,
                )

            with d_col3:
                json_str = rep.model_dump_json(indent=2)
                st.download_button(
                    label="💾 Unduh Data JSON",
                    data=json_str,
                    file_name=f"FTO_Report_{rep.product_name.replace(' ', '_')}.json",
                    mime="application/json",
                    use_container_width=True,
                )


# ==============================================================================
# MODE 2: GENERAL ENGINEERING PATENT MODULE
# ==============================================================================
else:
    st.info("⚙️ **Modul Paten Rekayasa Umum Aktif:** Untuk analisis paten mekanikal, elektronik, AI, telekomunikasi, dan drone.")

    col_pat_gen, col_prod_gen = st.columns(2)
    with col_pat_gen:
        p_title_gen = st.text_input("Judul Paten", value=st.session_state.get("patent_title", ""))
        p_text_gen = st.text_area("Teks Klaim Paten", value=st.session_state.get("patent_text", ""), height=260)
    with col_prod_gen:
        pr_name_gen = st.text_input("Nama Produk", value=st.session_state.get("product_name", ""))
        pr_desc_gen = st.text_area("Deskripsi Fitur Produk", value=st.session_state.get("product_desc", ""), height=260)

    if st.button("🚀 Jalankan Analisis All-Elements Rule Paten Umum", use_container_width=True, type="primary"):
        eff_k = custom_api_key.strip() if custom_api_key else None
        an = InfringementAnalyzer(api_key=eff_k)
        req = PatentAnalysisRequest(
            patent_title=p_title_gen,
            patent_text=p_text_gen,
            product_name=pr_name_gen,
            product_features=pr_desc_gen,
            api_key=eff_k,
        )
        try:
            g_rep = an.analyze(req)
            st.session_state["general_report"] = g_rep
        except Exception as e:
            st.error(f"Gagal analisis: {e}")

    if st.session_state.get("general_report"):
        g_rep: InfringementReport = st.session_state["general_report"]
        st.markdown(f"### Kesimpulan Risiko: {g_rep.overall_risk.value}")
        st.write(g_rep.executive_summary)
        for cr in g_rep.claim_results:
            with st.expander(f"Klaim {cr.claim_number} [{cr.claim_type.value}] - {cr.risk_level.value}"):
                for elem in cr.element_analyses:
                    st.markdown(f"- **{elem.claim_element}**: `{elem.status.value}` — {elem.reasoning}")

# Footer
st.markdown("---")
st.caption("PatentGuard AI © 2026 — Ditenagai oleh Google Gemini 3.8 Flash, ReportLab, & Python-Docx. Analisis bersifat teknis indikatif untuk keperluan Freedom-to-Operate awal.")
