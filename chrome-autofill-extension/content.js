/**
 * Bewerbung AutoFill – Content Script
 * Füllt Formularfelder automatisch mit den persönlichen Daten aus.
 */

// ─── PERSÖNLICHE DATEN ──────────────────────────────────────────────────────
const PROFILE = {
  // Grunddaten
  vorname: "Hamza",
  nachname: "Öztürk",
  vollname: "Hamza Öztürk",
  
  // Anschrift
  strasse: "Bissierstr. 16",
  plz: "79114",
  ort: "Freiburg",
  stadt: "Freiburg im Breisgau",
  land: "Deutschland",
  bundesland: "Baden-Württemberg",
  
  // Kontakt
  email: "oeztuerk.hamza@web.de",
  telefon: "+4915566859378",
  telefonFormatiert: "+49 155 66859378",
  mobil: "+4915566859378",
  mobilFormatiert: "+49 155 66859378",
  
  // Geburtsdaten
  geburtsdatum: "1996",
  geburtsort: "",
  
  // Online-Profile
  linkedin: "https://linkedin.com/in/hamzaoeztuerk",
  github: "https://github.com/oeztuerkhamza",
  website: "https://hamzaoeztuerk.de",
  xing: "",
  
  // Berufliche Angaben
  beruf: "Fullstack Entwickler",
  position: "Full-Stack Entwickler",
  aktuellerArbeitgeber: "Dicom GmbH",
  berufserfahrungJahre: "2",
  
  // Ausbildung
  ausbildung: "Fachinformatiker für Anwendungsentwicklung (IHK)",
  hochschule: "Walther-Rathenau-Gewerbeschule, Freiburg",
  abschluss: "IHK-Abschluss",
  
  // Bewerbung
  gehaltsvorstellung: "",
  eintrittsdatum: "",
  arbeitsmodell: "",
  
  // Sprachen
  spracheDeutsch: "Fließend",
  spracheEnglisch: "Fließend",
  spracheTuerkisch: "Muttersprache",
  
  // Nationalität
  nationalitaet: "Türkisch",
  staatsangehoerigkeit: "Türkisch",
};

// ─── FELD-ZUORDNUNGEN ──────────────────────────────────────────────────────
// Jedes Mapping ordnet Schlüsselwörter (in Labels, Placeholders, Names, IDs)
// einem Profil-Feld zu.
const FIELD_MAPPINGS = [
  // Vorname
  {
    keywords: [
      "vorname", "first.?name", "given.?name", "fname", "prenom",
      "first_name", "firstname", "givenname", "forename"
    ],
    value: PROFILE.vorname,
    priority: 10,
  },
  // Nachname
  {
    keywords: [
      "nachname", "last.?name", "sur.?name", "family.?name", "lname",
      "last_name", "lastname", "familyname", "surname"
    ],
    value: PROFILE.nachname,
    priority: 10,
  },
  // Vollständiger Name
  {
    keywords: [
      "vollst.?ndiger?.?name", "full.?name", "your.?name", "^name$",
      "bewerbername", "applicant.?name", "complete.?name",
      "name.?des.?bewerbers", "ihr.?name"
    ],
    value: PROFILE.vollname,
    priority: 5,
  },
  // E-Mail
  {
    keywords: [
      "e.?mail", "email", "mail", "e-mail-adresse", "emailaddress",
      "email.?address", "elektronische.?post"
    ],
    value: PROFILE.email,
    priority: 10,
  },
  // Telefon
  {
    keywords: [
      "telefon", "phone", "tel", "rufnummer", "phone.?number",
      "telephone", "handy", "mobil", "mobile", "cell",
      "telefonnummer", "mobilnummer", "handynummer"
    ],
    value: PROFILE.telefonFormatiert,
    priority: 10,
  },
  // Straße
  {
    keywords: [
      "stra.?e", "street", "address", "adresse", "anschrift",
      "address.?line", "street.?address", "stra.?enname",
      "wohnort.*stra", "addr1"
    ],
    value: PROFILE.strasse,
    priority: 8,
  },
  // PLZ
  {
    keywords: [
      "plz", "postleitzahl", "zip", "postal", "zip.?code",
      "postal.?code", "postcode"
    ],
    value: PROFILE.plz,
    priority: 10,
  },
  // Ort / Stadt
  {
    keywords: [
      "^ort$", "^stadt$", "^city$", "wohnort", "town", "location",
      "city", "residence"
    ],
    value: PROFILE.ort,
    priority: 8,
  },
  // Land
  {
    keywords: [
      "^land$", "country", "staat"
    ],
    value: PROFILE.land,
    priority: 5,
  },
  // Bundesland
  {
    keywords: [
      "bundesland", "state", "province", "region"
    ],
    value: PROFILE.bundesland,
    priority: 5,
  },
  // LinkedIn
  {
    keywords: [
      "linkedin", "linked.?in"
    ],
    value: PROFILE.linkedin,
    priority: 10,
  },
  // GitHub
  {
    keywords: [
      "github", "git.?hub"
    ],
    value: PROFILE.github,
    priority: 10,
  },
  // Website
  {
    keywords: [
      "website", "webseite", "homepage", "portfolio",
      "personal.?website", "url", "web"
    ],
    value: PROFILE.website,
    priority: 7,
  },
  // Xing
  {
    keywords: ["xing"],
    value: PROFILE.xing,
    priority: 10,
  },
  // Beruf / Position
  {
    keywords: [
      "beruf", "position", "job.?title", "stellenbezeichnung",
      "aktuelle.?position", "current.?position", "jobtitle",
      "title", "rolle", "role", "berufsbezeichnung"
    ],
    value: PROFILE.position,
    priority: 5,
  },
  // Arbeitgeber
  {
    keywords: [
      "arbeitgeber", "employer", "unternehmen", "firma",
      "company", "current.?employer", "aktueller.?arbeitgeber",
      "organization", "organisation"
    ],
    value: PROFILE.aktuellerArbeitgeber,
    priority: 5,
  },
  // Geburtsdatum
  {
    keywords: [
      "geburtsdatum", "birth.?date", "date.?of.?birth", "dob",
      "geboren", "birthday", "geburtsjahr"
    ],
    value: PROFILE.geburtsdatum,
    priority: 8,
  },
  // Ausbildung
  {
    keywords: [
      "ausbildung", "education", "qualification", "abschluss",
      "degree", "studium", "bildung"
    ],
    value: PROFILE.ausbildung,
    priority: 5,
  },
  // Gehaltsvorstellung
  {
    keywords: [
      "gehalt", "salary", "gehaltsvorstellung", "salary.?expectation",
      "vergütung", "compensation", "gehaltswunsch"
    ],
    value: PROFILE.gehaltsvorstellung,
    priority: 5,
  },
  // Eintrittsdatum
  {
    keywords: [
      "eintritt", "start.?date", "earliest.?start", "verfügbar",
      "available", "eintrittsdatum", "frühester.?eintritt",
      "availability", "starttermin"
    ],
    value: PROFILE.eintrittsdatum,
    priority: 5,
  },
  // Nationalität
  {
    keywords: [
      "nationalit.?t", "nationality", "staatsangeh.?rigkeit",
      "citizenship"
    ],
    value: PROFILE.nationalitaet,
    priority: 5,
  },
  // Deutsch
  {
    keywords: [
      "deutsch.?kenntnisse", "german.?level", "german.?proficiency"
    ],
    value: PROFILE.spracheDeutsch,
    priority: 5,
  },
  // Englisch
  {
    keywords: [
      "englisch.?kenntnisse", "english.?level", "english.?proficiency"
    ],
    value: PROFILE.spracheEnglisch,
    priority: 5,
  },
  // Berufserfahrung
  {
    keywords: [
      "berufserfahrung", "experience", "years.?of.?experience",
      "work.?experience", "erfahrung.?jahre"
    ],
    value: PROFILE.berufserfahrungJahre,
    priority: 5,
  },
];

// ─── HILFSFUNKTIONEN ────────────────────────────────────────────────────────

/**
 * Sammelt alle Texthinweise eines Formularfeldes:
 * - name, id, placeholder, autocomplete, aria-label
 * - zugehöriges <label>
 * - umschließender Text
 */
function getFieldHints(field) {
  const hints = [];
  
  // Direkte Attribute
  ["name", "id", "placeholder", "autocomplete", "aria-label", "title"].forEach(attr => {
    const val = field.getAttribute(attr);
    if (val) hints.push(val.toLowerCase());
  });
  
  // Label via for-Attribut
  const id = field.id;
  if (id) {
    const label = document.querySelector(`label[for="${CSS.escape(id)}"]`);
    if (label) hints.push(label.textContent.trim().toLowerCase());
  }
  
  // Label als Elternelement
  const parentLabel = field.closest("label");
  if (parentLabel) {
    hints.push(parentLabel.textContent.trim().toLowerCase());
  }
  
  // Vorheriges Sibling-Label
  let prev = field.previousElementSibling;
  if (prev && prev.tagName === "LABEL") {
    hints.push(prev.textContent.trim().toLowerCase());
  }
  
  // aria-labelledby
  const labelledBy = field.getAttribute("aria-labelledby");
  if (labelledBy) {
    const labelEl = document.getElementById(labelledBy);
    if (labelEl) hints.push(labelEl.textContent.trim().toLowerCase());
  }
  
  // data-label, data-field
  ["data-label", "data-field", "data-name", "data-qa"].forEach(attr => {
    const val = field.getAttribute(attr);
    if (val) hints.push(val.toLowerCase());
  });
  
  return hints;
}

/**
 * Prüft, ob mindestens ein Keyword auf die Hinweise passt.
 */
function matchesKeywords(hints, keywords) {
  const joined = hints.join(" ");
  return keywords.some(kw => {
    try {
      const regex = new RegExp(kw, "i");
      return hints.some(h => regex.test(h));
    } catch {
      return joined.includes(kw.toLowerCase());
    }
  });
}

/**
 * Simuliert Benutzereingaben so natürlich wie möglich,
 * damit React/Angular/Vue die Änderung erkennen.
 */
function setFieldValue(field, value) {
  if (!value) return false;
  
  // Focus
  field.focus();
  field.dispatchEvent(new Event("focus", { bubbles: true }));
  
  // Für React: nutze den nativen Setter
  const nativeInputValueSetter = Object.getOwnPropertyDescriptor(
    window.HTMLInputElement.prototype, "value"
  )?.set;
  const nativeTextareaValueSetter = Object.getOwnPropertyDescriptor(
    window.HTMLTextAreaElement.prototype, "value"
  )?.set;
  
  if (field.tagName === "INPUT" && nativeInputValueSetter) {
    nativeInputValueSetter.call(field, value);
  } else if (field.tagName === "TEXTAREA" && nativeTextareaValueSetter) {
    nativeTextareaValueSetter.call(field, value);
  } else {
    field.value = value;
  }
  
  // Alle notwendigen Events auslösen
  field.dispatchEvent(new Event("input", { bubbles: true }));
  field.dispatchEvent(new Event("change", { bubbles: true }));
  field.dispatchEvent(new KeyboardEvent("keydown", { bubbles: true }));
  field.dispatchEvent(new KeyboardEvent("keyup", { bubbles: true }));
  field.dispatchEvent(new Event("blur", { bubbles: true }));
  
  return true;
}

/**
 * Versucht, ein Select-Feld auf einen passenden Wert zu setzen.
 */
function setSelectValue(select, value) {
  if (!value) return false;
  
  const valueLower = value.toLowerCase();
  const options = Array.from(select.options);
  
  // Exakte Übereinstimmung (Wert oder Text)
  let match = options.find(
    o => o.value.toLowerCase() === valueLower || o.text.toLowerCase() === valueLower
  );
  
  // Teilweise Übereinstimmung
  if (!match) {
    match = options.find(
      o => o.text.toLowerCase().includes(valueLower) || valueLower.includes(o.text.toLowerCase())
    );
  }
  
  if (match) {
    select.value = match.value;
    select.dispatchEvent(new Event("change", { bubbles: true }));
    select.dispatchEvent(new Event("input", { bubbles: true }));
    return true;
  }
  
  return false;
}

// ─── HAUPTFUNKTION ──────────────────────────────────────────────────────────

/**
 * Füllt alle erkannten Formularfelder auf der Seite aus.
 * Gibt die Anzahl der ausgefüllten Felder zurück.
 */
function fillAllFields() {
  let filledCount = 0;
  const results = [];
  
  // Input- und Textarea-Felder
  const inputs = document.querySelectorAll(
    'input[type="text"], input[type="email"], input[type="tel"], ' +
    'input[type="url"], input[type="search"], input[type="number"], ' +
    'input:not([type]), textarea'
  );
  
  inputs.forEach(field => {
    // Versteckte oder deaktivierte Felder überspringen
    if (field.type === "hidden" || field.disabled || field.readOnly) return;
    if (field.offsetParent === null && field.style.display !== "contents") return;
    
    const hints = getFieldHints(field);
    if (hints.length === 0) return;
    
    // Bestes Mapping finden
    let bestMatch = null;
    let bestPriority = -1;
    
    for (const mapping of FIELD_MAPPINGS) {
      if (matchesKeywords(hints, mapping.keywords) && mapping.priority > bestPriority) {
        bestMatch = mapping;
        bestPriority = mapping.priority;
      }
    }
    
    if (bestMatch && bestMatch.value) {
      if (setFieldValue(field, bestMatch.value)) {
        filledCount++;
        results.push({
          field: hints[0] || "unbekannt",
          value: bestMatch.value,
        });
      }
    }
  });
  
  // Select-Felder
  const selects = document.querySelectorAll("select");
  selects.forEach(select => {
    if (select.disabled) return;
    
    const hints = getFieldHints(select);
    if (hints.length === 0) return;
    
    let bestMatch = null;
    let bestPriority = -1;
    
    for (const mapping of FIELD_MAPPINGS) {
      if (matchesKeywords(hints, mapping.keywords) && mapping.priority > bestPriority) {
        bestMatch = mapping;
        bestPriority = mapping.priority;
      }
    }
    
    if (bestMatch && bestMatch.value) {
      if (setSelectValue(select, bestMatch.value)) {
        filledCount++;
        results.push({
          field: hints[0] || "unbekannt",
          value: bestMatch.value,
        });
      }
    }
  });
  
  return { filledCount, results };
}

// ─── MESSAGE HANDLER ────────────────────────────────────────────────────────

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.action === "fillForm") {
    const result = fillAllFields();
    sendResponse(result);
  } else if (message.action === "getFieldCount") {
    // Wie viele ausfüllbare Felder gibt es?
    const inputs = document.querySelectorAll(
      'input[type="text"], input[type="email"], input[type="tel"], ' +
      'input[type="url"], input[type="search"], input[type="number"], ' +
      'input:not([type]), textarea, select'
    );
    let count = 0;
    inputs.forEach(f => {
      if (f.type !== "hidden" && !f.disabled && !f.readOnly) count++;
    });
    sendResponse({ fieldCount: count });
  }
  return true;
});
