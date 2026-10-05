import os
from fastapi import FastAPI, HTTPException, UploadFile, File, Form, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any

from models import (
    PatentAnalysisRequest,
    InfringementReport,
    Claim,
    PharmaAnalysisRequest,
    PharmaInfringementReport,
    ReformulationSimRequest,
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

app = FastAPI(
    title="PatentGuard AI - Pharmaceutical Patent Intelligence & FTO Engine",
    description="Sistem Deteksi Pelanggaran Paten Farmasi & Kimia Berbasis AI (IUPAC, Excipient Function, All-Elements Rule, & Doctrine of Equivalents)",
    version="2.0.0",
)

# CORS Middleware agar dapat diakses dari frontend client
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

analyzer = InfringementAnalyzer()


class ExtractClaimsRequest(BaseModel):
    patent_text: str


@app.get("/api/health")
def health_check():
    """Mengecek status ketersediaan API dan konfigurasi Gemini."""
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
    return {
        "status": "healthy",
        "service": "PatentGuard AI",
        "pharma_module": "active",
        "gemini_api_configured": has_gemini_key,
        "default_model": "gemini-3.8-flash",
        "version": "2.0.0",
    }


# ==============================================================================
# PHARMACEUTICAL & CHEMICAL SPECIALIZED ENDPOINTS
# ==============================================================================

@app.post("/api/pharma/analyze", response_model=PharmaInfringementReport)
def analyze_pharma_infringement(payload: PharmaAnalysisRequest):
    """
    Melakukan analisis komprehensif paten farmasi & kimia:
    - Verifikasi zat aktif via tata nama IUPAC, INN, nama dagang, dan bentuk garam.
    - Pemetaan fungsi eksipien (polimer retardant, pengisi, pelincir) & uji Function-Way-Result.
    - Claim Chart 4 pilar (Zat Aktif, Rentang Konsentrasi, Fisikokimia, Proses).
    - Skor risiko pelanggaran dan rekomendasi taktis Design-Around.
    """
    if not payload.patent_text.strip():
        raise HTTPException(status_code=400, detail="Teks klaim paten wajib diisi.")
    if not payload.product_formula_text.strip():
        raise HTTPException(status_code=400, detail="Deskripsi spesifikasi formula produk wajib diisi.")

    try:
        report = pharma_engine.analyze(payload)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal melakukan analisis paten farmasi: {str(e)}")


@app.post("/api/pharma/reformulate-sim", response_model=PharmaInfringementReport)
def simulate_reformulation(payload: ReformulationSimRequest):
    """
    Simulator reformulasi interaktif:
    Pengguna dapat memodifikasi persentase eksipien atau mengganti bahan secara live
    dan melihat perubahan skor risiko serta status hukum FTO secara seketika.
    """
    if not payload.modified_formula_text.strip():
        raise HTTPException(status_code=400, detail="Teks formula yang dimodifikasi tidak boleh kosong.")

    req = PharmaAnalysisRequest(
        patent_title="Paten Pembanding Terpilih",
        patent_text=payload.patent_text,
        product_name=payload.product_name,
        product_formula_text=payload.modified_formula_text,
        api_key=payload.api_key,
    )
    try:
        return pharma_engine.analyze(req)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal mensimulasikan reformulasi: {str(e)}")


@app.post("/api/pharma/parse-formula")
def parse_formula_details(payload: Dict[str, str]):
    """
    Menguraikan komponen kimia, eksipien, dan tahapan proses dari teks formula bebas.
    """
    text = payload.get("formula_text", "")
    if not text.strip():
        raise HTTPException(status_code=400, detail="Teks formula tidak boleh kosong.")

    parsed = DocumentParser.parse_formula_specification(text)
    chemicals = ChemicalResolver.identify_entities(text)
    excipients = ExcipientEvaluator.extract_and_map_excipients(text, "")

    return {
        "parsed_specs": parsed,
        "identified_active_ingredients": chemicals,
        "mapped_excipients": excipients,
    }


@app.post("/api/pharma/upload-docs")
async def upload_documents(
    patent_file: Optional[UploadFile] = File(None),
    formula_file: Optional[UploadFile] = File(None),
):
    """
    Upload dokumen multi-format (PDF, TXT, DOCX) untuk dokumen paten & formula internal.
    """
    result = {"patent_text": "", "formula_text": "", "patent_filename": "", "formula_filename": ""}

    if patent_file:
        content = await patent_file.read()
        result["patent_text"] = DocumentParser.extract_text_from_bytes(content, patent_file.filename)
        result["patent_filename"] = patent_file.filename

    if formula_file:
        content = await formula_file.read()
        result["formula_text"] = DocumentParser.extract_text_from_bytes(content, formula_file.filename)
        result["formula_filename"] = formula_file.filename

    return result


@app.post("/api/pharma/export-pdf")
def export_fto_pdf(report: PharmaInfringementReport):
    """
    Menghasilkan dan mengunduh berkas laporan FTO resmi dalam format PDF biner.
    """
    try:
        pdf_bytes = FTOReportGenerator.generate_pdf(report)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=FTO_Report_{report.product_name.replace(' ', '_')}.pdf"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat laporan PDF: {str(e)}")


@app.post("/api/pharma/export-docx")
def export_fto_docx(report: PharmaInfringementReport):
    """
    Menghasilkan dan mengunduh berkas laporan FTO resmi dalam format Word (.docx) biner.
    """
    try:
        docx_bytes = FTOReportGenerator.generate_docx(report)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": f"attachment; filename=FTO_Report_{report.product_name.replace(' ', '_')}.docx"
            },
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal membuat laporan Word: {str(e)}")


@app.get("/api/pharma/sample-cases")
def get_pharma_sample_cases():
    """
    Menyediakan data kasus uji farmasi nyata:
    1. Metformin XR (High Risk - Literal Infringement)
    2. Atorvastatin Solid Dispersion (Low Risk - Safe Design-Around)
    3. Paracetamol Sustained-Release (Medium Risk - Doctrine of Equivalents)
    """
    return {
        "cases": [
            {
                "id": "metformin-literal-high",
                "badge": "HIGH RISK / LITERAL",
                "badge_color": "rose",
                "title": "Kasus 1: Metformin XR Extended-Release (Literal Infringement)",
                "patent_title": "US654321 - Extended-Release Metformin Biguanide Matrix Formulation",
                "patent_text": """What is claimed is:
1. An extended-release pharmaceutical matrix tablet comprising:
    500 mg to 1000 mg of 1,1-dimethylbiguanide hydrochloride;
    20% to 40% by weight of hydroxypropyl methylcellulose having a viscosity of 100,000 mPa.s; and
    0.5% to 2.0% by weight of a lubricant,
    wherein the tablet is manufactured via wet granulation and releases at least 80% of the active ingredient over a 12-hour period.

2. The extended-release tablet according to claim 1, wherein the lubricant is magnesium stearate.""",
                "product_name": "Glucosafe XR 500mg Extended Release",
                "dosage_form": "Tablet Lepas Lambat (Hydrophilic Matrix)",
                "product_formula_text": """Spesifikasi Formula Tablet Glucosafe XR:
- Zat Aktif: 1,1-dimethylbiguanide monohydrochloride (Metformin HCl) = 500 mg/tablet
- Polimer Matriks: Hydroxypropyl Methylcellulose (HPMC K100M) = 28% w/w
- Pengisi/Pengikat: Microcrystalline Cellulose (Avicel PH 102) = 20% w/w
- Pelincir: Magnesium Stearate = 1.0% w/w
- Glidan: Colloidal Silicon Dioxide (Aerosil 200) = 0.5% w/w
Proses: High-shear wet granulation menggunakan larutan pengikat PVP K30, pengeringan fluid bed dryer, dan pencetakan tablet rotari.
Uji Disolusi: 85% terlarut pada jam ke-12 (buffer fosfat pH 6.8).""",
            },
            {
                "id": "atorvastatin-design-around-low",
                "badge": "LOW RISK / SAFE DESIGN-AROUND",
                "badge_color": "emerald",
                "title": "Kasus 2: Atorvastatin Lipid Erosion Matrix (Safe Design-Around)",
                "patent_title": "EP2198765 - Crystalline Atorvastatin Calcium Trihydrate Matrix Formulation",
                "patent_text": """What is claimed is:
1. A solid pharmaceutical dosage form comprising:
    crystalline atorvastatin calcium trihydrate Form I characterized by X-ray powder diffraction peaks at 2-theta of 11.9, 17.0, and 21.6 degrees;
    15% to 35% by weight of hydroxypropyl methylcellulose phthalate as an enteric erosion polymer; and
    a wetting surfactant selected from sodium lauryl sulfate,
    wherein the formulation is processed by hot melt extrusion.

2. The solid dosage form according to claim 1, further comprising a plasticizer.""",
                "product_name": "Atorva-Pure 40mg (Lipid Matrix Design-Around)",
                "dosage_form": "Tablet Kempa Langsung",
                "product_formula_text": """Spesifikasi Formula Rekayasa Bebas Paten (Design-Around):
- Zat Aktif: Atorvastatin free base amorf dalam bentuk Co-Crystal dengan Nikotinamid (1:1 molar ratio, BUKAN garam kalsium trihidrat kristalin Form I) = 40 mg
- Matriks Pelepasan: Glycerol Distearate (Precirol ATO 5) = 20% w/w (Matriks lipid hidrofobik erosi kanal pori, TIDAK MENGGUNAKAN HPMC Phthalate)
- Pengisi Deformasi Plastis: Microcrystalline Cellulose (Avicel PH 200) = 38% w/w
- Pelincir: Sodium Stearyl Fumarate (Pruv) = 1.5% w/w (Bebas dari Sodium Lauryl Sulfate)
- Metode Manufaktur: Kempa Langsung (Direct Compression) tanpa proses hot melt extrusion maupun wet granulation.
- Profil Disolusi: Pelepasan mandiri pH-independen melalui erosi lipid.""",
            },
            {
                "id": "paracetamol-doe-medium",
                "badge": "MEDIUM RISK / EQUIVALENCE",
                "badge_color": "amber",
                "title": "Kasus 3: Paracetamol Sustained-Release Hydrogel (Doctrine of Equivalents)",
                "patent_title": "WO202109876 - Extended-Release Acetaminophen Formulation Using Polysaccharide Hydrogel",
                "patent_text": """What is claimed is:
1. A sustained-release oral caplet comprising:
    650 mg of N-(4-hydroxyphenyl)acetamide;
    15% to 30% by weight of xanthan gum as the primary hydrophilic swellable matrix agent; and
    microcrystalline cellulose as a dry binder,
    wherein upon ingestion the xanthan gum hydrates to form a viscous hydrogel barrier controlling diffusion of the active substance.

2. The caplet of claim 1, wherein the caplet exhibits zero-order release kinetics for 8 hours.""",
                "product_name": "Paramol Retard 650mg Caplets",
                "dosage_form": "Kaplet Lepas Lambat",
                "product_formula_text": """Formula Sediaan Lepas Lambat:
- Zat Aktif: Paracetamol (Acetaminophen / N-(4-hydroxyphenyl)acetamide) = 650 mg/kaplet
- Polimer Matriks: Polyethylene Oxide (Polyox WSR-303) = 22% w/w (Substitusi dari Xanthan Gum; keduanya merupakan polimer hidrofilik yang mengembang dan berdisolusi membentuk lapisan gel penahan difusi)
- Pengisi/Pengikat: Microcrystalline Cellulose (Avicel PH 101) = 18% w/w
- Pelincir: Magnesium Stearate = 0.8% w/w
- Proses: Roller compaction (granulasi kering) dan kompresi kaplet lonjong.""",
            },
        ]
    }


@app.get("/api/pharma/registry")
def get_pharma_registry():
    """Mengembalikan daftar zat aktif dan taksonomi eksipien yang didukung."""
    return {
        "chemicals": list(CHEMICAL_REGISTRY.keys()),
        "excipients": list(EXCIPIENT_DATABASE.keys()),
    }


# ==============================================================================
# GENERAL CLAIM EXTRACTION & GENERAL PATENT ENDPOINTS (BACKWARDS COMPATIBILITY)
# ==============================================================================

@app.post("/api/extract-claims", response_model=List[Claim])
def extract_claims(payload: ExtractClaimsRequest):
    """Mengekstrak dan memilah klaim independen/dependen dari teks dokumen paten."""
    if not payload.patent_text.strip():
        raise HTTPException(status_code=400, detail="Teks dokumen paten tidak boleh kosong.")
    return ClaimExtractor.extract_claims(payload.patent_text)


@app.post("/api/analyze", response_model=InfringementReport)
def analyze_infringement(payload: PatentAnalysisRequest):
    """Melakukan analisis komparatif umum All-Elements Rule & Doctrine of Equivalents."""
    if not payload.patent_text.strip():
        raise HTTPException(status_code=400, detail="Teks dokumen paten wajib diisi.")
    if not payload.product_features.strip():
        raise HTTPException(status_code=400, detail="Deskripsi fitur produk wajib diisi.")

    try:
        report = analyzer.analyze(payload)
        return report
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Gagal melakukan analisis paten: {str(e)}")


@app.get("/api/sample-data")
def get_sample_data():
    """Menyediakan data paten & produk sampel umum untuk demonstrasi."""
    return {
        "samples": [
            {
                "id": "high-risk",
                "title": "US9876543 - Autonomous Surveillance Drone with Thermal Object Tracking",
                "patent_title": "Autonomous Surveillance Drone with Thermal Object Tracking",
                "patent_text": """What is claimed is:
1. An autonomous aerial surveillance system comprising:
    a multi-rotor unmanned aerial vehicle (UAV) frame;
    a thermal imaging sensor mounted on a 3-axis gimbal;
    an onboard processor coupled to the thermal imaging sensor, wherein the processor executes a convolutional neural network to classify living objects based on thermal signatures; and
    a wireless telemetry transmitter configured to stream real-time alert coordinates to a ground control station.

2. The system according to claim 1, further comprising an acoustic siren mounted to the UAV frame for perimeter deterrence.""",
                "product_name": "AeroGuard Pro X",
                "product_features": """AeroGuard Pro X adalah quadcopter pengawas otomatis yang memiliki:
- Rangka drone serat karbon 4-rotor yang kokoh.
- Kamera pencitraan termal beresolusi tinggi yang terpasang pada gimbal 3-sumbu dengan stabilisasi otomatis.
- Komputer mini onboard bertenaga AI dengan model deep learning CNN untuk mendeteksi dan mengklasifikasikan manusia dan hewan berdasarkan jejak panas secara real-time.
- Modul radio telemetri nirkabel untuk mengirim koordinat GPS dan peringatan otomatis ke stasiun operator darat.""",
            },
            {
                "id": "low-risk",
                "title": "IDP0000456 - Sistem Dispenser Air Pintar dengan Sterilisasi UV dan Sensor Ultrasonik",
                "patent_title": "Sistem Dispenser Air Pintar dengan Sterilisasi UV",
                "patent_text": """Klaim:
1. Suatu sistem dispenser air pintar terdiri dari:
    sebuah tangki penampung air berkapasitas ganda;
    sebuah lampu sterilisasi sinar ultraviolet (UV-C) yang dipasang di dalam tangki penampung;
    sebuah sensor level air berbasis ultrasonik yang terhubung ke mikrokontroler; dan
    sebuah katup solenoid elektromagnetik yang membuka aliran air secara otomatis saat wadah terdeteksi.

2. Sistem dispenser air pintar sesuai klaim 1, di mana lampu sterilisasi UV-C beroperasi secara berkala setiap 30 menit.""",
                "product_name": "AquaPure ECO (Design-Around)",
                "product_features": """AquaPure ECO adalah dispenser air modern yang menggunakan:
- Tangki penampung air tunggal berbahan stainless steel food grade.
- Filtrasi membran keramik mikro dan karbon aktif biologis (TIDAK MENGGUNAKAN lampu sinar UV atau sterilisasi radiasi UV).
- Sensor berat (load cell) pada tatakan gelas untuk mengukur volume pengisian.
- Katup manual dengan tuas mekanis tekan fisik.""",
            }
        ]
    }


# Static files mount
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(static_dir, "index.html"))

