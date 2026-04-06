'use client'

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'

// ═══════════════════════════════════════════════════
// Тил турлари
// ═══════════════════════════════════════════════════

export type LangCode = 'en' | 'ru' | 'uz-lat' | 'uz-cyr'

interface LangContextValue {
  lang: LangCode
  setLang: (lang: LangCode) => void
  t: (key: string) => string
  isUzbek: boolean
  isLatin: boolean
  isCyrillic: boolean
}

const LangContext = createContext<LangContextValue>({
  lang: 'uz-cyr', setLang: () => {}, t: (k) => k,
  isUzbek: true, isLatin: false, isCyrillic: true
})

export const useLang = () => useContext(LangContext)

// ═══════════════════════════════════════════════════
// Таржималар базаси
// ═══════════════════════════════════════════════════

const translations: Record<string, Record<LangCode, string>> = {
  // Навигация
  'nav.dashboard': { en: 'Dashboard', ru: 'Дашборд', 'uz-lat': 'Dashboard', 'uz-cyr': 'Дашборд' },
  'nav.paragraphs': { en: 'Paragraphs', ru: 'Хатбошилар', 'uz-lat': 'Xatboshilar', 'uz-cyr': 'Хатбошилар' },
  'nav.projects': { en: 'Projects', ru: 'Проекты', 'uz-lat': 'Loyihalar', 'uz-cyr': 'Лойиҳалар' },
  'nav.files': { en: 'Files', ru: 'Файлы', 'uz-lat': 'Fayllar', 'uz-cyr': 'Файллар' },
  'nav.rules': { en: 'Sayqallash DB', ru: 'Sayqallash DB', 'uz-lat': 'Sayqallash DB', 'uz-cyr': 'Sayqallash DB' },
  'nav.annotated': { en: 'Annotated', ru: 'Изоҳли луғат', 'uz-lat': 'Izohli lug\'at', 'uz-cyr': 'Изоҳли луғат' },
  'nav.disputed': { en: 'Disputed', ru: 'Мунозарали', 'uz-lat': 'Munozarali', 'uz-cyr': 'Мунозарали' },
  'nav.abbreviations': { en: 'Abbreviations', ru: 'Сокращения', 'uz-lat': 'Qisqartmalar', 'uz-cyr': 'Қисқартмалар' },
  'nav.synonyms': { en: 'Synonyms', ru: 'Синонимы', 'uz-lat': 'Sinonimlar', 'uz-cyr': 'Синонимлар' },
  'nav.dictionary': { en: 'Dictionary', ru: 'Словарь', 'uz-lat': 'Lug\'at', 'uz-cyr': 'Луғат' },
  'nav.affixFlags': { en: 'Affix Flags', ru: 'Аффикс флаги', 'uz-lat': 'Affix Flags', 'uz-cyr': 'Affix Flags' },
  'nav.admin': { en: 'Admin', ru: 'Админ', 'uz-lat': 'Admin', 'uz-cyr': 'Админ' },

  // Умумий
  'common.save': { en: 'Save', ru: 'Сохранить', 'uz-lat': 'Saqlash', 'uz-cyr': 'Сақлаш' },
  'common.delete': { en: 'Delete', ru: 'Удалить', 'uz-lat': 'O\'chirish', 'uz-cyr': 'Ўчириш' },
  'common.edit': { en: 'Edit', ru: 'Редактировать', 'uz-lat': 'Tahrirlash', 'uz-cyr': 'Таҳрирлаш' },
  'common.cancel': { en: 'Cancel', ru: 'Отмена', 'uz-lat': 'Bekor qilish', 'uz-cyr': 'Бекор қилиш' },
  'common.search': { en: 'Search...', ru: 'Поиск...', 'uz-lat': 'Qidirish...', 'uz-cyr': 'Қидириш...' },
  'common.loading': { en: 'Loading...', ru: 'Загрузка...', 'uz-lat': 'Yuklanmoqda...', 'uz-cyr': 'Юкланмоқда...' },
  'common.refresh': { en: 'Refresh', ru: 'Обновить', 'uz-lat': 'Yangilash', 'uz-cyr': 'Янгилаш' },
  'common.export': { en: 'Export', ru: 'Экспорт', 'uz-lat': 'Eksport', 'uz-cyr': 'Экспорт' },
  'common.all': { en: 'All', ru: 'Все', 'uz-lat': 'Barchasi', 'uz-cyr': 'Барчаси' },
  'common.close': { en: 'Close', ru: 'Закрыть', 'uz-lat': 'Yopish', 'uz-cyr': 'Ёпиш' },
  'common.confirm': { en: 'Confirm', ru: 'Подтвердить', 'uz-lat': 'Tasdiqlash', 'uz-cyr': 'Тасдиқлаш' },
  'common.yes': { en: 'Yes', ru: 'Да', 'uz-lat': 'Ha', 'uz-cyr': 'Ҳа' },
  'common.no': { en: 'No', ru: 'Нет', 'uz-lat': 'Yo\'q', 'uz-cyr': 'Йўқ' },
  'common.add': { en: 'Add', ru: 'Добавить', 'uz-lat': 'Qo\'shish', 'uz-cyr': 'Қўшиш' },
  'common.total': { en: 'Total', ru: 'Всего', 'uz-lat': 'Jami', 'uz-cyr': 'Жами' },
  'common.prev': { en: '← Previous', ru: '← Предыдущая', 'uz-lat': '← Oldingi', 'uz-cyr': '← Олдинги' },
  'common.next': { en: 'Next →', ru: 'Следующая →', 'uz-lat': 'Keyingi →', 'uz-cyr': 'Кейинги →' },
  'common.logout': { en: 'Logout', ru: 'Выйти', 'uz-lat': 'Chiqish', 'uz-cyr': 'Чиқиш' },

  // Dashboard
  'dashboard.title': { en: 'Dashboard', ru: 'Дашборд', 'uz-lat': 'Dashboard', 'uz-cyr': 'Дашборд' },
  'dashboard.welcome': { en: 'Welcome', ru: 'Добро пожаловать', 'uz-lat': 'Xush kelibsiz', 'uz-cyr': 'Хуш келибсиз' },
  'dashboard.upload': { en: 'Upload File', ru: 'Загрузить файл', 'uz-lat': 'Fayl yuklash', 'uz-cyr': 'Файл юклаш' },
  'dashboard.recent': { en: 'Recent Projects', ru: 'Недавние проекты', 'uz-lat': 'So\'nggi loyihalar', 'uz-cyr': 'Сўнгги лойиҳалар' },

  // Файллар
  'files.title': { en: 'Files Directory', ru: 'Директория файлов', 'uz-lat': 'Fayllar direktoriyasi', 'uz-cyr': 'Файллар директорияси' },
  'files.upload': { en: 'Upload File', ru: 'Загрузить файл', 'uz-lat': 'Fayl yuklash', 'uz-cyr': 'Файл юклаш' },
  'files.empty': { en: 'No files uploaded yet', ru: 'Файлы ещё не загружены', 'uz-lat': 'Fayllar hali yuklanmagan', 'uz-cyr': 'Файллар ҳали юкланмаган' },
  'files.newFolder': { en: '+ New Folder', ru: '+ Новая папка', 'uz-lat': '+ Yangi papka', 'uz-cyr': '+ Янги папка' },
  'files.open': { en: 'Open', ru: 'Открыть', 'uz-lat': 'Ochish', 'uz-cyr': 'Очиш' },

  // Лойиҳалар
  'projects.title': { en: 'Projects', ru: 'Проекты', 'uz-lat': 'Loyihalar', 'uz-cyr': 'Лойиҳалар' },
  'projects.textId': { en: 'Text №', ru: 'Матн №', 'uz-lat': 'Matn №', 'uz-cyr': 'Матн №' },
  'projects.specialist': { en: 'Specialist', ru: 'Мутахассис', 'uz-lat': 'Mutaxassis', 'uz-cyr': 'Мутахассис' },
  'projects.updated': { en: 'Updated', ru: 'Обновлено', 'uz-lat': 'Yangilangan', 'uz-cyr': 'Янгиланган' },
  'projects.actions': { en: 'Actions', ru: 'Действия', 'uz-lat': 'Amallar', 'uz-cyr': 'Амаллар' },

  // Синонимлар
  'synonyms.title': { en: 'Synonyms Database', ru: 'База синонимов', 'uz-lat': 'Sinonimlar bazasi', 'uz-cyr': 'Синонимлар базаси' },
  'synonyms.word': { en: 'Word', ru: 'Слово', 'uz-lat': 'So\'z', 'uz-cyr': 'Сўз' },
  'synonyms.add': { en: 'Add Synonym', ru: 'Добавить синоним', 'uz-lat': 'Sinonim qo\'shish', 'uz-cyr': 'Синоним қўшиш' },

  // Хатбошилар
  'paragraphs.title': { en: 'Paragraphs', ru: 'Хатбошилар', 'uz-lat': 'Xatboshilar', 'uz-cyr': 'Хатбошилар' },
  'paragraphs.empty': { en: 'No entries found', ru: 'Записи не найдены', 'uz-lat': 'Yozuvlar topilmadi', 'uz-cyr': 'Ёзувлар топилмади' },

  // Таҳрир
  'editor.save': { en: 'Save', ru: 'Сохранить', 'uz-lat': 'Saqlash', 'uz-cyr': 'Сақлаш' },
  'editor.export': { en: 'Export DOCX', ru: 'Экспорт DOCX', 'uz-lat': 'Eksport DOCX', 'uz-cyr': 'Экспорт DOCX' },
  'editor.finish': { en: 'Finish', ru: 'Завершить', 'uz-lat': 'Yakunlash', 'uz-cyr': 'Якунлаш' },
  'editor.cyrillic': { en: 'Cyrillic', ru: 'Кириллица', 'uz-lat': 'Kiril', 'uz-cyr': 'Кирил' },
  'editor.latin': { en: 'Latin', ru: 'Латиница', 'uz-lat': 'Lotin', 'uz-cyr': 'Лотин' },

  // Footer
  'footer.copyright': { en: '© 2026 Pharma Translation Platform', ru: '© 2026 Pharma Translation Platform', 'uz-lat': '© 2026 Pharma Translation Platform', 'uz-cyr': '© 2026 Pharma Translation Platform' },
  'footer.description': { en: 'State Pharmacopoeia Development System', ru: 'Система разработки государственной фармакопеи', 'uz-lat': 'Davlat farmakopeyasini ishlab chiqish tizimi', 'uz-cyr': 'Давлат фармакопеясини ишлаб чиқиш тизими' },

  // Sayqallash Rules page
  'rules.title': { en: 'Sayqallash Rules', ru: 'Правила Sayqallash', 'uz-lat': 'Sayqallash Qoidalari', 'uz-cyr': 'Sayqallash Қоидалари' },
  'rules.subtitle': { en: 'Spelling and correction rules database', ru: 'База правил орфографии и исправлений', 'uz-lat': 'Imlo xatoliklari va tuzatish qoidalari bazasi', 'uz-cyr': 'Имло хатоликлари ва тузатиш қоидалари базаси' },
  'rules.wrongForm': { en: 'Wrong form', ru: 'Неправильная форма', 'uz-lat': 'Xato shakl', 'uz-cyr': 'Хато шакл' },
  'rules.correctForm': { en: 'Correct form', ru: 'Правильная форма', 'uz-lat': 'To\'g\'ri shakl', 'uz-cyr': 'Тўғри шакл' },
  'rules.type': { en: 'Type', ru: 'Тип', 'uz-lat': 'Turi', 'uz-cyr': 'Тури' },
  'rules.frequency': { en: 'Frequency', ru: 'Частота', 'uz-lat': 'Chastota', 'uz-cyr': 'Частота' },
  'rules.modifiedBy': { en: 'Modified by', ru: 'Изменено', 'uz-lat': 'O\'zgartirgan', 'uz-cyr': 'Ўзгартирган' },
  'rules.actions': { en: 'Actions', ru: 'Действия', 'uz-lat': 'Amallar', 'uz-cyr': 'Амаллар' },
  'rules.add': { en: 'Add Rule', ru: 'Добавить правило', 'uz-lat': 'Yangi qoida', 'uz-cyr': 'Янги қоида' },

  // Dictionary
  'dict.title': { en: 'Dictionary — Hunspell', ru: 'Словарь — Hunspell', 'uz-lat': 'Lug\'at — Hunspell', 'uz-cyr': 'Луғат — Hunspell' },
  'dict.subtitle': { en: 'Uzbek spelling dictionary', ru: 'Узбекский орфографический словарь', 'uz-lat': 'O\'zbek tili imlo lug\'ati', 'uz-cyr': 'Ўзбек тили имло луғати' },
  'dict.word': { en: 'Word', ru: 'Слово', 'uz-lat': 'So\'z', 'uz-cyr': 'Сўз' },
  'dict.pos': { en: 'POS', ru: 'Тип', 'uz-lat': 'Turkum', 'uz-cyr': 'Туркум' },
  'dict.translation': { en: 'Translation', ru: 'Перевод', 'uz-lat': 'Tarjima', 'uz-cyr': 'Таржима' },
  'dict.definition': { en: 'Definition', ru: 'Определение', 'uz-lat': 'Izoh', 'uz-cyr': 'Изоҳ' },
  'dict.aiTranslate': { en: '🤖 AI Translate', ru: '🤖 AI Перевод', 'uz-lat': '🤖 AI Tarjima', 'uz-cyr': '🤖 AI Таржима' },

  // Affix Flags
  'affix.title': { en: 'Affix Flags — Hunspell', ru: 'Аффикс флаги — Hunspell', 'uz-lat': 'Affix Flags — Hunspell', 'uz-cyr': 'Affix Flags — Hunspell' },
  'affix.subtitle': { en: 'Suffix/Prefix rules', ru: 'Правила суффиксов и префиксов', 'uz-lat': 'Suffix/Prefix qoidalari', 'uz-cyr': 'Suffix/Prefix қоидалари' },
  'affix.flag': { en: 'Flag', ru: 'Флаг', 'uz-lat': 'Flag', 'uz-cyr': 'Flag' },
  'affix.count': { en: 'Count', ru: 'Кол-во', 'uz-lat': 'Soni', 'uz-cyr': 'Сони' },
  'affix.description': { en: 'Description', ru: 'Описание', 'uz-lat': 'Vazifa', 'uz-cyr': 'Вазифа' },
  'affix.examples': { en: 'Examples', ru: 'Примеры', 'uz-lat': 'Misol', 'uz-cyr': 'Мисол' },

  // Synonyms
  'syn.title': { en: 'Synonyms Database', ru: 'База синонимов', 'uz-lat': 'Sinonimlar bazasi', 'uz-cyr': 'Синонимлар базаси' },
  'syn.word': { en: 'Word', ru: 'Слово', 'uz-lat': 'So\'z', 'uz-cyr': 'Сўз' },
  'syn.synonyms': { en: 'Synonyms', ru: 'Синонимы', 'uz-lat': 'Sinonimlar', 'uz-cyr': 'Синонимлар' },
  'syn.lang': { en: 'Lang', ru: 'Язык', 'uz-lat': 'Til', 'uz-cyr': 'Тил' },
  'syn.add': { en: '+ Add Synonym', ru: '+ Добавить синоним', 'uz-lat': '+ Sinonim qo\'shish', 'uz-cyr': '+ СИНОНИМ ҚЎШИШ' },

  // Files
  'files.directory': { en: 'Files Directory', ru: 'Директория файлов', 'uz-lat': 'Fayllar direktoriyasi', 'uz-cyr': 'Файллар директорияси' },
  'files.archive': { en: 'Uploaded documents archive', ru: 'Архив загруженных документов', 'uz-lat': 'Yuklangan hujjatlar arxivi', 'uz-cyr': 'Юкланган ҳужжатлар архиви' },
  'files.uploadBtn': { en: 'UPLOAD FILE', ru: 'ЗАГРУЗИТЬ ФАЙЛ', 'uz-lat': 'FAYL YUKLASH', 'uz-cyr': 'ФАЙЛ ЮКЛАШ' },
  'files.dragHere': { en: 'Or drag file here', ru: 'Или перетащите файл сюда', 'uz-lat': 'Yoki faylni bu yerga torting', 'uz-cyr': 'Ёки файлни бу ерга тортинг' },

  // Paragraphs
  'para.title': { en: 'Paragraphs', ru: 'Параграфы', 'uz-lat': 'Xatboshilar', 'uz-cyr': 'Хатбошилар' },
  'para.subtitle': { en: 'Audit trail — all edits and AI processing history', ru: 'История всех правок и обработки AI', 'uz-lat': 'Audit trail — barcha tahrir va AI ishlov berish tarixi', 'uz-cyr': 'Audit trail — барча таҳрир ва AI ишлов бериш тарихи' },
  'para.specialist': { en: 'Specialist', ru: 'Специалист', 'uz-lat': 'Mutaxassis', 'uz-cyr': 'Мутахассис' },
  'para.actionType': { en: 'Action Type', ru: 'Тип действия', 'uz-lat': 'Amal turi', 'uz-cyr': 'Амал тури' },
  'para.date': { en: 'Date', ru: 'Дата', 'uz-lat': 'Sana', 'uz-cyr': 'Сана' },

  // Projects
  'proj.title': { en: 'Projects', ru: 'Проекты', 'uz-lat': 'Loyihalar', 'uz-cyr': 'Лойиҳалар' },
  'proj.subtitle': { en: 'List of all uploaded documents', ru: 'Список всех загруженных документов', 'uz-lat': 'Barcha yuklangan hujjatlar ro\'yxati', 'uz-cyr': 'Барча юкланган ҳужжатлар рўйхати' },
  'proj.textNum': { en: 'Text №', ru: 'Текст №', 'uz-lat': 'Matn №', 'uz-cyr': 'Матн №' },
  'proj.updated': { en: 'Updated', ru: 'Обновлено', 'uz-lat': 'Yangilangan', 'uz-cyr': 'Янгиланган' },
}

// ═══════════════════════════════════════════════════
// Провайдер
// ═══════════════════════════════════════════════════

export default function LanguageProvider({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<LangCode>('uz-cyr')

  useEffect(() => {
    const stored = localStorage.getItem('pharma_lang') as LangCode | null
    if (stored && ['en', 'ru', 'uz-lat', 'uz-cyr'].includes(stored)) {
      setLangState(stored)
    }
  }, [])

  const setLang = useCallback((newLang: LangCode) => {
    setLangState(newLang)
    localStorage.setItem('pharma_lang', newLang)
  }, [])

  const t = useCallback((key: string): string => {
    const entry = translations[key]
    if (!entry) return key
    return entry[lang] || entry['uz-cyr'] || key
  }, [lang])

  const value: LangContextValue = {
    lang,
    setLang,
    t,
    isUzbek: lang === 'uz-lat' || lang === 'uz-cyr',
    isLatin: lang === 'uz-lat',
    isCyrillic: lang === 'uz-cyr',
  }

  return <LangContext.Provider value={value}>{children}</LangContext.Provider>
}
