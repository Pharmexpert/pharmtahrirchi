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
