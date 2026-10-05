from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ClaimType(str, Enum):
    INDEPENDENT = "INDEPENDENT"
    DEPENDENT = "DEPENDENT"


class ElementMatchStatus(str, Enum):
    MATCHED = "MATCHED"          # Fitur produk memenuhi elemen klaim secara literal
    MISSING = "MISSING"          # Fitur produk tidak memiliki elemen klaim ini
    EQUIVALENT = "EQUIVALENT"    # Doctrine of Equivalents: fungsi, cara, hasil ekuivalen
    UNCLEAR = "UNCLEAR"          # Deskripsi produk ambigu / butuh klarifikasi lebih lanjut


class InfringementRiskLevel(str, Enum):
    HIGH = "HIGH"        # Potensi pelanggaran literal tinggi (semua elemen terpenuhi)
    MEDIUM = "MEDIUM"    # Potensi pelanggaran doktrin ekuivalensi atau elemen ambigu
    LOW = "LOW"          # Risiko rendah / lolos paten (terdapat elemen kunci yang hilang)


class PharmaClaimCategory(str, Enum):
    ACTIVE_INGREDIENT = "ACTIVE_INGREDIENT"            # Zat Aktif, Garam, Ester, Polimorf
    CONCENTRATION_RANGE = "CONCENTRATION_RANGE"        # Rentang Konsentrasi (% w/w, mg/dose, rasio)
    PHYSICOCHEMICAL_PROPERTY = "PHYSICOCHEMICAL"       # Viskositas, profil disolusi, d90, kristalinitas
    MANUFACTURING_PROCESS = "MANUFACTURING_PROCESS"    # Granulasi basah/kering, kempa langsung, HME, coating


class ExcipientFunctionType(str, Enum):
    RELEASE_CONTROLLING_POLYMER = "RELEASE_CONTROLLING_POLYMER"  # HPMC, Etilselulosa, Eudragit, Carbopol, Polyox
    DILUENT_FILLER = "DILUENT_FILLER"                            # Avicel PH 102, Laktosa, Manitol, DCP
    BINDER = "BINDER"                                            # PVP K30, HPC, Gelatin, Pregelatinized Starch
    DISINTEGRANT = "DISINTEGRANT"                                # Croscarmellose, Sodium Starch Glycolate, Crospovidone
    LUBRICANT_GLIDANT = "LUBRICANT_GLIDANT"                      # Mg Stearate, Aerosil 200, Talc, Stearyl Fumarate
    SURFACTANT_SOLUBILIZER = "SURFACTANT_SOLUBILIZER"            # Polysorbate 80, SLS, Poloxamer 188
    COATING_PLASTICIZER = "COATING_PLASTICIZER"                  # Triethyl Citrate, PEG 6000, TiO2
    BUFFER_STABILIZER = "BUFFER_STABILIZER"                      # Asam Sitrat, Meglumine, BHT, Asam Askorbat
    OTHER = "OTHER"


class EquivalenceTestStatus(str, Enum):
    LITERAL_MATCH = "LITERAL_MATCH"            # Identik secara literal (IUPAC sama / garam sama / klaim terpenuhi)
    EQUIVALENT_MATCH = "EQUIVALENT_MATCH"      # Doctrine of Equivalents: Function-Way-Result substansial sama
    OUT_OF_RANGE = "OUT_OF_RANGE"              # Nilai numerik / proporsi di luar batas klaim
    MISSING_ELEMENT = "MISSING_ELEMENT"        # Elemen/eksipien/proses tidak ada dalam formula
    UNCLEAR = "UNCLEAR"                        # Memerlukan pengujian laboratorium lebih lanjut


# General Models
class Claim(BaseModel):
    claim_number: int = Field(..., description="Nomor urut klaim (misal: 1, 2, dst)")
    claim_type: ClaimType = Field(..., description="Tipe klaim: INDEPENDENT atau DEPENDENT")
    depends_on: Optional[int] = Field(None, description="Nomor klaim induk jika DEPENDENT")
    preamble: str = Field(..., description="Preamble / pendahuluan klaim sebelum kata transisi")
    body: str = Field(..., description="Isi klaim teknis")
    elements: List[str] = Field(default_factory=list, description="Daftar elemen klaim terpisah (limitations)")
    full_text: str = Field(..., description="Teks lengkap klaim")


class ClaimElementAnalysis(BaseModel):
    element_index: int = Field(..., description="Indeks elemen klaim (1, 2, ...)")
    claim_element: str = Field(..., description="Teks elemen klaim paten yang diuji")
    matched_product_feature: Optional[str] = Field(None, description="Fitur produk yang berkorespondensi")
    status: ElementMatchStatus = Field(..., description="Status pencocokan elemen")
    reasoning: str = Field(..., description="Penjelasan teknis dan justifikasi hukum paten")
    doctrine_applied: str = Field(default="All-Elements Rule", description="Doktrin hukum paten yang diterapkan")


class ClaimAnalysisResult(BaseModel):
    claim_number: int = Field(..., description="Nomor klaim yang dianalisis")
    claim_type: ClaimType = Field(..., description="Tipe klaim")
    depends_on: Optional[int] = Field(None, description="Nomor klaim induk jika dependen")
    claim_preamble: str = Field(default="", description="Preamble klaim")
    risk_level: InfringementRiskLevel = Field(..., description="Tingkat risiko pelanggaran klaim ini")
    element_analyses: List[ClaimElementAnalysis] = Field(..., description="Daftar matriks perbandingan per elemen")
    summary: str = Field(..., description="Kesimpulan analisis untuk klaim ini")


class PatentAnalysisRequest(BaseModel):
    patent_title: Optional[str] = Field(None, description="Judul atau nomor paten (opsional)")
    patent_text: str = Field(..., description="Teks lengkap paten atau bagian klaim paten")
    product_name: str = Field(..., description="Nama produk atau layanan yang diuji")
    product_features: str = Field(..., description="Deskripsi lengkap fitur dan cara kerja produk")
    api_key: Optional[str] = Field(None, description="Kunci API Gemini opsional (jika tidak menggunakan env)")


class InfringementReport(BaseModel):
    patent_title: str = Field(..., description="Judul atau referensi paten")
    product_name: str = Field(..., description="Nama produk yang dianalisis")
    overall_risk: InfringementRiskLevel = Field(..., description="Tingkat risiko keseluruhan")
    total_claims_analyzed: int = Field(..., description="Jumlah total klaim yang dianalisis")
    independent_claims_count: int = Field(..., description="Jumlah klaim independen")
    dependent_claims_count: int = Field(..., description="Jumlah klaim dependen")
    claim_results: List[ClaimAnalysisResult] = Field(..., description="Hasil claim chart tiap klaim")
    design_around_recommendations: List[str] = Field(
        default_factory=list,
        description="Rekomendasi modifikasi teknis (design-around) agar terhindar dari pelanggaran"
    )
    executive_summary: str = Field(..., description="Ringkasan eksekutif untuk manajemen dan tim legal")


# ==========================================
# Pharmaceutical & Chemical Specialized Models
# ==========================================

class ChemicalEntity(BaseModel):
    """Representasi zat aktif farmasi dengan penelusuran tata nama IUPAC, INN, sinonim, dan bentuk garam."""
    inn_name: str = Field(..., description="International Nonproprietary Name (contoh: Metformin, Atorvastatin)")
    trade_names: List[str] = Field(default_factory=list, description="Nama dagang umum (contoh: Glucophage, Lipitor)")
    iupac_name: str = Field(..., description="Nama kimia standar IUPAC")
    synonyms: List[str] = Field(default_factory=list, description="Sinonim kimia dan kode laboratorium")
    molecular_formula: Optional[str] = Field(None, description="Rumus molekul (contoh: C4H11N5·HCl)")
    molecular_weight: Optional[str] = Field(None, description="Berat molekul dalam g/mol")
    cas_number: Optional[str] = Field(None, description="Nomor registri CAS")
    chemical_form: str = Field("FREE_BASE", description="Bentuk kimia: BASE, SALT (HCl, Ca, Na, dll), HYDRATE, POLYMORPH")
    detected_in_patent: bool = Field(False, description="Apakah terdeteksi di dokumen paten")
    detected_in_formula: bool = Field(False, description="Apakah terdeteksi di formula produk")
    is_equivalent_entity: bool = Field(False, description="Apakah entitas kimia formula identik/ekuivalen dengan paten")
    equivalence_note: Optional[str] = Field(None, description="Catatan justifikasi kimia/hukum mengenai bentuk garam atau polimorf")


class FunctionWayResultTest(BaseModel):
    """Uji Doktrin Ekuivalensi Farmasetik (Graver Tank / Warner-Jenkinson standard)."""
    function_analysis: str = Field(..., description="Peran fungsional: Apakah melakukan fungsi yang sama?")
    way_analysis: str = Field(..., description="Mekanisme fisikokimia: Apakah bekerja dengan cara yang substansial sama?")
    result_analysis: str = Field(..., description="Hasil kinerja farmasetik: Apakah menghasilkan performa yang sama?")
    is_substantially_equivalent: bool = Field(..., description="Hasil akhir uji Function-Way-Result")
    legal_doctrine_summary: str = Field(..., description="Ringkasan pertimbangan hukum paten")


class ExcipientMapping(BaseModel):
    """Pemetaan bahan eksipien, peran fungsional, dan evaluasi substitusi."""
    ingredient_name: str = Field(..., description="Nama bahan eksipien (misal: HPMC K100M, Avicel PH 102)")
    functional_category: ExcipientFunctionType = Field(..., description="Kategori fungsi farmasetik")
    role_description: str = Field(..., description="Deskripsi peran spesifik dalam sediaan")
    concentration_w_w: Optional[float] = Field(None, description="Konsentrasi dalam formula (% w/w)")
    unit_dosage_amount: Optional[str] = Field(None, description="Jumlah per dosis (misal: 150 mg/tablet)")
    claimed_counterpart: Optional[str] = Field(None, description="Komponen paten yang berkorespondensi")
    claimed_range: Optional[str] = Field(None, description="Rentang batas dalam klaim paten")
    is_within_claimed_range: Optional[bool] = Field(None, description="Apakah konsentrasi masuk dalam rentang klaim")
    fwr_test: Optional[FunctionWayResultTest] = Field(None, description="Hasil uji Function-Way-Result")
    equivalence_status: EquivalenceTestStatus = Field(..., description="Status ekuivalensi fungsional")


class PharmaClaimElement(BaseModel):
    """Detail perbandingan elemen klaim farmasi spesifik."""
    element_index: int = Field(..., description="Indeks elemen klaim")
    category: PharmaClaimCategory = Field(..., description="Kategori elemen: Zat Aktif, Rentang, Fisikokimia, Proses")
    claim_limitation: str = Field(..., description="Teks pembatas klaim paten")
    formula_feature: Optional[str] = Field(None, description="Fitur/bahan formula produk yang diuji")
    status: EquivalenceTestStatus = Field(..., description="Status keterpenuhan elemen")
    scientific_justification: str = Field(..., description="Justifikasi ilmiah farmasetika dan kimia")
    legal_doctrine: str = Field(default="All-Elements Rule", description="Doktrin hukum paten yang diterapkan")


class PharmaClaimResult(BaseModel):
    """Hasil analisis per klaim paten farmasi."""
    claim_number: int = Field(..., description="Nomor urut klaim")
    claim_type: ClaimType = Field(..., description="Tipe klaim: INDEPENDENT / DEPENDENT")
    depends_on: Optional[int] = Field(None, description="Klaim induk jika dependen")
    preamble: str = Field(default="", description="Preamble klaim")
    risk_level: InfringementRiskLevel = Field(..., description="Tingkat risiko klaim")
    elements: List[PharmaClaimElement] = Field(default_factory=list, description="Elemen-elemen pembatas klaim")
    summary: str = Field(..., description="Ringkasan analisis klaim")


class PharmaDesignAround(BaseModel):
    """Rekomendasi taktis formulasi ulang (design-around) bebas paten."""
    strategy_type: str = Field(..., description="Jenis strategi: MODIFIKASI_KONSENTRASI, SUBSTITUSI_EKSIPIEN, PERUBAHAN_BENTUK_PADAT, MODIFIKASI_PROSES")
    title: str = Field(..., description="Judul strategi reformulasi")
    description: str = Field(..., description="Penjelasan teknis sains farmasi")
    reformulation_steps: List[str] = Field(default_factory=list, description="Langkah-langkah konkret modifikasi formula")
    scientific_rationale: str = Field(..., description="Dasar ilmiah kenapa strategi ini bebas dari cakupan klaim")
    fto_advantage: str = Field(..., description="Keunggulan Freedom-to-Operate (FTO)")


class PharmaInfringementReport(BaseModel):
    """Laporan komprehensif FTO & Analisis Pelanggaran Paten Farmasi."""
    patent_title: str = Field(..., description="Judul paten pembanding")
    patent_number: Optional[str] = Field(None, description="Nomor paten (USPTO, WIPO, DJKI)")
    product_name: str = Field(..., description="Nama produk/formula internal")
    dosage_form: Optional[str] = Field("Tablet Lepas Lambat (Extended Release)", description="Bentuk sediaan farmasi")
    overall_risk: InfringementRiskLevel = Field(..., description="Tingkat risiko keseluruhan")
    risk_score_numeric: int = Field(..., ge=0, le=100, description="Skor risiko numerik (0-100%)")
    all_elements_rule_met: bool = Field(..., description="Apakah seluruh elemen terpenuhi (Literal Infringement)")
    doctrine_of_equivalents_triggered: bool = Field(..., description="Apakah doktrin ekuivalensi terpicu")
    executive_summary: str = Field(..., description="Ringkasan eksekutif tingkat analis HAKI dan formulator")
    fto_verdict: str = Field(..., description="Opini kelayakan Freedom-To-Operate (FTO)")
    chemical_entities: List[ChemicalEntity] = Field(default_factory=list, description="Dossier validasi zat aktif & tata nama IUPAC")
    excipient_evaluations: List[ExcipientMapping] = Field(default_factory=list, description="Pemetaan fungsional bahan baku & uji FWR")
    claim_results: List[PharmaClaimResult] = Field(default_factory=list, description="Matriks Claim Chart farmasi")
    design_around_recommendations: List[PharmaDesignAround] = Field(default_factory=list, description="Rekomendasi reformulasi bebas paten")


class PharmaAnalysisRequest(BaseModel):
    patent_title: Optional[str] = Field(None, description="Judul atau nomor paten")
    patent_text: str = Field(..., description="Teks klaim paten pembanding")
    product_name: str = Field(..., description="Nama produk/formula farmasi")
    product_formula_text: str = Field(..., description="Deskripsi spesifikasi formula dan proses manufaktur")
    dosage_form: Optional[str] = Field(None, description="Bentuk sediaan (Tablet, Kapsul, Suspensi, Injeksi)")
    api_key: Optional[str] = Field(None, description="Kunci API Gemini opsional")


class ReformulationSimRequest(BaseModel):
    patent_text: str = Field(..., description="Teks klaim paten pembanding")
    product_name: str = Field(..., description="Nama formula")
    modified_formula_text: str = Field(..., description="Teks formula yang telah dimodifikasi oleh pengguna")
    api_key: Optional[str] = Field(None, description="Kunci API Gemini opsional")

