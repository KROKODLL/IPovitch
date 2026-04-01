import i18n from "i18next";
import { initReactI18next } from "react-i18next";
import en from "./locales/en.json";
import fr from "./locales/fr.json";

const stored = typeof localStorage !== "undefined" ? localStorage.getItem("nmv_lang") : null;
const fallback = stored === "fr" ? "fr" : "en";

void i18n.use(initReactI18next).init({
  interpolation: { escapeValue: false },
  lng: fallback,
  resources: {
    en: { translation: en },
    fr: { translation: fr },
  },
});

export function setLocale(code: "en" | "fr") {
  void i18n.changeLanguage(code);
  localStorage.setItem("nmv_lang", code);
}

export default i18n;
