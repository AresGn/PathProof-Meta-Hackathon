// Interface texts: English first for the jury, French one click away.
export const I18N = {
  en: {
    tagline: "Every study path comes with its proof. The agent picks its own tools, deterministic code does the math, and only proven claims reach the report.",
    badgeGuide: "Official 2026-2027 guide", badgeProofs: "Code-verified proofs",
    badgeSeries: "Series C and D", badgeFictional: "Fictional data only",
    heroProof: "Every claim opens its source. Try it in the report:",
    serverChecking: "Checking the demo server…",
    serverReady: "Demo server ready.",
    serverReadyLocal: "Demo server ready (local API, port 8000).",
    serverDown: "Demo server unreachable: run “python -m uvicorn src.api.server:app --port 8000” from the repository root, then open http://127.0.0.1:8000/ (not a static preview).",
    how1: "Send a grade-sheet photo and a voice note — or launch a fictional example.",
    how2: "The agent reads, transcribes, computes by code, and asks when something is unsure.",
    how3: "You get a verified report where every claim opens its proof.",
    examplesLegend: "Fictional examples — one click, nothing to prepare",
    ex1Title: "Clear serie D sheet + matching voice note",
    ex1Desc: "Serie D, “maybe a doctor”: expect a full report.",
    ex2Title: "Blurry sheet",
    ex2Desc: "One unreadable grade: the agent asks instead of guessing.",
    ex3Title: "Contradictory voice note",
    ex3Desc: "“14 average” said, 11.2 on the sheet: the agent flags the gap.",
    formLegend: "Student inputs",
    photoTitle: "Grade-sheet photo (JPEG/PNG)", voiceTitle: "Voice note",
    noFile: "No file chosen",
    fallbackLabel: "Fallback text (if no voice note)",
    fallbackPh: "Series, interests, target job…",
    submit: "Start orientation",
    stepsHeading: "Agent steps", stepsEmpty: "No run yet.",
    stepsWaiting: "Working… Reading the sheet and transcribing can take up to a minute; each tool appears here as soon as it answers.",
    inputOutput: "Input / output", input: "Input", output: "Output", stepWord: "step",
    tool_transcribe_voice: "Voice transcription", tool_extract_profile: "Student profile",
    tool_read_grade_sheet: "Grade-sheet reading", tool_compute_ranking_average: "Ranking average (code)",
    tool_lookup_filieres: "Program search (code)", tool_ask_student: "Question for the student",
    tool_verify_report: "Proof check (code)", tool_build_report: "Final report", tool_other: "Step",
    decision_continue: "continue", decision_suspend: "question asked",
    decision_stop_unverified: "stopped: unverified", decision_stop_step_limit: "step limit reached",
    questionHeading: "A question from the agent", answerLabel: "Your answer", answerButton: "Reply",
    askedStatus: "The agent is asking a question: reply in the orange box.",
    reportHeading: "Report", reportEmpty: "The report will appear here.",
    reportNote: "The verified report is written in French for the student; each claim below opens its proof.",
    verifiedBanner: "Verified report — every claim checked by code",
    proofsHeading: "Claims and proofs",
    proofsIntro: "Every proof is clickable and opens its source: a read grade, a voice quote, a guide row, or the calculation detail.",
    close: "Close",
    footer: "Demo on fictional data only. Recommendations are limited to public offers for series C and D of the 2026-2027 guide whose row passed quality control.",
    statusSending: "Sending to the server…", statusLoadingExample: "Loading the fictional example…",
    statusDone: "Run complete.", statusUnverified: "Unverified report: see “What I could not verify”.",
    statusDoneOther: "Run finished ({status}).",
    errorPrefix: "Error: ", retrySuffix: " — you can retry.", unknownError: "unknown error",
    serverUnreachable: "server unreachable: check that uvicorn is running from the repository root, then retry",
    interrupted: "Connection interrupted: no final event received. Run it again.",
    answerInterrupted: "Connection interrupted: the answer did not go through. You can retry.",
    sampleUnreadable: "unreadable example ({name}): {detail}",
    serverNoDetail: "the server answered {status} without detail",
    problemsIntro: "Claims refused by the verifier (never shown as facts):",
    proofGrade: "Grade · {matiere} {note}/20", proofTranscript: "Quote · “{quote}”",
    proofFiliere: "Guide · {id} (page {page})", proofCalc: "Result · {result}",
    proofOther: "Proof · {type}",
    gradeTitle: "Grade proof — {matiere}: {note}/20",
    gradeNote: "Grade input included in the context accepted by the verifier.",
    sheetUnavailable: "The sheet detail is no longer in the displayed trace.",
    guideRowUnavailable: "The complete guide row is not present in the displayed trace.",
    serieRead: "Series read: {serie}.", displayedAverage: "Average printed on the sheet: {avg}/20.",
    unreadable: "unreadable",
    transcriptTitle: "Quote proof — voice note",
    transcriptNote: "Exact quote searched word for word in the transcript.",
    transcriptUnavailable: "Transcript unavailable in the displayed trace.",
    filiereTitle: "Guide proof — {id}, page {page}",
    filiereNote: "Row of the official 2026-2027 information guide. Only rows with Statut_qualité = OK are recommended.",
    fieldPage: "Guide page (PDF)", fieldChamp: "Proven field", fieldValeur: "Proven value",
    calcTitle: "Calculation proof — {result}/20",
    calcNote: "Guide formula (page 8): {formula}. Series coefficients, never computed by the model.",
    calcSubject: "Subject", calcGrade: "Grade", calcCoefficient: "Coefficient", calcProduct: "Grade × coefficient",
    calcDetail: "Detail: {total} / {coeffs} = {result}/20 (guide rounding).",
    calcUnavailable: "Calculation details are unavailable because the verified inputs are invalid.",
  },
  fr: {
    tagline: "Every study path comes with its proof. L’agent choisit ses outils, calcule par du code, et ne recommande que ce qu’il peut prouver.",
    badgeGuide: "Guide officiel 2026-2027", badgeProofs: "Preuves vérifiées par code",
    badgeSeries: "Séries C et D", badgeFictional: "Données fictives uniquement",
    heroProof: "Chaque affirmation ouvre sa source. Essayez dans le rapport :",
    serverChecking: "Vérification du serveur…",
    serverReady: "Serveur de démo prêt.",
    serverReadyLocal: "Serveur de démo prêt (API locale, port 8000).",
    serverDown: "Serveur de démo injoignable : lancez « python -m uvicorn src.api.server:app --port 8000 » depuis la racine du dépôt, puis ouvrez http://127.0.0.1:8000/ (pas un aperçu statique).",
    how1: "Envoyez une photo de relevé et une note vocale — ou lancez un exemple fictif.",
    how2: "L’agent lit, transcrit, calcule par du code et demande quand un point est incertain.",
    how3: "Vous recevez un rapport vérifié où chaque affirmation ouvre sa preuve.",
    examplesLegend: "Exemples fictifs — un clic, rien à préparer",
    ex1Title: "Relevé D net + voix cohérente",
    ex1Desc: "Série D, « peut-être médecin » : rapport complet attendu.",
    ex2Title: "Relevé flou",
    ex2Desc: "Une note illisible : l’agent demande au lieu de deviner.",
    ex3Title: "Voix contradictoire",
    ex3Desc: "« 14 de moyenne » dite, 11,2 au relevé : l’agent signale l’écart.",
    formLegend: "Entrées élève",
    photoTitle: "Photo du relevé (JPEG/PNG)", voiceTitle: "Message vocal",
    noFile: "Aucun fichier choisi",
    fallbackLabel: "Texte de secours (si pas de note vocale)",
    fallbackPh: "Série, intérêts, métier visé…",
    submit: "Lancer l’orientation",
    stepsHeading: "Étapes de l’agent", stepsEmpty: "Aucune exécution pour l’instant.",
    stepsWaiting: "Analyse en cours… La lecture du relevé et la transcription peuvent prendre une minute ; chaque outil s’affichera ici dès qu’il répond.",
    inputOutput: "Entrée / sortie", input: "Entrée", output: "Sortie", stepWord: "pas",
    tool_transcribe_voice: "Transcription de la voix", tool_extract_profile: "Profil de l’élève",
    tool_read_grade_sheet: "Lecture du relevé", tool_compute_ranking_average: "Moyenne de classement (code)",
    tool_lookup_filieres: "Recherche des filières (code)", tool_ask_student: "Question à l’élève",
    tool_verify_report: "Vérification des preuves (code)", tool_build_report: "Rapport final", tool_other: "Étape",
    decision_continue: "continue", decision_suspend: "question posée",
    decision_stop_unverified: "arrêt : non vérifié", decision_stop_step_limit: "limite de pas atteinte",
    questionHeading: "Question de l’agent", answerLabel: "Votre réponse", answerButton: "Répondre",
    askedStatus: "L’agent pose une question : répondez dans l’encadré orange ci-contre.",
    reportHeading: "Rapport", reportEmpty: "Le rapport apparaîtra ici.",
    reportNote: "Le rapport vérifié est rédigé en français pour l’élève ; chaque affirmation ci-dessous ouvre sa preuve.",
    verifiedBanner: "Rapport vérifié — chaque affirmation contrôlée par code",
    proofsHeading: "Affirmations et preuves",
    proofsIntro: "Chaque preuve est cliquable et ouvre sa source : note lue, citation de la voix, ligne du guide ou détail du calcul.",
    close: "Fermer",
    footer: "Démo sur données fictives uniquement. Recommandations limitées aux offres publiques des séries C et D du guide 2026-2027 dont la ligne a passé le contrôle qualité.",
    statusSending: "Envoi au serveur…", statusLoadingExample: "Chargement de l’exemple fictif…",
    statusDone: "Exécution terminée.", statusUnverified: "Rapport non vérifié : voir « Ce que je n’ai pas pu vérifier ».",
    statusDoneOther: "Exécution terminée ({status}).",
    errorPrefix: "Erreur : ", retrySuffix: " — vous pouvez réessayer.", unknownError: "erreur inconnue",
    serverUnreachable: "serveur injoignable : vérifiez que uvicorn tourne depuis la racine du dépôt, puis réessayez",
    interrupted: "Connexion interrompue : aucun événement final reçu. Relancez l’exécution.",
    answerInterrupted: "Connexion interrompue : la réponse n’a pas abouti. Vous pouvez réessayer.",
    sampleUnreadable: "exemple illisible ({name}) : {detail}",
    serverNoDetail: "le serveur a répondu {status} sans détail",
    problemsIntro: "Affirmations refusées par le vérificateur (jamais présentées comme des faits) :",
    proofGrade: "Note · {matiere} {note}/20", proofTranscript: "Citation · « {quote} »",
    proofFiliere: "Guide · {id} (page {page})", proofCalc: "Calcul · {result}",
    proofOther: "Preuve · {type}",
    gradeTitle: "Preuve note — {matiere} : {note}/20",
    gradeNote: "Note figurant dans le contexte accepté par le vérificateur.",
    sheetUnavailable: "Le détail du relevé n’est plus dans la trace affichée.",
    guideRowUnavailable: "La ligne complète du guide n'est pas présente dans la trace affichée.",
    serieRead: "Série lue : {serie}.", displayedAverage: "Moyenne affichée sur le relevé : {avg}/20.",
    unreadable: "illisible",
    transcriptTitle: "Preuve citation — note vocale",
    transcriptNote: "Citation exacte cherchée mot pour mot dans la transcription.",
    transcriptUnavailable: "Transcription indisponible dans la trace affichée.",
    filiereTitle: "Preuve guide — {id}, page {page}",
    filiereNote: "Ligne du Guide d’information 2026-2027 officiel. Seules les lignes Statut_qualité = OK sont recommandées.",
    fieldPage: "Page du guide (PDF)", fieldChamp: "Champ prouvé", fieldValeur: "Valeur prouvée",
    calcTitle: "Preuve calcul — {result}/20",
    calcNote: "Formule du guide (page 8) : {formula}. Coefficients de la série, jamais calculés par le modèle.",
    calcSubject: "Matière", calcGrade: "Note", calcCoefficient: "Coefficient", calcProduct: "Note × coefficient",
    calcDetail: "Détail : {total} / {coeffs} = {result}/20 (arrondi du guide).",
    calcUnavailable: "Le détail du calcul est indisponible : les entrées vérifiées sont invalides.",
  },
};
const STORAGE_KEY = "pathproof-lang";

function readStoredLanguage() {
  try {
    return window.localStorage.getItem(STORAGE_KEY);
  } catch (error) {
    if (!isStorageUnavailable(error)) throw error;
    return null;
  }
}

function storeLanguage(language) {
  try {
    window.localStorage.setItem(STORAGE_KEY, language);
  } catch (error) {
    if (!isStorageUnavailable(error)) throw error;
  }
}

function isStorageUnavailable(error) {
  return error && ["SecurityError", "QuotaExceededError"].includes(error.name);
}

let currentLanguage = readStoredLanguage() === "fr" ? "fr" : "en";

export function getLanguage() {
  return currentLanguage;
}

export function setLanguage(next) {
  currentLanguage = next === "fr" ? "fr" : "en";
  storeLanguage(currentLanguage);
  return currentLanguage;
}

export function t(key, params) {
  let text = I18N[currentLanguage][key] || I18N.en[key] || key;
  for (const [name, value] of Object.entries(params || {})) {
    text = text.replaceAll(`{${name}}`, String(value));
  }
  return text;
}

// Static page text only; dynamic regions re-render themselves in app.js.
export function applyTranslations() {
  document.documentElement.lang = currentLanguage;
  for (const el of document.querySelectorAll("[data-i18n]")) {
    el.textContent = t(el.dataset.i18n);
  }
  for (const el of document.querySelectorAll("[data-i18n-ph]")) {
    el.placeholder = t(el.dataset.i18nPh);
  }
  for (const btn of document.querySelectorAll("[data-set-lang]")) {
    btn.classList.toggle("active", btn.dataset.setLang === currentLanguage);
  }
}
