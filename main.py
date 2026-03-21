#!/usr/bin/env python3
"""AVTOSERVIS BOT v3.2 — kassa module (balance, income, expense by category)"""

import os, json, logging, re
from datetime import datetime, date
import pg8000
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters, CallbackQueryHandler,
)

TOKEN        = os.environ.get("BOT_TOKEN", "")
OWNER_ID     = int(os.environ.get("OWNER_ID", "368817660"))
DATABASE_URL = os.environ.get("DATABASE_URL", "")
MORNING_HOUR_UTC = 4   # 09:00 Tashkent (UTC+5)
MORNING_MIN_UTC  = 0

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ══════════════════════════════════════════════
# ГЛОБАЛЬНЫЕ ДАННЫЕ
# ══════════════════════════════════════════════
STAFF: dict = {OWNER_ID: "Rahbar"}
ROLES: dict = {OWNER_ID: "owner"}
USER_LANG: dict = {}

ROLE_NAMES = {
    "uz": {"owner": "Rahbar 👑", "mechanic": "Mexanik 🔧", "wash": "Yuvuvchi 🚿",
           "tint": "Tonirovkachi 🪟", "body": "Kuzovchi 🔨", "elec": "Elektrik ⚡"},
    "ru": {"owner": "Руководитель 👑", "mechanic": "Механик 🔧", "wash": "Мойщик 🚿",
           "tint": "Тонировщик 🪟", "body": "Кузовщик 🔨", "elec": "Электрик ⚡"}
}

# Роли с доступом к запчастям
PARTS_ROLES = {"owner", "mechanic", "body", "elec"}
# Роли с доступом к оплате
PAY_ROLES   = {"owner", "mechanic"}

# Услуги по ролям (None = все)
ROLE_SERVICES = {
    "owner":    None,
    "mechanic": None,
    "wash":     ["🚿 Мойка", "🚿 Yuvish"],
    "tint":     ["🪟 Тонировка", "🪟 Tonirovka", "🛡 Бронеплёнка", "🛡 Himoya plyonka"],
    "body":     ["🔨 PDR (вмятина)", "🔨 PDR (botiq)", "✨ Полировка", "✨ Sayqallash"],
    "elec":     ["⚡ Электрика", "⚡ Elektr"],
}

# ══════════════════════════════════════════════
# ПЕРЕВОДЫ
# ══════════════════════════════════════════════
T = {
    "cancel":        {"uz": "◀️ Ortga",           "ru": "◀️ Назад"},
    "skip":          {"uz": "⏭ O'tkazib",          "ru": "⏭ Пропустить"},
    "done":          {"uz": "✅ Tayyor",            "ru": "✅ Готово"},
    "cancelled":     {"uz": "❌ Bekor qilindi.",    "ru": "❌ Отменено."},
    "only_owner":    {"uz": "⛔ Faqat rahbar.",     "ru": "⛔ Только для руководителя."},
    "no_access":     {"uz": "⛔ Ruxsat yo'q.",      "ru": "⛔ Нет доступа."},
    "no_open":       {"uz": "Ochiq buyurtma yo'q.", "ru": "Нет открытых заявок."},
    "enter_num":     {"uz": "Faqat raqam kiriting:","ru": "Введи только цифры:"},
    "not_found":     {"uz": "❌ Topilmadi.",        "ru": "❌ Не найдено."},
    "enter_order":   {"uz": "Buyurtma *raqamini* kiriting:\n📌 Misol: `1`",
                      "ru": "Введи *номер заявки:*\n📌 Пример: `1`"},
    "list_open_parts":  {"uz": "🔩 *Ochiq buyurtmalar:*", "ru": "🔩 *Открытые заявки:*"},
    "list_open_pay":    {"uz": "💰 *Ochiq buyurtmalar:*", "ru": "💰 *Открытые заявки:*"},
    "list_open_close":  {"uz": "✅ *Yopish:*",            "ru": "✅ *Закрыть:*"},
    "list_open_trans":  {"uz": "🔄 *Topshirish:*",        "ru": "🔄 *Передать:*"},
    "list_open_exp":    {"uz": "📤 *Xarajat:*",           "ru": "📤 *Расход:*"},
    "list_open_status": {"uz": "🔄 *Status:*",            "ru": "🔄 *Статус:*"},
    "list_open_edit":   {"uz": "✏️ *Tahrirlash:*",        "ru": "✏️ *Редактировать:*"},
    "works_label_short": {"uz": "🔧 *Ishlar / Работы:*\n", "ru": "🔧 *Работы:*\n"},
    "list_open_all":    {"uz": "📋 *Barcha ochiq ({n} ta):*", "ru": "📋 *Все открытые ({n}):*"},
    "list_open_my":     {"uz": "📋 *{name} ({n} ta):*",   "ru": "📋 *{name} ({n}):*"},
    "works_list_label": {"uz": "✅ *Ishlar:*",            "ru": "✅ *Работы:*"},
    "not_found_order":  {"uz": "❌ Buyurtma topilmadi.",  "ru": "❌ Заявка не найдена."},
    "choose_lang":   {"uz": "🌐 Tilni tanlang / Выберите язык:", "ru": "🌐 Tilni tanlang / Выберите язык:"},
    "lang_set":      {"uz": "✅ Til: O'zbek\n\nAmal tanlang:", "ru": "✅ Язык: Русский\n\nВыбери действие:"},

    # Кнопки меню
    "btn_accept":    {"uz": "🚗 Qabul",               "ru": "🚗 Принять"},
    "btn_my":        {"uz": "📋 Mening mashinalarim",  "ru": "📋 Мои машины"},
    "btn_all":       {"uz": "📋 Barcha ochiq",         "ru": "📋 Все открытые"},
    "btn_part":      {"uz": "🔩 Ehtiyot qism",         "ru": "🔩 Запчасть"},
    "btn_pay":       {"uz": "💰 To'lov",               "ru": "💰 Оплата"},
    "btn_expense":   {"uz": "📤 Xarajat",              "ru": "📤 Расход"},
    "btn_close":     {"uz": "✅ Yopish",               "ru": "✅ Закрыть"},
    "btn_history":   {"uz": "📞 Mijoz tarixi",         "ru": "📞 История клиента"},
    "btn_report":    {"uz": "📊 Hisobot",              "ru": "📊 Отчёт"},
    "btn_debts":     {"uz": "💸 Qarzlar",              "ru": "💸 Долги"},
    "btn_staff":     {"uz": "👥 Xodimlar",             "ru": "👥 Сотрудники"},
    "btn_myreport":  {"uz": "📊 Mening hisobotim",     "ru": "📊 Мой отчёт"},
    "btn_kassa":     {"uz": "💵 Kassa",                "ru": "💵 Касса"},
    "btn_add_svc":   {"uz": "➕ Xizmat qo'shish",      "ru": "➕ Добавить услугу"},
    "btn_transfer":  {"uz": "🔄 Topshirish",           "ru": "🔄 Передать"},
    "btn_status":    {"uz": "🔄 Status",               "ru": "🔄 Статус"},
    "btn_edit":      {"uz": "✏️ Tahrirlash",           "ru": "✏️ Редактировать"},

    # Статусы
    "st_accepted": {"uz": "qabul qilindi 📥", "ru": "принята 📥"},
    "st_in_work":  {"uz": "ishda 🔧",          "ru": "в работе 🔧"},
    "st_ready":    {"uz": "tayyor ✅",          "ru": "готова ✅"},
    "st_done":     {"uz": "berildi 🏁",         "ru": "выдана 🏁"},
    "st_closed":   {"uz": "yopildi ✅",         "ru": "закрыто ✅"},
    "statuses": {
        "uz": ["📥 Qabul qilindi", "🔧 Ishda", "✅ Tayyor", "🏁 Berildi"],
        "ru": ["📥 Принята",       "🔧 В работе", "✅ Готова", "🏁 Выдана"]
    },
    "status_map": {
        "📥 Qabul qilindi": "accepted", "📥 Принята":   "accepted",
        "🔧 Ishda":         "in_work",  "🔧 В работе":  "in_work",
        "✅ Tayyor":        "ready",    "✅ Готова":     "ready",
        "🏁 Berildi":       "delivered","🏁 Выдана":    "delivered",
    },

    # Приёмка
    "accept_hint": {
        "uz": "🚗 *Qabul*\n\nBir qatorda kiriting:\n`raqam * marka * ism`\n\n📌 Misol:\n`10C444TA * Nexia oq * Alisher`",
        "ru": "🚗 *Приёмка*\n\nВведи одной строкой:\n`номер * марка * имя клиента`\n\n📌 Пример:\n`10C444TA * Nexia белая * Алишер`"
    },
    "accept_fmt_err": {
        "uz": "❌ Format xato!\nTo'g'ri: `raqam * marka * ism`",
        "ru": "❌ Неверный формат!\nПравильно: `номер * марка * имя`"
    },
    "accept_phone": {
        "uz": "📱 *Telefon raqami (majburiy):*\n📌 Misol: `901112233`",
        "ru": "📱 *Телефон клиента (обязательно):*\n📌 Пример: `901112233`"
    },
    "phone_err": {
        "uz": "❌ Noto'g'ri format!\nMisol: `901112233` (9 raqam)",
        "ru": "❌ Неверный формат!\nПример: `901112233` (9 цифр)"
    },
    "accept_problem": {
        "uz": "📝 *Muammo / shikoyat:*\n📌 Misol: `Dvigatel tuki bor`",
        "ru": "📝 *Проблема / жалоба:*\n📌 Пример: `Стук в двигателе`"
    },
    "accept_master":  {"uz": "👨‍🔧 Qaysi usta?",  "ru": "👨‍🔧 Какой мастер?"},
    "accept_service": {"uz": "🔧 Xizmat turi:",  "ru": "🔧 Тип услуги:"},
    "accept_price_q": {
        "uz": "💰 *Taxminiy narx (ixtiyoriy):*\n📌 Misol: `500000` so'm\nYoki o'tkazib yuboring:",
        "ru": "💰 *Примерная цена (необязательно):*\n📌 Пример: `500000` сум\nИли пропустите:"
    },
    "accept_done": {
        "uz": "✅ *Buyurtma №{id}*\n🚗 {car} | {client}\n🔧 {service}\n📝 {problem}",
        "ru": "✅ *Заявка №{id}*\n🚗 {car} | {client}\n🔧 {service}\n📝 {problem}"
    },
    "repeat_client": {
        "uz": "\n\n⚡ Mijoz bizda *{n} marta* bo'lgan\nOxirgi: {date} | {svc}",
        "ru": "\n\n⚡ Клиент был у нас *{n} раз(а)*\nПоследний: {date} | {svc}"
    },
    "add_parts_q": {
        "uz": "🔩 Ehtiyot qism qo'shishni xohlaysizmi?",
        "ru": "🔩 Добавить запчасти?"
    },

    # Подвиды услуг
    "svc_sub_price": {
        "uz": "💰 *Narxini kiriting (to'liq summa):*\n📌 Misol: `500000` = 500 000 so'm",
        "ru": "💰 *Введи цену (полная сумма):*\n📌 Пример: `500000` = 500 000 сум"
    },
    "svc_works_hint": {
        "uz": ("📋 *Bajarilgan ishlar ro'yxatini kiriting*\n"
               "Har bir ish yangi qatorda:\n\n"
               "📌 Misol:\n`Moy almashtirish`\n`Tormoz kolodkasi`"),
        "ru": ("📋 *Введи список работ*\n"
               "Каждая работа с новой строки:\n\n"
               "📌 Пример:\n`Замена масла`\n`Замена колодок`")
    },
    "svc_works_prices_hint": {
        "uz": ("💰 *Narxlarni kiriting (to'liq summa)*\n"
               "Har bir narx yangi qatorda:\n\n"
               "📌 Misol ({works}):\n{example}"),
        "ru": ("💰 *Введи цены (полная сумма)*\n"
               "Каждая цена с новой строки:\n\n"
               "📌 Пример ({works}):\n{example}")
    },
    "svc_works_mismatch": {
        "uz": "❌ Narxlar soni ({n_prices}) ishlar soniga ({n_works}) mos kelmaydi!\nQayta kiriting:",
        "ru": "❌ Количество цен ({n_prices}) не совпадает с количеством работ ({n_works})!\nВведи заново:"
    },

    # Подвиды тонировки / плёнки / мойки
    "tint_subs": {
        "uz": ["🪟 Full (barcha oynalar)", "🪟 Orqa oynalar", "🪟 Old oynalar",
               "🪟 Faqat orqa shisha", "🪟 Faqat old shisha (lob)"],
        "ru": ["🪟 Full (все окна)", "🪟 Задние окна", "🪟 Передние окна",
               "🪟 Только заднее стекло", "🪟 Только лобовое"]
    },
    "film_subs": {
        "uz": ["🛡 Salon laminatsiya", "🛡 Far laminatsiya", "🛡 Kuzov detallari", "🛡 To'liq kuzov"],
        "ru": ["🛡 Ламинация салона", "🛡 Ламинация фар", "🛡 Детали кузова", "🛡 Полный кузов"]
    },
    "wash_subs": {
        "uz": ["🚿 Kuzov", "🚿 Motor", "🚿 Kuzov + Motor"],
        "ru": ["🚿 Кузов", "🚿 Двигатель", "🚿 Кузов + Двигатель"]
    },

    # Услуги
    "svc": {
        "uz": ["🔧 Ko'taruvchi/ta'mir", "🛢 Moy almashtirish", "⚡ Elektr",
               "🚿 Yuvish", "✨ Sayqallash", "🪟 Tonirovka",
               "🔨 PDR (botiq)", "🛡 Himoya plyonka", "🔩 Boshqa"],
        "ru": ["🔧 Подъёмник/ремонт", "🛢 Замена масла", "⚡ Электрика",
               "🚿 Мойка", "✨ Полировка", "🪟 Тонировка",
               "🔨 PDR (вмятина)", "🛡 Бронеплёнка", "🔩 Другое"]
    },
    "svc_with_works": {
        "uz": ["🔧 Ko'taruvchi/ta'mir", "⚡ Elektr", "🔨 PDR (botiq)"],
        "ru": ["🔧 Подъёмник/ремонт", "⚡ Электрика", "🔨 PDR (вмятина)"]
    },
    "svc_with_subs": {
        "uz": ["🚿 Yuvish", "🪟 Tonirovka", "🛡 Himoya plyonka"],
        "ru": ["🚿 Мойка", "🪟 Тонировка", "🛡 Бронеплёнка"]
    },

    # Запчасти
    "part_name_q": {
        "uz": "🔩 *Ehtiyot qism nomi:*\n📌 Misol: `Sharovoy chap`",
        "ru": "🔩 *Название запчасти:*\n📌 Пример: `Шаровой левый`"
    },
    "part_source_q": {"uz": "*{name}*\n\nManba:", "ru": "*{name}*\n\nИсточник:"},
    "part_cost_q": {
        "uz": "💸 *Tannarxi (to'liq summa):*\n📌 Misol: `350000`",
        "ru": "💸 *Себестоимость (полная сумма):*\n📌 Пример: `350000`"
    },
    "part_sell_q": {
        "uz": "💰 *Mijoz narxi (to'liq summa):*\n📌 Misol: `420000`",
        "ru": "💰 *Цена клиенту (полная сумма):*\n📌 Пример: `420000`"
    },
    "part_work_q": {
        "uz": "💰 *Ish narxi (to'liq summa):*\n_(Mijoz o'z zapchastini olib keldi)_\n📌 Misol: `50000`",
        "ru": "💰 *Цена работы (полная сумма):*\n_(Клиент привёз свою запчасть)_\n📌 Пример: `50000`"
    },
    "part_added": {
        "uz": "✅ *{name}* qo'shildi\n💰 {sell} so'm\n\nYana ehtiyot qism?",
        "ru": "✅ *{name}* добавлена\n💰 {sell} сум\n\nЕщё запчасть?"
    },
    "src_stock":    {"uz": "📦 Ombordan",        "ru": "📦 Со склада"},
    "src_client":   {"uz": "👤 Mijoz olib keldi", "ru": "👤 Клиент привёз"},
    "src_bought":   {"uz": "🛒 Biz oldik",        "ru": "🛒 Мы купили"},
    "part_more":    {"uz": "➕ Yana qo'shing yoki *Tayyor*:", "ru": "➕ Ещё или *Готово*:"},
    "part_done_msg":{"uz": "✅ *{n} ta qo'shildi №{id}*\n{lines}", "ru": "✅ *{n} запч. к №{id}*\n{lines}"},
    "part_err":     {"uz": "⚠️ Qo'shilmadi: {v}", "ru": "⚠️ Не добавлено: {v}"},

    # Расходы
    "exp_title":  {"uz": "📤 *Xarajat*\n",  "ru": "📤 *Расход*\n"},
    "exp_type_q": {"uz": "Xarajat turi:",   "ru": "Тип расхода:"},
    "exp_desc_q": {"uz": "📝 Izoh (yoki O'tkazib):", "ru": "📝 Описание (или Пропустить):"},
    "exp_amt_q":  {
        "uz": "💸 *Xarajat summasi (to'liq):*\n📌 Misol: `60000`",
        "ru": "💸 *Сумма расхода (полная):*\n📌 Пример: `60000`"
    },
    "exp_done":   {"uz": "📤 Xarajat #{id}: {type} — {amt} so'm", "ru": "📤 Расход #{id}: {type} — {amt} сум"},
    "exp_benzin": {"uz": "🚗 Benzin/yetkazish",    "ru": "🚗 Бензин/доставка"},
    "exp_parts":  {"uz": "🛒 Ehtiyot qism sotib",  "ru": "🛒 Покупка запчастей"},
    "exp_master": {"uz": "👨‍🔧 Chaqirilgan usta",   "ru": "👨‍🔧 Вызывной мастер"},
    "exp_tool":   {"uz": "🧰 Asbob/sarflanadigan", "ru": "🧰 Инструмент/расходники"},
    "exp_other":  {"uz": "💰 Boshqa",              "ru": "💰 Другое"},

    # Оплата
    "pay_invoice": {
        "uz": ("🧾 *Hisob №{id}*\n\n{works}{parts}{expenses}"
               "─────────────\n💰 *Jami: {total} so'm*\n✅ To'landi: {paid} so'm\n⏳ *Qoldiq: {remaining} so'm*"),
        "ru": ("🧾 *Счёт №{id}*\n\n{works}{parts}{expenses}"
               "─────────────\n💰 *Итого: {total} сум*\n✅ Оплачено: {paid} сум\n⏳ *Остаток: {remaining} сум*")
    },
    "pay_no_price": {
        "uz": "⚠️ *Buyurtma №{id}* — narx belgilanmagan!\n\nNarxni kiriting:",
        "ru": "⚠️ *Заявка №{id}* — цена не указана!\n\nВведи цену:"
    },
    "pay_set_price": {
        "uz": "💰 *Narxini kiriting (to'liq summa):*\n📌 Misol: `500000`",
        "ru": "💰 *Введи цену (полная сумма):*\n📌 Пример: `500000`"
    },
    "pay_method_q": {"uz": "💳 To'lov usuli:",  "ru": "💳 Способ оплаты:"},
    "pay_amt_q": {
        "uz": "💵 *Summa (to'liq, UZS):*\n📌 Misol: `500000`",
        "ru": "💵 *Сумма (полностью, UZS):*\n📌 Пример: `500000`"
    },
    "pay_rate_q": {
        "uz": "💱 *Dollar kursi:*\n📌 Misol: `12800`",
        "ru": "💱 *Курс доллара:*\n📌 Пример: `12800`"
    },
    "pay_usd_q": {
        "uz": "💵 *Dollar miqdori ($):*\n📌 Misol: `50`",
        "ru": "💵 *Сумма в долларах ($):*\n📌 Пример: `50`"
    },
    "pay_added": {
        "uz": "✅ {method}: {amt} so'm\n⏳ Qoldiq: {rem} so'm",
        "ru": "✅ {method}: {amt} сум\n⏳ Остаток: {rem} сум"
    },
    "pay_done": {
        "uz": "✅ *To'lov №{id}*\n💰 Jami: {total} so'm",
        "ru": "✅ *Оплата №{id}*\n💰 Итого: {total} сум"
    },
    "pay_methods": {
        "uz": ["💵 Naqd UZS", "💵 Naqd USD", "💳 Karta", "🏦 O'tkazma", "📝 Qarz"],
        "ru": ["💵 Наличные UZS", "💵 Наличные USD", "💳 Карта", "🏦 Перечисление", "📝 Долг"]
    },

    # Закрытие
    "close_no_pay":   {"uz": "⛔ *Avval to'lovni rasmiylashtiring!*", "ru": "⛔ *Сначала оформи оплату!*"},
    "close_no_right": {"uz": "⛔ Siz bu buyurtmani yopa olmaysiz.",   "ru": "⛔ Вы не можете закрыть эту заявку."},
    "close_done": {
        "uz": "✅ *№{id} yopildi!*\n🚗 {car} | {client}\n📞 *{phone}*{debt}\n\n{summary}",
        "ru": "✅ *№{id} закрыта!*\n🚗 {car} | {client}\n📞 *{phone}*{debt}\n\n{summary}"
    },
    "close_debt_w":  {"uz": "\n⚠️ Qarz bor!", "ru": "\n⚠️ Есть долг!"},
    "close_summary": {
        "uz": "📊 *Yakun:*\n💰 To'landi: {paid} so'm\n📤 Xarajat: {exp} so'm\n✅ Sof: {net} so'm",
        "ru": "📊 *Итог:*\n💰 Оплачено: {paid} сум\n📤 Расходы: {exp} сум\n✅ Чистая: {net} сум"
    },

    # Передача
    "transfer_who":  {"uz": "🔄 *Topshirish*\n\nKimga topshirasiz?", "ru": "🔄 *Передать*\n\nКому передаёте?"},
    "transfer_done": {"uz": "✅ №{id} — {master}ga topshirildi.",     "ru": "✅ №{id} передана — {master}."},

    # Статус
    "status_q":   {"uz": "🔄 Yangi status:", "ru": "🔄 Новый статус:"},
    "status_set": {"uz": "✅ №{id} status: *{status}*", "ru": "✅ №{id} статус: *{status}*"},

    # Редактирование
    "edit_q":       {"uz": "✏️ *Tahrirlash №{id}*\n\nNimani o'zgartirish kerak?",
                     "ru": "✏️ *Редактировать №{id}*\n\nЧто изменить?"},
    "edit_fields":  {"uz": ["👤 Ism", "📱 Telefon", "💰 Narx"],
                     "ru": ["👤 Имя", "📱 Телефон", "💰 Цена"]},
    "edit_name_q":  {"uz": "👤 Yangi ism:",         "ru": "👤 Новое имя:"},
    "edit_phone_q": {"uz": "📱 Yangi telefon:",      "ru": "📱 Новый телефон:"},
    "edit_price_q": {"uz": "💰 Yangi narx (to'liq summa):", "ru": "💰 Новая цена (полная сумма):"},
    "edit_done":    {"uz": "✅ *№{id}* yangilandi.", "ru": "✅ *№{id}* обновлена."},

    "card_debt":     {"uz": " 💸QARZ", "ru": " 💸ДОЛГ"},

    # Детали
    "btn_details":   {"uz": "📋 Tafsilotlar", "ru": "📋 Детали"},
    "details_title": {"uz": "📋 *Buyurtma №{id} tafsilotlari*\n", "ru": "📋 *Детали заявки №{id}*\n"},
    "details_dates": {
        "uz": "📅 Qabul: {start}\n✅ Yopildi: {end}\n⏱ Davomiyligi: {duration}",
        "ru": "📅 Приём: {start}\n✅ Закрыто: {end}\n⏱ Длительность: {duration}"
    },
    "details_works": {"uz": "\n🔧 *Ishlar:*",          "ru": "\n🔧 *Работы:*"},
    "details_parts": {"uz": "\n🔩 *Ehtiyot qismlar:*",  "ru": "\n🔩 *Запчасти:*"},
    "details_total": {"uz": "\n💰 *Jami to'lov: {total} so'm*", "ru": "\n💰 *Итого: {total} сум*"},

    # История
    "hist_q": {
        "uz": "📞 *Mijoz qidirish*\n\nTelefon kiriting:\n📌 Misol: `901112233`\n\nYoki mashina raqami:\n📌 Misol: `10C444TA`",
        "ru": "📞 *Поиск клиента*\n\nВведи телефон:\n📌 Пример: `901112233`\n\nИли номер машины:\n📌 Пример: `10C444TA`"
    },
    "hist_none":   {"uz": "🔍 '{q}' bo'yicha topilmadi.", "ru": "🔍 По '{q}' ничего не найдено."},
    "hist_header": {
        "uz": "👤 *{name}* | {phone}\n📊 {n} ta tashrif | Jami: {total} so'm",
        "ru": "👤 *{name}* | {phone}\n📊 Визитов: {n} | Итого: {total} сум"
    },

    # Отчёт
    "rep_title":   {"uz": "📊 *{date} hisoboti*\n",      "ru": "📊 *Отчёт за {date}*\n"},
    "rep_orders":  {"uz": "📋 Buyurtmalar: {t} | Yopilgan: {c} | Ishda: {w}",
                    "ru": "📋 Заявок: {t} | Закрыто: {c} | В работе: {w}"},
    "rep_income":  {"uz": "\n💰 *Tushum: {v} so'm*",     "ru": "\n💰 *Приход: {v} сум*"},
    "rep_uzs":     {"uz": "  💵 Naqd UZS: {v} so'm",    "ru": "  💵 Наличные UZS: {v} сум"},
    "rep_usd":     {"uz": "  💵 Naqd USD: {v} so'm",    "ru": "  💵 Наличные USD: {v} сум"},
    "rep_card":    {"uz": "  💳 Karta: {v} so'm",       "ru": "  💳 Карта: {v} сум"},
    "rep_bank":    {"uz": "  🏦 O'tkazma: {v} so'm",    "ru": "  🏦 Перечисление: {v} сум"},
    "rep_debt":    {"uz": "  📝 Qarzlar: {v} so'm",     "ru": "  📝 Долги: {v} сум"},
    "rep_expense": {"uz": "\n📤 Xarajatlar: {v} so'm",   "ru": "\n📤 Расходы: {v} сум"},
    "rep_margin":  {"uz": "📈 Ehtiyot qism foydasi: {v} so'm", "ru": "📈 Маржа запчастей: {v} сум"},
    "rep_profit":  {"uz": "\n✅ *Sof foyda: {v} so'm*",  "ru": "\n✅ *Чистая прибыль: {v} сум*"},
    "rep_none":    {"uz": "Bugun buyurtma yo'q.",          "ru": "Сегодня заявок нет."},
    "myreport": {
        "uz": "📊 *{name}*\n\n🔧 Ishda: {active} ta\n✅ Bugun yopilgan: {closed} ta\n💰 Bugun tushum: {income} so'm",
        "ru": "📊 *{name}*\n\n🔧 В работе: {active}\n✅ Закрыто сегодня: {closed}\n💰 Приход сегодня: {income} сум"
    },

    # Долги
    "debt_title":  {"uz": "💸 *Qarzlar ({n}) — {total} so'm*\n", "ru": "💸 *Долги ({n}) — {total} сум*\n"},
    "debt_none":   {"uz": "✅ Qarz yo'q!",  "ru": "✅ Долгов нет!"},
    "debt_cmd":    {"uz": "\nYopish: /qarz RAQAM", "ru": "\nЗакрыть: /debt НОМЕР"},
    "debt_closed": {"uz": "✅ #{id} qarzi yopildi!", "ru": "✅ Долг по №{id} закрыт!"},

    # Добавить услугу
    "add_svc_order": {
        "uz": "➕ *Xizmat qo'shish*\n\nQaysi mashinaga?\n\n{orders}\n\nBuyurtma raqamini kiriting:",
        "ru": "➕ *Добавить услугу*\n\nК какой машине?\n\n{orders}\n\nВведи номер заявки:"
    },
    "add_svc_done": {
        "uz": "✅ *Xizmat qo'shildi №{id}*\n🔧 {svc}\n👤 {master}\n💰 {total} so'm",
        "ru": "✅ *Услуга добавлена к №{id}*\n🔧 {svc}\n👤 {master}\n💰 {total} сум"
    },

    # Касса
    "kassa_title":     {"uz": "💵 *Kassa holati ({date})*\n",          "ru": "💵 *Касса на {date}*\n"},
    "kassa_cash":      {"uz": "💵 Naqd UZS:      *{v} so'm*",         "ru": "💵 Наличные UZS:   *{v} сум*"},
    "kassa_usd":       {"uz": "💵 Naqd USD:      *${usd}* ({v} so'm)","ru": "💵 Наличные USD:   *${usd}* ({v} сум)"},
    "kassa_card":      {"uz": "💳 Karta:         *{v} so'm*",         "ru": "💳 Карта:          *{v} сум*"},
    "kassa_bank":      {"uz": "🏦 O'tkazma:      *{v} so'm*",         "ru": "🏦 Перечисление:   *{v} сум*"},
    "kassa_debt":      {"uz": "📝 Qarz:          *{v} so'm*",         "ru": "📝 Долг (ожидается): *{v} сум*"},
    "kassa_total":     {"uz": "─────────────\n✅ *Jami tushum: {v} so'm*","ru": "─────────────\n✅ *Итого приход: {v} сум*"},
    "kassa_exp":       {"uz": "📤 Xarajatlar:    *{v} so'm*",         "ru": "📤 Расходы:        *{v} сум*"},
    "kassa_net":       {"uz": "💰 *Sof foyda:    {v} so'm*",          "ru": "💰 *Чистая прибыль: {v} сум*"},
    "kassa_none":      {"uz": "Bugun to'lov yo'q.", "ru": "Сегодня оплат нет."},
    "kassa_my_title":  {"uz": "💵 *{name} — bugungi kassa*\n",        "ru": "💵 *{name} — касса за сегодня*\n"},
    "kassa_my_works":  {
        "uz": "🔧 *Bajarilgan ishlar:*\n{lines}\n\n💰 *Jami: {total} so'm*",
        "ru": "🔧 *Выполненные работы:*\n{lines}\n\n💰 *Итого: {total} сум*"
    },
    "kassa_my_exp":    {
        "uz": "\n📤 *Xarajatlarim: {total} so'm*\n{lines}",
        "ru": "\n📤 *Мои расходы: {total} сум*\n{lines}"
    },
    "kassa_my_net":    {"uz": "\n✅ *Sof: {v} so'm*",  "ru": "\n✅ *Итого на руках: {v} сум*"},
    "kassa_my_none":   {"uz": "Bugun bajarilgan ish yo'q.", "ru": "Сегодня выполненных работ нет."},
    "kassa_exp_detail":{"uz": "\n📤 *Xarajatlar bo'yicha:*", "ru": "\n📤 *Расходы по сотрудникам:*"},

    # Сотрудники
    "staff_title": {"uz": "👥 *Xodimlar:*\n", "ru": "👥 *Сотрудники:*\n"},

    # Уведомления мастерам
    "notify_assigned": {
        "uz": "🚗 *Yangi mashina №{id}!*\n{car} | {client}\n🔧 {service}\n📝 {problem}",
        "ru": "🚗 *Новая машина №{id}!*\n{car} | {client}\n🔧 {service}\n📝 {problem}"
    },
    "notify_transferred": {
        "uz": "🔄 *№{id} sizga topshirildi*\n{car} | {client}\n👤 {from_master}dan",
        "ru": "🔄 *№{id} передана вам*\n{car} | {client}\n👤 от {from_master}"
    },
    "notify_paid": {
        "uz": "✅ *№{id} to'liq to'landi*\n{car} | {client}\n💰 {total} so'm — olib ketishga tayyor",
        "ru": "✅ *№{id} полностью оплачена*\n{car} | {client}\n💰 {total} сум — готова к выдаче"
    },

    # ── Касса ─────────────────────────────────────
    "kassa_btn_balance":  {"uz": "💰 Balans",          "ru": "💰 Баланс"},
    "kassa_btn_income":   {"uz": "➕ Kirim",            "ru": "➕ Приход"},
    "kassa_btn_expense":  {"uz": "➖ Chiqim",           "ru": "➖ Расход"},
    "kassa_btn_history":  {"uz": "📜 Tarix",            "ru": "📜 История"},
    "kassa_menu_title":   {"uz": "💵 *Kassa*\n\nNimani qilmoqchisiz?",
                           "ru": "💵 *Касса*\n\nЧто хотите сделать?"},
    "kassa_balance_title": {
        "uz": ("💰 *Kassa balansi*\n\n"
               "📥 Jami kirim:    *{income} so'm*\n"
               "📤 Jami chiqim:  *{expense} so'm*\n"
               "─────────────────\n"
               "✅ *Joriy balans: {balance} so'm*\n\n"
               "📅 Bugun kirimi:  {today_in} so'm\n"
               "📅 Bugun chiqimi: {today_out} so'm"),
        "ru": ("💰 *Баланс кассы*\n\n"
               "📥 Всего приходов:  *{income} сум*\n"
               "📤 Всего расходов: *{expense} сум*\n"
               "─────────────────\n"
               "✅ *Текущий баланс: {balance} сум*\n\n"
               "📅 Сегодня приход:  {today_in} сум\n"
               "📅 Сегодня расход:  {today_out} сум")
    },
    "kassa_inc_amt_q":    {"uz": "➕ *Kirim*\n\nSumma (to'liq):\n📌 Misol: `500000`",
                           "ru": "➕ *Приход*\n\nСумма (полностью):\n📌 Пример: `500000`"},
    "kassa_inc_method_q": {"uz": "💳 To'lov usuli:", "ru": "💳 Способ поступления:"},
    "kassa_inc_desc_q":   {"uz": "📝 *Izoh — mablag' qaerdan keldi?*\n📌 Misol: `Egasidan qarz`",
                           "ru": "📝 *Описание — откуда деньги?*\n📌 Пример: `Займ от владельца`"},
    "kassa_inc_done":     {"uz": "✅ *Kirim qo'shildi*\n💰 {amount} so'm ({method})\n📝 {desc}",
                           "ru": "✅ *Приход добавлен*\n💰 {amount} сум ({method})\n📝 {desc}"},
    "kassa_exp_cat_q":    {"uz": "➖ *Chiqim*\n\nChiqim turi:", "ru": "➖ *Расход*\n\nТип расхода:"},
    "kassa_exp_cat_order": {"uz": "🚗 Mashina bo'yicha",  "ru": "🚗 По машине"},
    "kassa_exp_cat_master":{"uz": "👨\u200d🔧 Masterlarga", "ru": "👨\u200d🔧 Мастерам"},
    "kassa_exp_cat_other": {"uz": "💼 Boshqa",            "ru": "💼 Прочее"},
    "kassa_exp_order_q":  {"uz": "🚗 Qaysi mashina?\n\nBuyurtma raqamini kiriting:",
                           "ru": "🚗 К какой машине?\n\nВведи номер заявки:"},
    "kassa_exp_master_q": {"uz": "👨\u200d🔧 Qaysi mastarga?", "ru": "👨\u200d🔧 Какому мастеру?"},
    "kassa_exp_desc_q":   {"uz": "📝 *Izoh (majburiy):*\n📌 Misol: `Yog' sotib olindi`",
                           "ru": "📝 *Описание (обязательно):*\n📌 Пример: `Куплено масло`"},
    "kassa_exp_amt_q":    {"uz": "💸 *Summa (to'liq):*\n📌 Misol: `150000`",
                           "ru": "💸 *Сумма (полностью):*\n📌 Пример: `150000`"},
    "kassa_exp_method_q": {"uz": "💳 Qanday to'landi?", "ru": "💳 Как выплачено?"},
    "kassa_exp_done":     {"uz": "✅ *Chiqim qo'shildi*\n💸 {amount} so'm\n📂 {category}\n📝 {desc}",
                           "ru": "✅ *Расход добавлен*\n💸 {amount} сум\n📂 {category}\n📝 {desc}"},
    "kassa_history_title":{"uz": "📜 *Kassa tarixi* (oxirgi {n} ta):\n",
                           "ru": "📜 *История кассы* (последние {n}):\n"},
    "kassa_history_none": {"uz": "Hali operatsiya yo'q.", "ru": "Операций пока нет."},
    "kassa_methods":      {"uz": ["💵 Naqd UZS","💳 Karta","🏦 O'tkazma","💵 Naqd USD"],
                           "ru": ["💵 Наличные UZS","💳 Карта","🏦 Перечисление","💵 Наличные USD"]},

    # Утреннее уведомление
    "morning_msg": {
        "uz": ("🌅 *Bugungi holat*\n\n"
               "🔧 Ochiq buyurtmalar: *{open_count}* ta\n{open_lines}"
               "💸 To'lanmagan qarzlar: *{debt_count}* ta — *{debt_total} so'm*\n{debt_lines}"),
        "ru": ("🌅 *Утренний отчёт*\n\n"
               "🔧 Открытых заявок: *{open_count}*\n{open_lines}"
               "💸 Непогашенных долгов: *{debt_count}* — *{debt_total} сум*\n{debt_lines}")
    },
}


def tr(key, uid, **kw):
    language = USER_LANG.get(uid, "ru")
    v = T.get(key, {})
    text = v.get(language, v.get("ru", key))
    if kw:
        try:
            text = text.format(**kw)
        except Exception:
            pass
    return text


def lg(uid): return USER_LANG.get(uid, "ru")
def get_services(uid): return T["svc"][lg(uid)]
def get_pay_methods(uid): return T["pay_methods"][lg(uid)]
def get_expenses_list(uid): return [tr(k, uid) for k in ["exp_benzin","exp_parts","exp_master","exp_tool","exp_other"]]
def get_tint_subs(uid): return T["tint_subs"][lg(uid)]
def get_film_subs(uid): return T["film_subs"][lg(uid)]
def get_wash_subs(uid): return T["wash_subs"][lg(uid)]
def svc_needs_works(svc, uid): return svc in T["svc_with_works"][lg(uid)]
def svc_needs_subs(svc, uid): return svc in T["svc_with_subs"][lg(uid)]


def get_available_services(uid):
    role = ROLES.get(uid, "mechanic")
    allowed = ROLE_SERVICES.get(role)
    if allowed is None:
        return get_services(uid)
    return [s for s in get_services(uid) if s in allowed]


def status_label(status, uid):
    mapping = {
        "accepted":  "st_accepted",
        "in_work":   "st_in_work",
        "ready":     "st_ready",
        "delivered": "st_done",
        "closed":    "st_closed",
    }
    return tr(mapping.get(status, "st_in_work"), uid)


# ══════════════════════════════════════════════
# СОСТОЯНИЯ
# ══════════════════════════════════════════════
(
    A_CAR_LINE, A_PHONE, A_PROBLEM, A_MASTER, A_SERVICE,
    A_SVC_SUB, A_ACCEPT_PRICE,
    A_WORKS_LIST, A_WORKS_PRICE,
    AFTER_ACCEPT,
    P_ORDER, P_NAME, P_SOURCE, P_COST, P_SELL, P_MORE,
    PAY_ORDER, PAY_PRICE, PAY_METHOD, PAY_AMOUNT, PAY_RATE,
    EXP_ORDER, EXP_TYPE, EXP_DESC, EXP_AMOUNT,
    CLOSE_ORDER,
    HIST_PHONE,
    AS_ORDER, AS_SERVICE, AS_SUB, AS_WORKS_LIST, AS_WORKS_PRICE, AS_PRICE,
    TR_ORDER, TR_MASTER,
    ST_ORDER, ST_STATUS,
    ED_ORDER, ED_FIELD, ED_VALUE,
    # Касса
    KA_MENU, KA_INC_AMT, KA_INC_METHOD, KA_INC_DESC,
    KA_EXP_CAT, KA_EXP_ORDER, KA_EXP_MASTER, KA_EXP_DESC, KA_EXP_AMT, KA_EXP_METHOD,
) = range(50)

# ══════════════════════════════════════════════
# БАЗА ДАННЫХ
# ══════════════════════════════════════════════
def get_conn():
    import urllib.parse
    r = urllib.parse.urlparse(DATABASE_URL)
    conn = pg8000.connect(
        host=r.hostname,
        port=r.port or 5432,
        database=r.path.lstrip("/"),
        user=r.username,
        password=r.password,
        ssl_context=True if "railway" in (r.hostname or "") else None,
    )
    return conn


def db_run(sql, params=None, fetch=False):
    pg_sql = re.sub(r'[$][0-9]+', '%s', sql)
    conn = get_conn()
    try:
        cur = conn.cursor()
        if params:
            cur.execute(pg_sql, list(params))
        else:
            cur.execute(pg_sql)
        if fetch:
            cols = [d[0] for d in cur.description] if cur.description else []
            rows = cur.fetchall()
            return [dict(zip(cols, row)) for row in rows]
        conn.commit()
        return []
    except Exception as e:
        logger.error(f"db_run error: {e} | SQL: {pg_sql[:120]} | params: {params}")
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    db_run("""
        CREATE TABLE IF NOT EXISTS orders (
            id SERIAL PRIMARY KEY,
            date TEXT, time TEXT,
            car TEXT, car_num TEXT,
            client TEXT, phone TEXT,
            problem TEXT, master TEXT, master_id TEXT DEFAULT '',
            service TEXT,
            works TEXT DEFAULT '[]',
            parts TEXT DEFAULT '[]',
            payments TEXT DEFAULT '[]',
            expenses TEXT DEFAULT '[]',
            status TEXT DEFAULT 'accepted',
            created_by TEXT, created_by_id TEXT DEFAULT '',
            closed_time TEXT, closed_date TEXT, closed_by TEXT
        )
    """)
    # Миграция: добавить колонки если не существуют (для уже существующей БД)
    for col_sql in [
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS master_id TEXT DEFAULT ''",
        "ALTER TABLE orders ADD COLUMN IF NOT EXISTS created_by_id TEXT DEFAULT ''",
    ]:
        try:
            db_run(col_sql)
        except Exception as e:
            logger.warning(f"Migration: {e}")
    db_run("""
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    """)
    db_run("""
        CREATE TABLE IF NOT EXISTS clients (
            phone TEXT PRIMARY KEY,
            name TEXT,
            order_ids TEXT DEFAULT '[]'
        )
    """)
    db_run("""
        CREATE TABLE IF NOT EXISTS kassa_ops (
            id SERIAL PRIMARY KEY,
            op_type TEXT,
            amount INTEGER,
            method TEXT DEFAULT 'cash_uzs',
            category TEXT,
            description TEXT,
            order_id INTEGER DEFAULT NULL,
            master_name TEXT DEFAULT '',
            by_name TEXT,
            by_id TEXT,
            date TEXT,
            time TEXT
        )
    """)
    logger.info("DB initialized")


def load_langs():
    try:
        rows = db_run("SELECT key, value FROM settings WHERE key IN ('langs','staff','roles')", fetch=True)
        for row in rows:
            k = row["key"]
            v = json.loads(row["value"]) if isinstance(row["value"], str) else row["value"]
            if k == "langs":
                for uid_s, lang in v.items():
                    USER_LANG[int(uid_s)] = lang
            elif k == "staff":
                for uid_s, name in v.items():
                    STAFF[int(uid_s)] = name
            elif k == "roles":
                for uid_s, role in v.items():
                    ROLES[int(uid_s)] = role
    except Exception as e:
        logger.warning(f"load_langs: {e}")


def _save_setting(key, value):
    db_run("DELETE FROM settings WHERE key=$1", [key])
    db_run("INSERT INTO settings(key, value) VALUES($1, $2)", [key, json.dumps(value)])


def save_lang(uid, l):
    USER_LANG[uid] = l
    _save_setting("langs", {str(k): v for k, v in USER_LANG.items()})


def _save_staff():
    _save_setting("staff", {str(k): v for k, v in STAFF.items()})
    _save_setting("roles", {str(k): v for k, v in ROLES.items()})


def _row_to_order(row):
    if not row:
        return None
    o = dict(row)
    for f in ["works", "parts", "payments", "expenses"]:
        v = o.get(f)
        if isinstance(v, str):
            try:
                o[f] = json.loads(v)
            except Exception:
                o[f] = []
        elif v is None:
            o[f] = []
    return o


def new_id():
    rows = db_run("SELECT nextval('orders_id_seq')", fetch=True)
    return rows[0]["nextval"]


def add_order(o):
    db_run("""
        INSERT INTO orders
        (id, date, time, car, car_num, client, phone, problem, master, master_id,
         service, works, parts, payments, expenses, status, created_by, created_by_id)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)
    """, [
        o["id"], o["date"], o["time"], o["car"], o.get("car_num", ""),
        o["client"], o.get("phone", ""), o["problem"], o["master"], str(o.get("master_id", "")),
        o["service"],
        json.dumps(o.get("works", [])), json.dumps(o.get("parts", [])),
        json.dumps(o.get("payments", [])), json.dumps(o.get("expenses", [])),
        o.get("status", "accepted"), o.get("created_by", ""), str(o.get("created_by_id", ""))
    ])
    ph = o.get("phone", "").strip()
    if ph:
        existing = db_run("SELECT order_ids FROM clients WHERE phone=$1", [ph], fetch=True)
        if existing:
            ids = json.loads(existing[0]["order_ids"]) + [o["id"]]
            db_run("UPDATE clients SET order_ids=$1 WHERE phone=$2", [json.dumps(ids), ph])
        else:
            db_run("INSERT INTO clients(phone,name,order_ids) VALUES($1,$2,$3)",
                   [ph, o["client"], json.dumps([o["id"]])])


def get_order(oid):
    rows = db_run("SELECT * FROM orders WHERE id=$1", [oid], fetch=True)
    return _row_to_order(rows[0]) if rows else None


def upd_order(oid, u):
    if not u:
        return
    sets, vals, i = [], [], 1
    for k, v in u.items():
        sets.append(f"{k} = ${i}")
        vals.append(json.dumps(v) if isinstance(v, (list, dict)) else v)
        i += 1
    if not sets:
        return
    vals.append(oid)
    db_run(f"UPDATE orders SET {', '.join(sets)} WHERE id=${i}", vals)


def open_orders():
    rows = db_run("SELECT * FROM orders WHERE status != 'closed' ORDER BY id", fetch=True)
    return [_row_to_order(r) for r in rows]


def today_orders():
    rows = db_run("SELECT * FROM orders WHERE date=$1 ORDER BY id", [date.today().isoformat()], fetch=True)
    return [_row_to_order(r) for r in rows]


def all_orders_list():
    rows = db_run("SELECT * FROM orders ORDER BY id DESC", fetch=True)
    return [_row_to_order(r) for r in rows]


def my_open(uid):
    name = STAFF.get(uid, "")
    uid_str = str(uid)
    result = []
    for o in open_orders():
        mid = o.get("master_id", "")
        if (mid and mid == uid_str) or (not mid and o.get("master") == name):
            result.append(o)
    return result


def all_debts():
    result = []
    for o in open_orders():
        amt = sum(p["amt_uzs"] for p in o.get("payments", []) if p.get("is_debt") and not p.get("paid"))
        if amt > 0:
            result.append((o, amt))
    return result


def client_history(phone):
    rows = db_run("SELECT order_ids FROM clients WHERE phone=$1", [phone], fetch=True)
    if not rows:
        return []
    ids = rows[0]["order_ids"]
    if isinstance(ids, str):
        ids = json.loads(ids)
    return [o for oid in ids for o in [get_order(oid)] if o]


def search_by_car(car_num):
    rows = db_run(
        "SELECT * FROM orders WHERE UPPER(car_num)=UPPER($1) OR UPPER(car) LIKE UPPER($2) ORDER BY id DESC",
        [car_num, f"%{car_num}%"], fetch=True
    )
    return [_row_to_order(r) for r in rows]


def calc_total(o):
    return (sum(p.get("sell_price", 0) for p in o.get("parts", [])) +
            sum(w.get("price", 0) for w in o.get("works", [])))


def calc_paid(o):
    return sum(p["amt_uzs"] for p in o.get("payments", [])
               if not (p.get("is_debt") and not p.get("paid")))


def calc_remaining(o):
    return max(0, calc_total(o) - calc_paid(o))


def calc_margin(o):
    return sum(p.get("sell_price", 0) - p.get("cost_price", 0) for p in o.get("parts", []))


def calc_expenses(o):
    return sum(e["amount"] for e in o.get("expenses", []))


# ── Кассовые операции ──────────────────────────────────────────────────────
def kassa_add(op):
    db_run("""
        INSERT INTO kassa_ops
        (op_type, amount, method, category, description, order_id,
         master_name, by_name, by_id, date, time)
        VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
    """, [
        op["op_type"], int(op["amount"]),
        op.get("method", "cash_uzs"),
        op.get("category", ""),
        op.get("description", ""),
        op.get("order_id"),
        op.get("master_name", ""),
        op.get("by_name", ""),
        str(op.get("by_id", "")),
        today_d(), now_t()
    ])


def kassa_ops_today():
    rows = db_run("SELECT * FROM kassa_ops WHERE date=$1 ORDER BY id", [today_d()], fetch=True)
    return rows or []


def kassa_ops_all(limit=100):
    rows = db_run("SELECT * FROM kassa_ops ORDER BY id DESC LIMIT $1", [limit], fetch=True)
    return rows or []




# ══════════════════════════════════════════════
# УТИЛИТЫ
# ══════════════════════════════════════════════
def is_owner(uid): return ROLES.get(uid) == "owner" or uid == OWNER_ID
def is_staff(uid): return uid in STAFF or uid == OWNER_ID
def can_parts(uid): return ROLES.get(uid, "mechanic") in PARTS_ROLES
def can_pay(uid):   return ROLES.get(uid, "mechanic") in PAY_ROLES
def can_close_order(uid, o):
    if is_owner(uid):
        return True
    uid_str = str(uid)
    mid = o.get("master_id", "")
    if mid:
        return mid == uid_str
    return o.get("master") == STAFF.get(uid, "")
def sname(uid): return STAFF.get(uid, f"ID:{uid}")


def fmt(n):
    try:
        return f"{int(n):,}".replace(",", " ")
    except Exception:
        return str(n)


def now_t(): return datetime.now().strftime("%H:%M")
def today_d(): return date.today().isoformat()
def is_back(text, uid): return text == tr("cancel", uid)
def is_cancel(text, uid): return is_back(text, uid)
def is_skip(text, uid): return text == tr("skip", uid)
def is_done(text, uid): return text == tr("done", uid)


def validate_phone(phone):
    p = re.sub(r'\D', '', phone)
    return p if (len(p) == 9 and p.startswith('9')) else None


def build_invoice(o, uid):
    works_block = ""
    if o.get("works"):
        lines = [f"  • {w['name']} — {fmt(w['price'])} сум" for w in o["works"]]
        works_block = tr("works_label_short", uid) + "\n".join(lines) + "\n\n"
    parts_block = ""
    if o.get("parts"):
        lines = [f"  • {p['name']} — {fmt(p['sell_price'])} сум" for p in o["parts"]]
        parts_block = "🔩 *Ehtiyot qismlar / Запчасти:*\n" + "\n".join(lines) + "\n\n"
    exp_block = ""
    if o.get("expenses"):
        lines = [f"  • {e['type']}: {fmt(e['amount'])} сум" for e in o["expenses"]]
        exp_block = "📤 *Xarajatlar / Расходы:*\n" + "\n".join(lines) + "\n\n"
    return tr("pay_invoice", uid,
              id=o["id"], works=works_block, parts=parts_block, expenses=exp_block,
              total=fmt(calc_total(o)), paid=fmt(calc_paid(o)), remaining=fmt(calc_remaining(o)))


def order_short(o, uid, show_margin=False):
    has_debt = any(p.get("is_debt") and not p.get("paid") for p in o.get("payments", []))
    st = o.get("status", "in_work")
    icons = {"accepted": "📥", "in_work": "🔧", "ready": "✅", "delivered": "🏁", "closed": "✅"}
    icon = "⏳" if has_debt else icons.get(st, "🔧")
    debt_m = tr("card_debt", uid) if has_debt else ""
    works_info = ""
    if o.get("works"):
        works_info = f"\n   📋 {', '.join(w['name'] for w in o['works'][:2])}"
        if len(o["works"]) > 2:
            works_info += f" +{len(o['works'])-2}"
    return (f"{icon} №{o['id']} | {o['car']} | {o['client']}\n"
            f"   {o['service']} → {o['master']} | {status_label(st, uid)}{debt_m}{works_info}\n"
            f"   📅 {o['date']} {o['time']}")


async def notify(ctx, text, uid):
    if uid != OWNER_ID:
        try:
            await ctx.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"notify: {e}")


# ══════════════════════════════════════════════
# КЛАВИАТУРЫ
# ══════════════════════════════════════════════
def kb_main(uid):
    # Ряд 1: приёмка + мои машины (самые частые)
    rows = [
        [tr("btn_accept", uid), tr("btn_my", uid)],
    ]

    # Ряд 2: запчасть + оплата (только у тех у кого есть доступ)
    row_part_pay = []
    if can_parts(uid):
        row_part_pay.append(tr("btn_part", uid))
    if can_pay(uid):
        row_part_pay.append(tr("btn_pay", uid))
    if row_part_pay:
        rows.append(row_part_pay)

    # Ряд 3: добавить услугу + расход
    rows.append([tr("btn_add_svc", uid), tr("btn_expense", uid)])

    # Ряд 4: закрыть + передать
    rows.append([tr("btn_close", uid), tr("btn_transfer", uid)])

    # Ряд 5: история + мой отчёт
    rows.append([tr("btn_history", uid), tr("btn_myreport", uid)])

    # Ряд 6: язык (одна кнопка)
    rows.append(["🌐 Til / Язык"])

    # Владелец — дополнительные ряды
    if is_owner(uid):
        rows += [
            [tr("btn_all", uid),   tr("btn_report", uid)],
            [tr("btn_kassa", uid), tr("btn_debts", uid)],
            [tr("btn_staff", uid), tr("btn_edit", uid)],
        ]

    return ReplyKeyboardMarkup([[KeyboardButton(b) for b in r] for r in rows], resize_keyboard=True)


def kb_lang():
    return ReplyKeyboardMarkup(
        [[KeyboardButton("🇺🇿 O'zbek"), KeyboardButton("🇷🇺 Русский")]],
        resize_keyboard=True
    )


def kb_list(items, uid, cols=2, extra=None):
    rows = [items[i:i+cols] for i in range(0, len(items), cols)]
    if extra:
        rows.append([extra])
    rows.append([tr("cancel", uid)])
    return ReplyKeyboardMarkup([[KeyboardButton(b) for b in r] for r in rows], resize_keyboard=True)


def kb_back(uid):
    return ReplyKeyboardMarkup([[KeyboardButton(tr("cancel", uid))]], resize_keyboard=True)


def kb_skip_back(uid):
    return ReplyKeyboardMarkup(
        [[KeyboardButton(tr("skip", uid)), KeyboardButton(tr("cancel", uid))]],
        resize_keyboard=True
    )


def kb_done_back(uid):
    return ReplyKeyboardMarkup(
        [[KeyboardButton(tr("done", uid)), KeyboardButton(tr("cancel", uid))]],
        resize_keyboard=True
    )


def kb_pay(uid):
    methods = get_pay_methods(uid)
    rows = [methods[i:i+2] for i in range(0, len(methods), 2)]
    rows.append([tr("cancel", uid)])
    return ReplyKeyboardMarkup([[KeyboardButton(b) for b in r] for r in rows], resize_keyboard=True)


def kb_yes_no(uid):
    return ReplyKeyboardMarkup(
        [[KeyboardButton("✅ Ha / Да"), KeyboardButton("➡️ Yo'q / Нет")]],
        resize_keyboard=True
    )


# ══════════════════════════════════════════════
# СТАРТ
# ══════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        await update.message.reply_text(f"⛔ Ruxsat yo'q / Нет доступа.\n\nID: `{uid}`", parse_mode="Markdown")
        return
    if uid in USER_LANG:
        await update.message.reply_text(tr("lang_set", uid), parse_mode="Markdown", reply_markup=kb_main(uid))
        return
    await update.message.reply_text(tr("choose_lang", uid), reply_markup=kb_lang())


async def cmd_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return
    await update.message.reply_text(tr("choose_lang", uid), reply_markup=kb_lang())


async def cmd_add_staff(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return
    args = ctx.args
    if not args:
        instr = (
            "👥 *Xodim qo'shish / Добавить сотрудника*\n\n"
            "Format: `/add_staff ID Ism rol`\n\n"
            "*Rollar / Роли:*\n"
            "  `owner` — Rahbar 👑\n"
            "  `mechanic` — Mexanik 🔧 _(standart)_\n"
            "  `wash` — Yuvuvchi 🚿\n"
            "  `tint` — Tonirovkachi 🪟\n"
            "  `body` — Kuzovchi 🔨\n"
            "  `elec` — Elektrik ⚡\n\n"
            "*Misollar:*\n"
            "`/add_staff 123456789 Abduraxmon`\n"
            "`/add_staff 123456789 Abduraxmon mechanic`\n"
            "`/add_staff 123456789 Sarvarbek wash`"
        )
        await update.message.reply_text(instr, parse_mode="Markdown")
        return
    if len(args) < 2:
        await update.message.reply_text("Format: `/add_staff 123456789 Ism`", parse_mode="Markdown")
        return
    try:
        sid = int(args[0])
        valid_roles = ["owner", "mechanic", "wash", "tint", "body", "elec"]
        if len(args) >= 3 and args[-1].lower() in valid_roles:
            role = args[-1].lower()
            sn = " ".join(args[1:-1])
        else:
            role = "mechanic"
            sn = " ".join(args[1:])
        STAFF[sid] = sn
        ROLES[sid] = role
        _save_staff()
        role_label = ROLE_NAMES[lg(uid)].get(role, role)
        await update.message.reply_text(
            f"✅ *{sn}* qo'shildi!\n👤 Rol: {role_label}\n🆔 ID: `{sid}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_del_staff(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return
    args = ctx.args
    if not args:
        await update.message.reply_text("Format: `/del_staff 123456789`", parse_mode="Markdown")
        return
    try:
        sid = int(args[0])
        if sid == OWNER_ID:
            await update.message.reply_text("⛔ Asosiy rahbarni o'chirish mumkin emas.")
            return
        if sid == uid:
            await update.message.reply_text("⛔ O'zingizni o'chira olmaysiz.")
            return
        if sid not in STAFF:
            await update.message.reply_text("❌ Xodim topilmadi.")
            return
        name = STAFF.pop(sid)
        ROLES.pop(sid, None)
        _save_staff()
        await update.message.reply_text(f"✅ *{name}* o'chirildi.", parse_mode="Markdown", reply_markup=kb_main(uid))
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


async def cmd_edit_staff(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return
    args = ctx.args
    if len(args) < 3:
        instr = (
            "*O'zgartirish / Изменить:*\n\n"
            "`/edit_staff ID name Yangi Ism`\n"
            "`/edit_staff ID role mechanic`\n"
            "_Rollar: owner mechanic wash tint body elec_"
        )
        await update.message.reply_text(instr, parse_mode="Markdown")
        return
    try:
        sid = int(args[0])
        field = args[1].lower()
        value = " ".join(args[2:])
        if sid not in STAFF:
            await update.message.reply_text("❌ Xodim topilmadi.")
            return
        old_name = STAFF[sid]
        if field == "name":
            STAFF[sid] = value
            _save_staff()
            await update.message.reply_text(f"✅ *{old_name}* → *{value}*", parse_mode="Markdown")
        elif field == "role":
            valid_roles = ["owner", "mechanic", "wash", "tint", "body", "elec"]
            if value not in valid_roles:
                await update.message.reply_text(f"❌ Rollar: {', '.join(valid_roles)}")
                return
            ROLES[sid] = value
            _save_staff()
            label = ROLE_NAMES[lg(uid)].get(value, value)
            await update.message.reply_text(f"✅ *{old_name}* roli: {label}", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Field: `name` | `role`", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ {e}")


# ══════════════════════════════════════════════
# 1. ПРИЁМКА
# ══════════════════════════════════════════════
async def accept_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return ConversationHandler.END
    ctx.user_data.clear()
    await update.message.reply_text(tr("accept_hint", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
    return A_CAR_LINE


async def accept_car_line(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    parts = [p.strip() for p in update.message.text.split("*")]
    if len(parts) < 3:
        await update.message.reply_text(tr("accept_fmt_err", uid), parse_mode="Markdown")
        return A_CAR_LINE
    ctx.user_data["car_num"]   = parts[0]
    ctx.user_data["car_model"] = parts[1]
    ctx.user_data["client"]    = parts[2]
    await update.message.reply_text(tr("accept_phone", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
    return A_PHONE


async def accept_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("accept_hint", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return A_CAR_LINE
    phone = validate_phone(update.message.text)
    if not phone:
        await update.message.reply_text(tr("phone_err", uid), parse_mode="Markdown")
        return A_PHONE
    ctx.user_data["phone"] = phone
    extra = ""
    h = client_history(phone)
    if h:
        last = h[-1]
        extra = tr("repeat_client", uid, n=len(h), date=last["date"], svc=last["service"])
    await update.message.reply_text(tr("accept_problem", uid) + extra, parse_mode="Markdown", reply_markup=kb_back(uid))
    return A_PROBLEM


async def accept_problem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("accept_phone", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return A_PHONE
    ctx.user_data["problem"] = update.message.text
    masters = list(STAFF.values())
    await update.message.reply_text(tr("accept_master", uid), reply_markup=kb_list(masters, uid))
    return A_MASTER


async def accept_master(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("accept_problem", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return A_PROBLEM
    masters = list(STAFF.values())
    if update.message.text not in masters:
        await update.message.reply_text(tr("accept_master", uid), reply_markup=kb_list(masters, uid))
        return A_MASTER
    ctx.user_data["master"] = update.message.text
    svcs = get_available_services(uid)
    await update.message.reply_text(tr("accept_service", uid), reply_markup=kb_list(svcs, uid, cols=2))
    return A_SERVICE


async def accept_service(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        masters = list(STAFF.values())
        await update.message.reply_text(tr("accept_master", uid), reply_markup=kb_list(masters, uid))
        return A_MASTER
    svc = update.message.text
    ctx.user_data["service"] = svc
    ctx.user_data["works"] = []

    if svc_needs_subs(svc, uid):
        if "Yuvish" in svc or "Мойка" in svc:
            subs = get_wash_subs(uid)
        elif "Tonirovka" in svc or "Тонировка" in svc:
            subs = get_tint_subs(uid)
        else:
            subs = get_film_subs(uid)
        await update.message.reply_text(f"📋 {svc}\n\nVid / Вид:", reply_markup=kb_list(subs, uid, cols=1))
        return A_SVC_SUB

    if svc_needs_works(svc, uid):
        await update.message.reply_text(tr("svc_works_hint", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return A_WORKS_LIST

    # Цена при приёмке необязательна
    await update.message.reply_text(tr("accept_price_q", uid), parse_mode="Markdown", reply_markup=kb_skip_back(uid))
    return A_ACCEPT_PRICE


async def accept_svc_sub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        svcs = get_available_services(uid)
        await update.message.reply_text(tr("accept_service", uid), reply_markup=kb_list(svcs, uid, cols=2))
        return A_SERVICE
    ctx.user_data["svc_sub"] = update.message.text
    await update.message.reply_text(tr("accept_price_q", uid), parse_mode="Markdown", reply_markup=kb_skip_back(uid))
    return A_ACCEPT_PRICE


async def accept_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Цена при приёмке — необязательна (можно пропустить)"""
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        # Назад — к выбору услуги
        svc = ctx.user_data.get("service", "")
        if svc_needs_subs(svc, uid):
            svcs = get_available_services(uid)
            await update.message.reply_text(tr("accept_service", uid), reply_markup=kb_list(svcs, uid, cols=2))
            return A_SERVICE
        svcs = get_available_services(uid)
        await update.message.reply_text(tr("accept_service", uid), reply_markup=kb_list(svcs, uid, cols=2))
        return A_SERVICE

    if is_skip(update.message.text, uid):
        # Пропустить — создаём заявку без цены
        ctx.user_data["works"] = []
        return await _save_order(update, ctx)

    try:
        price = int(update.message.text.replace(" ", ""))
        sub = ctx.user_data.get("svc_sub", "")
        work_name = f"{ctx.user_data['service']}{' — ' + sub if sub else ''}"
        ctx.user_data["works"] = [{"name": work_name, "price": price, "master": sname(uid)}]
        return await _save_order(update, ctx)
    except Exception as e:
        logger.error(f"accept_price error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return A_ACCEPT_PRICE


async def accept_works_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        svcs = get_available_services(uid)
        await update.message.reply_text(tr("accept_service", uid), reply_markup=kb_list(svcs, uid, cols=2))
        return A_SERVICE
    works_raw = [l.strip() for l in update.message.text.strip().split("\n") if l.strip()]
    if not works_raw:
        await update.message.reply_text("❌ Bo'sh / Пустой список")
        return A_WORKS_LIST
    ctx.user_data["works_raw"] = works_raw
    example_prices = "\n".join(["500000", "200000", "150000"][:len(works_raw)])
    hint = tr("svc_works_prices_hint", uid, works=f"{len(works_raw)} ta / шт.", example=example_prices)
    works_list = "\n".join(f"{i+1}. {w}" for i, w in enumerate(works_raw))
    await update.message.reply_text(
        f"{tr('works_list_label', uid)}\n{works_list}\n\n{hint}",
        parse_mode="Markdown", reply_markup=kb_back(uid)
    )
    return A_WORKS_PRICE


async def accept_work_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("svc_works_hint", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return A_WORKS_LIST
    works_raw = ctx.user_data["works_raw"]
    price_lines = [l.strip() for l in update.message.text.strip().split("\n") if l.strip()]
    if len(price_lines) != len(works_raw):
        await update.message.reply_text(
            tr("svc_works_mismatch", uid, n_prices=len(price_lines), n_works=len(works_raw)),
            parse_mode="Markdown"
        )
        return A_WORKS_PRICE
    try:
        works = []
        for work_name, price_str in zip(works_raw, price_lines):
            price = int(price_str.replace(" ", ""))
            works.append({"name": work_name, "price": price, "master": sname(uid)})
        ctx.user_data["works"] = works
        return await _save_order(update, ctx)
    except Exception as e:
        logger.error(f"accept_work_price error: {e}")
        await update.message.reply_text("❌ Narxlarda xato!\n📌 Misol: `500000`", parse_mode="Markdown")
        return A_WORKS_PRICE


async def _save_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    car = f"{ctx.user_data['car_num']} {ctx.user_data['car_model']}"
    oid = new_id()
    works = ctx.user_data.get("works", [])
    total_works = sum(w["price"] for w in works)

    # Найти uid мастера по имени
    master_name = ctx.user_data["master"]
    master_uid = next((k for k, v in STAFF.items() if v == master_name), None)

    order = {
        "id": oid, "date": today_d(), "time": now_t(),
        "car": car, "car_num": ctx.user_data["car_num"],
        "client": ctx.user_data["client"], "phone": ctx.user_data.get("phone", ""),
        "problem": ctx.user_data["problem"], "master": master_name,
        "master_id": str(master_uid) if master_uid else "",
        "service": ctx.user_data["service"],
        "works": works,
        "parts": [], "payments": [], "expenses": [],
        "status": "accepted", "created_by": sname(uid), "created_by_id": str(uid),
    }
    add_order(order)

    works_lines = "\n".join(f"  • {w['name']} — {fmt(w['price'])} сум" for w in works)
    total_line = f"\n💰 Jami / Итого: {fmt(total_works)} сум" if works else ""
    msg = tr("accept_done", uid, id=oid, car=car, client=order["client"],
             service=order["service"], problem=order["problem"])
    if works_lines:
        msg += f"\n\n📋 *Ishlar / Работы:*\n{works_lines}{total_line}"

    ctx.user_data["last_order_id"] = oid
    await update.message.reply_text(msg, parse_mode="Markdown")
    await notify(ctx, msg, uid)

    # Уведомить мастера если он не тот кто принял
    if master_uid and master_uid != uid and master_uid in USER_LANG:
        try:
            notify_text = tr("notify_assigned", master_uid,
                             id=oid, car=car, client=order["client"],
                             service=order["service"], problem=order["problem"])
            await ctx.bot.send_message(chat_id=master_uid, text=notify_text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"notify master: {e}")

    await update.message.reply_text(tr("add_parts_q", uid), reply_markup=kb_yes_no(uid))
    return AFTER_ACCEPT


async def after_accept(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if "Ha" in update.message.text or "Да" in update.message.text:
        oid = ctx.user_data.get("last_order_id")
        if oid:
            ctx.user_data.clear()
            ctx.user_data["order_id"] = oid
            await update.message.reply_text(tr("part_name_q", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
            return P_NAME
    await update.message.reply_text("✅", reply_markup=kb_main(uid))
    return ConversationHandler.END


# ══════════════════════════════════════════════
# 2. ЗАПЧАСТИ
# ══════════════════════════════════════════════
async def part_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return ConversationHandler.END
    if not can_parts(uid):
        await update.message.reply_text(tr("no_access", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    orders = open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    lines = [tr("list_open_parts", uid)] + [order_short(o, uid) for o in orders] + ["\n" + tr("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_back(uid))
    return P_ORDER


async def part_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o or o["status"] == "closed":
            await update.message.reply_text(tr("not_found", uid))
            return P_ORDER
        ctx.user_data["order_id"] = oid
        await update.message.reply_text(tr("part_name_q", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return P_NAME
    except Exception as e:
        logger.error(f"part_order error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return P_ORDER


async def part_name(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    ctx.user_data["part_name"] = update.message.text.strip()
    sources = [tr("src_client", uid), tr("src_bought", uid), tr("src_stock", uid)]
    await update.message.reply_text(
        tr("part_source_q", uid, name=ctx.user_data["part_name"]),
        parse_mode="Markdown", reply_markup=kb_list(sources, uid, cols=1)
    )
    return P_SOURCE


async def part_source(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("part_name_q", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return P_NAME
    sources = [tr("src_client", uid), tr("src_bought", uid), tr("src_stock", uid)]
    if update.message.text not in sources:
        await update.message.reply_text(
            tr("part_source_q", uid, name=ctx.user_data.get("part_name", "")),
            parse_mode="Markdown", reply_markup=kb_list(sources, uid, cols=1))
        return P_SOURCE
    ctx.user_data["part_source"] = update.message.text
    if update.message.text == tr("src_client", uid):
        ctx.user_data["part_cost"] = 0
        await update.message.reply_text(tr("part_work_q", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return P_SELL
    elif update.message.text == tr("src_bought", uid):
        await update.message.reply_text(tr("part_cost_q", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return P_COST
    else:  # src_stock
        ctx.user_data["part_cost"] = 0
        await update.message.reply_text(tr("part_sell_q", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return P_SELL


async def part_cost(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        sources = [tr("src_client", uid), tr("src_bought", uid), tr("src_stock", uid)]
        await update.message.reply_text(
            tr("part_source_q", uid, name=ctx.user_data.get("part_name", "")),
            parse_mode="Markdown", reply_markup=kb_list(sources, uid, cols=1))
        return P_SOURCE
    try:
        ctx.user_data["part_cost"] = int(update.message.text.replace(" ", ""))
        await update.message.reply_text(tr("part_sell_q", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return P_SELL
    except Exception as e:
        logger.error(f"part_cost error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return P_COST


async def part_sell(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        if ctx.user_data.get("part_source") == tr("src_bought", uid):
            await update.message.reply_text(tr("part_cost_q", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
            return P_COST
        sources = [tr("src_client", uid), tr("src_bought", uid), tr("src_stock", uid)]
        await update.message.reply_text(
            tr("part_source_q", uid, name=ctx.user_data.get("part_name", "")),
            parse_mode="Markdown", reply_markup=kb_list(sources, uid, cols=1))
        return P_SOURCE
    try:
        sell = int(update.message.text.replace(" ", ""))
        cost = ctx.user_data.get("part_cost", 0)
        part = {
            "name": ctx.user_data["part_name"],
            "source": ctx.user_data["part_source"],
            "cost_price": cost,
            "sell_price": sell
        }
        oid = ctx.user_data["order_id"]
        o = get_order(oid)
        upd_order(oid, {"parts": o.get("parts", []) + [part]})
        margin_line = f" | 📈 {fmt(sell-cost)}" if (is_owner(uid) and sell > cost) else ""
        await update.message.reply_text(
            tr("part_added", uid, name=part["name"], sell=fmt(sell) + margin_line),
            parse_mode="Markdown"
        )
        await notify(ctx, f"🔩 #{oid} | {part['name']} — {fmt(sell)} сум", uid)
        await update.message.reply_text(
            "➕",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("➕ Yana / Ещё"), KeyboardButton(tr("done", uid))],
                [KeyboardButton(tr("cancel", uid))]
            ], resize_keyboard=True)
        )
        return P_MORE
    except Exception as e:
        logger.error(f"part_sell error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return P_SELL


async def part_more(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    if is_done(update.message.text, uid):
        await update.message.reply_text("✅", reply_markup=kb_main(uid))
        return ConversationHandler.END
    await update.message.reply_text(tr("part_name_q", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
    return P_NAME


# ══════════════════════════════════════════════
# 3. ОПЛАТА
# ══════════════════════════════════════════════
async def pay_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return ConversationHandler.END
    if not can_pay(uid):
        await update.message.reply_text(tr("no_access", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    orders = my_open(uid) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    lines = [tr("list_open_pay", uid)] + [order_short(o, uid) for o in orders] + ["\n" + tr("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_back(uid))
    return PAY_ORDER


async def pay_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o or o["status"] == "closed":
            await update.message.reply_text(tr("not_found", uid))
            return PAY_ORDER
        ctx.user_data["order_id"] = oid
        # Если цены нет — сначала запрашиваем
        if calc_total(o) == 0:
            await update.message.reply_text(tr("pay_no_price", uid, id=oid), parse_mode="Markdown")
            await update.message.reply_text(tr("pay_set_price", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
            return PAY_PRICE
        remaining = calc_remaining(o)
        if remaining <= 0 and calc_total(o) > 0:
            await update.message.reply_text(
                build_invoice(o, uid) + "\n\n✅ To'liq to'langan / Полностью оплачено!",
                parse_mode="Markdown", reply_markup=kb_main(uid)
            )
            return ConversationHandler.END
        await update.message.reply_text(build_invoice(o, uid), parse_mode="Markdown", reply_markup=kb_pay(uid))
        return PAY_METHOD
    except Exception as e:
        logger.error(f"pay_order error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return PAY_ORDER


async def pay_set_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Устанавливаем цену если не было при приёмке"""
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    try:
        price = int(update.message.text.replace(" ", ""))
        oid = ctx.user_data["order_id"]
        o = get_order(oid)
        svc = o.get("service", "Xizmat")
        work = {"name": svc, "price": price, "master": o.get("master", "")}
        upd_order(oid, {"works": o.get("works", []) + [work]})
        o = get_order(oid)
        await update.message.reply_text(build_invoice(o, uid), parse_mode="Markdown", reply_markup=kb_pay(uid))
        return PAY_METHOD
    except Exception as e:
        logger.error(f"pay_set_price error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return PAY_PRICE


async def pay_method(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    if update.message.text not in get_pay_methods(uid):
        await update.message.reply_text(tr("pay_method_q", uid), reply_markup=kb_pay(uid))
        return PAY_METHOD
    ctx.user_data["pay_method"] = update.message.text
    if "USD" in update.message.text:
        await update.message.reply_text(tr("pay_rate_q", uid), reply_markup=kb_back(uid))
        return PAY_RATE
    await update.message.reply_text(tr("pay_amt_q", uid), reply_markup=kb_back(uid))
    return PAY_AMOUNT


async def pay_rate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("pay_method_q", uid), reply_markup=kb_pay(uid))
        return PAY_METHOD
    try:
        ctx.user_data["usd_rate"] = int(update.message.text.replace(" ", ""))
        await update.message.reply_text(tr("pay_usd_q", uid), reply_markup=kb_back(uid))
        return PAY_AMOUNT
    except Exception as e:
        logger.error(f"pay_rate error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return PAY_RATE


async def pay_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        if ctx.user_data.get("usd_rate"):
            await update.message.reply_text(tr("pay_rate_q", uid), reply_markup=kb_back(uid))
            return PAY_RATE
        await update.message.reply_text(tr("pay_method_q", uid), reply_markup=kb_pay(uid))
        return PAY_METHOD
    try:
        raw = int(update.message.text.replace(" ", ""))
        method = ctx.user_data["pay_method"]
        rate = ctx.user_data.get("usd_rate", 1)
        is_usd  = "USD" in method
        is_debt = "Qarz" in method or "Долг" in method
        # v3.0: суммы полные — без *1000
        # USD: вводится в долларах → amt_uzs = доллары * курс
        amount  = raw
        amt_uzs = amount * rate if is_usd else amount

        oid = ctx.user_data["order_id"]
        o = get_order(oid)
        payments = o.get("payments", []) + [{
            "method": method, "amount": amount, "amt_uzs": amt_uzs,
            "usd_rate": rate if is_usd else None,
            "is_debt": is_debt, "paid": not is_debt,
            "time": now_t(), "by": sname(uid),
        }]
        upd_order(oid, {"payments": payments})
        o = get_order(oid)
        remaining = calc_remaining(o)

        if is_debt or remaining <= 0:
            # Автостатус: полностью оплачено → готова
            if not is_debt and o.get("status") not in ("closed", "delivered"):
                upd_order(oid, {"status": "ready"})
            msg = tr("pay_done", uid, id=oid, total=fmt(calc_paid(o)))
            if is_debt:
                msg += f"\n📝 Qarz / Долг: {fmt(amt_uzs)} сум"
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
            await notify(ctx, msg, uid)
            # Уведомить мастера об оплате (если не он сам принимал оплату)
            if not is_debt:
                o_fresh = get_order(oid)
                mid_str = o_fresh.get("master_id", "")
                if mid_str:
                    try:
                        master_notify_uid = int(mid_str)
                        if master_notify_uid != uid and master_notify_uid in USER_LANG:
                            ntxt = tr("notify_paid", master_notify_uid,
                                      id=oid, car=o["car"], client=o["client"],
                                      total=fmt(calc_paid(o_fresh)))
                            await ctx.bot.send_message(chat_id=master_notify_uid,
                                                       text=ntxt, parse_mode="Markdown")
                    except Exception as e:
                        logger.warning(f"notify paid master: {e}")
            return ConversationHandler.END
        else:
            await update.message.reply_text(
                tr("pay_added", uid, method=method, amt=fmt(amt_uzs), rem=fmt(remaining)),
                parse_mode="Markdown"
            )
            await update.message.reply_text(build_invoice(o, uid), parse_mode="Markdown", reply_markup=kb_pay(uid))
            return PAY_METHOD
    except Exception as e:
        logger.error(f"pay_amount error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return PAY_AMOUNT


# ══════════════════════════════════════════════
# 4. РАСХОДЫ
# ══════════════════════════════════════════════
async def exp_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return ConversationHandler.END
    orders = open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    lines = [tr("exp_title", uid)] + [order_short(o, uid) for o in orders] + ["\n" + tr("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_back(uid))
    return EXP_ORDER


async def exp_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o:
            await update.message.reply_text(tr("not_found", uid))
            return EXP_ORDER
        ctx.user_data["order_id"] = oid
        await update.message.reply_text(tr("exp_type_q", uid), reply_markup=kb_list(get_expenses_list(uid), uid))
        return EXP_TYPE
    except Exception as e:
        logger.error(f"exp_order error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return EXP_ORDER


async def exp_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    if update.message.text not in get_expenses_list(uid):
        await update.message.reply_text(tr("exp_type_q", uid), reply_markup=kb_list(get_expenses_list(uid), uid))
        return EXP_TYPE
    ctx.user_data["exp_type"] = update.message.text
    await update.message.reply_text(tr("exp_desc_q", uid), reply_markup=kb_skip_back(uid))
    return EXP_DESC


async def exp_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("exp_type_q", uid), reply_markup=kb_list(get_expenses_list(uid), uid))
        return EXP_TYPE
    ctx.user_data["exp_desc"] = "" if is_skip(update.message.text, uid) else update.message.text
    await update.message.reply_text(tr("exp_amt_q", uid), reply_markup=kb_back(uid))
    return EXP_AMOUNT


async def exp_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("exp_desc_q", uid), reply_markup=kb_skip_back(uid))
        return EXP_DESC
    try:
        amount = int(update.message.text.replace(" ", ""))
        oid = ctx.user_data["order_id"]
        exp = {
            "type": ctx.user_data["exp_type"],
            "desc": ctx.user_data.get("exp_desc", ""),
            "amount": amount, "time": now_t(), "by": sname(uid), "by_id": uid
        }
        o = get_order(oid)
        upd_order(oid, {"expenses": o.get("expenses", []) + [exp]})
        msg = tr("exp_done", uid, id=oid, type=exp["type"], amt=fmt(amount))
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
        await notify(ctx, msg, uid)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"exp_amount error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return EXP_AMOUNT


# ══════════════════════════════════════════════
# 5. ЗАКРЫТИЕ
# ══════════════════════════════════════════════
async def close_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return ConversationHandler.END
    orders = my_open(uid) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    lines = [tr("list_open_close", uid)] + [order_short(o, uid) for o in orders] + ["\n" + tr("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_back(uid))
    return CLOSE_ORDER


async def close_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o:
            await update.message.reply_text(tr("not_found", uid))
            return CLOSE_ORDER

        # Только принявший мастер или владелец
        if not can_close_order(uid, o):
            await update.message.reply_text(tr("close_no_right", uid), reply_markup=kb_main(uid))
            return ConversationHandler.END

        if not o.get("payments"):
            await update.message.reply_text(tr("close_no_pay", uid), parse_mode="Markdown", reply_markup=kb_main(uid))
            return ConversationHandler.END

        remaining = calc_remaining(o)
        has_debt = any(p.get("is_debt") and not p.get("paid") for p in o.get("payments", []))
        if remaining > 0 and not has_debt:
            await update.message.reply_text(tr("close_no_pay", uid), parse_mode="Markdown", reply_markup=kb_main(uid))
            return ConversationHandler.END

        upd_order(oid, {"status": "closed", "closed_time": now_t(),
                        "closed_date": today_d(), "closed_by": sname(uid)})
        # Автостатус: выдана при закрытии
        o = get_order(oid)

        paid     = calc_paid(o)
        expenses = calc_expenses(o)
        margin   = calc_margin(o)
        net      = paid - expenses

        summary = tr("close_summary", uid, paid=fmt(paid), exp=fmt(expenses), net=fmt(net))
        if is_owner(uid) and margin > 0:
            summary += f"\n📈 Marja / Маржа: {fmt(margin)} сум"

        debt_line = tr("close_debt_w", uid) if has_debt else ""
        msg = tr("close_done", uid, id=oid, car=o["car"], client=o["client"],
                 phone=o.get("phone", "—"), debt=debt_line, summary=summary)

        inline_kb = InlineKeyboardMarkup([[
            InlineKeyboardButton(tr("btn_details", uid), callback_data=f"details_{oid}_{uid}")
        ]])
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
        await update.message.reply_text("👇", reply_markup=inline_kb)
        await notify(ctx, f"🏁 №{oid} yopildi | {o['car']} | {o['client']} | {sname(uid)}", uid)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"close_confirm error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return CLOSE_ORDER


# ══════════════════════════════════════════════
# 6. ИСТОРИЯ
# ══════════════════════════════════════════════
async def hist_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return ConversationHandler.END
    ctx.user_data.clear()
    await update.message.reply_text(tr("hist_q", uid), reply_markup=kb_back(uid))
    return HIST_PHONE


async def hist_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    query = update.message.text.strip()
    digits_only = re.sub(r'\D', '', query)

    history = []
    if digits_only and len(digits_only) >= 7:
        history = client_history(digits_only)
    if not history:
        history = search_by_car(query.upper().replace(" ", ""))

    if not history:
        await update.message.reply_text(tr("hist_none", uid, q=query), reply_markup=kb_main(uid))
        return ConversationHandler.END

    total = sum(calc_paid(o) for o in history)
    lines = [
        tr("hist_header", uid, name=history[0]["client"],
           phone=history[0].get("phone", "-"), n=len(history), total=fmt(total)),
        "─────────────"
    ]
    for o in history[-5:]:
        lines.append(order_short(o, uid, show_margin=is_owner(uid)))
        lines.append("─────────────")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))
    return ConversationHandler.END


# ══════════════════════════════════════════════
# 7. ПЕРЕДАЧА МАШИНЫ
# ══════════════════════════════════════════════
async def transfer_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return ConversationHandler.END
    orders = my_open(uid) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    lines = [tr("list_open_trans", uid)] + [order_short(o, uid) for o in orders] + ["\n" + tr("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_back(uid))
    return TR_ORDER


async def transfer_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o or o["status"] == "closed":
            await update.message.reply_text(tr("not_found", uid))
            return TR_ORDER
        ctx.user_data["order_id"] = oid
        masters = list(STAFF.values())
        await update.message.reply_text(tr("transfer_who", uid), reply_markup=kb_list(masters, uid))
        return TR_MASTER
    except Exception as e:
        logger.error(f"transfer_order error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return TR_ORDER


async def transfer_master(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    masters = list(STAFF.values())
    if update.message.text not in masters:
        await update.message.reply_text(tr("transfer_who", uid), reply_markup=kb_list(masters, uid))
        return TR_MASTER
    new_master_name = update.message.text
    new_master_uid = next((k for k, v in STAFF.items() if v == new_master_name), None)
    oid = ctx.user_data["order_id"]
    upd_order(oid, {
        "master": new_master_name,
        "master_id": str(new_master_uid) if new_master_uid else "",
    })
    msg = tr("transfer_done", uid, id=oid, master=new_master_name)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
    await notify(ctx, msg, uid)

    # Уведомить нового мастера
    if new_master_uid and new_master_uid != uid and new_master_uid in USER_LANG:
        try:
            o = get_order(oid)
            notify_text = tr("notify_transferred", new_master_uid,
                             id=oid, car=o["car"], client=o["client"],
                             from_master=sname(uid))
            await ctx.bot.send_message(chat_id=new_master_uid, text=notify_text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"notify transfer: {e}")

    return ConversationHandler.END


# ══════════════════════════════════════════════
# 8. СМЕНА СТАТУСА
# ══════════════════════════════════════════════
async def status_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return ConversationHandler.END
    orders = my_open(uid) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    lines = [tr("list_open_status", uid)] + [order_short(o, uid) for o in orders] + ["\n" + tr("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_back(uid))
    return ST_ORDER


async def status_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o or o["status"] == "closed":
            await update.message.reply_text(tr("not_found", uid))
            return ST_ORDER
        ctx.user_data["order_id"] = oid
        await update.message.reply_text(tr("status_q", uid),
                                        reply_markup=kb_list(T["statuses"][lg(uid)], uid, cols=2))
        return ST_STATUS
    except Exception as e:
        logger.error(f"status_order error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return ST_ORDER


async def status_set(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    status_code = T["status_map"].get(update.message.text)
    if not status_code:
        await update.message.reply_text(tr("status_q", uid),
                                        reply_markup=kb_list(T["statuses"][lg(uid)], uid, cols=2))
        return ST_STATUS
    oid = ctx.user_data["order_id"]
    upd_order(oid, {"status": status_code})
    msg = tr("status_set", uid, id=oid, status=status_label(status_code, uid))
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
    await notify(ctx, msg, uid)
    return ConversationHandler.END


# ══════════════════════════════════════════════
# 9. РЕДАКТИРОВАНИЕ ЗАЯВКИ
# ══════════════════════════════════════════════
async def edit_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text(tr("only_owner", uid))
        return ConversationHandler.END
    orders = open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    lines = [tr("list_open_edit", uid)] + [order_short(o, uid) for o in orders] + ["\n" + tr("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_back(uid))
    return ED_ORDER


async def edit_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o:
            await update.message.reply_text(tr("not_found", uid))
            return ED_ORDER
        ctx.user_data["order_id"] = oid
        fields = T["edit_fields"][lg(uid)]
        await update.message.reply_text(
            tr("edit_q", uid, id=oid), parse_mode="Markdown",
            reply_markup=kb_list(fields, uid, cols=1)
        )
        return ED_FIELD
    except Exception as e:
        logger.error(f"edit_order error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return ED_ORDER


async def edit_field(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    text = update.message.text
    fields = T["edit_fields"][lg(uid)]
    if text not in fields:
        await update.message.reply_text(
            tr("edit_q", uid, id=ctx.user_data.get("order_id", "?")),
            parse_mode="Markdown", reply_markup=kb_list(fields, uid, cols=1)
        )
        return ED_FIELD
    ctx.user_data["edit_field"] = text
    if "Ism" in text or "Имя" in text:
        await update.message.reply_text(tr("edit_name_q", uid), reply_markup=kb_back(uid))
    elif "Telefon" in text:
        await update.message.reply_text(tr("edit_phone_q", uid), reply_markup=kb_back(uid))
    else:
        await update.message.reply_text(tr("edit_price_q", uid), reply_markup=kb_back(uid))
    return ED_VALUE


async def edit_value(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        fields = T["edit_fields"][lg(uid)]
        await update.message.reply_text(
            tr("edit_q", uid, id=ctx.user_data.get("order_id", "?")),
            parse_mode="Markdown", reply_markup=kb_list(fields, uid, cols=1)
        )
        return ED_FIELD
    oid = ctx.user_data["order_id"]
    field = ctx.user_data.get("edit_field", "")
    value = update.message.text.strip()
    try:
        if "Ism" in field or "Имя" in field:
            upd_order(oid, {"client": value})
        elif "Telefon" in field:
            phone = validate_phone(value)
            if not phone:
                await update.message.reply_text(tr("phone_err", uid))
                return ED_VALUE
            upd_order(oid, {"phone": phone})
        else:
            price = int(value.replace(" ", ""))
            o = get_order(oid)
            works = o.get("works", [])
            if works:
                works[0]["price"] = price
            else:
                works = [{"name": o.get("service", "Xizmat"), "price": price, "master": o.get("master", "")}]
            upd_order(oid, {"works": works})
        await update.message.reply_text(tr("edit_done", uid, id=oid), parse_mode="Markdown", reply_markup=kb_main(uid))
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"edit_value error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return ED_VALUE


# ══════════════════════════════════════════════
# 10. ДОБАВИТЬ УСЛУГУ
# ══════════════════════════════════════════════
async def add_svc_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return ConversationHandler.END
    orders = open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    orders_text = "\n".join(order_short(o, uid) for o in orders)
    await update.message.reply_text(
        tr("add_svc_order", uid, orders=orders_text),
        parse_mode="Markdown", reply_markup=kb_back(uid)
    )
    return AS_ORDER


async def add_svc_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o or o["status"] == "closed":
            await update.message.reply_text(tr("not_found", uid))
            return AS_ORDER
        ctx.user_data["order_id"] = oid
        svcs = get_available_services(uid)
        await update.message.reply_text(
            f"🚗 *{o['car']}* | {o['client']}\n\n" + tr("accept_service", uid),
            parse_mode="Markdown",
            reply_markup=kb_list(svcs, uid, cols=2)
        )
        return AS_SERVICE
    except Exception as e:
        logger.error(f"add_svc_order error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return AS_ORDER


async def add_svc_service(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    svc = update.message.text
    ctx.user_data["add_svc_name"]   = svc
    ctx.user_data["add_svc_master"] = sname(uid)

    if svc_needs_subs(svc, uid):
        if "Yuvish" in svc or "Мойка" in svc:
            subs = get_wash_subs(uid)
        elif "Tonirovka" in svc or "Тонировка" in svc:
            subs = get_tint_subs(uid)
        else:
            subs = get_film_subs(uid)
        await update.message.reply_text(f"📋 {svc}\n\nVid / Вид:", reply_markup=kb_list(subs, uid, cols=1))
        return AS_SUB

    if svc_needs_works(svc, uid):
        await update.message.reply_text(tr("svc_works_hint", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return AS_WORKS_LIST

    await update.message.reply_text(tr("svc_sub_price", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
    return AS_PRICE


async def add_svc_sub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        svcs = get_available_services(uid)
        await update.message.reply_text(tr("accept_service", uid), reply_markup=kb_list(svcs, uid, cols=2))
        return AS_SERVICE
    ctx.user_data["add_svc_name"] = f"{ctx.user_data['add_svc_name']} — {update.message.text}"
    await update.message.reply_text(tr("svc_sub_price", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
    return AS_PRICE


async def add_svc_works_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        svcs = get_available_services(uid)
        await update.message.reply_text(tr("accept_service", uid), reply_markup=kb_list(svcs, uid, cols=2))
        return AS_SERVICE
    works_raw = [l.strip() for l in update.message.text.strip().split("\n") if l.strip()]
    if not works_raw:
        await update.message.reply_text("❌")
        return AS_WORKS_LIST
    ctx.user_data["add_svc_works_raw"] = works_raw
    example = "\n".join(["500000", "200000", "150000"][:len(works_raw)])
    works_list = "\n".join(f"{i+1}. {w}" for i, w in enumerate(works_raw))
    await update.message.reply_text(
        f"{tr('works_list_label', uid)}\n{works_list}\n\n" + tr("svc_works_prices_hint", uid, works=f"{len(works_raw)} ta", example=example),
        parse_mode="Markdown", reply_markup=kb_back(uid)
    )
    return AS_WORKS_PRICE


async def add_svc_works_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("svc_works_hint", uid), parse_mode="Markdown", reply_markup=kb_back(uid))
        return AS_WORKS_LIST
    works_raw = ctx.user_data["add_svc_works_raw"]
    price_lines = [l.strip() for l in update.message.text.strip().split("\n") if l.strip()]
    if len(price_lines) != len(works_raw):
        await update.message.reply_text(
            tr("svc_works_mismatch", uid, n_prices=len(price_lines), n_works=len(works_raw)),
            parse_mode="Markdown"
        )
        return AS_WORKS_PRICE
    try:
        works = [{"name": w, "price": int(p.replace(" ", "")), "master": sname(uid)}
                 for w, p in zip(works_raw, price_lines)]
        return await _save_add_svc(update, ctx, works=works)
    except Exception as e:
        logger.error(f"add_svc_works_price error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return AS_WORKS_PRICE


async def add_svc_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        return await cancel(update, ctx)
    try:
        price = int(update.message.text.replace(" ", ""))
        work = {"name": ctx.user_data["add_svc_name"], "price": price, "master": sname(uid)}
        return await _save_add_svc(update, ctx, works=[work])
    except Exception as e:
        logger.error(f"add_svc_price error: {e}")
        await update.message.reply_text(tr("enter_num", uid))
        return AS_PRICE


async def _save_add_svc(update, ctx, works):
    uid = update.effective_user.id
    oid = ctx.user_data["order_id"]
    o = get_order(oid)
    existing_works = o.get("works", [])
    existing_works.extend(works)
    upd_order(oid, {"works": existing_works})
    # Автоматически меняем статус на in_work
    if o.get("status") == "accepted":
        upd_order(oid, {"status": "in_work"})
    total = sum(w["price"] for w in works)
    svc_name = works[0]["name"] if len(works) == 1 else f"{len(works)} ta ish"
    msg = tr("add_svc_done", uid, id=oid, svc=svc_name, master=sname(uid), total=fmt(total))
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
    await notify(ctx, msg, uid)
    return ConversationHandler.END


# ══════════════════════════════════════════════
# КОМАНДЫ И ОТЧЁТЫ
# ══════════════════════════════════════════════
async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text(tr("only_owner", uid))
        return
    orders = today_orders()
    if not orders:
        await update.message.reply_text(tr("rep_none", uid))
        return
    t_uzs = t_usd = t_card = t_bank = t_debt = t_exp = t_margin = 0
    for o in orders:
        for p in o.get("payments", []):
            if p.get("is_debt") and not p.get("paid"):
                t_debt += p["amt_uzs"]
            else:
                m = p["method"]
                if "UZS" in m:                              t_uzs  += p["amt_uzs"]
                elif "USD" in m:                            t_usd  += p["amt_uzs"]
                elif "Karta" in m or "Карта" in m:          t_card += p["amt_uzs"]
                elif "O'tkazma" in m or "Перечисл" in m:   t_bank += p["amt_uzs"]
        t_exp    += calc_expenses(o)
        t_margin += calc_margin(o)
    received = t_uzs + t_usd + t_card + t_bank
    closed = sum(1 for o in orders if o["status"] == "closed")
    lines = [
        tr("rep_title",   uid, date=today_d()),
        tr("rep_orders",  uid, t=len(orders), c=closed, w=len(orders)-closed),
        tr("rep_income",  uid, v=fmt(received)),
        tr("rep_uzs",     uid, v=fmt(t_uzs)),
        tr("rep_usd",     uid, v=fmt(t_usd)),
        tr("rep_card",    uid, v=fmt(t_card)),
        tr("rep_bank",    uid, v=fmt(t_bank)),
        tr("rep_debt",    uid, v=fmt(t_debt)),
        tr("rep_expense", uid, v=fmt(t_exp)),
        tr("rep_margin",  uid, v=fmt(t_margin)),
        tr("rep_profit",  uid, v=fmt(received - t_exp)),
        "\n─────────────────"
    ]
    for o in orders:
        lines.append(order_short(o, uid, show_margin=True))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))


async def cmd_myreport(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return
    name = sname(uid)
    all_o = all_orders_list()
    active = [o for o in all_o if o.get("master") == name and o["status"] != "closed"]
    closed_today = [o for o in all_o if o.get("master") == name and o.get("closed_date", "") == today_d()]
    income = sum(calc_paid(o) for o in closed_today)
    msg = tr("myreport", uid, name=name, active=len(active), closed=len(closed_today), income=fmt(income))
    lines = [msg, "\n─────────────\n*Ishda / В работе:*"]
    for o in active:
        lines.append(order_short(o, uid))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))


async def cmd_my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return
    orders = my_open(uid) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return
    # Заголовок
    await update.message.reply_text(
        tr("list_open_my", uid, name=sname(uid), n=len(orders)),
        parse_mode="Markdown", reply_markup=kb_main(uid)
    )
    # Каждая машина отдельным сообщением с inline-кнопками
    for o in orders:
        await send_order_card(ctx.bot, uid, o)


async def cmd_all_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text(tr("only_owner", uid))
        return
    orders = open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return
    await update.message.reply_text(
        tr("list_open_all", uid, n=len(orders)),
        parse_mode="Markdown", reply_markup=kb_main(uid)
    )
    for o in orders:
        await send_order_card(ctx.bot, uid, o, show_margin=True)


async def cmd_debts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text(tr("only_owner", uid))
        return
    debts = all_debts()
    if not debts:
        await update.message.reply_text(tr("debt_none", uid), reply_markup=kb_main(uid))
        return
    total = sum(a for _, a in debts)
    lines = [tr("debt_title", uid, n=len(debts), total=fmt(total))]
    for o, amt in debts:
        lines.append(f"#{o['id']} | {o['car']} | {o['client']}\n  📱 {o.get('phone','-')} | {fmt(amt)} сум | {o['date']}")
        lines.append("─────────────")
    lines.append(tr("debt_cmd", uid))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))


async def cmd_close_debt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return
    args = ctx.args
    if not args:
        await update.message.reply_text("/debt 5 yoki /qarz 5")
        return
    try:
        oid = int(args[0])
        o = get_order(oid)
        if not o:
            await update.message.reply_text(tr("not_found", uid))
            return
        payments = o.get("payments", [])
        for p in payments:
            if p.get("is_debt") and not p.get("paid"):
                p["paid"] = True
                p["paid_time"] = now_t()
        upd_order(oid, {"payments": payments})
        await update.message.reply_text(tr("debt_closed", uid, id=oid), reply_markup=kb_main(uid))
    except Exception as e:
        logger.error(f"close_debt error: {e}")
        await update.message.reply_text("/debt 5")


async def cmd_staff(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        return
    language = lg(uid)
    lines = [tr("staff_title", uid)]
    for i, (sid, name) in enumerate(STAFF.items(), 1):
        role = ROLES.get(sid, "mechanic")
        role_label = ROLE_NAMES[language].get(role, role)
        is_me = " _(siz/вы)_" if sid == uid else ""
        lines.append(f"{i}. *{name}*{is_me}\n   {role_label}\n   🆔 `{sid}`")

    # Футер — переведён по языку, без бэкслэшей перед апострофом
    lines.append("\n─────────────────")
    if language == "uz":
        lines.append(
            "*Qoshish:* `/add_staff ID Ism rol`\n"
            "*Ochirish:* `/del_staff ID`\n"
            "*Ozgartirish:* `/edit_staff ID name Yangi Ism`\n"
            "*Rollar:* `owner` `mechanic` `wash` `tint` `body` `elec`\n\n"
            "💡 ID ni bilish: @userinfobot ga yozing"
        )
    else:
        lines.append(
            "*Добавить:* `/add_staff ID Имя роль`\n"
            "*Удалить:* `/del_staff ID`\n"
            "*Изменить:* `/edit_staff ID name НовоеИмя`\n"
            "*Роли:* `owner` `mechanic` `wash` `tint` `body` `elec`\n\n"
            "💡 Узнать ID: напиши @userinfobot"
        )
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))


# ══════════════════════════════════════════════
# КАССА v3.2 — полный модуль
# ══════════════════════════════════════════════
def get_kassa_methods(uid):
    return T["kassa_methods"][lg(uid)]


def kassa_menu_kb(uid):
    return ReplyKeyboardMarkup([
        [KeyboardButton(tr("kassa_btn_balance", uid)), KeyboardButton(tr("kassa_btn_history", uid))],
        [KeyboardButton(tr("kassa_btn_income",  uid)), KeyboardButton(tr("kassa_btn_expense", uid))],
        [KeyboardButton(tr("cancel", uid))],
    ], resize_keyboard=True)


async def kassa_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return ConversationHandler.END
    if not is_owner(uid):
        await _kassa_my_show(update, uid)
        return ConversationHandler.END
    ctx.user_data.clear()
    await update.message.reply_text(
        tr("kassa_menu_title", uid), parse_mode="Markdown",
        reply_markup=kassa_menu_kb(uid)
    )
    return KA_MENU


async def _kassa_my_show(update, uid):
    name = sname(uid)
    today = today_d()
    my_works = [
        (o, w) for o in all_orders_list()
        for w in o.get("works", [])
        if w.get("master") == name and o["date"] == today
    ]
    if not my_works:
        await update.message.reply_text(tr("kassa_my_none", uid), reply_markup=kb_main(uid))
        return
    works_total = sum(w["price"] for _, w in my_works)
    works_lines = "\n".join(
        f"  • №{o['id']} {o['car']} | {w['name']} — {fmt(w['price'])} сум"
        for o, w in my_works
    )
    my_expenses = [
        (o, e) for o in all_orders_list()
        for e in o.get("expenses", [])
        if e.get("by_id") == uid and o["date"] == today
    ]
    exp_total = sum(e["amount"] for _, e in my_expenses)
    exp_lines = "\n".join(
        f"  • №{o['id']} | {e['type']}: {e.get('desc','')} — {fmt(e['amount'])} сум"
        for o, e in my_expenses
    )
    lines = [tr("kassa_my_title", uid, name=name)]
    lines.append(tr("kassa_my_works", uid, lines=works_lines, total=fmt(works_total)))
    if my_expenses:
        lines.append(tr("kassa_my_exp", uid, total=fmt(exp_total), lines=exp_lines))
    lines.append(tr("kassa_my_net", uid, v=fmt(works_total - exp_total)))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))


async def kassa_menu(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    if is_back(text, uid):
        return await cancel(update, ctx)
    if text == tr("kassa_btn_balance", uid):
        await _kassa_balance(update, uid)
        return KA_MENU
    if text == tr("kassa_btn_history", uid):
        await _kassa_history(update, uid)
        return KA_MENU
    if text == tr("kassa_btn_income", uid):
        await update.message.reply_text(tr("kassa_inc_amt_q", uid),
                                        parse_mode="Markdown", reply_markup=kb_back(uid))
        return KA_INC_AMT
    if text == tr("kassa_btn_expense", uid):
        cats = [tr("kassa_exp_cat_order", uid),
                tr("kassa_exp_cat_master", uid),
                tr("kassa_exp_cat_other", uid)]
        await update.message.reply_text(tr("kassa_exp_cat_q", uid),
                                        parse_mode="Markdown",
                                        reply_markup=kb_list(cats, uid, cols=1))
        return KA_EXP_CAT
    await update.message.reply_text(tr("kassa_menu_title", uid),
                                    parse_mode="Markdown", reply_markup=kassa_menu_kb(uid))
    return KA_MENU


async def _kassa_balance(update, uid):
    ops = kassa_ops_all(limit=100000)
    total_income  = sum(op["amount"] for op in ops if op["op_type"] == "income")
    total_expense = sum(op["amount"] for op in ops if op["op_type"] == "expense")
    all_ords = all_orders_list()
    orders_income = orders_expense = 0
    for o in all_ords:
        for p in o.get("payments", []):
            if not (p.get("is_debt") and not p.get("paid")):
                orders_income += p.get("amt_uzs", 0)
        orders_expense += calc_expenses(o)
    total_in  = total_income  + orders_income
    total_out = total_expense + orders_expense
    balance   = total_in - total_out
    today_ops = kassa_ops_today()
    t_in  = sum(op["amount"] for op in today_ops if op["op_type"] == "income")
    t_out = sum(op["amount"] for op in today_ops if op["op_type"] == "expense")
    for o in today_orders():
        for p in o.get("payments", []):
            if not (p.get("is_debt") and not p.get("paid")):
                t_in += p.get("amt_uzs", 0)
        t_out += calc_expenses(o)
    await update.message.reply_text(
        tr("kassa_balance_title", uid,
           income=fmt(total_in), expense=fmt(total_out), balance=fmt(balance),
           today_in=fmt(t_in), today_out=fmt(t_out)),
        parse_mode="Markdown"
    )


async def _kassa_history(update, uid, limit=20):
    ops = kassa_ops_all(limit=limit)
    if not ops:
        await update.message.reply_text(tr("kassa_history_none", uid))
        return
    lines = [tr("kassa_history_title", uid, n=len(ops))]
    for op in ops:
        icon = "📥" if op["op_type"] == "income" else "📤"
        cat  = op.get("category") or ""
        master = f" | 👤 {op['master_name']}" if op.get("master_name") else ""
        order  = f" | 🚗 №{op['order_id']}" if op.get("order_id") else ""
        desc   = op.get("description") or "—"
        lines.append(
            f"{icon} *{fmt(op['amount'])} сум* — {op['date']}\n"
            f"   {cat}{master}{order}\n"
            f"   📝 {desc} | {op.get('method','')}"
        )
        lines.append("─────────────")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ── ПРИХОД ────────────────────────────────────────────────────────────────
async def kassa_inc_amt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("kassa_menu_title", uid),
                                        parse_mode="Markdown", reply_markup=kassa_menu_kb(uid))
        return KA_MENU
    try:
        ctx.user_data["ka_amount"] = int(update.message.text.replace(" ", ""))
        await update.message.reply_text(tr("kassa_inc_method_q", uid),
                                        reply_markup=kb_list(get_kassa_methods(uid), uid, cols=2))
        return KA_INC_METHOD
    except Exception:
        await update.message.reply_text(tr("enter_num", uid))
        return KA_INC_AMT


async def kassa_inc_method(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("kassa_inc_amt_q", uid),
                                        parse_mode="Markdown", reply_markup=kb_back(uid))
        return KA_INC_AMT
    if update.message.text not in get_kassa_methods(uid):
        await update.message.reply_text(tr("kassa_inc_method_q", uid),
                                        reply_markup=kb_list(get_kassa_methods(uid), uid, cols=2))
        return KA_INC_METHOD
    ctx.user_data["ka_method"] = update.message.text
    await update.message.reply_text(tr("kassa_inc_desc_q", uid),
                                    parse_mode="Markdown", reply_markup=kb_back(uid))
    return KA_INC_DESC


async def kassa_inc_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("kassa_inc_method_q", uid),
                                        reply_markup=kb_list(get_kassa_methods(uid), uid, cols=2))
        return KA_INC_METHOD
    desc   = update.message.text.strip()
    amount = ctx.user_data["ka_amount"]
    method = ctx.user_data["ka_method"]
    kassa_add({"op_type": "income", "amount": amount, "method": method,
               "category": "Kirim / Приход", "description": desc,
               "by_name": sname(uid), "by_id": uid})
    msg = tr("kassa_inc_done", uid, amount=fmt(amount), method=method, desc=desc)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kassa_menu_kb(uid))
    if uid != OWNER_ID:
        try:
            await ctx.bot.send_message(OWNER_ID,
                f"📥 *Kassa kirim: {fmt(amount)} сум*\n💳 {method}\n📝 {desc}\n👤 {sname(uid)}",
                parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"kassa notify: {e}")
    return KA_MENU


# ── РАСХОД ────────────────────────────────────────────────────────────────
async def kassa_exp_cat(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("kassa_menu_title", uid),
                                        parse_mode="Markdown", reply_markup=kassa_menu_kb(uid))
        return KA_MENU
    cats = [tr("kassa_exp_cat_order", uid),
            tr("kassa_exp_cat_master", uid),
            tr("kassa_exp_cat_other", uid)]
    if update.message.text not in cats:
        await update.message.reply_text(tr("kassa_exp_cat_q", uid),
                                        parse_mode="Markdown", reply_markup=kb_list(cats, uid, cols=1))
        return KA_EXP_CAT
    ctx.user_data["ka_category"] = update.message.text
    if update.message.text == tr("kassa_exp_cat_order", uid):
        orders = open_orders()
        if not orders:
            await update.message.reply_text(tr("no_open", uid), reply_markup=kassa_menu_kb(uid))
            return KA_MENU
        lines = ["🚗 *Ochiq / Открытые:*\n"]
        lines += [f"  №{o['id']} | {o['car']} | {o['client']} | {o['master']}" for o in orders]
        lines.append("\n" + tr("enter_order", uid))
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown",
                                        reply_markup=kb_back(uid))
        return KA_EXP_ORDER
    elif update.message.text == tr("kassa_exp_cat_master", uid):
        await update.message.reply_text(tr("kassa_exp_master_q", uid),
                                        reply_markup=kb_list(list(STAFF.values()), uid, cols=1))
        return KA_EXP_MASTER
    else:
        await update.message.reply_text(tr("kassa_exp_desc_q", uid),
                                        parse_mode="Markdown", reply_markup=kb_back(uid))
        return KA_EXP_DESC


async def kassa_exp_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        cats = [tr("kassa_exp_cat_order",uid), tr("kassa_exp_cat_master",uid), tr("kassa_exp_cat_other",uid)]
        await update.message.reply_text(tr("kassa_exp_cat_q",uid), parse_mode="Markdown",
                                        reply_markup=kb_list(cats, uid, cols=1))
        return KA_EXP_CAT
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o:
            await update.message.reply_text(tr("not_found", uid)); return KA_EXP_ORDER
        ctx.user_data["ka_order_id"]  = oid
        ctx.user_data["ka_order_str"] = f"№{oid} {o['car']} | {o['client']}"
        await update.message.reply_text(tr("kassa_exp_desc_q", uid),
                                        parse_mode="Markdown", reply_markup=kb_back(uid))
        return KA_EXP_DESC
    except Exception:
        await update.message.reply_text(tr("enter_num", uid)); return KA_EXP_ORDER


async def kassa_exp_master(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        cats = [tr("kassa_exp_cat_order",uid), tr("kassa_exp_cat_master",uid), tr("kassa_exp_cat_other",uid)]
        await update.message.reply_text(tr("kassa_exp_cat_q",uid), parse_mode="Markdown",
                                        reply_markup=kb_list(cats, uid, cols=1))
        return KA_EXP_CAT
    if update.message.text not in list(STAFF.values()):
        await update.message.reply_text(tr("kassa_exp_master_q", uid),
                                        reply_markup=kb_list(list(STAFF.values()), uid, cols=1))
        return KA_EXP_MASTER
    ctx.user_data["ka_master"] = update.message.text
    await update.message.reply_text(tr("kassa_exp_desc_q", uid),
                                    parse_mode="Markdown", reply_markup=kb_back(uid))
    return KA_EXP_DESC


async def kassa_exp_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        cat = ctx.user_data.get("ka_category", "")
        if cat == tr("kassa_exp_cat_order", uid):
            orders = open_orders()
            lines = ["🚗 *Ochiq / Открытые:*\n"]
            lines += [f"  №{o['id']} | {o['car']} | {o['client']}" for o in orders]
            await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_back(uid))
            return KA_EXP_ORDER
        elif cat == tr("kassa_exp_cat_master", uid):
            await update.message.reply_text(tr("kassa_exp_master_q", uid),
                                            reply_markup=kb_list(list(STAFF.values()), uid, cols=1))
            return KA_EXP_MASTER
        else:
            cats = [tr("kassa_exp_cat_order",uid), tr("kassa_exp_cat_master",uid), tr("kassa_exp_cat_other",uid)]
            await update.message.reply_text(tr("kassa_exp_cat_q",uid), parse_mode="Markdown",
                                            reply_markup=kb_list(cats, uid, cols=1))
            return KA_EXP_CAT
    ctx.user_data["ka_desc"] = update.message.text.strip()
    await update.message.reply_text(tr("kassa_exp_amt_q", uid),
                                    parse_mode="Markdown", reply_markup=kb_back(uid))
    return KA_EXP_AMT


async def kassa_exp_amt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("kassa_exp_desc_q", uid),
                                        parse_mode="Markdown", reply_markup=kb_back(uid))
        return KA_EXP_DESC
    try:
        ctx.user_data["ka_amount"] = int(update.message.text.replace(" ", ""))
        await update.message.reply_text(tr("kassa_exp_method_q", uid),
                                        reply_markup=kb_list(get_kassa_methods(uid), uid, cols=2))
        return KA_EXP_METHOD
    except Exception:
        await update.message.reply_text(tr("enter_num", uid)); return KA_EXP_AMT


async def kassa_exp_method(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_back(update.message.text, uid):
        await update.message.reply_text(tr("kassa_exp_amt_q", uid),
                                        parse_mode="Markdown", reply_markup=kb_back(uid))
        return KA_EXP_AMT
    if update.message.text not in get_kassa_methods(uid):
        await update.message.reply_text(tr("kassa_exp_method_q", uid),
                                        reply_markup=kb_list(get_kassa_methods(uid), uid, cols=2))
        return KA_EXP_METHOD
    amount    = ctx.user_data["ka_amount"]
    desc      = ctx.user_data.get("ka_desc", "")
    cat_raw   = ctx.user_data.get("ka_category", "")
    method    = update.message.text
    order_id  = ctx.user_data.get("ka_order_id")
    master    = ctx.user_data.get("ka_master", "")
    order_str = ctx.user_data.get("ka_order_str", "")
    cat_display = cat_raw
    if order_str: cat_display = f"{cat_raw} — {order_str}"
    elif master:  cat_display = f"{cat_raw} — {master}"
    kassa_add({"op_type": "expense", "amount": amount, "method": method,
               "category": cat_display, "description": desc, "order_id": order_id,
               "master_name": master, "by_name": sname(uid), "by_id": uid})
    msg = tr("kassa_exp_done", uid, amount=fmt(amount), category=cat_display, desc=desc)
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kassa_menu_kb(uid))
    if uid != OWNER_ID:
        try:
            await ctx.bot.send_message(OWNER_ID,
                f"📤 *Kassa chiqim: {fmt(amount)} сум*\n📂 {cat_display}\n📝 {desc}\n👤 {sname(uid)}",
                parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"kassa notify: {e}")
    return KA_MENU


async def cmd_kassa(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        return

    if not is_owner(uid):
        name = sname(uid)
        all_ords = all_orders_list()
        today = today_d()
        my_works = [
            (o, w) for o in all_ords
            for w in o.get("works", [])
            if w.get("master") == name and o["date"] == today
        ]
        if not my_works:
            await update.message.reply_text(tr("kassa_my_none", uid), reply_markup=kb_main(uid))
            return
        works_total = sum(w["price"] for _, w in my_works)
        works_lines = "\n".join(
            f"  • №{o['id']} {o['car']} | {w['name']} — {fmt(w['price'])} сум"
            for o, w in my_works
        )
        my_expenses = [
            (o, e) for o in all_ords
            for e in o.get("expenses", [])
            if e.get("by_id") == uid and o["date"] == today
        ]
        exp_total = sum(e["amount"] for _, e in my_expenses)
        exp_lines = "\n".join(
            f"  • №{o['id']} | {e['type']}: {e.get('desc','')} — {fmt(e['amount'])} сум"
            for o, e in my_expenses
        )
        net = works_total - exp_total
        lines = [tr("kassa_my_title", uid, name=name)]
        lines.append(tr("kassa_my_works", uid, lines=works_lines, total=fmt(works_total)))
        if my_expenses:
            lines.append(tr("kassa_my_exp", uid, total=fmt(exp_total), lines=exp_lines))
        lines.append(tr("kassa_my_net", uid, v=fmt(net)))
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))
        return

    # Касса владельца
    orders = today_orders()
    if not orders:
        await update.message.reply_text(tr("kassa_none", uid), reply_markup=kb_main(uid))
        return

    cash_uzs = cash_usd_amt = cash_usd_uzs = card = bank = debt = 0
    for o in orders:
        for p in o.get("payments", []):
            if p.get("is_debt") and not p.get("paid"):
                debt += p["amt_uzs"]
                continue
            m = p["method"]
            if "UZS" in m:                              cash_uzs     += p["amt_uzs"]
            elif "USD" in m:                            cash_usd_amt += p.get("amount", 0); cash_usd_uzs += p["amt_uzs"]
            elif "Karta" in m or "Карта" in m:          card         += p["amt_uzs"]
            elif "O'tkazma" in m or "Перечисл" in m:   bank         += p["amt_uzs"]

    total = cash_uzs + cash_usd_uzs + card + bank
    exp_by_staff = {}
    total_exp = 0
    for o in orders:
        for e in o.get("expenses", []):
            exp_by_staff.setdefault(e.get("by", "—"), []).append((o, e))
            total_exp += e["amount"]

    net = total - total_exp
    lines = [tr("kassa_title", uid, date=today_d())]
    if cash_uzs > 0:     lines.append(tr("kassa_cash", uid, v=fmt(cash_uzs)))
    if cash_usd_amt > 0: lines.append(tr("kassa_usd", uid, usd=cash_usd_amt, v=fmt(cash_usd_uzs)))
    if card > 0:         lines.append(tr("kassa_card", uid, v=fmt(card)))
    if bank > 0:         lines.append(tr("kassa_bank", uid, v=fmt(bank)))
    if debt > 0:         lines.append(tr("kassa_debt", uid, v=fmt(debt)))
    lines.append(tr("kassa_total", uid, v=fmt(total)))

    if exp_by_staff:
        lines.append(tr("kassa_exp_detail", uid))
        for staff_name, exps in exp_by_staff.items():
            staff_total = sum(e["amount"] for _, e in exps)
            lines.append(f"  👤 *{staff_name}* — {fmt(staff_total)} сум")
            for o, e in exps:
                lines.append(f"    • №{o['id']} | {e['type']}: {e.get('desc','')} — {fmt(e['amount'])} сум")
        lines.append(tr("kassa_exp", uid, v=fmt(total_exp)))

    lines.append(tr("kassa_net", uid, v=fmt(net)))

    open_debts = [
        (o, sum(p["amt_uzs"] for p in o.get("payments", []) if p.get("is_debt") and not p.get("paid")))
        for o in open_orders()
    ]
    open_debts = [(o, a) for o, a in open_debts if a > 0]
    if open_debts:
        lines.append("\n⚠️ *Ochiq qarzlar / Открытые долги:*")
        for o, amt in open_debts:
            lines.append(f"  №{o['id']} | {o['car']} | {o['client']} — {fmt(amt)} сум")

    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))


# ══════════════════════════════════════════════
# УТРЕННЕЕ УВЕДОМЛЕНИЕ
# ══════════════════════════════════════════════
async def morning_reminder(ctx: ContextTypes.DEFAULT_TYPE):
    """Отправляется владельцу каждое утро в 09:00 Ташкент (04:00 UTC)"""
    uid = OWNER_ID
    try:
        orders = open_orders()
        debts  = all_debts()
        open_lines = ""
        if orders:
            open_lines = "\n".join(
                f"  • №{o['id']} | {o['car']} | {o['client']} | {o['master']}"
                for o in orders[:15]
            ) + "\n\n"
        debt_total = sum(a for _, a in debts)
        debt_lines = ""
        if debts:
            debt_lines = "\n".join(
                f"  • №{o['id']} | {o['client']} | 📱 {o.get('phone','-')} — {fmt(amt)} сум"
                for o, amt in debts[:10]
            )
        text = tr("morning_msg", uid,
                  open_count=len(orders), open_lines=open_lines,
                  debt_count=len(debts), debt_total=fmt(debt_total), debt_lines=debt_lines)
        await ctx.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode="Markdown")
    except Exception as e:
        logger.error(f"morning_reminder error: {e}")


# ══════════════════════════════════════════════
# ДЕТАЛИ (inline кнопка)
# ══════════════════════════════════════════════
async def callback_details(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    parts_data = query.data.split("_")
    if len(parts_data) < 3:
        return
    oid = int(parts_data[1])
    uid = query.from_user.id
    o = get_order(oid)
    if not o:
        await query.message.reply_text(tr("not_found_order", uid))
        return

    try:
        start_dt = datetime.strptime(f"{o['date']} {o['time']}", "%Y-%m-%d %H:%M")
        end_time = o.get("closed_time", now_t())
        end_date = o.get("closed_date", o["date"])
        end_dt   = datetime.strptime(f"{end_date} {end_time}", "%Y-%m-%d %H:%M")
        diff     = end_dt - start_dt
        hours    = int(diff.total_seconds() // 3600)
        mins     = int((diff.total_seconds() % 3600) // 60)
        duration = f"{hours}h {mins}min" if hours > 0 else f"{mins} min"
        start_str = f"{o['date']} {o['time']}"
        end_str   = f"{end_date} {end_time}"
    except Exception as e:
        logger.error(f"callback_details error: {e}")
        duration  = "—"
        start_str = f"{o['date']} {o['time']}"
        end_str   = o.get("closed_time", "—")

    lines = [tr("details_title", uid, id=oid)]
    lines.append(f"🚗 {o['car']} | 👤 {o['client']} | 📱 {o.get('phone','-')}")
    lines.append(tr("details_dates", uid, start=start_str, end=end_str, duration=duration))

    if o.get("works"):
        lines.append(tr("details_works", uid))
        works_total = 0
        for w in o["works"]:
            master_line = f" | 👤 {w['master']}" if w.get("master") else ""
            lines.append(f"  • {w['name']} — {fmt(w['price'])} сум{master_line}")
            works_total += w["price"]
        lines.append(f"  Jami / Итого: {fmt(works_total)} сум")

    if o.get("parts"):
        lines.append(tr("details_parts", uid))
        for p in o["parts"]:
            line = f"  • {p['name']} [{p['source']}] — {fmt(p['sell_price'])} сум"
            if is_owner(uid) and p.get("cost_price", 0) > 0:
                line += f" _(📈 {fmt(p['sell_price'] - p['cost_price'])})_"
            lines.append(line)

    lines.append(tr("details_total", uid, total=fmt(calc_total(o))))
    await query.message.reply_text("\n".join(lines), parse_mode="Markdown")


# ══════════════════════════════════════════════
# INLINE КАРТОЧКА ЗАЯВКИ
# ══════════════════════════════════════════════
async def send_order_card(bot, uid, o, show_margin=False):
    """Отправляет карточку заявки с inline-кнопками действий"""
    text = order_short(o, uid, show_margin=show_margin)
    oid = o["id"]
    st = o.get("status", "in_work")

    # Кнопки зависят от роли и статуса
    btn_rows = []

    # Строка 1: основные действия
    row1 = []
    if can_pay(uid) and st not in ("closed",):
        row1.append(InlineKeyboardButton("💰", callback_data=f"quick_pay_{oid}_{uid}"))
    if can_parts(uid) and st not in ("closed",):
        row1.append(InlineKeyboardButton("🔩", callback_data=f"quick_part_{oid}_{uid}"))
    row1.append(InlineKeyboardButton("➕", callback_data=f"quick_svc_{oid}_{uid}"))
    if st not in ("closed",):
        row1.append(InlineKeyboardButton("📤", callback_data=f"quick_exp_{oid}_{uid}"))
    if row1:
        btn_rows.append(row1)

    # Строка 2: закрыть / статус
    row2 = []
    if can_close_order(uid, o) and st not in ("closed",):
        row2.append(InlineKeyboardButton("✅ " + tr("btn_close", uid), callback_data=f"quick_close_{oid}_{uid}"))
    row2.append(InlineKeyboardButton("📋", callback_data=f"details_{oid}_{uid}"))
    if row2:
        btn_rows.append(row2)

    if not btn_rows:
        btn_rows = [[InlineKeyboardButton("📋", callback_data=f"details_{oid}_{uid}")]]

    await bot.send_message(
        chat_id=uid, text=text,
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(btn_rows)
    )


async def callback_quick(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Обработчик быстрых inline-кнопок из карточки"""
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    parts = query.data.split("_")
    # quick_ACTION_OID_CALLERUID
    action = parts[1]
    oid = int(parts[2])

    o = get_order(oid)
    if not o:
        await query.message.reply_text(tr("not_found", uid))
        return

    if action == "close":
        # Быстрое закрытие прямо из карточки
        if not can_close_order(uid, o):
            await query.message.reply_text(tr("close_no_right", uid))
            return
        if not o.get("payments"):
            await query.message.reply_text(tr("close_no_pay", uid), parse_mode="Markdown")
            return
        remaining = calc_remaining(o)
        has_debt = any(p.get("is_debt") and not p.get("paid") for p in o.get("payments", []))
        if remaining > 0 and not has_debt:
            await query.message.reply_text(tr("close_no_pay", uid), parse_mode="Markdown")
            return
        upd_order(oid, {"status": "closed", "closed_time": now_t(),
                        "closed_date": today_d(), "closed_by": sname(uid)})
        o = get_order(oid)
        paid = calc_paid(o)
        net = paid - calc_expenses(o)
        summary = tr("close_summary", uid, paid=fmt(paid), exp=fmt(calc_expenses(o)), net=fmt(net))
        debt_line = tr("close_debt_w", uid) if has_debt else ""
        msg = tr("close_done", uid, id=oid, car=o["car"], client=o["client"],
                 phone=o.get("phone", "—"), debt=debt_line, summary=summary)
        await query.message.reply_text(msg, parse_mode="Markdown")
        await ctx.bot.send_message(chat_id=OWNER_ID,
            text=f"🏁 №{oid} yopildi | {o['car']} | {o['client']} | {sname(uid)}",
            parse_mode="Markdown")

    elif action == "pay":
        # Запускаем оплату — отвечаем с подсказкой
        if not can_pay(uid):
            await query.message.reply_text(tr("no_access", uid))
            return
        ctx.user_data.clear()
        ctx.user_data["order_id"] = oid
        if calc_total(o) == 0:
            await query.message.reply_text(tr("pay_no_price", uid, id=oid), parse_mode="Markdown")
            await query.message.reply_text(tr("pay_set_price", uid), parse_mode="Markdown",
                                           reply_markup=kb_back(uid))
            ctx.user_data["quick_flow"] = "pay_price"
        else:
            await query.message.reply_text(build_invoice(o, uid), parse_mode="Markdown",
                                           reply_markup=kb_pay(uid))
            ctx.user_data["quick_flow"] = "pay_method"

    elif action == "part":
        if not can_parts(uid):
            await query.message.reply_text(tr("no_access", uid))
            return
        ctx.user_data.clear()
        ctx.user_data["order_id"] = oid
        await query.message.reply_text(tr("part_name_q", uid), parse_mode="Markdown",
                                       reply_markup=kb_back(uid))

    elif action == "svc":
        ctx.user_data.clear()
        ctx.user_data["order_id"] = oid
        svcs = get_available_services(uid)
        await query.message.reply_text(
            f"🚗 *{o['car']}* | {o['client']}\n\n" + tr("accept_service", uid),
            parse_mode="Markdown",
            reply_markup=kb_list(svcs, uid, cols=2)
        )

    elif action == "exp":
        ctx.user_data.clear()
        ctx.user_data["order_id"] = oid
        await query.message.reply_text(tr("exp_type_q", uid),
                                       reply_markup=kb_list(get_expenses_list(uid), uid))


# ══════════════════════════════════════════════
# ОТМЕНА И РОУТЕР
# ══════════════════════════════════════════════
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ctx.user_data.clear()
    await update.message.reply_text(tr("cancelled", uid), reply_markup=kb_main(uid))
    return ConversationHandler.END


async def router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid  = update.effective_user.id
    text = update.message.text

    if text == "🇺🇿 O'zbek":
        save_lang(uid, "uz")
        await update.message.reply_text(tr("lang_set", uid), parse_mode="Markdown", reply_markup=kb_main(uid))
        return
    if text == "🇷🇺 Русский":
        save_lang(uid, "ru")
        await update.message.reply_text(tr("lang_set", uid), parse_mode="Markdown", reply_markup=kb_main(uid))
        return

    if not is_staff(uid):
        await update.message.reply_text(f"⛔ ID: `{uid}`", parse_mode="Markdown")
        return
    if uid not in USER_LANG:
        await update.message.reply_text(tr("choose_lang", uid), reply_markup=kb_lang())
        return

    if text == "🌐 Til / Язык":
        await update.message.reply_text(tr("choose_lang", uid), reply_markup=kb_lang())
        return

    btn_map = {
        "btn_my":       cmd_my_orders,
        "btn_all":      cmd_all_orders,
        "btn_report":   cmd_report,
        "btn_debts":    cmd_debts,
        "btn_staff":    cmd_staff,
        "btn_kassa":    cmd_kassa,
        "btn_myreport": cmd_myreport,
    }
    for btn_key, fn in btn_map.items():
        if text in [T[btn_key]["uz"], T[btn_key]["ru"]]:
            await fn(update, ctx)
            return



# ══════════════════════════════════════════════
# ЭКСПОРТ БАЗЫ ДАННЫХ
# ══════════════════════════════════════════════
async def cmd_export(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """
    /export         — все заявки + касса
    /export orders  — только заявки
    /export kassa   — только кассовые операции
    /export finance — финансовый отчёт (оплаты + расходы по заявкам)
    """
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text(tr("only_owner", uid))
        return

    import io, csv
    from datetime import datetime as _dt

    arg = (ctx.args[0].lower() if ctx.args else "all")
    now_str = _dt.now().strftime("%Y-%m-%d_%H-%M")

    await update.message.reply_text("⏳ Tayyor qilinmoqda / Подготавливаю...", parse_mode="Markdown")

    files_sent = 0

    # ── ЗАЯВКИ ──────────────────────────────────────────────────────────
    if arg in ("all", "orders"):
        orders = db_run("SELECT * FROM orders ORDER BY id", fetch=True)

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow([
            "ID", "Дата", "Время", "Машина", "Номер", "Клиент", "Телефон",
            "Проблема", "Мастер", "Услуга", "Статус",
            "Работы (итого)", "Запчасти (итого)", "Расходы (итого)",
            "Оплачено", "Долг", "Маржа запчастей",
            "Создал", "Дата закрытия", "Закрыл"
        ])
        for row in orders:
            o = _row_to_order(row)
            works_total  = sum(w.get("price", 0)      for w in o.get("works", []))
            parts_sell   = sum(p.get("sell_price", 0)  for p in o.get("parts", []))
            parts_cost   = sum(p.get("cost_price", 0)  for p in o.get("parts", []))
            parts_margin = parts_sell - parts_cost
            exp_total    = sum(e.get("amount", 0)      for e in o.get("expenses", []))
            paid         = calc_paid(o)
            debt         = sum(p["amt_uzs"] for p in o.get("payments", [])
                               if p.get("is_debt") and not p.get("paid"))
            writer.writerow([
                o["id"], o.get("date",""), o.get("time",""),
                o.get("car",""), o.get("car_num",""),
                o.get("client",""), o.get("phone",""),
                o.get("problem",""), o.get("master",""),
                o.get("service",""), o.get("status",""),
                works_total, parts_sell, exp_total,
                paid, debt, parts_margin,
                o.get("created_by",""),
                o.get("closed_date",""), o.get("closed_by","")
            ])

        buf.seek(0)
        await ctx.bot.send_document(
            chat_id=uid,
            document=io.BytesIO(buf.getvalue().encode("utf-8-sig")),
            filename=f"orders_{now_str}.csv",
            caption=f"📋 Buyurtmalar / Заявки — {len(orders)} ta"
        )
        files_sent += 1

    # ── ДЕТАЛИ РАБОТ ────────────────────────────────────────────────────
    if arg in ("all", "orders"):
        orders = db_run("SELECT * FROM orders ORDER BY id", fetch=True)

        buf2 = io.StringIO()
        w2 = csv.writer(buf2)
        w2.writerow([
            "Заявка ID", "Дата", "Машина", "Клиент", "Мастер",
            "Тип", "Название", "Цена", "Себестоимость", "Источник"
        ])
        for row in orders:
            o = _row_to_order(row)
            oid = o["id"]
            for work in o.get("works", []):
                w2.writerow([oid, o.get("date",""), o.get("car",""), o.get("client",""),
                              o.get("master",""), "Работа", work.get("name",""),
                              work.get("price",0), "", ""])
            for part in o.get("parts", []):
                w2.writerow([oid, o.get("date",""), o.get("car",""), o.get("client",""),
                              o.get("master",""), "Запчасть", part.get("name",""),
                              part.get("sell_price",0), part.get("cost_price",0),
                              part.get("source","")])
            for exp in o.get("expenses", []):
                w2.writerow([oid, o.get("date",""), o.get("car",""), o.get("client",""),
                              o.get("master",""), "Расход", exp.get("type",""),
                              -exp.get("amount",0), "", exp.get("by","")])

        buf2.seek(0)
        await ctx.bot.send_document(
            chat_id=uid,
            document=io.BytesIO(buf2.getvalue().encode("utf-8-sig")),
            filename=f"details_{now_str}.csv",
            caption="📋 Работы, запчасти, расходы по заявкам"
        )
        files_sent += 1

    # ── ОПЛАТЫ ──────────────────────────────────────────────────────────
    if arg in ("all", "finance"):
        orders = db_run("SELECT * FROM orders ORDER BY id", fetch=True)

        buf3 = io.StringIO()
        w3 = csv.writer(buf3)
        w3.writerow([
            "Заявка ID", "Дата заявки", "Машина", "Клиент", "Мастер",
            "Способ", "Сумма UZS", "Долг", "Время", "Принял"
        ])
        for row in orders:
            o = _row_to_order(row)
            for p in o.get("payments", []):
                w3.writerow([
                    o["id"], o.get("date",""), o.get("car",""), o.get("client",""),
                    o.get("master",""),
                    p.get("method",""), p.get("amt_uzs",0),
                    "Да" if p.get("is_debt") else "Нет",
                    p.get("time",""), p.get("by","")
                ])

        buf3.seek(0)
        await ctx.bot.send_document(
            chat_id=uid,
            document=io.BytesIO(buf3.getvalue().encode("utf-8-sig")),
            filename=f"payments_{now_str}.csv",
            caption="💰 Оплаты по заявкам"
        )
        files_sent += 1

    # ── КАССА ────────────────────────────────────────────────────────────
    if arg in ("all", "kassa"):
        ops = db_run("SELECT * FROM kassa_ops ORDER BY id", fetch=True)

        if ops:
            buf4 = io.StringIO()
            w4 = csv.writer(buf4)
            w4.writerow([
                "ID", "Тип", "Сумма", "Способ", "Категория",
                "Описание", "Заявка ID", "Мастер", "Кто добавил", "Дата", "Время"
            ])
            for op in ops:
                w4.writerow([
                    op.get("id",""), op.get("op_type",""),
                    op.get("amount",0), op.get("method",""),
                    op.get("category",""), op.get("description",""),
                    op.get("order_id",""), op.get("master_name",""),
                    op.get("by_name",""), op.get("date",""), op.get("time","")
                ])
            buf4.seek(0)
            await ctx.bot.send_document(
                chat_id=uid,
                document=io.BytesIO(buf4.getvalue().encode("utf-8-sig")),
                filename=f"kassa_{now_str}.csv",
                caption=f"💵 Kassa operatsiyalari / Кассовые операции — {len(ops)} ta"
            )
            files_sent += 1

    # ── ИТОГОВОЕ СООБЩЕНИЕ ───────────────────────────────────────────────
    await update.message.reply_text(
        f"✅ *Export tayyor!*\n"
        f"📁 {files_sent} ta fayl yuborildi / файлов отправлено\n\n"
        f"💡 Excel-da ochish: *Matn → ustunlar* → ajratgich: *vergul*\n"
        f"_(или файл сразу откроется в Excel если UTF-8 BOM)_",
        parse_mode="Markdown"
    )

# ══════════════════════════════════════════════
# ЗАПУСК
# ══════════════════════════════════════════════
def main():
    init_db()
    load_langs()

    app = Application.builder().token(TOKEN).build()

    def btns(key):
        return [T[key]["uz"], T[key]["ru"]]

    def safe_pattern(triggers):
        escaped = [re.escape(t) for t in triggers]
        return "^(" + "|".join(escaped) + ")$"

    def conv(triggers, states, fn):
        return ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(safe_pattern(triggers)), fn)],
            states=states,
            fallbacks=[MessageHandler(filters.ALL, cancel)],
        )

    # Приёмка (включает запчасти после приёмки)
    app.add_handler(conv(btns("btn_accept"), {
        A_CAR_LINE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_car_line)],
        A_PHONE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_phone)],
        A_PROBLEM:     [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_problem)],
        A_MASTER:      [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_master)],
        A_SERVICE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_service)],
        A_SVC_SUB:     [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_svc_sub)],
        A_ACCEPT_PRICE:[MessageHandler(filters.TEXT & ~filters.COMMAND, accept_price)],
        A_WORKS_LIST:  [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_works_list)],
        A_WORKS_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_work_price)],
        AFTER_ACCEPT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, after_accept)],
        P_NAME:        [MessageHandler(filters.TEXT & ~filters.COMMAND, part_name)],
        P_SOURCE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, part_source)],
        P_COST:        [MessageHandler(filters.TEXT & ~filters.COMMAND, part_cost)],
        P_SELL:        [MessageHandler(filters.TEXT & ~filters.COMMAND, part_sell)],
        P_MORE:        [MessageHandler(filters.TEXT & ~filters.COMMAND, part_more)],
    }, accept_start))

    # Запчасти
    app.add_handler(conv(btns("btn_part"), {
        P_ORDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, part_order)],
        P_NAME:   [MessageHandler(filters.TEXT & ~filters.COMMAND, part_name)],
        P_SOURCE: [MessageHandler(filters.TEXT & ~filters.COMMAND, part_source)],
        P_COST:   [MessageHandler(filters.TEXT & ~filters.COMMAND, part_cost)],
        P_SELL:   [MessageHandler(filters.TEXT & ~filters.COMMAND, part_sell)],
        P_MORE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, part_more)],
    }, part_start))

    # Добавить услугу
    app.add_handler(conv(btns("btn_add_svc"), {
        AS_ORDER:       [MessageHandler(filters.TEXT & ~filters.COMMAND, add_svc_order)],
        AS_SERVICE:     [MessageHandler(filters.TEXT & ~filters.COMMAND, add_svc_service)],
        AS_SUB:         [MessageHandler(filters.TEXT & ~filters.COMMAND, add_svc_sub)],
        AS_WORKS_LIST:  [MessageHandler(filters.TEXT & ~filters.COMMAND, add_svc_works_list)],
        AS_WORKS_PRICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_svc_works_price)],
        AS_PRICE:       [MessageHandler(filters.TEXT & ~filters.COMMAND, add_svc_price)],
    }, add_svc_start))

    # Оплата
    app.add_handler(conv(btns("btn_pay"), {
        PAY_ORDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_order)],
        PAY_PRICE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_set_price)],
        PAY_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_method)],
        PAY_RATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_rate)],
        PAY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_amount)],
    }, pay_start))

    # Расходы
    app.add_handler(conv(btns("btn_expense"), {
        EXP_ORDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_order)],
        EXP_TYPE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_type)],
        EXP_DESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_desc)],
        EXP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_amount)],
    }, exp_start))

    # Закрытие
    app.add_handler(conv(btns("btn_close"), {
        CLOSE_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, close_confirm)],
    }, close_start))

    # История
    app.add_handler(conv(btns("btn_history"), {
        HIST_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, hist_show)],
    }, hist_start))

    # Передача
    app.add_handler(conv(btns("btn_transfer"), {
        TR_ORDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_order)],
        TR_MASTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, transfer_master)],
    }, transfer_start))

    # Редактировать
    app.add_handler(conv(btns("btn_edit"), {
        ED_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_order)],
        ED_FIELD: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_field)],
        ED_VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, edit_value)],
    }, edit_start))

    # Команды
    app.add_handler(CommandHandler("start",      cmd_start))
    app.add_handler(CommandHandler("lang",       cmd_lang))
    app.add_handler(CommandHandler("add_staff",  cmd_add_staff))
    app.add_handler(CommandHandler("del_staff",  cmd_del_staff))
    app.add_handler(CommandHandler("edit_staff", cmd_edit_staff))
    app.add_handler(CommandHandler("debt",       cmd_close_debt))
    app.add_handler(CommandHandler("export",     cmd_export))
    app.add_handler(CommandHandler("qarz",       cmd_close_debt))

    # Кнопки меню (group=0)
    # Касса — полный диалог
    kassa_btns_list = [T["btn_kassa"]["uz"], T["btn_kassa"]["ru"]]
    app.add_handler(conv(kassa_btns_list, {
        KA_MENU:       [MessageHandler(filters.TEXT & ~filters.COMMAND, kassa_menu)],
        KA_INC_AMT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, kassa_inc_amt)],
        KA_INC_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, kassa_inc_method)],
        KA_INC_DESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, kassa_inc_desc)],
        KA_EXP_CAT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, kassa_exp_cat)],
        KA_EXP_ORDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, kassa_exp_order)],
        KA_EXP_MASTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, kassa_exp_master)],
        KA_EXP_DESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, kassa_exp_desc)],
        KA_EXP_AMT:    [MessageHandler(filters.TEXT & ~filters.COMMAND, kassa_exp_amt)],
        KA_EXP_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, kassa_exp_method)],
    }, kassa_start))

    for btn_key, fn in [
        ("btn_kassa",    cmd_kassa),
        ("btn_staff",    cmd_staff),
        ("btn_report",   cmd_report),
        ("btn_debts",    cmd_debts),
        ("btn_all",      cmd_all_orders),
        ("btn_my",       cmd_my_orders),
        ("btn_myreport", cmd_myreport),
    ]:
        b = [T[btn_key]["uz"], T[btn_key]["ru"]]
        app.add_handler(MessageHandler(filters.Regex(safe_pattern(b)), fn), group=0)

    app.add_handler(CallbackQueryHandler(callback_details, pattern="^details_"))
    app.add_handler(CallbackQueryHandler(callback_quick, pattern="^quick_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    # Утреннее напоминание — 09:00 Ташкент (04:00 UTC)
    # Реализовано через asyncio — без job-queue
    import asyncio as _asyncio

    async def _morning_loop(application):
        """Фоновая задача: каждый день в MORNING_HOUR_UTC:MORNING_MIN_UTC UTC"""
        while True:
            now = datetime.utcnow()
            next_run = now.replace(
                hour=MORNING_HOUR_UTC, minute=MORNING_MIN_UTC,
                second=5, microsecond=0
            )
            if next_run <= now:
                from datetime import timedelta
                next_run += timedelta(days=1)
            wait_secs = (next_run - now).total_seconds()
            logger.info(f"Morning reminder in {int(wait_secs//3600)}h {int((wait_secs%3600)//60)}m")
            await _asyncio.sleep(wait_secs)

            class _Ctx:
                bot = application.bot
            try:
                await morning_reminder(_Ctx())
            except Exception as _e:
                logger.error(f"morning_reminder error: {_e}")

    async def _post_init(application):
        _asyncio.ensure_future(_morning_loop(application))

    app.post_init = _post_init

    print("✅ Avtoservis Bot v3.0 ishga tushdi!")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
