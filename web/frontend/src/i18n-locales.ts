export const languages = [
  {
    "code": "zh-CN",
    "name": "简体中文",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "zh-TW",
    "name": "繁體中文",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "en",
    "name": "English",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "ja",
    "name": "日本語",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "ko",
    "name": "한국어",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "es",
    "name": "Español",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "fr",
    "name": "Français",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "de",
    "name": "Deutsch",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "ru",
    "name": "Русский",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "pt-BR",
    "name": "Português (Brasil)",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "pt-PT",
    "name": "Português (Portugal)",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "it",
    "name": "Italiano",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "nl",
    "name": "Nederlands",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "pl",
    "name": "Polski",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "uk",
    "name": "Українська",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "tr",
    "name": "Türkçe",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "id",
    "name": "Bahasa Indonesia",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "vi",
    "name": "Tiếng Việt",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "th",
    "name": "ไทย",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "ms",
    "name": "Bahasa Melayu",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "hi",
    "name": "हिन्दी",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "bn",
    "name": "বাংলা",
    "dir": "ltr",
    "status": "PARTIAL"
  },
  {
    "code": "ur",
    "name": "اردو",
    "dir": "rtl",
    "status": "PARTIAL"
  },
  {
    "code": "ar",
    "name": "العربية",
    "dir": "rtl",
    "status": "PARTIAL"
  },
  {
    "code": "fa",
    "name": "فارسی",
    "dir": "rtl",
    "status": "PARTIAL"
  },
  {
    "code": "he",
    "name": "עברית",
    "dir": "rtl",
    "status": "PARTIAL"
  }
] as const;
export type UiLocale = typeof languages[number]["code"];
export const isUiLocale = (v: unknown): v is UiLocale => typeof v === "string" && languages.some(l => l.code === v);
