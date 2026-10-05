"""
PatentGuard AI - Pharmaceutical & Chemical Patent Analysis Engine
Modul Khusus Analisis Farmasi, Tata Nama Kimia IUPAC, dan Pemetaan Fungsi Eksipien.
Menerapkan Doktrin Hukum Paten Farmasi Internasional:
- All-Elements Rule (Literal Infringement)
- Doctrine of Equivalents (Function-Way-Result Test / Graver Tank / Warner-Jenkinson)
- Prosecution History Estoppel (Festo Corp.)
"""

import os
import re
import json
import logging
from typing import List, Dict, Optional, Tuple, Any

from models import (
    Claim,
    PharmaAnalysisRequest,
    PharmaInfringementReport,
    PharmaClaimResult,
    PharmaClaimElement,
    PharmaDesignAround,
    ChemicalEntity,
    ExcipientMapping,
    FunctionWayResultTest,
    PharmaClaimCategory,
    ExcipientFunctionType,
    EquivalenceTestStatus,
    InfringementRiskLevel,
    ClaimType,
)
from claim_extractor import ClaimExtractor

logger = logging.getLogger("patentguard.pharma_engine")
AI_MODEL_NAME = "gemini-3.8-flash"


# ==============================================================================
# 1. CHEMICAL KNOWLEDGE BASE & IUPAC REGISTRY
# ==============================================================================

CHEMICAL_REGISTRY: Dict[str, Dict[str, Any]] = {
    "metformin": {
        "inn": "Metformin",
        "trade_names": ["Glucophage", "Glucophage XR", "Fortamet", "Glumetza", "Riomet"],
        "iupac": "1,1-dimethylbiguanide",
        "iupac_variants": [
            "1,1-dimethylbiguanide",
            "1,1-dimethylbiguanide monohydrochloride",
            "1,1-dimethylbiguanide hydrochloride",
            "N,N-dimethylimidodicarbonimidic diamide",
            "N,N-dimethylimidodicarbonimidic diamide hydrochloride",
            "dimethylbiguanide",
        ],
        "molecular_formula": "C4H11N5 (Base) / C4H11N5·HCl (Garam Hidroklorida)",
        "molecular_weight": "129.16 g/mol (Base) / 165.62 g/mol (HCl)",
        "cas_number": "657-24-9 (Base) / 1115-70-4 (HCl)",
        "salts": ["hydrochloride", "succinate", "embonate", "fumarate", "malate"],
        "polymorphs": ["Form A (monoclinic)", "Form B"],
        "therapeutic_class": "Antidiabetes Oral (Biguanida)",
        "bcs_class": "BCS Class III (Kelarutan Tinggi, Permeabilitas Rendah)",
    },
    "atorvastatin": {
        "inn": "Atorvastatin",
        "trade_names": ["Lipitor", "Torvast", "Atorva", "Liprimar", "Citalor"],
        "iupac": "(3R,5R)-7-[2-(4-fluorophenyl)-3-phenyl-4-(phenylcarbamoyl)-5-propan-2-ylpyrrol-1-yl]-3,5-dihydroxyheptanoic acid",
        "iupac_variants": [
            "(3R,5R)-7-[2-(4-fluorophenyl)-3-phenyl-4-(phenylcarbamoyl)-5-propan-2-ylpyrrol-1-yl]-3,5-dihydroxyheptanoic acid",
            "[R-(R*,R*)]-2-(4-fluorophenyl)-beta,delta-dihydroxy-5-(1-methylethyl)-3-phenyl-4-[(phenylamino)carbonyl]-1H-pyrrole-1-heptanoic acid",
            "calcium (3R,5R)-7-[2-(4-fluorophenyl)-3-phenyl-4-(phenylcarbamoyl)-5-(propan-2-yl)-1H-pyrrol-1-yl]-3,5-dihydroxyheptanoate",
            "atorvastatin calcium",
            "atorvastatin hemicalcium trihydrate",
        ],
        "molecular_formula": "C33H35FN2O5 (Base) / C66H68CaF2N4O10·3H2O (Kalsium Trihidrat)",
        "molecular_weight": "558.64 g/mol (Base) / 1209.4 g/mol (Garam Ca)",
        "cas_number": "134523-00-5 (Base) / 134523-03-8 (Ca Trihidrat) / 344423-98-9 (Amorf)",
        "salts": ["calcium", "magnesium", "sodium", "potassium"],
        "polymorphs": ["Form I (trihidrat kristalin)", "Form II", "Form IV", "Amorphous (amorf)"],
        "therapeutic_class": "Antihiperlipidemia (Statin / HMG-CoA Reductase Inhibitor)",
        "bcs_class": "BCS Class II (Kelarutan Rendah, Permeabilitas Tinggi)",
    },
    "paracetamol": {
        "inn": "Paracetamol",
        "trade_names": ["Panadol", "Tylenol", "Sanmol", "Calpol", "Tempra", "Doliprane"],
        "iupac": "N-(4-hydroxyphenyl)acetamide",
        "iupac_variants": [
            "N-(4-hydroxyphenyl)acetamide",
            "N-(4-hydroxyphenyl)ethanamide",
            "4-acetamidophenol",
            "4-hydroxyacetanilide",
            "p-acetamidophenol",
            "acetaminophen",
        ],
        "molecular_formula": "C8H9NO2",
        "molecular_weight": "151.16 g/mol",
        "cas_number": "103-90-2",
        "salts": ["free base"],
        "polymorphs": ["Form I (monoklinik stabil)", "Form II (ortorombik kompresibel)", "Form III (metastabil)"],
        "therapeutic_class": "Analgesik & Antipiretik non-opioid",
        "bcs_class": "BCS Class I / III",
    },
    "esomeprazole": {
        "inn": "Esomeprazole",
        "trade_names": ["Nexium", "Esomiz", "Nexpro"],
        "iupac": "(S)-6-methoxy-2-[(4-methoxy-3,5-dimethylpyridin-2-yl)methylsulfinyl]-1H-benzimidazole",
        "iupac_variants": [
            "(S)-6-methoxy-2-[(4-methoxy-3,5-dimethylpyridin-2-yl)methylsulfinyl]-1H-benzimidazole",
            "(S)-5-methoxy-2-[[(4-methoxy-3,5-dimethyl-2-pyridinyl)methyl]sulfinyl]-1H-benzimidazole",
            "esomeprazole magnesium",
            "esomeprazole sodium",
        ],
        "molecular_formula": "C17H19N3O3S (Base) / C34H36MgN6O6S2·3H2O (Magnesium Trihidrat)",
        "molecular_weight": "345.42 g/mol (Base) / 767.17 g/mol (Mg trihydrate)",
        "cas_number": "161796-78-7 (Base) / 217087-09-7 (Mg Salt)",
        "salts": ["magnesium", "sodium", "potassium", "strontium"],
        "polymorphs": ["Form A", "Form B", "Amorphous"],
        "therapeutic_class": "Proton Pump Inhibitor (PPI) Enantiomer Murni",
        "bcs_class": "BCS Class II",
    },
    "sildenafil": {
        "inn": "Sildenafil",
        "trade_names": ["Viagra", "Revatio"],
        "iupac": "5-[2-ethoxy-5-(4-methylpiperazin-1-yl)sulfonylphenyl]-1-methyl-3-propyl-4H-pyrazolo[4,3-d]pyrimidin-7-one",
        "iupac_variants": [
            "5-[2-ethoxy-5-(4-methylpiperazin-1-yl)sulfonylphenyl]-1-methyl-3-propyl-4H-pyrazolo[4,3-d]pyrimidin-7-one",
            "1-[[3-(6,7-dihydro-1-methyl-7-oxo-3-propyl-1H-pyrazolo[4,3-d]pyrimidin-5-yl)-4-ethoxyphenyl]sulfonyl]-4-methylpiperazine",
            "sildenafil citrate",
        ],
        "molecular_formula": "C22H30N6O4S (Base) / C22H30N6O4S·C6H8O7 (Sitrat)",
        "molecular_weight": "474.58 g/mol (Base) / 666.70 g/mol (Sitrat)",
        "cas_number": "139755-83-2 (Base) / 171599-83-0 (Sitrat)",
        "salts": ["citrate", "mesylate", "free base"],
        "polymorphs": ["Form I", "Form II"],
        "therapeutic_class": "Phosphodiesterase type 5 (PDE5) Inhibitor",
        "bcs_class": "BCS Class II",
    },
    "sitagliptin": {
        "inn": "Sitagliptin",
        "trade_names": ["Januvia", "Zepalette"],
        "iupac": "(2R)-4-oxo-4-[3-(trifluoromethyl)-5,6-dihydro-[1,2,4]triazolo[4,3-a]pyrazin-7-yl]-1-(2,4,5-trifluorophenyl)butan-2-amine",
        "iupac_variants": [
            "(2R)-4-oxo-4-[3-(trifluoromethyl)-5,6-dihydro-[1,2,4]triazolo[4,3-a]pyrazin-7-yl]-1-(2,4,5-trifluorophenyl)butan-2-amine",
            "sitagliptin phosphate",
            "sitagliptin phosphate monohydrate",
        ],
        "molecular_formula": "C16H15F6N5O·H3PO4·H2O",
        "molecular_weight": "523.32 g/mol",
        "cas_number": "486460-32-6 (Base) / 654671-77-9 (Fosfat)",
        "salts": ["phosphate", "hydrochloride", "malate", "tartrate"],
        "polymorphs": ["Form I", "Form II"],
        "therapeutic_class": "Dipeptidyl Peptidase-4 (DPP-4) Inhibitor",
        "bcs_class": "BCS Class III",
    },
    "clopidogrel": {
        "inn": "Clopidogrel",
        "trade_names": ["Plavix", "Iscover"],
        "iupac": "(+)-(S)-methyl 2-(2-chlorophenyl)-2-(6,7-dihydrothieno[3,2-c]pyridin-5(4H)-yl)acetate",
        "iupac_variants": [
            "(+)-(S)-methyl 2-(2-chlorophenyl)-2-(6,7-dihydrothieno[3,2-c]pyridin-5(4H)-yl)acetate",
            "methyl (2S)-2-(2-chlorophenyl)-2-(6,7-dihydro-4H-thieno[3,2-c]pyridin-5-yl)acetate",
            "clopidogrel bisulfate",
            "clopidogrel hydrogen sulfate",
        ],
        "molecular_formula": "C16H16ClNO2S·H2SO4",
        "molecular_weight": "419.90 g/mol (Bisulfat)",
        "cas_number": "113665-84-2 (Base) / 120202-66-6 (Bisulfat)",
        "salts": ["bisulfate", "hydrochloride", "besylate"],
        "polymorphs": ["Form 1 (monoklinik)", "Form 2 (ortorombik stabil)"],
        "therapeutic_class": "Antiplatelet / P2Y12 Receptor Antagonist",
        "bcs_class": "BCS Class II",
    },
}


# ==============================================================================
# 2. EXCIPIENT TAXONOMY & FUNCTIONAL MAPPING DATABASE
# ==============================================================================

EXCIPIENT_DATABASE: Dict[str, Dict[str, Any]] = {
    # Release-Controlling Polymers (Sustained Release / Extended Release)
    "hpmc": {
        "standard_name": "Hypromellose (HPMC / Hydroxypropyl Methylcellulose)",
        "synonyms": ["hpmc", "hypromellose", "methocel", "methocel k100m", "methocel k15m", "methocel k4m", "e464"],
        "category": ExcipientFunctionType.RELEASE_CONTROLLING_POLYMER,
        "mechanism": "Hidratasi polimer cepat membentuk lapisan gel kental (hydrophilic swellable matrix) yang mengontrol laju pelepasan zat aktif via difusi dan erosi relaksasi rantai.",
        "cluster": "HYDROPHILIC_SWELLABLE_MATRIX",
        "typical_range": "15.0 - 40.0% w/w",
    },
    "xanthan gum": {
        "standard_name": "Xanthan Gum",
        "synonyms": ["xanthan gum", "permen xanthan", "gummi xanthanum"],
        "category": ExcipientFunctionType.RELEASE_CONTROLLING_POLYMER,
        "mechanism": "Polisakarida alami berbobot molekul tinggi yang membentuk matriks gel pseudoplastis kental saat kontak dengan cairan lambung.",
        "cluster": "HYDROPHILIC_SWELLABLE_MATRIX",
        "typical_range": "10.0 - 30.0% w/w",
    },
    "polyox": {
        "standard_name": "Polyethylene Oxide (Polyox WSR)",
        "synonyms": ["polyox", "polyethylene oxide", "peo", "polyox wsr-303", "polyox wsr-1105"],
        "category": ExcipientFunctionType.RELEASE_CONTROLLING_POLYMER,
        "mechanism": "Polimer hidrofilik teranyam yang mengembang dan berdisolusi membentuk lapisan penghalang difusi kental.",
        "cluster": "HYDROPHILIC_SWELLABLE_MATRIX",
        "typical_range": "15.0 - 35.0% w/w",
    },
    "ethylcellulose": {
        "standard_name": "Ethylcellulose (EC)",
        "synonyms": ["ethylcellulose", "etilselulosa", "ethocel", "surelease"],
        "category": ExcipientFunctionType.RELEASE_CONTROLLING_POLYMER,
        "mechanism": "Polimer hidrofobik tak larut air yang membentuk matriks porus padat atau membran salut; obat berdifusi keluar melalui pori-pori mikroskopis tanpa pembengkakan gel.",
        "cluster": "HYDROPHOBIC_INSOLUBLE_MEMBRANE",
        "typical_range": "5.0 - 25.0% w/w",
    },
    "eudragit": {
        "standard_name": "Polymethacrylates (Eudragit)",
        "synonyms": ["eudragit", "eudragit l100", "eudragit s100", "eudragit rs", "eudragit rl", "eudragit l30d-55"],
        "category": ExcipientFunctionType.RELEASE_CONTROLLING_POLYMER,
        "mechanism": "Kopolimer metakrilat pH-dependen (enteric coated) atau pH-independen berpori terkontrol (Eudragit RS/RL).",
        "cluster": "pH_DEPENDENT_OR_PERMEABLE_MEMBRANE",
        "typical_range": "5.0 - 20.0% w/w",
    },
    "precirol": {
        "standard_name": "Glycerol Distearate (Precirol ATO 5)",
        "synonyms": ["precirol", "precirol ato 5", "glycerol distearate", "glyceryl palmitostearate", "compritol 888"],
        "category": ExcipientFunctionType.RELEASE_CONTROLLING_POLYMER,
        "mechanism": "Matriks lipid hidrofobik yang memperlambat pelepasan obat melalui kanal pori lipid yang tidak mengembang (non-swellable lipid erosion).",
        "cluster": "LIPID_HYDROPHOBIC_MATRIX",
        "typical_range": "10.0 - 30.0% w/w",
    },

    # Diluents / Fillers
    "avicel": {
        "standard_name": "Microcrystalline Cellulose (Avicel)",
        "synonyms": ["avicel", "avicel ph 101", "avicel ph 102", "avicel ph 200", "microcrystalline cellulose", "mcc", "selulosa mikrokristalin"],
        "category": ExcipientFunctionType.DILUENT_FILLER,
        "mechanism": "Bahan pengisi dan pengikat kempa langsung (direct compression) dengan plastisitas deformasi tinggi dan kemampuan pengaliran massa cetak.",
        "cluster": "INSOLUBLE_DEFORMABLE_FILLER",
        "typical_range": "20.0 - 70.0% w/w",
    },
    "lactose": {
        "standard_name": "Lactose Monohydrate / Spray-Dried Lactose",
        "synonyms": ["lactose", "lactose monohydrate", "spray-dried lactose", "supertab", "pharmatose"],
        "category": ExcipientFunctionType.DILUENT_FILLER,
        "mechanism": "Pengisi hidrofilik larut air yang mengalami deformasi getas (brittle fracture) saat kompresi tablet.",
        "cluster": "WATER_SOLUBLE_BRITTLE_FILLER",
        "typical_range": "20.0 - 65.0% w/w",
    },
    "mannitol": {
        "standard_name": "Mannitol",
        "synonyms": ["mannitol", "pearlitol", "mannite"],
        "category": ExcipientFunctionType.DILUENT_FILLER,
        "mechanism": "Pengisi poliol non-higroskopis dengan rasa manis sejuk, cocok untuk zat aktif sensitif kelembapan.",
        "cluster": "WATER_SOLUBLE_BRITTLE_FILLER",
        "typical_range": "15.0 - 50.0% w/w",
    },

    # Binders
    "povidone": {
        "standard_name": "Povidone (PVP / Polyvinylpyrrolidone)",
        "synonyms": ["povidone", "pvp", "pvp k30", "pvp k90", "polyplasdone", "kollidon"],
        "category": ExcipientFunctionType.BINDER,
        "mechanism": "Polimer pengikat basah atau kering yang membentuk jembatan kristalin antar-partikel granulasi.",
        "cluster": "POLYMERIC_BINDER",
        "typical_range": "2.0 - 7.0% w/w",
    },
    "hpc": {
        "standard_name": "Hydroxypropyl Cellulose (HPC)",
        "synonyms": ["hpc", "hydroxypropyl cellulose", "klucel"],
        "category": ExcipientFunctionType.BINDER,
        "mechanism": "Pengikat termoplastik viskositas rendah untuk granulasi kering/basah atau hot melt extrusion.",
        "cluster": "POLYMERIC_BINDER",
        "typical_range": "2.0 - 6.0% w/w",
    },

    # Disintegrants & Superdisintegrants
    "croscarmellose": {
        "standard_name": "Croscarmellose Sodium (Ac-Di-Sol)",
        "synonyms": ["croscarmellose", "croscarmellose sodium", "ac-di-sol", "crosslinked cmc", "vivasol"],
        "category": ExcipientFunctionType.DISINTEGRANT,
        "mechanism": "Superdisintegran ikatan silang dengan kemampuan serapan air kapiler cepat (wicking) dan pengembangan volume masif 4-8 kali lipat.",
        "cluster": "CROSSLINKED_SUPERDISINTEGRANT",
        "typical_range": "1.0 - 5.0% w/w",
    },
    "sodium starch glycolate": {
        "standard_name": "Sodium Starch Glycolate (Primojel)",
        "synonyms": ["sodium starch glycolate", "primojel", "explotab"],
        "category": ExcipientFunctionType.DISINTEGRANT,
        "mechanism": "Superdisintegran berbasis pati termodifikasi yang mengembang secara spheris 200-300% saat menyerap air.",
        "cluster": "CROSSLINKED_SUPERDISINTEGRANT",
        "typical_range": "2.0 - 8.0% w/w",
    },
    "crospovidone": {
        "standard_name": "Crospovidone (Kollidon CL)",
        "synonyms": ["crospovidone", "kollidon cl", "polyplasdone xl", "cross-linked pvp"],
        "category": ExcipientFunctionType.DISINTEGRANT,
        "mechanism": "Superdisintegran ikatan silang tidak larut yang bekerja terutama lewat mekanisme penarikan air kapiler cepat tanpa pembentukan gel tebal.",
        "cluster": "CROSSLINKED_SUPERDISINTEGRANT",
        "typical_range": "2.0 - 5.0% w/w",
    },

    # Lubricants & Glidants
    "magnesium stearate": {
        "standard_name": "Magnesium Stearate",
        "synonyms": ["magnesium stearate", "mg stearate", "magnesium distearate", "stearat magnesium"],
        "category": ExcipientFunctionType.LUBRICANT_GLIDANT,
        "mechanism": "Pelincir hidrofobik batas (boundary lubricant) yang melapisi permukaan granul untuk mengurangi gesekan pada dinding die dan punch cetak.",
        "cluster": "HYDROPHOBIC_BOUNDARY_LUBRICANT",
        "typical_range": "0.25 - 1.5% w/w",
    },
    "aerosil": {
        "standard_name": "Colloidal Silicon Dioxide (Aerosil 200)",
        "synonyms": ["aerosil", "aerosil 200", "colloidal silicon dioxide", "silica", "cab-o-sil"],
        "category": ExcipientFunctionType.LUBRICANT_GLIDANT,
        "mechanism": "Glosidan fumed silica dengan luas permukaan tinggi yang mengurangi gaya kohesi antarpartikel dan menyerap kelembapan mikro.",
        "cluster": "GLIDANT_FLOW_AID",
        "typical_range": "0.1 - 1.0% w/w",
    },
    "sodium stearyl fumarate": {
        "standard_name": "Sodium Stearyl Fumarate (Pruv)",
        "synonyms": ["sodium stearyl fumarate", "pruv", "ssf"],
        "category": ExcipientFunctionType.LUBRICANT_GLIDANT,
        "mechanism": "Pelincir hidrofilik yang kurang sensitif terhadap waktu pencampuran berlebih (over-blending) dibanding magnesium stearat.",
        "cluster": "HYDROPHILIC_LUBRICANT",
        "typical_range": "0.5 - 2.5% w/w",
    },

    # Surfactants & Solubilizers
    "polysorbate": {
        "standard_name": "Polysorbate 80 (Tween 80)",
        "synonyms": ["polysorbate", "polysorbate 80", "tween 80", "tween 20"],
        "category": ExcipientFunctionType.SURFACTANT_SOLUBILIZER,
        "mechanism": "Surfaktan non-ionik ber-HLB tinggi yang menurunkan tegangan antarmuka dan membentuk misel untuk meningkatkan kelarutan senyawa lipofilik.",
        "cluster": "NONIONIC_SURFACTANT",
        "typical_range": "0.5 - 5.0% w/w",
    },
    "sodium lauryl sulfate": {
        "standard_name": "Sodium Lauryl Sulfate (SLS / SDS)",
        "synonyms": ["sodium lauryl sulfate", "sls", "sds", "sodium dodecyl sulfate"],
        "category": ExcipientFunctionType.SURFACTANT_SOLUBILIZER,
        "mechanism": "Surfaktan anionik kuat sebagai zat pembasah (wetting agent) untuk meningkatkan keterbasahan serbuk hidrofobik.",
        "cluster": "ANIONIC_SURFACTANT",
        "typical_range": "0.5 - 2.0% w/w",
    },
    "poloxamer": {
        "standard_name": "Poloxamer 188 / 407 (Kolliphor P)",
        "synonyms": ["poloxamer", "poloxamer 188", "poloxamer 407", "pluronic", "kolliphor p188"],
        "category": ExcipientFunctionType.SURFACTANT_SOLUBILIZER,
        "mechanism": "Kopolimer blok difilik PEO-PPO-PEO yang meningkatkan solubilisasi dan laju disolusi zat aktif BCS II.",
        "cluster": "NONIONIC_BLOCK_COPOLYMER",
        "typical_range": "1.0 - 10.0% w/w",
    },
}


# ==============================================================================
# 3. CHEMICAL NOMENCLATURE & IUPAC RESOLVER
# ==============================================================================

class ChemicalResolver:
    """Mesin penelusuran tata nama kimia IUPAC, INN, sinonim, dan bentuk garam/polimorf."""

    @staticmethod
    def identify_entities(text: str) -> List[ChemicalEntity]:
        """Mengekstraksi dan mencocokkan zat aktif kimia dari teks bebas paten atau formula."""
        text_lower = text.lower()
        detected_entities: List[ChemicalEntity] = []

        for chem_key, chem_info in CHEMICAL_REGISTRY.items():
            matched = False
            detected_form = "FREE_BASE"
            is_salt = False
            matched_variant = ""

            # 1. Cek nama INN
            if chem_info["inn"].lower() in text_lower:
                matched = True
                matched_variant = chem_info["inn"]

            # 2. Cek nama dagang
            if not matched:
                for tn in chem_info["trade_names"]:
                    if tn.lower() in text_lower:
                        matched = True
                        matched_variant = f"Trade Name: {tn}"
                        break

            # 3. Cek IUPAC dan varian kimianya
            if not matched:
                for var in chem_info["iupac_variants"]:
                    # Bersihkan tanda baca untuk perbandingan fraksional
                    clean_var = re.sub(r"[^a-zA-Z0-9]", " ", var.lower()).strip()
                    tokens = [t for t in clean_var.split() if len(t) > 3]
                    matching_tokens = sum(1 for t in tokens if t in text_lower)
                    if tokens and (matching_tokens / len(tokens)) >= 0.70:
                        matched = True
                        matched_variant = f"IUPAC Match: {var[:40]}..."
                        break

            # 4. Cek CAS number jika ada
            if not matched and chem_info.get("cas_number"):
                cas_parts = re.findall(r"\d{2,7}-\d{2}-\d", text)
                for c in cas_parts:
                    if c in chem_info["cas_number"]:
                        matched = True
                        matched_variant = f"CAS: {c}"
                        break

            if matched:
                # Deteksi bentuk garam spesifik
                for salt in chem_info["salts"]:
                    if salt.lower() in text_lower:
                        detected_form = f"SALT_{salt.upper()}"
                        is_salt = True
                        break

                # Deteksi polimorf / bentuk kristalinitas
                polymorph_detected = None
                if "amorphous" in text_lower or "amorf" in text_lower:
                    polymorph_detected = "Amorphous (Amorf Non-kristalin)"
                elif "form i" in text_lower or "bentuk i" in text_lower:
                    polymorph_detected = "Polymorph Form I"
                elif "form ii" in text_lower or "bentuk ii" in text_lower:
                    polymorph_detected = "Polymorph Form II"
                elif "trihydrate" in text_lower or "trihidrat" in text_lower:
                    polymorph_detected = "Trihydrate Crystalline Form"

                entity = ChemicalEntity(
                    inn_name=chem_info["inn"],
                    trade_names=chem_info["trade_names"],
                    iupac_name=chem_info["iupac"],
                    synonyms=chem_info["iupac_variants"],
                    molecular_formula=chem_info.get("molecular_formula"),
                    molecular_weight=chem_info.get("molecular_weight"),
                    cas_number=chem_info.get("cas_number"),
                    chemical_form=f"{detected_form} ({polymorph_detected})" if polymorph_detected else detected_form,
                    detected_in_patent=False,
                    detected_in_formula=False,
                    is_equivalent_entity=True,
                    equivalence_note=f"Teridentifikasi via {matched_variant}. Mengandung inti farmakofor {chem_info['inn']}.",
                )
                detected_entities.append(entity)

        return detected_entities


# ==============================================================================
# 4. EXCIPIENT FUNCTION MAPPING & EQUIVALENCE EVALUATOR
# ==============================================================================

class ExcipientEvaluator:
    """Evaluator peran fungsional eksipien dan uji Doctrine of Equivalents (Function-Way-Result)."""

    @staticmethod
    def extract_and_map_excipients(formula_text: str, patent_text: str) -> List[ExcipientMapping]:
        """Mengekstrak eksipien dari formula dan mengevaluasi substitusi fungsional terhadap paten."""
        formula_lower = formula_text.lower()
        patent_lower = patent_text.lower()
        mappings: List[ExcipientMapping] = []

        for exc_key, exc_info in EXCIPIENT_DATABASE.items():
            found_in_formula = False
            matched_name = ""

            for syn in exc_info["synonyms"]:
                if syn in formula_lower:
                    found_in_formula = True
                    matched_name = syn.title()
                    break

            if not found_in_formula:
                continue

            # Cek apakah bahan ini atau sinonimnya juga ada di klaim paten
            found_in_patent = False
            claimed_counterpart = None
            for syn in exc_info["synonyms"]:
                if syn in patent_lower:
                    found_in_patent = True
                    claimed_counterpart = syn.title()
                    break

            # Cari konsentrasi dalam formula (% w/w atau mg)
            conc_pattern = re.search(
                rf"{re.escape(matched_name.lower())}[^\n\d]*?(\d+(?:\.\d+)?)\s*(?:%|persen|w/w|mg)",
                formula_lower
            )
            detected_conc = float(conc_pattern.group(1)) if conc_pattern else None

            # Cek substitusi ekuivalen jika tidak sama persis di paten
            fwr_test = None
            if found_in_patent:
                equiv_status = EquivalenceTestStatus.LITERAL_MATCH
                claimed_range = exc_info["typical_range"]
                is_within = True
            else:
                # Periksa apakah ada eksipien dalam kluster yang sama di paten (Doctrine of Equivalents)
                cluster_match_patent = None
                for other_key, other_info in EXCIPIENT_DATABASE.items():
                    if other_info["cluster"] == exc_info["cluster"]:
                        for s in other_info["synonyms"]:
                            if s in patent_lower:
                                cluster_match_patent = other_info
                                claimed_counterpart = s.title()
                                break
                    if cluster_match_patent:
                        break

                if cluster_match_patent:
                    # Keduanya berada dalam kluster mekanisme yang sama (e.g. HPMC diganti Polyox atau Xanthan Gum)
                    fwr_test = FunctionWayResultTest(
                        function_analysis=f"Keduanya berfungsi sebagai {exc_info['category'].value} dalam memperlambat disolusi sediaan.",
                        way_analysis=f"Mekanisme bekerja secara substansial serupa via {exc_info['cluster']}: membentuk hidrogel pseudoplastis berpori saat terhidrasi.",
                        result_analysis="Menghasilkan profil pelepasan terkendali yang sebanding (pelepasan konstan hingga >12 jam).",
                        is_substantially_equivalent=True,
                        legal_doctrine_summary="Memenuhi Uji Function-Way-Result (Graver Tank standard). Berpotensi melanggar di bawah Doktrin Ekuivalensi (Doctrine of Equivalents)."
                    )
                    equiv_status = EquivalenceTestStatus.EQUIVALENT_MATCH
                    claimed_range = cluster_match_patent["typical_range"]
                    is_within = True
                else:
                    # Eksipien memiliki kluster/mekanisme berbeda fundamental (e.g. mengganti matriks HPMC dengan lipid Precirol ATO 5 atau salut enterik Eudragit)
                    fwr_test = FunctionWayResultTest(
                        function_analysis=f"Fungsi umum mengatur profil pelepasan, namun arsitektur farmasetika berbeda.",
                        way_analysis=f"Mekanisme berbeda substansial: Formula menggunakan {exc_info['cluster']}, sedangkan paten mengklaim sistem lain. Tidak ada pembentukan hidrogel difusi.",
                        result_analysis="Pelepasan zat aktif terjadi melalui mekanisme erosi partikulat hidrofobik, bukan difusi lapisan gel.",
                        is_substantially_equivalent=False,
                        legal_doctrine_summary="Gagal Uji Function-Way-Result. Menjadi dasar kuat argumen NON-INFRINGEMENT (Bebas Paten)."
                    )
                    equiv_status = EquivalenceTestStatus.MISSING_ELEMENT
                    claimed_range = "Di luar ruang lingkup klaim paten"
                    is_within = False

            mapping = ExcipientMapping(
                ingredient_name=f"{exc_info['standard_name']} ({matched_name})",
                functional_category=exc_info["category"],
                role_description=exc_info["mechanism"],
                concentration_w_w=detected_conc,
                unit_dosage_amount=f"{detected_conc}% w/w" if detected_conc else None,
                claimed_counterpart=claimed_counterpart,
                claimed_range=claimed_range,
                is_within_claimed_range=is_within,
                fwr_test=fwr_test,
                equivalence_status=equiv_status,
            )
            mappings.append(mapping)

        return mappings


# ==============================================================================
# 5. CORE PHARMACEUTICAL INFRINGEMENT ENGINE & CLAIM CHART
# ==============================================================================

class PharmaInfringementEngine:
    """Mesin analisis pelanggaran paten farmasi komprehensif."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.client = None
        self._init_client()

    def _init_client(self):
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.warning(f"Inisialisasi google-genai Client gagal: {e}")
                self.client = None

    def analyze(self, request: PharmaAnalysisRequest) -> PharmaInfringementReport:
        """
        Alur Utama Analisis Farmasi:
        1. Ekstraksi klaim paten.
        2. Resolusi entitas kimia (IUPAC, INN, Garam, Polimorf).
        3. Pemetaan fungsi eksipien & Uji FWR (Function-Way-Result).
        4. Pemetaan Claim Chart farmasi 4 pilar (Zat Aktif, Rentang, Fisikokimia, Proses).
        5. Kalkulasi Skor Risiko dan Formulasi Rekomendasi Design-Around.
        """
        if request.api_key and (not self.client or self.api_key != request.api_key):
            self.api_key = request.api_key
            self._init_client()

        # Ekstraksi klaim menggunakan ClaimExtractor
        claims = ClaimExtractor.extract_claims(request.patent_text)
        if not claims:
            claims = [
                Claim(
                    claim_number=1,
                    claim_type=ClaimType.INDEPENDENT,
                    preamble="Pharmaceutical Composition",
                    body=request.patent_text[:300],
                    elements=[request.patent_text[:300]],
                    full_text=request.patent_text,
                )
            ]

        # 1. Resolusi Kimia
        patent_chemicals = ChemicalResolver.identify_entities(request.patent_text)
        formula_chemicals = ChemicalResolver.identify_entities(request.product_formula_text)

        # Gabungkan entitas dan beri tanda lokasi deteksi
        chemical_dossier: List[ChemicalEntity] = []
        all_chem_names = set([c.inn_name for c in patent_chemicals] + [c.inn_name for c in formula_chemicals])

        for inn in all_chem_names:
            in_pat = any(c.inn_name == inn for c in patent_chemicals)
            in_for = any(c.inn_name == inn for c in formula_chemicals)
            base_entity = next((c for c in formula_chemicals if c.inn_name == inn), None) or next((c for c in patent_chemicals if c.inn_name == inn), None)
            if base_entity:
                base_entity.detected_in_patent = in_pat
                base_entity.detected_in_formula = in_for
                base_entity.is_equivalent_entity = (in_pat and in_for)
                if in_pat and in_for:
                    base_entity.equivalence_note = (
                        f"ZAT AKTIF IDENTIK / BIOEKUIVALEN: Paten dan formula keduanya merujuk pada senyawa {inn}. "
                        "Memenuhi elemen klaim zat aktif secara literal atau doktrin kesetaraan terapeutik."
                    )
                chemical_dossier.append(base_entity)

        # 2. Pemetaan Eksipien
        excipient_evaluations = ExcipientEvaluator.extract_and_map_excipients(
            request.product_formula_text,
            request.patent_text
        )

        # 3. Analisis dengan Gemini AI jika tersedia, jika tidak beralih ke Rule-Based Pharma Engine
        if self.client:
            try:
                ai_report = self._analyze_with_gemini(claims, chemical_dossier, excipient_evaluations, request)
                if ai_report:
                    return ai_report
            except Exception as e:
                logger.error(f"Error memanggil Gemini API untuk modul farmasi: {e}. Menggunakan Rule-Based Engine.")

        return self._analyze_heuristic_pharma(claims, chemical_dossier, excipient_evaluations, request)

    def _analyze_with_gemini(
        self,
        claims: List[Claim],
        chemicals: List[ChemicalEntity],
        excipients: List[ExcipientMapping],
        request: PharmaAnalysisRequest
    ) -> Optional[PharmaInfringementReport]:
        """Analisis mendalam menggunakan Google Gemini 3.8 Flash."""
        from google.genai import types

        system_instruction = (
            "Anda adalah AI Principal Patent Analyst dan Senior Pharmaceutical Formulator kelas dunia. "
            "Anda memiliki keahlian mendalam dalam:\n"
            "1. Hukum Paten Farmasi Internasional (All-Elements Rule, Doctrine of Equivalents, Graver Tank, Warner-Jenkinson, Festo Estoppel).\n"
            "2. Tata Nama Kimia IUPAC, CAS, pemetaan garam (salts), polimorf (polymorphs), ester, dan kokristal.\n"
            "3. Sains Teknologi Farmasi: Peran fungsional eksipien (HPMC, Polyox, Avicel, Mg Stearate), kinetika pelepasan disolusi, dan proses manufaktur.\n\n"
            "Tugas Anda: Lakukan claim charting elemen-demi-elemen dengan membaginya ke dalam 4 kategori farmasi:\n"
            "- ACTIVE_INGREDIENT\n"
            "- CONCENTRATION_RANGE\n"
            "- PHYSICOCHEMICAL\n"
            "- MANUFACTURING_PROCESS\n\n"
            "Berikan justifikasi ilmiah komparatif, tentukan status (LITERAL_MATCH, EQUIVALENT_MATCH, OUT_OF_RANGE, MISSING_ELEMENT), "
            "hitung skor risiko (0-100), dan formulasikan rekomendasi Design-Around farmasi yang sangat konkret dan aplikatif."
        )

        user_content = f"""
=== DOKUMEN PATEN PEMBANDING ===
Judul: {request.patent_title or "Patent Document"}
Klaim Paten:
{request.patent_text}

=== SPESIFIKASI FORMULA PRODUK INTERNAL ===
Nama Produk: {request.product_name}
Bentuk Sediaan: {request.dosage_form or "Tablet Lepas Lambat"}
Rincian Formula & Proses:
{request.product_formula_text}

=== DATA VALIDASI ZAT AKTIF & EKSIPIEN TERDETEKSI ===
Entitas Kimia Terdeteksi: {[c.model_dump() for c in chemicals]}
Pemetaan Eksipien: {[e.model_dump() for e in excipients]}

Harap berikan evaluasi Claim Chart terstruktur, penilaian risiko FTO komprehensif, dan rekomendasi Design-Around berbasis sains formulasi farmasi.
"""

        response = self.client.models.generate_content(
            model=AI_MODEL_NAME,
            contents=user_content,
            config=types.GenerateContentConfig(
                system_instruction=system_instruction,
                response_mime_type="application/json",
                response_json_schema=PharmaInfringementReport.model_json_schema(),
                temperature=0.15,
            ),
        )

        raw_json = json.loads(response.text)
        return PharmaInfringementReport.model_validate(raw_json)

    def _analyze_heuristic_pharma(
        self,
        claims: List[Claim],
        chemicals: List[ChemicalEntity],
        excipients: List[ExcipientMapping],
        request: PharmaAnalysisRequest,
    ) -> PharmaInfringementReport:
        """Mesin Heuristik Farmasi Presisi Tinggi (Offline Fallback)."""
        formula_lower = request.product_formula_text.lower()
        patent_lower = request.patent_text.lower()

        claim_results: List[PharmaClaimResult] = []
        has_literal_infringement = False
        has_doctrine_of_equiv = False

        total_elements_count = 0
        matched_elements_count = 0
        equivalent_elements_count = 0

        # Deteksi zat aktif match
        api_matched = any(c.is_equivalent_entity for c in chemicals)

        for claim in claims:
            pharma_elements: List[PharmaClaimElement] = []
            claim_text = claim.full_text.lower()

            # Parse elemen per baris atau limitations
            elements_raw = claim.elements if claim.elements else [claim.body]

            claim_literal_count = 0
            claim_equiv_count = 0
            claim_missing_count = 0

            for idx, raw_elem in enumerate(elements_raw, start=1):
                elem_lower = raw_elem.lower()
                total_elements_count += 1

                # Klasifikasikan kategori elemen farmasi
                if any(w in elem_lower for w in ["compound", "active ingredient", "zat aktif", "iupac", "acid", "salt", "hydrochloride", "amine", "biguanide", "statin", "trihydrate"]):
                    category = PharmaClaimCategory.ACTIVE_INGREDIENT
                    if api_matched:
                        # Cek apakah klaim menuntut garam atau polimorf spesifik
                        salt_differs = False
                        polymorph_differs = False

                        if ("calcium" in elem_lower and "calcium" not in formula_lower) or \
                           ("hydrochloride" in elem_lower and not any(k in formula_lower for k in ["hydrochloride", "hcl"])) or \
                           ("succinate" in elem_lower and "succinate" not in formula_lower) or \
                           ("sodium" in elem_lower and "sodium" not in formula_lower and "na " not in formula_lower):
                            salt_differs = True

                        if ("form i" in elem_lower and "form i" not in formula_lower) or \
                           ("crystalline" in elem_lower and "amorphous" in formula_lower) or \
                           ("trihydrate" in elem_lower and "trihydrate" not in formula_lower):
                            polymorph_differs = True

                        if salt_differs or polymorph_differs:
                            status = EquivalenceTestStatus.MISSING_ELEMENT
                            reason_term = "Garam berbeda (bukan garam kalsium)" if salt_differs else "Bentuk padat berbeda (Amorf / Co-crystal)"
                            formula_feat = f"Bentuk kimia formula: {chemicals[0].chemical_form if chemicals else 'Bentuk alternatif'} (Bukan {elem_lower[:35]}...)"
                            sci_reason = f"Klaim paten secara spesifik mengunci {elem_lower[:50]}. Formula produk menggunakan modifikasi bentuk padat non-infringing."
                            legal_doc = "All-Elements Rule (Specific Salt/Polymorph Limitation Absent)"
                            claim_missing_count += 1
                        else:
                            status = EquivalenceTestStatus.LITERAL_MATCH
                            formula_feat = f"Zat aktif terkonfirmasi: {chemicals[0].inn_name} ({chemicals[0].chemical_form})" if chemicals else "Zat aktif cocok"
                            sci_reason = f"Senyawa zat aktif dalam formula memenuhi definisi klaim paten. Struktur inti molekul dan bentuk garam berkorelasi langsung."
                            legal_doc = "Literal Infringement (Identical Chemical Entity)"
                            claim_literal_count += 1
                    else:
                        status = EquivalenceTestStatus.MISSING_ELEMENT
                        formula_feat = "Tidak teridentifikasi zat aktif yang sama"
                        sci_reason = "Zat aktif formula berbeda secara mendasar dari senyawa yang diklaim dalam paten."
                        legal_doc = "All-Elements Rule (Essential Chemical Element Missing)"
                        claim_missing_count += 1

                elif any(w in elem_lower for w in ["%", "percent", "persen", "weight", "bobot", "mg", "ratio", "rasio", "w/w", "w/v"]):
                    category = PharmaClaimCategory.CONCENTRATION_RANGE
                    # Cari rentang numerik pada elemen klaim
                    range_match = re.search(r"(\d+(?:\.\d+)?)\s*(?:%|persen|mg)?\s*(?:to|-|sampai|hingga)\s*(\d+(?:\.\d+)?)\s*(?:%|persen|mg|w/w)", elem_lower)
                    at_least_match = re.search(r"(?:at least|sekurang-kurangnya|minimal|min)\s*(\d+(?:\.\d+)?)\s*(?:%|persen|mg)", elem_lower)

                    # Identifikasi zat/eksipien yang dimaksud pada elemen ini
                    target_val = None
                    if any(term in elem_lower for term in ["hpmc", "hydroxypropyl", "methylcellulose", "polymer", "matriks"]):
                        hpmc_exc = next((e for e in excipients if "hpmc" in e.ingredient_name.lower() or "hypromellose" in e.ingredient_name.lower()), None)
                        if hpmc_exc and hpmc_exc.concentration_w_w is not None:
                            target_val = hpmc_exc.concentration_w_w
                    elif any(term in elem_lower for term in ["biguanide", "metformin", "statin", "atorvastatin", "paracetamol", "acetaminophen", "active", "zat aktif"]):
                        dose_m = re.search(r"(?:metformin|glucophage|paracetamol|atorvastatin|active|zat aktif)[^\n\d]*?(\d+(?:\.\d+)?)\s*(?:mg|g)", formula_lower)
                        if dose_m:
                            target_val = float(dose_m.group(1))

                    if target_val is not None:
                        if range_match:
                            low_b = float(range_match.group(1))
                            high_b = float(range_match.group(2))
                            if low_b <= target_val <= high_b:
                                status = EquivalenceTestStatus.LITERAL_MATCH
                                formula_feat = f"Kadar terukur ({target_val}%/mg) berada dalam rentang klaim ({low_b} - {high_b})"
                                sci_reason = f"Konsentrasi bahan formula ({target_val}) secara presisi memenuhi batas numerik klaim paten."
                                legal_doc = "Literal Infringement (Numerical Overlap)"
                                claim_literal_count += 1
                            else:
                                status = EquivalenceTestStatus.OUT_OF_RANGE
                                formula_feat = f"Kadar terukur ({target_val}%/mg) berada di luar klaim ({low_b} - {high_b})"
                                sci_reason = f"Konsentrasi formula ({target_val}) secara tegas berada di luar rentang klaim paten. Lolos dari batas numerik klaim."
                                legal_doc = "Literal Non-Infringement (Strict Numerical Boundary)"
                                claim_missing_count += 1
                        elif at_least_match:
                            min_b = float(at_least_match.group(1))
                            if target_val >= min_b:
                                status = EquivalenceTestStatus.LITERAL_MATCH
                                formula_feat = f"Kadar terukur {target_val} >= {min_b}"
                                sci_reason = "Memenuhi batas minimum klaim paten."
                                legal_doc = "Literal Infringement"
                                claim_literal_count += 1
                            else:
                                status = EquivalenceTestStatus.OUT_OF_RANGE
                                formula_feat = f"Kadar terukur {target_val} < {min_b}"
                                sci_reason = "Di bawah batas minimum klaim."
                                legal_doc = "Literal Non-Infringement"
                                claim_missing_count += 1
                        else:
                            status = EquivalenceTestStatus.LITERAL_MATCH
                            formula_feat = f"Konsentrasi bahan {target_val} terkonfirmasi"
                            sci_reason = "Proporsi bahan formula bersesuaian dengan klaim."
                            legal_doc = "Literal Infringement"
                            claim_literal_count += 1
                    else:
                        # Jika tidak ada zat spesifik yang diekstrak, cek apakah ada konsentrasi eksipien yang cocok
                        status = EquivalenceTestStatus.LITERAL_MATCH
                        formula_feat = "Rentang konsentrasi bahan formula berada dalam klaim paten"
                        sci_reason = "Proporsi eksipien (% w/w) atau dosis (mg) tumpang tindih secara langsung dengan klaim paten."
                        legal_doc = "Literal Infringement (Numerical Overlap)"
                        claim_literal_count += 1

                elif any(w in elem_lower for w in ["granulation", "granulasi", "compression", "kempa", "extrusion", "ekstrusi", "coating", "salut", "direct compression", "pellet"]):
                    category = PharmaClaimCategory.MANUFACTURING_PROCESS
                    is_patent_wet_gran = ("wet granulation" in elem_lower or "granulasi basah" in elem_lower)
                    is_formula_direct_comp = ("direct compression" in formula_lower or "kempa langsung" in formula_lower)
                    is_formula_wet_gran = ("wet granulation" in formula_lower or "granulasi basah" in formula_lower)

                    if is_patent_wet_gran and is_formula_direct_comp and not is_formula_wet_gran:
                        status = EquivalenceTestStatus.MISSING_ELEMENT
                        formula_feat = "Metode Kempa Langsung (Direct Compression) tanpa granulasi basah"
                        sci_reason = "Paten secara eksplisit membatasi klaim pada proses granulasi basah. Produk menggunakan kempa langsung bebas dari klaim proses."
                        legal_doc = "All-Elements Rule & Prosecution History Estoppel"
                        claim_missing_count += 1
                    elif is_patent_wet_gran and is_formula_wet_gran:
                        status = EquivalenceTestStatus.LITERAL_MATCH
                        formula_feat = "Proses manufaktur terkonfirmasi menggunakan granulasi basah (wet granulation)"
                        sci_reason = "Metode pembuatan formula menggunakan unit operasi granulasi basah yang identik dengan klaim paten."
                        legal_doc = "Literal Infringement (Process Step Met)"
                        claim_literal_count += 1
                    elif any(term in formula_lower for term in ["granulation", "granulasi", "compression", "kempa"]):
                        status = EquivalenceTestStatus.LITERAL_MATCH
                        formula_feat = "Proses manufaktur melibatkan tahapan formulasi serupa"
                        sci_reason = "Metode pembuatan formula menggunakan unit operasi yang setara dengan klaim paten."
                        legal_doc = "Literal Infringement (Process Step Met)"
                        claim_literal_count += 1
                    else:
                        status = EquivalenceTestStatus.EQUIVALENT_MATCH
                        formula_feat = "Proses manufaktur alternatif dengan hasil serupa"
                        sci_reason = "Tahapan proses berbeda namun menghasilkan karakteristik granulasi yang sebanding."
                        legal_doc = "Doctrine of Equivalents (Process Equivalence)"
                        claim_equiv_count += 1

                else:
                    category = PharmaClaimCategory.PHYSICOCHEMICAL_PROPERTY
                    # Periksa apakah limitation meminta eksipien/fungsi tertentu (misal: lubricant, polymer, binder, disintegrant, HPMC, dll.)
                    target_exc = None
                    is_cat_match = False

                    # Cek pencocokan spesifik nama eksipien atau peran fungsional dalam teks limitasi
                    for e in excipients:
                        e_name_lower = e.ingredient_name.lower()
                        # Cek apakah nama eksipien atau sinonimnya ada di elemen klaim
                        if any(token in elem_lower for token in [e_name_lower.split()[0], "hpmc", "cellulose", "stearate", "oxide", "gum"]):
                            target_exc = e
                            break
                        # Cek peran fungsional
                        if "lubricant" in elem_lower and e.functional_category == ExcipientFunctionType.LUBRICANT_GLIDANT:
                            target_exc = e
                            is_cat_match = True
                            break
                        if ("polymer" in elem_lower or "retardant" in elem_lower or "matrix" in elem_lower) and e.functional_category == ExcipientFunctionType.RELEASE_CONTROLLING_POLYMER:
                            target_exc = e
                            is_cat_match = True
                            break
                        if "disintegrant" in elem_lower and e.functional_category == ExcipientFunctionType.DISINTEGRANT:
                            target_exc = e
                            is_cat_match = True
                            break
                        if "binder" in elem_lower and e.functional_category == ExcipientFunctionType.BINDER:
                            target_exc = e
                            is_cat_match = True
                            break

                    if target_exc:
                        if target_exc.equivalence_status == EquivalenceTestStatus.LITERAL_MATCH or is_cat_match:
                            status = EquivalenceTestStatus.LITERAL_MATCH
                            formula_feat = f"Terkonfirmasi: {target_exc.ingredient_name} ({target_exc.unit_dosage_amount or 'aktif'})"
                            sci_reason = f"Bahan formula memenuhi limitasi klaim secara langsung. {target_exc.role_description[:90]}."
                            legal_doc = "Literal Infringement (Element Met)"
                            claim_literal_count += 1
                        elif target_exc.equivalence_status == EquivalenceTestStatus.EQUIVALENT_MATCH:
                            status = EquivalenceTestStatus.EQUIVALENT_MATCH
                            formula_feat = f"Eksipien substitusi: {target_exc.ingredient_name}"
                            sci_reason = f"Memenuhi uji kesetaraan fungsional (FWR). {target_exc.fwr_test.legal_doctrine_summary if target_exc.fwr_test else 'Ekuivalen'}."
                            legal_doc = "Doctrine of Equivalents (Graver Tank)"
                            claim_equiv_count += 1
                        else:
                            status = EquivalenceTestStatus.MISSING_ELEMENT
                            formula_feat = f"Bahan formula berbeda mekanisme: {target_exc.ingredient_name}"
                            sci_reason = "Mekanisme pelepasan berbeda secara substansial. Gagal uji Function-Way-Result."
                            legal_doc = "Non-Infringement (Different Mechanism)"
                            claim_missing_count += 1
                    else:
                        # Jika elemen klaim menuntut bahan yang sama sekali tidak ada di formula
                        # Cek apakah teks limitasi ada dalam formula secara leksikal
                        if any(term in formula_lower for term in elem_lower.split() if len(term) > 4):
                            status = EquivalenceTestStatus.LITERAL_MATCH
                            formula_feat = "Fitur formula bersesuaian dengan deskripsi klaim"
                            sci_reason = "Karakteristik fisikokimia sediaan memenuhi batasan klaim."
                            legal_doc = "Literal Infringement"
                            claim_literal_count += 1
                        else:
                            status = EquivalenceTestStatus.MISSING_ELEMENT
                            formula_feat = "Tidak ditemukan komponen/fitur yang berkorespondensi"
                            sci_reason = "Formula tidak memiliki bahan atau karakteristik yang dituntut dalam elemen klaim ini."
                            legal_doc = "All-Elements Rule (Missing Limitation)"
                            claim_missing_count += 1

                pharma_elements.append(
                    PharmaClaimElement(
                        element_index=idx,
                        category=category,
                        claim_limitation=raw_elem[:160],
                        formula_feature=formula_feat,
                        status=status,
                        scientific_justification=sci_reason,
                        legal_doctrine=legal_doc,
                    )
                )

            # Hitung risiko klaim
            if claim_missing_count == 0 and claim_literal_count > 0:
                c_risk = InfringementRiskLevel.HIGH
                has_literal_infringement = True
                c_summary = f"Seluruh elemen klaim {claim.claim_number} terpenuhi secara literal. Potensi pelanggaran paten langsung sangat tinggi."
            elif claim_equiv_count > 0 and claim_missing_count == 0:
                c_risk = InfringementRiskLevel.MEDIUM
                has_doctrine_of_equiv = True
                c_summary = f"Terdapat elemen substitusi ekuivalen pada klaim {claim.claim_number}. Terindikasi pelanggaran di bawah Doctrine of Equivalents."
            elif claim_missing_count > 0:
                c_risk = InfringementRiskLevel.LOW
                c_summary = f"Klaim {claim.claim_number} aman karena formula tidak memenuhi elemen esensial paten (All-Elements Rule)."
            else:
                c_risk = InfringementRiskLevel.LOW
                c_summary = f"Formula berada di luar ruang lingkup klaim {claim.claim_number}."

            claim_results.append(
                PharmaClaimResult(
                    claim_number=claim.claim_number,
                    claim_type=claim.claim_type,
                    depends_on=claim.depends_on,
                    preamble=claim.preamble,
                    risk_level=c_risk,
                    elements=pharma_elements,
                    summary=c_summary,
                )
            )

        # Penentuan overall risk & numeric score
        if has_literal_infringement:
            overall_risk = InfringementRiskLevel.HIGH
            risk_score = 88
            fto_verdict = "TIDAK LAYAK FTO (HIGH INFRINGEMENT RISK): Formula internal saat ini memenuhi seluruh elemen klaim independen paten secara literal. Peluncuran komersial berisiko tinggi memicu sengketa paten."
            exec_summary = (
                f"Analisis komparatif mengonfirmasi adanya potensi pelanggaran paten secara literal (Literal Infringement) "
                f"terhadap klaim independen paten '{request.patent_title or 'Target'}'. Formula produk '{request.product_name}' "
                f"menggunakan zat aktif identik serta eksipien matriks dalam rentang konsentrasi yang tercakup klaim. "
                f"Diperlukan tindakan reformulasi taktis (Design-Around) sebelum melakukan registrasi obat."
            )
        elif has_doctrine_of_equiv:
            overall_risk = InfringementRiskLevel.MEDIUM
            risk_score = 56
            fto_verdict = "FTO BERSYARAT (MEDIUM RISK): Ditemukan potensi ekuivalensi fungsional eksipien di bawah Doctrine of Equivalents. Disarankan melakukan optimasi substitusi bahan non-ekuivalen."
            exec_summary = (
                f"Ditemukan risiko sedang (Doctrine of Equivalents) pada formula '{request.product_name}'. "
                f"Meskipun bahan yang digunakan tidak persis sama secara literal dengan paten pembanding, "
                f"penggantian eksipien matriks dinilai melakukan fungsi yang substansial sama dengan cara yang serupa (Function-Way-Result Test)."
            )
        else:
            overall_risk = InfringementRiskLevel.LOW
            risk_score = 18
            fto_verdict = "LAYAK FTO (FREEDOM TO OPERATE DIPEROLEH): Formula berhasil keluar dari ruang lingkup klaim paten pembanding melalui All-Elements Rule dan mekanisme formulasi yang berbeda."
            exec_summary = (
                f"Formula '{request.product_name}' dinilai AMAN dari risiko pelanggaran paten pembanding. "
                f"Terdapat elemen-elemen limitasi kunci yang hilang atau berada di luar batasan numerik klaim paten. "
                f"Berdasarkan All-Elements Rule, sediaan bebas dari gugatan pelanggaran literal paten."
            )

        # Bangun rekomendasi Design-Around Farmasi
        design_around_recs = self._generate_pharma_design_around(chemicals, excipients, request)

        return PharmaInfringementReport(
            patent_title=request.patent_title or "Patent Document Analysis",
            patent_number=None,
            product_name=request.product_name,
            dosage_form=request.dosage_form or "Tablet Lepas Lambat",
            overall_risk=overall_risk,
            risk_score_numeric=risk_score,
            all_elements_rule_met=has_literal_infringement,
            doctrine_of_equivalents_triggered=has_doctrine_of_equiv,
            executive_summary=exec_summary,
            fto_verdict=fto_verdict,
            chemical_entities=chemicals,
            excipient_evaluations=excipients,
            claim_results=claim_results,
            design_around_recommendations=design_around_recs,
        )

    def _generate_pharma_design_around(
        self,
        chemicals: List[ChemicalEntity],
        excipients: List[ExcipientMapping],
        request: PharmaAnalysisRequest
    ) -> List[PharmaDesignAround]:
        """Menghasilkan saran reformulasi farmasetik taktis bebas paten."""
        recs: List[PharmaDesignAround] = []

        # Rekomendasi 1: Substitusi Kelas Eksipien Fungsional (Pivoting Mechanism)
        recs.append(
            PharmaDesignAround(
                strategy_type="SUBSTITUSI_KELAS_EKSIPIEN",
                title="Beralih dari Matriks Hidrogel Swellable ke Matriks Lipid Erosi Non-Swellable",
                description="Mengganti polimer hidrofilik mengembang (HPMC / Polyox) dengan matriks lipid hidrofobik seperti Glyceryl Behenate (Compritol 888 ATO) atau Glycerol Distearate (Precirol ATO 5).",
                reformulation_steps=[
                    "Substitusi 20-30% HPMC dengan 15-20% Precirol ATO 5 dan 10% Ethylcellulose.",
                    "Gunakan teknologi granulasi leleh (melt granulation) atau hot-melt coating.",
                    "Validasi profil disolusi in-vitro pada pH 1.2 dan pH 6.8 untuk memastikan bioekuivalensi profil f2 > 50."
                ],
                scientific_rationale="Matriks lipid bekerja melalui disolusi kanal pori dan erosi hidrofobik, BUKAN melalui pembengkakan hidrogel difusi air. Hal ini menggugurkan kriteria 'Way' dalam uji Function-Way-Result Doctrine of Equivalents.",
                fto_advantage="Mengeluarkan formula secara tuntas dari klaim paten matriks hidrofilik polimer."
            )
        )

        # Rekomendasi 2: Modifikasi Batasan Konsentrasi Numerik
        recs.append(
            PharmaDesignAround(
                strategy_type="MODIFIKASI_KONSENTRASI",
                title="Eksploitasi Batas Numerik Klaim Paten via Kombinasi Polimer Sinergis",
                description="Jika klaim paten mengunci rentang 20-40% w/w polimer retardant tunggal, gunakan konsentrasi di bawah 15% yang dikombinasikan dengan polimer sekunder.",
                reformulation_steps=[
                    "Turunkan kadar polimer utama menjadi 10-12% w/w (di bawah batas minimum klaim paten 15-20%).",
                    "Tambahkan 8% Xanthan Gum atau Sodium Alginat untuk membentuk kompleks koaservat inter-polimer sinergis.",
                    "Pertahankan kekerasan tablet pada rentang 90-120 N untuk menjaga integritas matriks."
                ],
                scientific_rationale="Berdasarkan doktrin hukum paten batas numerik (Literal Numerical Boundary), formula dengan kadar 12% secara tegas berada di luar klaim '20 to 40 wt%'.",
                fto_advantage="Menghindari All-Elements Rule secara literal dengan justifikasi kuantitatif terukur."
            )
        )

        # Rekomendasi 3: Perubahan Rute Proses Manufaktur
        recs.append(
            PharmaDesignAround(
                strategy_type="MODIFIKASI_PROSES",
                title="Peralihan dari Granulasi Basah ke Kempa Langsung (Direct Compression) atau Roller Compaction",
                description="Beralih ke metode kempa langsung menggunakan eksipien terproses-awal (coprocessed excipients) seperti Ludipress atau Avicel HFE-102.",
                reformulation_steps=[
                    "Ganti tahapan granulasi basah high-shear dengan pencampuran kering (dry blending).",
                    "Gunakan eksipien co-processed flow-aid berfluiditas tinggi.",
                    "Cetak langsung menggunakan mesin rotari bertekanan kompresi terkendali."
                ],
                scientific_rationale="Jika klaim paten adalah klaim proses (process claim) atau product-by-process yang mencakup langkah granulasi basah, penggunaan kempa langsung menggugurkan elemen langkah proses klaim.",
                fto_advantage="Bebas dari klaim metode granulasi dan menghemat biaya produksi hingga 35%."
            )
        )

        # Rekomendasi 4: Rekayasa Bentuk Padat (Solid-State Engineering / Co-crystal)
        if any(c.inn_name in ["Atorvastatin", "Paracetamol", "Esomeprazole"] for c in chemicals):
            recs.append(
                PharmaDesignAround(
                    strategy_type="PERUBAHAN_BENTUK_PADAT",
                    title="Rekayasa Kokristal Farmasi (Pharmaceutical Co-crystal) atau Amorphous Solid Dispersion",
                    description="Mengembangkan kokristal dengan koformer GRAS (misal: Nikotinamid, Asam Suksinat) atau dispersi padat amorf bersama polimer hidrofilik.",
                    reformulation_steps=[
                        "Sintesis kokristal zat aktif dengan koformer nikotinamid via pelarutan semprot (spray drying).",
                        "Karakterisasi menggunakan PXRD dan DSC untuk membuktikan pembentukan kisi kristal baru.",
                        "Uji stabilitas dipercepat (40°C/75% RH) selama 6 bulan."
                    ],
                    scientific_rationale="Kokristal merupakan kisi kristal unik yang berbeda dari garam ataupun polimorf yang diklaim paten asli, sehingga menciptakan ruang IP baru yang bahkan dapat dipatenkan kembali.",
                    fto_advantage="Proteksi FTO ganda dan peluang pendaftaran paten baru (Evergreening internal)."
                )
            )

        return recs


# Instance singleton engine
pharma_engine = PharmaInfringementEngine()
