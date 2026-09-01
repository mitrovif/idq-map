"""
Cross-check the UNHCR Registration Baseline Survey (2024/2025, 106 operations)
against config/protection_context.json and write config/protection_survey.json,

    python3 merge_registration_survey.py "<...Registration_Baseline_Survey...xlsx>"

an OVERLAY that protection.py applies at load time when the file is present.
The scrape JSON itself is never edited. The overlay is not committed: the
survey is an internal UNHCR dataset, so whether its content may appear on the
public site is a decision for the task team, not for this script.

Reconciliation rule for the registrar field, where the two sources disagree.
The survey's Q1 asks who does the majority of REGISTRATION ACTIVITIES; the
scrape recorded where a protection CLAIM IS LODGED. Those differ by design in
"parallel" arrangements (UNHCR registers for its own purposes alongside a
government asylum procedure), so:

  survey JOINT / SPLIT      -> BOTH        (respondent meets both bodies)
  survey PARALLEL           -> keep scrape (claim still lodged with government),
                               but flag the false-positive risk in the caveat
  survey UNHCR, scrape NONE -> UNHCR       (scrape simply missed it)
  survey UNHCR, scrape GOVT -> keep scrape, flag for review (usually a
                               non-asylum registration: Ukraine response, IDPs)
  survey GOVT,  scrape BOTH/UNHCR -> keep scrape, flag
  agree                     -> unchanged, marked corroborated

Countries in the survey but not in the scrape get a new record carrying only
what the survey knows: registrar, whether UNHCR issues documents and of what
type, refugee-law status, handover history. No office or document is NAMED,
so confidence is LOW and neither probe can be drafted yet.
"""
import json, sys, datetime, re
import pandas as pd
from paths import ROOT

import pandas as pd, pycountry, json, re

MANUAL = {
 'Bolivarian Republic of Venezuela':'VEN','Rep. of Chad':'TCD','Curacao':'CUW',
 'Czech Republic':'CZE','Democratic Republic of the Congo':'COD','Islamic Republic of Iran':'IRN',
 'Republic of Moldova':'MDA','Republic of Korea':'KOR','Republic of the Congo':'COG',
 'Syrian Arab Republic':'SYR','Turkiye':'TUR','United Republic of Tanzania':'TZA',
 'United States of America':'USA',"Côte d'Ivoire":'CIV','Gambia':'GMB',
}
def iso3(name):
    if name in MANUAL: return MANUAL[name]
    try: return pycountry.countries.lookup(name).alpha_3
    except LookupError: return None

def load(xlsx):
    df = pd.read_excel(xlsx, sheet_name='USE ME')
    df = df.drop(columns=df.columns[0])
    df['iso3'] = df['Country Name'].map(iso3)
    cols = list(df.columns)
    def col(prefix):
        m=[c for c in cols if c.startswith(prefix)]
        return m[0] if m else None
    df = df.rename(columns={
        col('1. Please'):'q1_who', col('2. Has a Memorandum'):'q2_mou',
        col('3. Are there any plans'):'q3_handover', col('3.a'):'q3a_done', col('3.b'):'q3b_planned',
        col('4. Does UNHCR conduct'):'q4_direct', col('5. Does UNHCR share'):'q5_share',
        col('16. Are there internally'):'q16_idps', 'Are IDPs in your operation being enrolled (registered)?':'q17_idp_enrol',
        col('18. What is the principal'):'q18_idp_tool',
        col('20. Are there stateless'):'q20_stateless', col('21. Are stateless'):'q21_stateless_reg',
        col('22. Are registered stateless'):'q22_stateless_doc',
        col('33. Is refugee protection'):'q33_law', 'If other, please specify_178':'q33_other',
        col('34. Does your Operation have'):'q34_mou',
        col('35. Does UNHCR issue'):'q35_unhcr_docs',
        [c for c in cols if c.startswith('36.') and '/' not in c][0]:'q36_doc_types',
        'If other please specify:…_179':'q36_other',
        col('37. Do you have'):'q37_sop', 'Focal Point Name':'focal','Focal Point Title':'focal_title',
        '_submission_time':'submitted','Year':'year',
    })
    return df


if len(sys.argv) != 2:
    sys.exit("usage: python3 merge_registration_survey.py <Registration_Baseline_Survey extract>.xlsx")
JSON = ROOT / 'config' / 'protection_context.json'
OVERLAY = ROOT / 'config' / 'protection_survey.json'
D = json.load(open(JSON, encoding='utf-8'))
P = D['countries']          # read only - the scrape stays as it is
OUT = {}                    # iso -> overlay entry
df = load(sys.argv[1])

DOCTYPES = ['Appointment card', 'Asylum-seeker certificate', 'Asylum-seeker card',
            'Proof of registration/enrolment', 'Refugee certificate', 'Refugee card',
            'Attestation', 'National Identity Card (for Asylum-Seekers)',
            'National Identity Card (for Refugees)', 'Other']

def s(v):
    return None if (v is None or (isinstance(v, float) and pd.isna(v)) or v in ('null', 'NaN')) else v

def arrangement(q1):
    q1 = s(q1)
    if not q1: return None
    if q1 == 'UNHCR': return 'UNHCR'
    if q1.startswith('The Government of the Country of Asylum and'):
        return re.search(r'(JOINT|PARALLEL|SPLIT)', q1).group(1)
    return 'GOVERNMENT'

def survey_reg(arr):
    return {'UNHCR': 'UNHCR', 'GOVERNMENT': 'GOVERNMENT', 'JOINT': 'BOTH',
            'SPLIT': 'BOTH', 'PARALLEL': 'BOTH', None: None}[arr]

def doc_types(row):
    raw = s(row['q36_doc_types'])
    if not raw: return []
    found = []
    for t in DOCTYPES:
        col = [c for c in df.columns if c.startswith('36.') and c.endswith('/' + t)]
        if col and row[col[0]] == 1: found.append(t)
    return found

def idp_enrolled_by(row):
    if s(row['q16_idps']) != 'Yes': return None
    who = []
    for col, lab in [('Yes, by UNHCR', 'UNHCR'), ('Yes, by Government', 'Government'),
                     ('Yes, by IOM', 'IOM'), ('Yes, by other UN Agency or partner', 'other UN agency or partner')]:
        if row[col] == 'Yes': who.append(lab)
    if row['No_147'] == 'Yes': return 'not enrolled'
    return ', '.join(who) if who else 'not stated'

def handover(row):
    h = s(row['q3_handover'])
    if not h: return None, None
    yr = None
    for c in ('q3a_done', 'q3b_planned'):
        v = s(row[c])
        if v:
            m = re.search(r'(\d{4})', str(v)); yr = int(m.group(1)) if m else None
    return h, yr

def year_of(v):
    v = s(v)
    if v is None: return None
    m = re.search(r'(\d{4})', str(v)); return int(m.group(1)) if m else None

log = []
for _, r in df.iterrows():
    iso = r['iso3']; arr = arrangement(r['q1_who']); sreg = survey_reg(arr)
    h, hyr = handover(r); types = doc_types(r)
    block = {
        'year': int(r['year']),
        'who_registers': s(r['q1_who']), 'arrangement': arr,
        'unhcr_delivery': s(r['q4_direct']),
        'handover': h, 'handover_year': hyr,
        'unhcr_issues_documents': s(r['q35_unhcr_docs']),
        'unhcr_document_types': types, 'unhcr_document_other': s(r['q36_other']),
        'refugee_law': s(r['q33_law']), 'refugee_law_other': s(r['q33_other']),
        'idps_present': s(r['q16_idps']), 'idps_enrolled_by': idp_enrolled_by(r),
        'idp_enrolment_tool': s(r['q18_idp_tool']),
        'stateless_present': s(r['q20_stateless']), 'stateless_registered': s(r['q21_stateless_reg']),
        'stateless_documented': s(r['q22_stateless_doc']),
    }
    # ---- sentences for the caveat (what a reviewer sees on the page) ----
    notes = []
    if h and h.startswith('Yes - Handover completed') and hyr:
        notes.append(f'registration was handed over from UNHCR to the Government in {hyr}, so '
                     f'respondents who applied before then applied to UNHCR')
    elif h and 'in progress' in h:
        notes.append('handover of registration from UNHCR to the Government is in progress')
    elif h and 'planned' in h and hyr:
        notes.append(f'handover of registration to the Government is planned for {hyr}')
    if arr == 'PARALLEL':
        notes.append('UNHCR runs its own registration in parallel to the government asylum '
                     'procedure, so a respondent registered with UNHCR for assistance may answer '
                     '"yes" to an office question without ever having lodged a protection claim')
    if arr == 'SPLIT':
        notes.append('registration is split by population between the Government and UNHCR, '
                     'so the right office depends on which group the respondent belongs to')
    if s(r['q35_unhcr_docs']) == 'Yes' and types:
        tl = [t for t in types if t != 'Other']
        if tl: notes.append('UNHCR issues: ' + ', '.join(tl).lower())
        if s(r['q36_other']):
            notes.append('UNHCR adds, in its own words: "' + str(s(r['q36_other'])).strip().rstrip('.') + '"')
    if s(r['q33_law']) == 'No':
        notes.append('no national refugee legislation, so "refugee status" may not be a term '
                     'respondents have encountered')
    sentence = ('UNHCR Registration Baseline Survey ' + str(int(r['year'])) + ': '
                + '; '.join(notes) + '.') if notes else None

    if iso in P:
        rec = P[iso]; preg = rec['registrar']; action = 'corroborated'; newreg = preg
        if sreg and sreg != preg:
            if arr in ('JOINT', 'SPLIT'):
                newreg, action = 'BOTH', f'{preg}→BOTH (survey: {arr.lower()} registration)'
            elif arr == 'PARALLEL':
                action = f'kept {preg} (survey: parallel — UNHCR registers alongside, claim still lodged with Government)'
            elif sreg == 'UNHCR' and preg == 'NONE':
                newreg, action = 'UNHCR', 'NONE→UNHCR (survey: UNHCR registers)'
            elif sreg == 'UNHCR' and preg == 'GOVERNMENT':
                action = f'kept GOVERNMENT — REVIEW: survey says UNHCR conducts most registration'
            else:
                action = f'kept {preg} — REVIEW: survey says {sreg}'
        elif not sreg:
            action = 'survey has no answer'
        if 'REVIEW' in action:
            extra = (f'the operation reports that {"UNHCR" if sreg=="UNHCR" else sreg.title()} conducts most '
                     f'registration activities, which does not match the office named above and needs checking')
            sentence = (sentence.rstrip('.') + '; ' + extra + '.') if sentence else \
                       ('UNHCR Registration Baseline Survey ' + str(int(r['year'])) + ': ' + extra + '.')
        OUT[iso] = {'survey': dict(block, registrar_reconciliation=action),
                    'registrar': newreg if newreg != preg else None,
                    'caveat_add': sentence}
        log.append((iso, rec['country'], preg, sreg, arr, newreg, action, 'in scrape'))
    else:
        reg = sreg or 'GOVERNMENT'
        OUT[iso] = {'new_record': {
            'country': r['Country Name'].replace('Rep. of Chad', 'Chad').replace(
                'Bolivarian Republic of Venezuela', 'Venezuela').replace('Curacao', 'Curaçao'),
            'registrar': reg, 'confidence': 'LOW', 'reword_v1': False,
            'office': '', 'office_local': '', 'office_alt': [],
            'office_why': 'No office named yet: this country was not covered by the help.unhcr.org '
                          'scrape; the registrar comes from the UNHCR Registration Baseline Survey.',
            'doc_pending': '', 'doc_pending_local': '', 'doc_pending_colloquial': '',
            'doc_recognised': '', 'doc_recognised_local': '', 'doc_recognised_colloquial': '',
            'doc_alt': '',
            'doc_why': ('UNHCR reports issuing ' + ', '.join(t.lower() for t in types if t != 'Other')
                        + ' here, but no local document name has been sourced yet') if types
                       else 'No document named; UNHCR reports issuing none itself',
            'channel': '', 'colours': [],
            'caveat': sentence or '',
            'survey': dict(block, registrar_reconciliation='new record from survey'),
        }}
        log.append((iso, OUT[iso]['new_record']['country'], None, sreg, arr, reg, 'new record from survey', 'survey only'))

META = ('UNHCR Registration Baseline Survey, extract from PowerBI (2024 and 2025 rounds), '
                '106 country operations, merged ' + datetime.date.today().isoformat() +
                '. The `survey` block on each country is the operation\'s own answers; '
                'registrar_reconciliation records how a disagreement with the scrape was resolved.')
json.dump({'_about': META, 'countries': OUT}, open(OVERLAY, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print('wrote overlay', OVERLAY)
pd.DataFrame(log, columns=['iso3', 'country', 'scrape_registrar', 'survey_registrar', 'survey_arrangement',
                           'registrar_now', 'action', 'coverage']).to_csv(str(ROOT / 'config' / 'protection_survey_log.csv'), index=False)
from collections import Counter
print(len(OUT), 'overlay entries')
print(Counter(a for *_, a, _ in log))
