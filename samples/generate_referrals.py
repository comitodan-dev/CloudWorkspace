"""Generate a PDF of synthetic GP referral letters for testing the referral summariser.

All practices, patients and clinical details are fictional. Most referrals are
well-formed; a known fraction deliberately omit the PRIORITY line, the patient
identifier, or any usable history, and an answer key at the end lists which.

Usage: python3 generate_referrals.py [count] [output.pdf] [--no-key]
"""

import random
import sys

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)

SEED = 20261004

# Each scenario: priority, complaint, history (list of options), done, safety-net,
# optional clinician notes. Sentences are combined to make each body read differently.
SCENARIOS = [
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with three weeks of painless visible haematuria, two episodes.",
         history=["Ex-smoker, 30 pack-years. Hypertension on amlodipine.",
                  "Previous smoker, quit 2015. No prior urological history."],
         done="Urine dip positive for blood, MSU negative for infection. U&E normal, eGFR 74.",
         safety="Advised to attend ED if unable to pass urine or passing clots.",
         notes=["Meets 2-week-wait criteria for suspected bladder cancer."]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with a two-year history of worsening bilateral knee pain, now limiting walking to 200 metres.",
         history=["BMI 34. Type 2 diabetes, HbA1c 58. Has completed a 12-week physiotherapy course.",
                  "Osteoarthritis on X-ray 2024. Regular paracetamol and topical NSAID with limited effect."],
         done="Weight-bearing X-ray shows moderate medial compartment narrowing bilaterally.",
         safety="Advised to return if knee becomes hot, swollen or unable to weight-bear.",
         notes=[]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with a new breast lump noticed four weeks ago, right upper outer quadrant.",
         history=["No family history of breast or ovarian cancer. Post-menopausal, not on HRT.",
                  "Mother diagnosed with breast cancer aged 52. On combined oral contraceptive."],
         done="Examination: 2 cm firm, non-tender, mobile lump. No axillary lymphadenopathy palpable.",
         safety="Patient aware this is a suspected cancer referral and to expect contact within two weeks.",
         notes=["Patient very anxious; please contact by phone rather than letter."]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with recurrent heartburn and regurgitation despite eight weeks of full-dose omeprazole.",
         history=["No weight loss, dysphagia or anaemia. H. pylori stool antigen negative.",
                  "Hiatus hernia suspected on previous barium swallow (2019)."],
         done="FBC normal. Lifestyle advice given; trial of alginate added.",
         safety="Told to seek review promptly if difficulty swallowing, vomiting blood or black stools.",
         notes=[]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with unintentional weight loss of 8 kg over three months and new change in bowel habit to looser stools.",
         history=["Father had colorectal cancer in his 60s. Otherwise fit and well.",
                  "Iron-deficiency anaemia picked up on routine bloods; no prior GI history."],
         done="FIT result 142 ug Hb/g. Hb 98 g/L, ferritin 6. Abdominal exam unremarkable.",
         safety="Advised to attend ED with any rectal bleeding causing dizziness or severe abdominal pain.",
         notes=["FIT positive above threshold.", "Lives alone; daughter is NOK and happy to be contacted."]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with gradually worsening hearing in the left ear over a year, with intermittent tinnitus.",
         history=["Works in construction, inconsistent hearing protection.",
                  "No vertigo or ear discharge. No previous ear surgery."],
         done="Otoscopy normal both sides. Rinne positive bilaterally, Weber lateralises to the right.",
         safety="To return urgently if sudden further loss of hearing or facial weakness.",
         notes=["Asymmetric loss; please consider MRI IAMs."]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with a persistent hoarse voice for four weeks.",
         history=["Current smoker, 20 per day. Drinks around 30 units a week.",
                  "Ex-smoker. Works as a teacher, voice use heavy."],
         done="No neck lumps palpable. Chest X-ray requested, result awaited.",
         safety="Advised to call 999 if any noisy breathing or difficulty breathing.",
         notes=[]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with lower urinary tract symptoms: frequency, nocturia x3 and poor stream for a year.",
         history=["Started tamsulosin six months ago with partial benefit. No haematuria.",
                  "IPSS 19. No family history of prostate cancer."],
         done="PSA 2.1 ng/mL. DRE: smooth, moderately enlarged, benign-feeling prostate. Renal function normal.",
         safety="Advised to attend ED if unable to pass urine.",
         notes=[]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with a pigmented lesion on the back that has changed shape and bled over the last two months.",
         history=["Fair skin, multiple sunburns as a child. No personal history of skin cancer.",
                  "Previous BCC excised from nose in 2021."],
         done="Dermoscopy: asymmetric, irregular border, multiple colours, 9 mm. 7-point checklist score 5.",
         safety="Patient informed of suspected cancer pathway.",
         notes=["Photographs attached to the e-RS referral."]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with poorly controlled asthma: two courses of oral steroids in the last year.",
         history=["Adherent to ICS/LABA (inhaler technique checked). Eosinophils 0.6.",
                  "Childhood asthma, worsened after moving to a damp flat."],
         done="Peak flow 68% of predicted. Spirometry shows reversible obstruction.",
         safety="Personal asthma action plan updated; advised 999 if not improving with reliever.",
         notes=[]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with new-onset atrial fibrillation and symptomatic breathlessness on mild exertion.",
         history=["Hypertension, previous TIA in 2022. CHA2DS2-VASc 5.",
                  "No previous cardiac history. Drinks heavily at weekends."],
         done="ECG confirms AF, rate 118. Started bisoprolol and apixaban. TFTs normal.",
         safety="Advised to call 999 for chest pain, collapse or worsening breathlessness.",
         notes=[]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with eight months of fatigue and low mood not responding to sertraline 100 mg.",
         history=["Second episode of depression. No current suicidal ideation; protective factors include children.",
                  "Previous trial of citalopram ineffective. Engaged with talking therapies, completed course."],
         done="Bloods including TFTs, B12 and ferritin normal. PHQ-9 18.",
         safety="Crisis line number given; advised to contact 111 option 2 or attend ED if thoughts of self-harm.",
         notes=[]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with a two-week history of new daily headaches, worse on waking, with one episode of vomiting.",
         history=["No previous headache history. No head injury.",
                  "Known migraine but describes these as different in character."],
         done="Neurological exam: no focal deficit. Fundoscopy inconclusive (small pupils). BP 132/84.",
         safety="Advised to attend ED immediately if new weakness, confusion, or sudden severe headache.",
         notes=["Please consider same-week imaging."]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with a carpal tunnel picture: numbness of thumb, index and middle fingers, waking at night.",
         history=["Symptoms for 9 months. Night splints for 3 months gave partial relief.",
                  "Hypothyroid on levothyroxine. Works on a production line."],
         done="Positive Phalen's and Tinel's. No thenar wasting. Steroid injection declined.",
         safety="To return if weakness or wasting develops.",
         notes=[]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with dysphagia to solids, progressive over six weeks, food sticking at mid-chest.",
         history=["Long-standing reflux. Lost 4 kg.",
                  "Barrett's oesophagus diagnosed 2018, lost to surveillance follow-up."],
         done="FBC shows mild microcytic anaemia, Hb 112.",
         safety="Advised to attend ED if unable to swallow fluids or saliva.",
         notes=[]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with heavy menstrual bleeding for over a year, flooding and changing pads hourly on heavy days.",
         history=["Tried tranexamic acid and mefenamic acid; declined hormonal options. Para 2.",
                  "Mirena coil removed last year due to side effects."],
         done="Hb 104, ferritin 9 - started on ferrous sulphate. Pelvic ultrasound: 3 cm intramural fibroid.",
         safety="Advised to seek urgent help if bleeding very heavy with dizziness.",
         notes=[]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with a hard, painless left testicular swelling noticed three weeks ago.",
         history=["No trauma. Previous orchidopexy for undescended testis as a child.",
                  "No urinary symptoms. No previous scrotal problems."],
         done="Examination: firm irregular mass within the body of the testis, separate from epididymis.",
         safety="Patient informed of suspected cancer referral.",
         notes=[]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with chronic plaque psoriasis covering roughly 15% of body surface area.",
         history=["Failed potent topical steroids and vitamin D analogue over 12 months. DLQI 16.",
                  "Psoriasis since teens; new joint pain in fingers over last 6 months."],
         done="Bloods: LFTs and FBC normal. Hep B/C and HIV screen negative.",
         safety="Advised to seek same-day review if skin becomes widespread red and hot.",
         notes=["Query psoriatic arthritis; consider joint rheumatology/dermatology clinic."]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with a neck lump present for five weeks, slowly enlarging.",
         history=["No recent infections. Non-smoker. Night sweats for two weeks.",
                  "Smoker; recent dental treatment but lump predates this."],
         done="3 cm firm, non-tender level II lymph node on the right. FBC and CRP normal.",
         safety="Patient aware of urgent suspected cancer referral.",
         notes=[]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with recurrent tonsillitis: seven episodes in the past year requiring antibiotics.",
         history=["Missing significant time from work. No quinsy.",
                  "Episodes documented in records for the past two years (5 and 6 per year)."],
         done="Currently well between episodes; tonsils grade 2.",
         safety="Advised to seek urgent review if unable to swallow or one-sided throat swelling.",
         notes=[]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with sudden painless loss of vision in the right eye this morning, now partially recovered.",
         history=["Hypertension, type 2 diabetes, smoker.",
                  "No previous eye problems. Takes no regular medication."],
         done="Visual acuity 6/12 right, 6/6 left. ECG sinus rhythm.",
         safety="Started aspirin 300 mg. Advised 999 if any weakness, speech disturbance or further visual loss.",
         notes=["Possible amaurosis fugax - TIA pathway may be more appropriate if not accepted."]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with lower back pain radiating to the left leg for 14 weeks.",
         history=["Office worker. Completed physiotherapy; still struggling with sitting.",
                  "Previous episode 5 years ago settled with physio."],
         done="Straight leg raise positive at 40 degrees. Power and reflexes normal. No red flags.",
         safety="Cauda equina safety-netting given verbally and in writing.",
         notes=[]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with post-menopausal bleeding, two episodes over the past month.",
         history=["Menopause age 51. Not on HRT. BMI 38.",
                  "On tamoxifen following breast cancer treatment in 2023."],
         done="Speculum: cervix looks normal. Smear up to date and normal.",
         safety="Told to expect contact within two weeks.",
         notes=[]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with gallstones on ultrasound and three episodes of biliary colic in four months.",
         history=["Pain after fatty meals, lasting 2-3 hours. No jaundice.",
                  "One A&E attendance last month; discharged with analgesia."],
         done="LFTs normal between episodes. Ultrasound: multiple gallstones, CBD 5 mm.",
         safety="Advised to attend ED if fever, jaundice or pain lasting over 6 hours.",
         notes=[]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with a swollen, hot, painful right calf for three days.",
         history=["Long-haul flight last week. On combined pill.",
                  "Recent knee arthroscopy two weeks ago."],
         done="Wells score 3. D-dimer raised. Started on apixaban treatment dose pending scan.",
         safety="Advised 999 for chest pain or breathlessness.",
         notes=[]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with suspected obstructive sleep apnoea: loud snoring, witnessed apnoeas and daytime sleepiness.",
         history=["Epworth score 15. Collar size 18 inches. Hypertension.",
                  "BMI 36. HGV driver - advised about DVLA obligations."],
         done="STOP-BANG 6. Thyroid function normal.",
         safety="Advised not to drive if feeling sleepy.",
         notes=["Occupational driver; would appreciate expedited assessment."]),
    dict(priority="ROUTINE",
         complaint="{age}-year-old {sex} with a two-year history of difficulty concentrating, disorganisation and impulsivity, seeking ADHD assessment.",
         history=["School reports describe similar difficulties. No substance misuse.",
                  "Lost two jobs in the past year due to missed deadlines."],
         done="ASRS screening questionnaire strongly positive. BP and pulse normal.",
         safety="No risk issues identified.",
         notes=[]),
    dict(priority="URGENT",
         complaint="{age}-year-old {sex} with persistent cough for six weeks and two episodes of haemoptysis.",
         history=["Smoker, 40 pack-years. COPD.",
                  "Asbestos exposure as a shipyard worker in the 1980s."],
         done="Chest X-ray: 3 cm right upper lobe opacity. Bloods normal.",
         safety="Advised to attend ED if coughing large volumes of blood.",
         notes=[]),
]

# Bodies with no usable history - each still has a header, so only "no history" is the gap.
THIN_BODIES = [
    "Please see.",
    "Thank you for seeing this patient.",
    "Referred as discussed.",
    "Please assess and advise. Many thanks.",
    "As per phone call.",
    "Kindly review.",
]

PRACTICE_PREFIXES = ["MPL", "HGT", "RVS", "OAK", "BRK", "WLW", "STN", "CLV"]


def practice_id(rng):
    return f"PRAC-{rng.choice(PRACTICE_PREFIXES)}-{rng.randint(100, 999)}"


def patient_id(rng):
    return f"TEST-{rng.randint(100000, 999999)}"


def make_referral(n, rng, defect):
    sc = rng.choice(SCENARIOS)
    age = rng.randint(28, 84)
    sex = rng.choice(["man", "woman"])
    if "breast lump" in sc["complaint"] or "menstrual" in sc["complaint"] or "menopausal" in sc["complaint"]:
        sex = "woman"
    if "testicular" in sc["complaint"] or "urinary tract symptoms" in sc["complaint"]:
        sex = "man"

    header = [("REFERRING PRACTICE", practice_id(rng)),
              ("PRIORITY", sc["priority"]),
              ("PATIENT", patient_id(rng))]
    if defect == "no_priority":
        header = [h for h in header if h[0] != "PRIORITY"]
    if defect == "no_patient":
        header = [h for h in header if h[0] != "PATIENT"]
    if defect == "no_priority_no_patient":
        header = [header[0]]

    if defect == "no_history":
        body = rng.choice(THIN_BODIES)
    else:
        parts = [sc["complaint"].format(age=age, sex=sex),
                 rng.choice(sc["history"]),
                 sc["done"],
                 sc["safety"]]
        body = " ".join(parts)

    notes = []
    if defect != "no_history" and sc["notes"] and rng.random() < 0.7:
        notes = rng.sample(sc["notes"], k=rng.randint(1, len(sc["notes"])))
    elif rng.random() < 0.08:
        notes = ["Patient requests a female clinician where possible."]

    return dict(n=n, header=header, body=body, notes=notes, defect=defect)


DEFECT_LABELS = {
    None: "Complete",
    "no_priority": "Missing PRIORITY line",
    "no_patient": "Missing patient identifier",
    "no_priority_no_patient": "Missing PRIORITY line and patient identifier",
    "no_history": "Body has no history to work from",
}


def pick_defect(rng):
    r = rng.random()
    if r < 0.72:
        return None
    if r < 0.80:
        return "no_priority"
    if r < 0.88:
        return "no_patient"
    if r < 0.92:
        return "no_priority_no_patient"
    return "no_history"


def add_answer_key(story, referrals, counts, styles):
    story.append(PageBreak())
    story.append(Paragraph("Answer Key", styles["Heading1"]))
    summary = ", ".join(f"{DEFECT_LABELS[k]}: {v}" for k, v in counts.items())
    story.append(Paragraph(summary, styles["Normal"]))
    story.append(Spacer(1, 5 * mm))

    rows = [["#", "Status"]]
    for r in referrals:
        rows.append([f"{r['n']:03d}", DEFECT_LABELS[r["defect"]]])
    key = Table(rows, colWidths=[20 * mm, 150 * mm], repeatRows=1)
    style = [("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
             ("FONTSIZE", (0, 0), (-1, -1), 9),
             ("LINEBELOW", (0, 0), (-1, 0), 0.8, colors.black),
             ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]
    for i, r in enumerate(referrals, start=1):
        if r["defect"]:
            style.append(("TEXTCOLOR", (1, i), (1, i), colors.HexColor("#B03A2E")))
    key.setStyle(TableStyle(style))
    story.append(key)


def build(count, out_path, answer_key=True):
    rng = random.Random(SEED)
    referrals = [make_referral(i + 1, rng, pick_defect(rng)) for i in range(count)]

    styles = getSampleStyleSheet()
    mono = ParagraphStyle("mono", parent=styles["Normal"], fontName="Courier",
                          fontSize=9.5, leading=13, alignment=TA_LEFT)
    title = ParagraphStyle("t", parent=styles["Title"], fontSize=20)
    label = ParagraphStyle("lbl", parent=styles["Normal"], fontName="Helvetica-Bold",
                           fontSize=10, textColor=colors.HexColor("#555555"), spaceAfter=4)

    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    story = [
        Paragraph("Sample Referral Letters", title),
        Paragraph(f"{count} synthetic referrals for testing. All practices, patients and "
                  "clinical details are fictional."
                  + (" Roughly a quarter are deliberately incomplete; the answer key at "
                     "the end lists which and why." if answer_key else ""),
                  styles["Normal"]),
        Spacer(1, 10 * mm),
    ]

    for r in referrals:
        lines = [f"{k}: {v}" for k, v in r["header"]]
        block = [Paragraph(f"Referral #{r['n']:03d}", label)]
        text = "<br/>".join(esc(l) for l in lines)
        text += "<br/><br/>" + esc(r["body"])
        if r["notes"]:
            text += "<br/><br/>" + "<br/>".join(esc(f"CLINICIAN NOTE: {n}") for n in r["notes"])
        cell = Table([[Paragraph(text, mono)]], colWidths=[170 * mm])
        cell.setStyle(TableStyle([
            ("BOX", (0, 0), (-1, -1), 0.6, colors.HexColor("#999999")),
            ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FAFAF7")),
            ("LEFTPADDING", (0, 0), (-1, -1), 8), ("RIGHTPADDING", (0, 0), (-1, -1), 8),
            ("TOPPADDING", (0, 0), (-1, -1), 7), ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ]))
        block.append(cell)
        block.append(Spacer(1, 7 * mm))
        story.append(KeepTogether(block))

    counts = {}
    for r in referrals:
        counts[r["defect"]] = counts.get(r["defect"], 0) + 1
    if answer_key:
        add_answer_key(story, referrals, counts, styles)

    def footer(canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawString(20 * mm, 10 * mm, "Synthetic test data - not real patients")
        canvas.drawRightString(190 * mm, 10 * mm, f"Page {doc.page}")
        canvas.restoreState()

    doc = SimpleDocTemplate(out_path, pagesize=A4, leftMargin=20 * mm, rightMargin=20 * mm,
                            topMargin=18 * mm, bottomMargin=18 * mm,
                            title="Sample Referral Letters")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return counts


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if a != "--no-key"]
    count = int(args[0]) if args else 200
    out = args[1] if len(args) > 1 else "sample_referrals.pdf"
    print(build(count, out, answer_key="--no-key" not in sys.argv))
