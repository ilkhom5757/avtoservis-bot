#!/usr/bin/env python3
"""AVTOSERVIS BOT v2.1"""

import os, json, logging, re
from datetime import datetime, date
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

TOKEN    = os.environ.get("BOT_TOKEN", "ТВОЙ_ТОКЕН")
OWNER_ID = int(os.environ.get("OWNER_ID", "368817660"))
DATA_FILE = "data.json"

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

STAFF: dict = {OWNER_ID: "Rahbar 👑"}
USER_LANG: dict = {}

# ══════════════════════════════════════════════
# ПЕРЕВОДЫ
# ══════════════════════════════════════════════
T = {
    "cancel":       {"uz": "❌ Bekor",         "ru": "❌ Отмена"},
    "skip":         {"uz": "⏭ O'tkazib",       "ru": "⏭ Пропустить"},
    "done":         {"uz": "✅ Tayyor",         "ru": "✅ Готово"},
    "cancelled":    {"uz": "❌ Bekor qilindi.", "ru": "❌ Отменено."},
    "only_owner":   {"uz": "⛔ Faqat rahbar.",  "ru": "⛔ Только для руководителя."},
    "no_open":      {"uz": "Ochiq buyurtma yo'q.", "ru": "Нет открытых заявок."},
    "enter_num":    {"uz": "Faqat raqam:",      "ru": "Только цифры:"},
    "not_found":    {"uz": "❌ Topilmadi:",     "ru": "❌ Не найдено:"},
    "enter_order":  {"uz": "Buyurtma *raqamini* kiriting:\n📌 Misol: `1`", "ru": "Введи *номер заявки:*\n📌 Пример: `1`"},
    "choose_lang":  {"uz": "🌐 Tilni tanlang / Выберите язык:", "ru": "🌐 Tilni tanlang / Выберите язык:"},
    "lang_set":     {"uz": "✅ Til: O'zbek\n\nAmal tanlang:", "ru": "✅ Язык: Русский\n\nВыбери действие:"},

    # Меню
    "btn_accept":   {"uz": "🚗 Qabul",              "ru": "🚗 Принять"},
    "btn_my":       {"uz": "📋 Mening mashinalarim", "ru": "📋 Мои машины"},
    "btn_all":      {"uz": "📋 Barcha ochiq",        "ru": "📋 Все открытые"},
    "btn_part":     {"uz": "🔩 Ehtiyot qism",        "ru": "🔩 Запчасть"},
    "btn_pay":      {"uz": "💰 To'lov",              "ru": "💰 Оплата"},
    "btn_expense":  {"uz": "📤 Xarajat",             "ru": "📤 Расход"},
    "btn_close":    {"uz": "✅ Yopish",              "ru": "✅ Закрыть"},
    "btn_history":  {"uz": "📞 Mijoz tarixi",        "ru": "📞 История клиента"},
    "btn_report":   {"uz": "📊 Hisobot",             "ru": "📊 Отчёт"},
    "btn_debts":    {"uz": "💸 Qarzlar",             "ru": "💸 Долги"},
    "btn_staff":    {"uz": "👥 Xodimlar",            "ru": "👥 Сотрудники"},
    "btn_myreport": {"uz": "📊 Mening hisobotim",    "ru": "📊 Мой отчёт"},

    # Приёмка
    "accept_hint": {
        "uz": "🚗 *Qabul*\n\nBir qatorda kiriting:\n`raqam * marka * ism`\n\n📌 Misol:\n`10C444TA * Nexia oq * Alisher`",
        "ru": "🚗 *Приёмка*\n\nВведи одной строкой:\n`номер * марка * имя клиента`\n\n📌 Пример:\n`10C444TA * Nexia белая * Алишер`"
    },
    "accept_fmt_err": {
        "uz": "❌ Format xato!\nTo'g'ri: `raqam * marka * ism`\nMisol: `10C444TA * Nexia * Alisher`",
        "ru": "❌ Неверный формат!\nПравильно: `номер * марка * имя`\nПример: `10C444TA * Nexia * Алишер`"
    },
    "accept_phone": {
        "uz": "📱 Telefon raqami:\n_(misol: 901112233)_\n_(yoki O'tkazib)_",
        "ru": "📱 Телефон клиента:\n_(пример: 901112233)_\n_(или Пропустить)_"
    },
    "phone_err": {
        "uz": "❌ Noto'g'ri format!\nMisol: `901112233` (9 raqam)",
        "ru": "❌ Неверный формат!\nПример: `901112233` (9 цифр)"
    },
    "accept_problem": {
        "uz": "📝 *Muammo / shikoyat:*\n📌 Misol: `Dvigatel tuki bor, moy oqmoqda`",
        "ru": "📝 *Проблема / жалоба:*\n📌 Пример: `Стук в двигателе, течёт масло`"
    },
    "accept_master":  {"uz": "👨‍🔧 Qaysi usta?",       "ru": "👨‍🔧 Какой мастер?"},
    "accept_service": {"uz": "🔧 Xizmat turi:",        "ru": "🔧 Тип услуги:"},
    "accept_done": {
        "uz": "✅ *Buyurtma №{id}*\n🚗 {car} | {client}\n🔧 {service}\n📝 {problem}",
        "ru": "✅ *Заявка №{id}*\n🚗 {car} | {client}\n🔧 {service}\n📝 {problem}"
    },
    "repeat_client": {
        "uz": "\n\n⚡ Mijoz bizda *{n} marta* bo'lgan\nOxirgi: {date} | {svc}",
        "ru": "\n\n⚡ Клиент был у нас *{n} раз(а)*\nПоследний: {date} | {svc}"
    },

    # Подвиды услуг
    "svc_sub_price": {
        "uz": "💰 Narxini kiriting (ming so'mda):\nMisol: `50` = 50 000 so'm",
        "ru": "💰 Введи цену (в тысячах):\nПример: `50` = 50 000 сум"
    },
    "svc_works_hint": {
        "uz": ("📋 *Bajarilgan ishlar ro'yxatini kiriting*\nHar bir ish yangi qatorda:\n\n"
               "Misol:\n`Moy almashtirish`\n`Tormoz kolodkasi`\n`Havo filtr`\n\n"
               "_Keyin har biri uchun narx so'raladi_"),
        "ru": ("📋 *Введи список выполненных работ*\nКаждая работа с новой строки:\n\n"
               "Пример:\n`Замена масла`\n`Замена колодок`\n`Воздушный фильтр`\n\n"
               "_Потом по каждой спросит цену_")
    },
    "svc_work_price": {
        "uz": "💰 *{work}*\nNarxi ming so'mda:\n📌 Misol: `50` = 50 000 so'm",
        "ru": "💰 *{work}*\nЦена в тысячах:\n📌 Пример: `50` = 50 000 сум"
    },
    "svc_works_done": {
        "uz": "✅ *Ishlar №{id}ga saqlandi:*\n{lines}\n\n💰 Jami: {total} so'm",
        "ru": "✅ *Работы по №{id}:*\n{lines}\n\n💰 Итого: {total} сум"
    },
    "add_parts_q": {
        "uz": "🔩 Ehtiyot qism qo'shishni xohlaysizmi?",
        "ru": "🔩 Добавить запчасти?"
    },

    # Подвиды тонировки
    "tint_subs": {
        "uz": ["🪟 Full (barcha oynalar)", "🪟 Orqa oynalar", "🪟 Old oynalar",
               "🪟 Faqat orqa shisha", "🪟 Faqat old shisha (lob)"],
        "ru": ["🪟 Full (все окна)", "🪟 Задние окна", "🪟 Передние окна",
               "🪟 Только заднее стекло", "🪟 Только лобовое"]
    },
    # Подвиды бронеплёнки
    "film_subs": {
        "uz": ["🛡 Salon laminatsiya", "🛡 Far laminatsiya",
               "🛡 Kuzov detallari", "🛡 To'liq kuzov"],
        "ru": ["🛡 Ламинация салона", "🛡 Ламинация фар",
               "🛡 Детали кузова", "🛡 Полный кузов"]
    },
    # Подвиды мойки
    "wash_subs": {
        "uz": ["🚿 Kuzov", "🚿 Motor", "🚿 Kuzov + Motor"],
        "ru": ["🚿 Кузов", "🚿 Двигатель", "🚿 Кузов + Двигатель"]
    },

    # Услуги (главный список)
    "svc": {
        "uz": ["🔧 Ko'taruvchi/ta'mir", "🛢 Moy almashtirish", "⚡ Elektr",
               "🚿 Yuvish", "✨ Sayqallash", "🪟 Tonirovka",
               "🔨 PDR (botiq)", "🛡 Himoya plyonka", "🔩 Boshqa"],
        "ru": ["🔧 Подъёмник/ремонт", "🛢 Замена масла", "⚡ Электрика",
               "🚿 Мойка", "✨ Полировка", "🪟 Тонировка",
               "🔨 PDR (вмятина)", "🛡 Бронеплёнка", "🔩 Другое"]
    },

    # Услуги с подвидами и списком работ
    "svc_with_works": {
        "uz": ["🔧 Ko'taruvchi/ta'mir", "⚡ Elektr", "🔨 PDR (botiq)"],
        "ru": ["🔧 Подъёмник/ремонт", "⚡ Электрика", "🔨 PDR (вмятина)"]
    },
    "svc_with_subs": {
        "uz": ["🚿 Yuvish", "🪟 Tonirovka", "🛡 Himoya plyonka"],
        "ru": ["🚿 Мойка", "🪟 Тонировка", "🛡 Бронеплёнка"]
    },

    # Запчасти
    "part_hint": {
        "uz": ("🔩 *Ehtiyot qism*\n\nHar bir qatorga:\n"
               "`nomi tannarxi mijoznarxi`\n\n"
               "📌 Misol:\n`Sharovoy 350000 420000`\n`Amortizator 250000 310000`\n\n"
               "_(Mijoz olib kelgan: `nomi narxi`)_\n\n"
               "Tayyor bo'lsa — *Tayyor* tugmasini bosing"),
        "ru": ("🔩 *Запчасти*\n\nКаждая с новой строки:\n"
               "`название себестоимость цена_клиенту`\n\n"
               "📌 Пример:\n`Шаровой левый 350000 420000`\n`Амортизатор пер 250000 310000`\n\n"
               "_(Клиент привёз: `название цена`)_\n\n"
               "Когда готово — нажми *Готово*")
    },
    "part_more":     {"uz": "➕ Yana qo'shing yoki *Tayyor*:", "ru": "➕ Ещё или *Готово*:"},
    "part_done_msg": {"uz": "✅ *{n} ta qo'shildi №{id}*\n{lines}", "ru": "✅ *{n} запч. к №{id}*\n{lines}"},
    "part_err":      {"uz": "⚠️ Qo'shilmadi: {v}", "ru": "⚠️ Не добавлено: {v}"},

    "src_client":    {"uz": "👤 Mijoz olib keldi", "ru": "👤 Клиент привёз"},
    "src_bought":    {"uz": "🛒 Biz oldik",        "ru": "🛒 Мы купили"},

    # Расходы
    "exp_title":   {"uz": "📤 *Xarajat*\n", "ru": "📤 *Расход*\n"},
    "exp_type_q":  {"uz": "Xarajat turi:",  "ru": "Тип расхода:"},
    "exp_desc_q":  {"uz": "📝 Izoh (yoki O'tkazib):", "ru": "📝 Описание (или Пропустить):"},
    "exp_amt_q":   {"uz": "💸 *Summa (so'm):*\n📌 Misol: `60000`", "ru": "💸 *Сумма (сум):*\n📌 Пример: `60000`"},
    "exp_done":    {"uz": "📤 Xarajat #{id}: {type} — {amt} so'm", "ru": "📤 Расход #{id}: {type} — {amt} сум"},
    "exp_benzin":  {"uz": "🚗 Benzin/yetkazish",   "ru": "🚗 Бензин/доставка"},
    "exp_parts":   {"uz": "🛒 Ehtiyot qism sotib", "ru": "🛒 Покупка запчастей"},
    "exp_master":  {"uz": "👨‍🔧 Chaqirilgan usta",  "ru": "👨‍🔧 Вызывной мастер"},
    "exp_tool":    {"uz": "🧰 Asbob/sarflanadigan","ru": "🧰 Инструмент/расходники"},
    "exp_other":   {"uz": "💰 Boshqa",             "ru": "💰 Другое"},

    # Оплата
    "pay_invoice": {
        "uz": ("🧾 *Hisob №{id}*\n\n{works}{parts}{expenses}"
               "─────────────\n💰 *Jami: {total} so'm*\n✅ To'landi: {paid} so'm\n⏳ *Qoldiq: {remaining} so'm*"),
        "ru": ("🧾 *Счёт №{id}*\n\n{works}{parts}{expenses}"
               "─────────────\n💰 *Итого: {total} сум*\n✅ Оплачено: {paid} сум\n⏳ *Остаток: {remaining} сум*")
    },
    "pay_method_q": {"uz": "💳 To'lov usuli:", "ru": "💳 Способ оплаты:"},
    "pay_amt_q":    {"uz": "💵 *Summa (so'm):*\n📌 Misol: `500000`", "ru": "💵 *Сумма (сум):*\n📌 Пример: `500000`"},
    "pay_rate_q":   {"uz": "💱 *Dollar kursi:*\n📌 Misol: `12800` (1$=12800 so'm)", "ru": "💱 *Курс доллара:*\n📌 Пример: `12800` (1$=12800 сум)"},
    "pay_usd_q":    {"uz": "💵 Dollar miqdori ($):", "ru": "💵 Сумма в долларах ($):"},
    "pay_added":    {"uz": "✅ {method}: {amt} so'm\n⏳ Qoldiq: {rem} so'm", "ru": "✅ {method}: {amt} сум\n⏳ Остаток: {rem} сум"},
    "pay_done":     {"uz": "✅ *To'lov №{id}*\n💰 Jami: {total} so'm", "ru": "✅ *Оплата №{id}*\n💰 Итого: {total} сум"},
    "pay_methods":  {
        "uz": ["💵 Naqd UZS","💵 Naqd USD","💳 Karta","🏦 O'tkazma","📝 Qarz"],
        "ru": ["💵 Наличные UZS","💵 Наличные USD","💳 Карта","🏦 Перечисление","📝 Долг"]
    },

    # Закрытие
    "close_no_pay": {"uz": "⛔ *Avval to'lovni rasmiylashtiring!*", "ru": "⛔ *Сначала оформи оплату!*"},
    "close_done":   {
        "uz": "✅ *№{id} yopildi!*\n🚗 {car} | {client}\n📞 *{phone}*{debt}\n\n{summary}",
        "ru": "✅ *№{id} закрыта!*\n🚗 {car} | {client}\n📞 *{phone}*{debt}\n\n{summary}"
    },
    "close_debt_w":  {"uz": "\n⚠️ Qarz bor!", "ru": "\n⚠️ Есть долг!"},
    "close_summary": {
        "uz": "📊 *Yakun:*\n💰 To'landi: {paid} so'm\n📤 Xarajat: {exp} so'm\n✅ Sof: {net} so'm",
        "ru": "📊 *Итог:*\n💰 Оплачено: {paid} сум\n📤 Расходы: {exp} сум\n✅ Чистая: {net} сум"
    },

    # Карточка
    "card_debt":     {"uz": " 💸QARZ", "ru": " 💸ДОЛГ"},
    "status_work":   {"uz": "ishda 🔧", "ru": "в работе 🔧"},
    "status_closed": {"uz": "yopildi ✅","ru": "закрыто ✅"},

    # История
    "hist_q": {
        "uz": "📞 *Mijoz qidirish*\n\nTelefon kiriting:\n📌 Misol: `901112233`\n\nYoki mashina raqami:\n📌 Misol: `10C444TA`",
        "ru": "📞 *Поиск клиента*\n\nВведи телефон:\n📌 Пример: `901112233`\n\nИли номер машины:\n📌 Пример: `10C444TA`"
    },
    "hist_none":   {"uz": "🔍 '{q}' bo'yicha topilmadi.", "ru": "🔍 По '{q}' ничего не найдено."},
    "hist_header": {"uz": "👤 *{name}* | {phone}\n📊 {n} ta tashrif | Jami: {total} so'm",
                    "ru": "👤 *{name}* | {phone}\n📊 Визитов: {n} | Итого: {total} сум"},

    # Отчёт
    "rep_title":   {"uz": "📊 *{date} hisoboti*\n", "ru": "📊 *Отчёт за {date}*\n"},
    "rep_orders":  {"uz": "📋 Buyurtmalar: {t} | Yopilgan: {c} | Ishda: {w}",
                    "ru": "📋 Заявок: {t} | Закрыто: {c} | В работе: {w}"},
    "rep_income":  {"uz": "\n💰 *Tushum: {v} so'm*", "ru": "\n💰 *Приход: {v} сум*"},
    "rep_uzs":     {"uz": "  💵 Naqd UZS: {v} so'm","ru": "  💵 Наличные UZS: {v} сум"},
    "rep_usd":     {"uz": "  💵 Naqd USD: {v} so'm","ru": "  💵 Наличные USD: {v} сум"},
    "rep_card":    {"uz": "  💳 Karta: {v} so'm",   "ru": "  💳 Карта: {v} сум"},
    "rep_bank":    {"uz": "  🏦 O'tkazma: {v} so'm","ru": "  🏦 Перечисление: {v} сум"},
    "rep_debt":    {"uz": "  📝 Qarzlar: {v} so'm", "ru": "  📝 Долги: {v} сум"},
    "rep_expense": {"uz": "\n📤 Xarajatlar: {v} so'm","ru": "\n📤 Расходы: {v} сум"},
    "rep_margin":  {"uz": "📈 Ehtiyot qism foydasi: {v} so'm","ru": "📈 Маржа запчастей: {v} сум"},
    "rep_profit":  {"uz": "\n✅ *Sof foyda: {v} so'm*","ru": "\n✅ *Чистая прибыль: {v} сум*"},
    "rep_none":    {"uz": "Bugun buyurtma yo'q.","ru": "Сегодня заявок нет."},
    "myreport": {
        "uz": "📊 *{name}*\n\n🔧 Ishda: {active} ta\n✅ Bugun yopilgan: {closed} ta\n💰 Bugun tushum: {income} so'm",
        "ru": "📊 *{name}*\n\n🔧 В работе: {active}\n✅ Закрыто сегодня: {closed}\n💰 Приход сегодня: {income} сум"
    },

    # Долги
    "debt_title":  {"uz": "💸 *Qarzlar ({n}) — {total} so'm*\n","ru": "💸 *Долги ({n}) — {total} сум*\n"},
    "debt_none":   {"uz": "✅ Qarz yo'q!","ru": "✅ Долгов нет!"},
    "debt_cmd":    {"uz": "\nYopish: /qarz RAQAM","ru": "\nЗакрыть: /debt НОМЕР"},
    "debt_closed": {"uz": "✅ #{id} qarzi yopildi!","ru": "✅ Долг по №{id} закрыт!"},

    # Сотрудники
    "staff_title": {"uz": "👥 *Xodimlar:*\n","ru": "👥 *Сотрудники:*\n"},
    "staff_add":   {"uz": "Qo'shish: /add_staff 123456789 Ism","ru": "Добавить: /add_staff 123456789 Имя"},
}

def tr(key, uid, **kw):
    lg = USER_LANG.get(uid, "ru")
    v = T.get(key, {})
    text = v.get(lg, v.get("ru", key))
    if kw:
        try: text = text.format(**kw)
        except: pass
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

# ══════════════════════════════════════════════
# СОСТОЯНИЯ
# ══════════════════════════════════════════════
(
    A_CAR_LINE, A_PHONE, A_PROBLEM, A_MASTER, A_SERVICE,
    A_SVC_SUB, A_SVC_PRICE,
    A_WORKS_LIST, A_WORKS_PRICE,
    AFTER_ACCEPT,
    P_ORDER, P_LINES,
    PAY_ORDER, PAY_METHOD, PAY_AMOUNT, PAY_RATE,
    EXP_ORDER, EXP_TYPE, EXP_DESC, EXP_AMOUNT,
    CLOSE_ORDER, HIST_PHONE,
) = range(22)

# ══════════════════════════════════════════════
# БАЗА ДАННЫХ
# ══════════════════════════════════════════════
def load():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"orders": [], "next_id": 1, "clients": {}, "langs": {}}

def save(d):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def load_langs():
    for k, v in load().get("langs", {}).items():
        USER_LANG[int(k)] = v

def save_lang(uid, l):
    USER_LANG[uid] = l
    d = load(); d.setdefault("langs", {})[str(uid)] = l; save(d)

def new_id():
    d = load(); n = d["next_id"]; d["next_id"] += 1; save(d); return n

def add_order(o):
    d = load(); d["orders"].append(o)
    ph = o.get("phone","").strip()
    if ph:
        d["clients"].setdefault(ph, {"name": o["client"], "orders": []})["orders"].append(o["id"])
    save(d)

def get_order(oid):
    return next((o for o in load()["orders"] if o["id"] == oid), None)

def upd_order(oid, u):
    d = load()
    for o in d["orders"]:
        if o["id"] == oid: o.update(u)
    save(d)

def open_orders(): return [o for o in load()["orders"] if o["status"] != "closed"]
def today_orders(): return [o for o in load()["orders"] if o["date"] == date.today().isoformat()]
def my_open(uid):
    name = STAFF.get(uid, "")
    return [o for o in open_orders() if o.get("master") == name]

def all_debts():
    r = []
    for o in load()["orders"]:
        amt = sum(p["amt_uzs"] for p in o.get("payments",[]) if p.get("is_debt") and not p.get("paid"))
        if amt > 0: r.append((o, amt))
    return r

def client_history(phone):
    d = load()
    if phone in d["clients"]:
        ids = set(d["clients"][phone]["orders"])
        return [o for o in d["orders"] if o["id"] in ids]
    return []

def calc_total(o):
    parts = sum(p.get("sell_price", 0) for p in o.get("parts", []))
    works = sum(w.get("price", 0) for w in o.get("works", []))
    return parts + works

def calc_paid(o):
    return sum(p["amt_uzs"] for p in o.get("payments", []) if not (p.get("is_debt") and not p.get("paid")))

def calc_remaining(o):
    return max(0, calc_total(o) - calc_paid(o))

def calc_margin(o):
    return sum(p.get("sell_price",0) - p.get("cost_price",0) for p in o.get("parts",[]))

def calc_expenses(o):
    return sum(e["amount"] for e in o.get("expenses", []))

# ══════════════════════════════════════════════
# УТИЛИТЫ
# ══════════════════════════════════════════════
def is_owner(uid): return uid == OWNER_ID
def is_staff(uid): return uid in STAFF or uid == OWNER_ID
def sname(uid): return STAFF.get(uid, f"ID:{uid}")
def fmt(n):
    try: return f"{int(n):,}".replace(",", " ")
    except: return str(n)
def now_t(): return datetime.now().strftime("%H:%M")
def today_d(): return date.today().isoformat()
def is_cancel(text, uid): return text == tr("cancel", uid)
def is_skip(text, uid): return text == tr("skip", uid)
def is_done(text, uid): return text == tr("done", uid)

def validate_phone(phone):
    """Проверяем формат 9XXXXXXXX — 9 цифр начиная с 9"""
    p = re.sub(r'\D', '', phone)
    return p if (len(p) == 9 and p.startswith('9')) else None

def build_invoice(o, uid):
    works_block = ""
    if o.get("works"):
        lines = [f"  • {w['name']} — {fmt(w['price'])} сум" for w in o["works"]]
        works_block = "🔧 *Ishlar / Работы:*\n" + "\n".join(lines) + "\n\n"

    parts_block = ""
    if o.get("parts"):
        lines = [f"  • {p['name']} — {fmt(p['sell_price'])} сум" for p in o["parts"]]
        parts_block = "🔩 *Ehtiyot qismlar / Запчасти:*\n" + "\n".join(lines) + "\n\n"

    exp_block = ""
    if o.get("expenses"):
        lines = [f"  • {e['type']}: {fmt(e['amount'])} сум" for e in o["expenses"]]
        exp_block = "📤 *Xarajatlar / Расходы:*\n" + "\n".join(lines) + "\n\n"

    total = calc_total(o)
    paid = calc_paid(o)
    remaining = calc_remaining(o)

    return tr("pay_invoice", uid,
        id=o["id"], works=works_block, parts=parts_block, expenses=exp_block,
        total=fmt(total), paid=fmt(paid), remaining=fmt(remaining)
    )

def order_short(o, uid, show_margin=False):
    has_debt = any(p.get("is_debt") and not p.get("paid") for p in o.get("payments", []))
    icon = "✅" if o["status"] == "closed" else ("⏳" if has_debt else "🔧")
    debt_m = tr("card_debt", uid) if has_debt else ""
    works_info = ""
    if o.get("works"):
        works_info = f"\n   📋 {', '.join(w['name'] for w in o['works'][:2])}"
        if len(o["works"]) > 2: works_info += f" +{len(o['works'])-2}"
    return (f"{icon} №{o['id']} | {o['car']} | {o['client']}\n"
            f"   {o['service']} → {o['master']}{debt_m}{works_info}\n"
            f"   📅 {o['date']} {o['time']}")

async def notify(ctx, text, uid):
    if uid != OWNER_ID:
        try: await ctx.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode="Markdown")
        except Exception as e: logger.warning(f"notify: {e}")

# ══════════════════════════════════════════════
# КЛАВИАТУРЫ
# ══════════════════════════════════════════════
def kb_main(uid):
    rows = [
        [tr("btn_accept",uid), tr("btn_my",uid)],
        [tr("btn_part",uid), tr("btn_pay",uid)],
        [tr("btn_expense",uid), tr("btn_close",uid)],
        [tr("btn_history",uid), tr("btn_myreport",uid)],
    ]
    if is_owner(uid):
        rows += [
            [tr("btn_all",uid), tr("btn_report",uid)],
            [tr("btn_debts",uid), tr("btn_staff",uid)],
        ]
    return ReplyKeyboardMarkup([[KeyboardButton(b) for b in r] for r in rows], resize_keyboard=True)

def kb_lang():
    return ReplyKeyboardMarkup([[KeyboardButton("🇺🇿 O'zbek"), KeyboardButton("🇷🇺 Русский")]], resize_keyboard=True)

def kb_list(items, uid, cols=2, extra=None):
    rows = [items[i:i+cols] for i in range(0, len(items), cols)]
    if extra: rows.append([extra])
    rows.append([tr("cancel", uid)])
    return ReplyKeyboardMarkup([[KeyboardButton(b) for b in r] for r in rows], resize_keyboard=True)

def kb_cancel(uid):
    return ReplyKeyboardMarkup([[KeyboardButton(tr("cancel", uid))]], resize_keyboard=True)

def kb_skip(uid):
    return ReplyKeyboardMarkup([[KeyboardButton(tr("skip", uid)), KeyboardButton(tr("cancel", uid))]], resize_keyboard=True)

def kb_done_cancel(uid):
    return ReplyKeyboardMarkup([[KeyboardButton(tr("done", uid)), KeyboardButton(tr("cancel", uid))]], resize_keyboard=True)

def kb_pay(uid):
    methods = get_pay_methods(uid)
    rows = [methods[i:i+2] for i in range(0, len(methods), 2)]
    rows.append([tr("cancel", uid)])
    return ReplyKeyboardMarkup([[KeyboardButton(b) for b in r] for r in rows], resize_keyboard=True)

def kb_yes_no(uid):
    return ReplyKeyboardMarkup([
        [KeyboardButton("✅ Ha / Да"), KeyboardButton("➡️ Yo'q / Нет")]
    ], resize_keyboard=True)

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
    if not is_staff(uid): return
    await update.message.reply_text(tr("choose_lang", uid), reply_markup=kb_lang())

async def cmd_add_staff(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Format: /add_staff 123456789 Abduraxmon"); return
    try:
        sid = int(args[0]); sn = " ".join(args[1:])
        STAFF[sid] = sn
        # Сохраняем в data.json
        d = load(); d.setdefault("staff", {})[str(sid)] = sn; save(d)
        await update.message.reply_text(f"✅ {sn} qo'shildi / добавлен!")
    except:
        await update.message.reply_text("❌ /add_staff 123456789 Ism")

# ══════════════════════════════════════════════
# 1. ПРИЁМКА
# ══════════════════════════════════════════════
async def accept_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    ctx.user_data.clear()
    await update.message.reply_text(tr("accept_hint", uid), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return A_CAR_LINE

async def accept_car_line(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    parts = [p.strip() for p in update.message.text.split("*")]
    if len(parts) < 3:
        await update.message.reply_text(tr("accept_fmt_err", uid), parse_mode="Markdown")
        return A_CAR_LINE
    ctx.user_data["car_num"]   = parts[0]
    ctx.user_data["car_model"] = parts[1]
    ctx.user_data["client"]    = parts[2]
    await update.message.reply_text(tr("accept_phone", uid), parse_mode="Markdown", reply_markup=kb_skip(uid))
    return A_PHONE

async def accept_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if is_skip(update.message.text, uid):
        ctx.user_data["phone"] = ""
    else:
        phone = validate_phone(update.message.text)
        if not phone:
            await update.message.reply_text(tr("phone_err", uid), parse_mode="Markdown")
            return A_PHONE
        ctx.user_data["phone"] = phone

    extra = ""
    ph = ctx.user_data["phone"]
    if ph:
        h = client_history(ph)
        if h:
            last = h[-1]
            extra = tr("repeat_client", uid, n=len(h), date=last["date"], svc=last["service"])
    await update.message.reply_text(tr("accept_problem", uid) + extra, parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return A_PROBLEM

async def accept_problem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    ctx.user_data["problem"] = update.message.text
    masters = list(STAFF.values())
    await update.message.reply_text(tr("accept_master", uid), reply_markup=kb_list(masters, uid))
    return A_MASTER

async def accept_master(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    masters = list(STAFF.values())
    if update.message.text not in masters:
        await update.message.reply_text(tr("accept_master", uid), reply_markup=kb_list(masters, uid))
        return A_MASTER
    ctx.user_data["master"] = update.message.text
    await update.message.reply_text(tr("accept_service", uid), reply_markup=kb_list(get_services(uid), uid, cols=2))
    return A_SERVICE

async def accept_service(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    svc = update.message.text
    ctx.user_data["service"] = svc
    ctx.user_data["works"] = []
    ctx.user_data["work_idx"] = 0

    # Услуги с подвидами
    if svc_needs_subs(svc, uid):
        if "Yuvish" in svc or "Мойка" in svc:
            subs = get_wash_subs(uid)
        elif "Tonirovka" in svc or "Тонировка" in svc:
            subs = get_tint_subs(uid)
        else:
            subs = get_film_subs(uid)
        await update.message.reply_text(f"📋 {svc}\n\nVid / Вид:", reply_markup=kb_list(subs, uid, cols=1))
        return A_SVC_SUB

    # Услуги со списком работ
    if svc_needs_works(svc, uid):
        await update.message.reply_text(tr("svc_works_hint", uid), parse_mode="Markdown", reply_markup=kb_cancel(uid))
        return A_WORKS_LIST

    # Простая услуга — только цена
    await update.message.reply_text(tr("svc_sub_price", uid), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return A_SVC_PRICE

async def accept_svc_sub(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    ctx.user_data["svc_sub"] = update.message.text
    await update.message.reply_text(tr("svc_sub_price", uid), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return A_SVC_PRICE

async def accept_svc_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        price = int(update.message.text.replace(" ", "")) * 1000
        sub = ctx.user_data.get("svc_sub", "")
        work_name = f"{ctx.user_data['service']}{' — ' + sub if sub else ''}"
        ctx.user_data["works"] = [{"name": work_name, "price": price}]
        return await _save_order(update, ctx)
    except:
        await update.message.reply_text(tr("enter_num", uid)); return A_SVC_PRICE

async def accept_works_list(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    works_raw = [l.strip() for l in update.message.text.strip().split("\n") if l.strip()]
    if not works_raw:
        await update.message.reply_text("❌ Bo'sh / Пустой список")
        return A_WORKS_LIST
    ctx.user_data["works_raw"] = works_raw
    ctx.user_data["works"] = []
    ctx.user_data["work_idx"] = 0
    # Спрашиваем цену первой работы
    await update.message.reply_text(
        tr("svc_work_price", uid, work=works_raw[0]),
        parse_mode="Markdown", reply_markup=kb_cancel(uid)
    )
    return A_WORKS_PRICE

async def accept_work_price(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        price = int(update.message.text.replace(" ", "")) * 1000
        idx = ctx.user_data["work_idx"]
        works_raw = ctx.user_data["works_raw"]
        ctx.user_data["works"].append({"name": works_raw[idx], "price": price})
        ctx.user_data["work_idx"] = idx + 1

        if idx + 1 < len(works_raw):
            # Следующая работа
            await update.message.reply_text(
                tr("svc_work_price", uid, work=works_raw[idx + 1]),
                parse_mode="Markdown", reply_markup=kb_cancel(uid)
            )
            return A_WORKS_PRICE
        else:
            # Все работы готовы
            return await _save_order(update, ctx)
    except:
        await update.message.reply_text(tr("enter_num", uid)); return A_WORKS_PRICE

async def _save_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    oid = new_id()
    car = f"{ctx.user_data['car_num']} {ctx.user_data['car_model']}"
    works = ctx.user_data.get("works", [])
    total_works = sum(w["price"] for w in works)

    order = {
        "id": oid, "date": today_d(), "time": now_t(),
        "car": car, "car_num": ctx.user_data["car_num"],
        "client": ctx.user_data["client"], "phone": ctx.user_data["phone"],
        "problem": ctx.user_data["problem"], "master": ctx.user_data["master"],
        "service": ctx.user_data["service"],
        "works": works,
        "parts": [], "payments": [], "expenses": [],
        "status": "in_work", "created_by": sname(uid),
    }
    add_order(order)

    # Показываем итог создания
    works_lines = "\n".join(f"  • {w['name']} — {fmt(w['price'])} сум" for w in works)
    total_line = f"\n💰 Jami ish narxi / Итого работы: {fmt(total_works)} сум" if works else ""
    msg = tr("accept_done", uid, id=oid, car=car, client=order["client"],
             service=order["service"], problem=order["problem"])
    if works_lines:
        msg += f"\n\n📋 *Ishlar / Работы:*\n{works_lines}{total_line}"

    ctx.user_data["last_order_id"] = oid
    await update.message.reply_text(msg, parse_mode="Markdown")
    await notify(ctx, msg, uid)

    # Предлагаем добавить запчасти
    await update.message.reply_text(
        tr("add_parts_q", uid),
        reply_markup=kb_yes_no(uid)
    )
    return AFTER_ACCEPT

async def after_accept(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    if "Ha" in text or "Да" in text:
        # Переходим к запчастям для только что созданной заявки
        oid = ctx.user_data.get("last_order_id")
        if oid:
            ctx.user_data.clear()
            ctx.user_data["order_id"] = oid
            await update.message.reply_text(tr("part_hint", uid), parse_mode="Markdown", reply_markup=kb_done_cancel(uid))
            return P_LINES
    await update.message.reply_text("✅", reply_markup=kb_main(uid))
    return ConversationHandler.END

# ══════════════════════════════════════════════
# 2. ЗАПЧАСТИ
# ══════════════════════════════════════════════
async def part_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    orders = my_open(uid) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    lines = ["🔩 *Ochiq / Открытые:*\n"] + [order_short(o, uid) for o in orders] + ["\n" + tr("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return P_ORDER

async def part_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o or o["status"] == "closed":
            await update.message.reply_text(tr("not_found", uid)); return P_ORDER
        ctx.user_data["order_id"] = oid
        await update.message.reply_text(tr("part_hint", uid), parse_mode="Markdown", reply_markup=kb_done_cancel(uid))
        return P_LINES
    except:
        await update.message.reply_text(tr("enter_num", uid)); return P_ORDER

async def part_lines(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    if is_cancel(text, uid): return await cancel(update, ctx)
    if is_done(text, uid):
        await update.message.reply_text("✅", reply_markup=kb_main(uid))
        return ConversationHandler.END

    oid = ctx.user_data["order_id"]
    o = get_order(oid)
    current = o.get("parts", [])
    added = []; errors = []

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line: continue
        tokens = line.rsplit(None, 2)
        if len(tokens) == 3:
            try:
                added.append({"name": tokens[0], "source": tr("src_bought", uid),
                              "cost_price": int(tokens[1].replace(" ","")),
                              "sell_price": int(tokens[2].replace(" ",""))})
            except: errors.append(line)
        elif len(tokens) == 2:
            try:
                added.append({"name": tokens[0], "source": tr("src_client", uid),
                              "cost_price": 0, "sell_price": int(tokens[1].replace(" ",""))})
            except: errors.append(line)
        else:
            errors.append(line)

    if added:
        current.extend(added)
        upd_order(oid, {"parts": current})

    out = []
    for p in added:
        m = p["sell_price"] - p["cost_price"]
        ml = f" | 📈 {fmt(m)}" if (is_owner(uid) and m > 0) else ""
        out.append(f"  🔩 {p['name']} — {fmt(p['sell_price'])} сум{ml}")
    if errors:
        out.append(tr("part_err", uid, v=", ".join(errors)))

    msg = tr("part_done_msg", uid, n=len(added), id=oid, lines="\n".join(out))
    await update.message.reply_text(msg, parse_mode="Markdown")
    if added: await notify(ctx, msg, uid)
    await update.message.reply_text(tr("part_more", uid), parse_mode="Markdown", reply_markup=kb_done_cancel(uid))
    return P_LINES

# ══════════════════════════════════════════════
# 3. ОПЛАТА
# ══════════════════════════════════════════════
async def pay_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    orders = my_open(uid) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    lines = ["💰 *Ochiq / Открытые:*\n"] + [order_short(o, uid) for o in orders] + ["\n" + tr("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return PAY_ORDER

async def pay_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o or o["status"] == "closed":
            await update.message.reply_text(tr("not_found", uid)); return PAY_ORDER
        ctx.user_data["order_id"] = oid
        remaining = calc_remaining(o)
        if remaining <= 0 and calc_total(o) > 0:
            invoice = build_invoice(o, uid)
            await update.message.reply_text(invoice + "\n\n✅ To'liq to'langan / Полностью оплачено!", parse_mode="Markdown", reply_markup=kb_main(uid))
            return ConversationHandler.END
        await update.message.reply_text(build_invoice(o, uid), parse_mode="Markdown", reply_markup=kb_pay(uid))
        return PAY_METHOD
    except:
        await update.message.reply_text(tr("enter_num", uid)); return PAY_ORDER

async def pay_method(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if update.message.text not in get_pay_methods(uid):
        await update.message.reply_text(tr("pay_method_q", uid), reply_markup=kb_pay(uid))
        return PAY_METHOD
    ctx.user_data["pay_method"] = update.message.text
    if "USD" in update.message.text:
        await update.message.reply_text(tr("pay_rate_q", uid), reply_markup=kb_cancel(uid))
        return PAY_RATE
    await update.message.reply_text(tr("pay_amt_q", uid), reply_markup=kb_cancel(uid))
    return PAY_AMOUNT

async def pay_rate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        ctx.user_data["usd_rate"] = int(update.message.text.replace(" ", ""))
        await update.message.reply_text(tr("pay_usd_q", uid), reply_markup=kb_cancel(uid))
        return PAY_AMOUNT
    except:
        await update.message.reply_text(tr("enter_num", uid)); return PAY_RATE

async def pay_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        amount = int(update.message.text.replace(" ", ""))
        method = ctx.user_data["pay_method"]
        rate = ctx.user_data.get("usd_rate", 1)
        is_usd = "USD" in method
        is_debt = "Qarz" in method or "Долг" in method
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
            msg = tr("pay_done", uid, id=oid, total=fmt(calc_paid(o)))
            if is_debt: msg += f"\n📝 Qarz / Долг: {fmt(amt_uzs)} сум"
            await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
            await notify(ctx, msg, uid)
            return ConversationHandler.END
        else:
            await update.message.reply_text(tr("pay_added", uid, method=method, amt=fmt(amt_uzs), rem=fmt(remaining)), parse_mode="Markdown")
            await update.message.reply_text(build_invoice(o, uid), parse_mode="Markdown", reply_markup=kb_pay(uid))
            return PAY_METHOD
    except Exception as e:
        logger.error(f"pay_amount: {e}")
        await update.message.reply_text(tr("enter_num", uid)); return PAY_AMOUNT

# ══════════════════════════════════════════════
# 4. РАСХОДЫ
# ══════════════════════════════════════════════
async def exp_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    orders = my_open(uid) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    lines = [tr("exp_title", uid)] + [order_short(o, uid) for o in orders] + ["\n" + tr("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return EXP_ORDER

async def exp_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o: await update.message.reply_text(tr("not_found", uid)); return EXP_ORDER
        ctx.user_data["order_id"] = oid
        await update.message.reply_text(tr("exp_type_q", uid), reply_markup=kb_list(get_expenses_list(uid), uid))
        return EXP_TYPE
    except:
        await update.message.reply_text(tr("enter_num", uid)); return EXP_ORDER

async def exp_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if update.message.text not in get_expenses_list(uid):
        await update.message.reply_text(tr("exp_type_q", uid), reply_markup=kb_list(get_expenses_list(uid), uid))
        return EXP_TYPE
    ctx.user_data["exp_type"] = update.message.text
    await update.message.reply_text(tr("exp_desc_q", uid), reply_markup=kb_skip(uid))
    return EXP_DESC

async def exp_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    ctx.user_data["exp_desc"] = "" if is_skip(update.message.text, uid) else update.message.text
    await update.message.reply_text(tr("exp_amt_q", uid), reply_markup=kb_cancel(uid))
    return EXP_AMOUNT

async def exp_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        amount = int(update.message.text.replace(" ", ""))
        oid = ctx.user_data["order_id"]
        exp = {"type": ctx.user_data["exp_type"], "desc": ctx.user_data["exp_desc"],
               "amount": amount, "time": now_t(), "by": sname(uid)}
        o = get_order(oid)
        upd_order(oid, {"expenses": o.get("expenses", []) + [exp]})
        msg = tr("exp_done", uid, id=oid, type=exp["type"], amt=fmt(amount))
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
        await notify(ctx, msg, uid)
        return ConversationHandler.END
    except:
        await update.message.reply_text(tr("enter_num", uid)); return EXP_AMOUNT

# ══════════════════════════════════════════════
# 5. ЗАКРЫТИЕ
# ══════════════════════════════════════════════
async def close_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    orders = my_open(uid) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid))
        return ConversationHandler.END
    ctx.user_data.clear()
    lines = ["✅ *Yopish / Закрыть:*\n"] + [order_short(o, uid) for o in orders] + ["\n" + tr("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return CLOSE_ORDER

async def close_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o: await update.message.reply_text(tr("not_found", uid)); return CLOSE_ORDER

        if not o.get("payments"):
            await update.message.reply_text(tr("close_no_pay", uid), parse_mode="Markdown", reply_markup=kb_main(uid))
            return ConversationHandler.END

        remaining = calc_remaining(o)
        has_debt = any(p.get("is_debt") and not p.get("paid") for p in o.get("payments", []))
        if remaining > 0 and not has_debt:
            await update.message.reply_text(tr("close_no_pay", uid), parse_mode="Markdown", reply_markup=kb_main(uid))
            return ConversationHandler.END

        upd_order(oid, {"status": "closed", "closed_time": now_t(), "closed_by": sname(uid)})
        o = get_order(oid)

        paid = calc_paid(o)
        expenses = calc_expenses(o)
        margin = calc_margin(o)
        net = paid - expenses

        summary = tr("close_summary", uid, paid=fmt(paid), exp=fmt(expenses), net=fmt(net))
        if is_owner(uid) and margin > 0:
            summary += f"\n📈 Marja / Маржа: {fmt(margin)} сум"

        debt_line = tr("close_debt_w", uid) if has_debt else ""
        phone = o.get("phone", "—")

        msg = tr("close_done", uid, id=oid, car=o["car"], client=o["client"],
                 phone=phone, debt=debt_line, summary=summary)
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
        await notify(ctx, f"🏁 №{oid} yopildi | {o['car']} | {o['client']} | {sname(uid)}", uid)
        return ConversationHandler.END
    except Exception as e:
        logger.error(f"close: {e}")
        await update.message.reply_text(tr("enter_num", uid)); return CLOSE_ORDER

# ══════════════════════════════════════════════
# 6. ИСТОРИЯ
# ══════════════════════════════════════════════
async def hist_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    ctx.user_data.clear()
    await update.message.reply_text(tr("hist_q", uid), reply_markup=kb_cancel(uid))
    return HIST_PHONE

async def hist_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    query = update.message.text.strip()
    digits_only = re.sub(r'\D', '', query)

    # Определяем тип поиска
    history = []
    search_key = query

    # Если только цифры — ищем по телефону
    if digits_only and len(digits_only) >= 7:
        history = client_history(digits_only)
        search_key = digits_only

    # Если не нашли по телефону — ищем по номеру машины
    if not history:
        car_num = query.upper().replace(" ", "")
        all_orders = load()["orders"]
        matched = [o for o in all_orders if o.get("car_num","").upper().replace(" ","") == car_num
                   or car_num in o.get("car","").upper().replace(" ","")]
        if matched:
            history = matched
            search_key = car_num

    if not history:
        await update.message.reply_text(tr("hist_none", uid, q=query), reply_markup=kb_main(uid))
        return ConversationHandler.END

    total = sum(calc_paid(o) for o in history)
    client_name = history[0]["client"]
    phone = history[0].get("phone", "-")
    lines = [tr("hist_header", uid, name=client_name, phone=phone, n=len(history), total=fmt(total)), "─────────────"]
    for o in history[-5:]:
        lines.append(order_short(o, uid, show_margin=is_owner(uid)))
        lines.append("─────────────")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))
    return ConversationHandler.END

# ══════════════════════════════════════════════
# 7. ОТЧЁТЫ
# ══════════════════════════════════════════════
async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid): await update.message.reply_text(tr("only_owner", uid)); return
    orders = today_orders()
    if not orders: await update.message.reply_text(tr("rep_none", uid)); return
    t_uzs=t_usd=t_card=t_bank=t_debt=t_exp=t_margin=0
    for o in orders:
        for p in o.get("payments",[]):
            if p.get("is_debt") and not p.get("paid"): t_debt += p["amt_uzs"]
            else:
                m = p["method"]
                if "UZS" in m: t_uzs += p["amt_uzs"]
                elif "USD" in m: t_usd += p["amt_uzs"]
                elif "Karta" in m or "Карта" in m: t_card += p["amt_uzs"]
                elif "O'tkazma" in m or "Перечисл" in m: t_bank += p["amt_uzs"]
        t_exp += calc_expenses(o)
        t_margin += calc_margin(o)
    received = t_uzs + t_usd + t_card + t_bank
    closed = sum(1 for o in orders if o["status"]=="closed")
    lines = [
        tr("rep_title",uid,date=today_d()),
        tr("rep_orders",uid,t=len(orders),c=closed,w=len(orders)-closed),
        tr("rep_income",uid,v=fmt(received)),
        tr("rep_uzs",uid,v=fmt(t_uzs)), tr("rep_usd",uid,v=fmt(t_usd)),
        tr("rep_card",uid,v=fmt(t_card)), tr("rep_bank",uid,v=fmt(t_bank)),
        tr("rep_debt",uid,v=fmt(t_debt)),
        tr("rep_expense",uid,v=fmt(t_exp)),
        tr("rep_margin",uid,v=fmt(t_margin)),
        tr("rep_profit",uid,v=fmt(received-t_exp)),
        "\n─────────────────"
    ]
    for o in orders: lines.append(order_short(o, uid, show_margin=True))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

async def cmd_myreport(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return
    name = sname(uid)
    all_o = load()["orders"]
    active = [o for o in all_o if o.get("master")==name and o["status"]!="closed"]
    closed_today = [o for o in all_o if o.get("master")==name and o.get("closed_time","")[:10]==today_d()]
    income = sum(calc_paid(o) for o in closed_today)
    msg = tr("myreport", uid, name=name, active=len(active), closed=len(closed_today), income=fmt(income))
    lines = [msg, "\n─────────────\n*Ishda / В работе:*"]
    for o in active: lines.append(order_short(o, uid))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

async def cmd_my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return
    orders = my_open(uid) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid)); return
    lines = [f"📋 *{sname(uid)}* ({len(orders)}):\n"]
    for o in orders:
        lines.append(order_short(o, uid))
        lines.append("─────────────")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

async def cmd_all_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid): await update.message.reply_text(tr("only_owner", uid)); return
    orders = open_orders()
    if not orders:
        await update.message.reply_text(tr("no_open", uid), reply_markup=kb_main(uid)); return
    lines = [f"📋 *Barcha ochiq / Все открытые ({len(orders)}):*\n"]
    for o in orders:
        lines.append(order_short(o, uid, show_margin=True))
        lines.append("─────────────")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

async def cmd_debts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid): await update.message.reply_text(tr("only_owner", uid)); return
    debts = all_debts()
    if not debts:
        await update.message.reply_text(tr("debt_none", uid), reply_markup=kb_main(uid)); return
    total = sum(a for _,a in debts)
    lines = [tr("debt_title", uid, n=len(debts), total=fmt(total))]
    for o, amt in debts:
        lines.append(f"#{o['id']} | {o['car']} | {o['client']}\n  📱 {o.get('phone','-')} | {fmt(amt)} сум | {o['date']}")
        lines.append("─────────────")
    lines.append(tr("debt_cmd", uid))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

async def cmd_close_debt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid): return
    args = ctx.args
    if not args: await update.message.reply_text("/debt 5 yoki /qarz 5"); return
    try:
        oid = int(args[0]); o = get_order(oid)
        if not o: await update.message.reply_text(tr("not_found", uid)); return
        payments = o.get("payments", [])
        for p in payments:
            if p.get("is_debt") and not p.get("paid"):
                p["paid"] = True; p["paid_time"] = now_t()
        upd_order(oid, {"payments": payments})
        await update.message.reply_text(tr("debt_closed", uid, id=oid), reply_markup=kb_main(uid))
    except: await update.message.reply_text("/debt 5")

async def cmd_staff(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid): return
    lines = [tr("staff_title", uid)] + [f"• {n} — `{sid}`" for sid, n in STAFF.items()]
    lines.append(tr("staff_add", uid))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

# ══════════════════════════════════════════════
# ОТМЕНА И РОУТЕР
# ══════════════════════════════════════════════
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ctx.user_data.clear()
    await update.message.reply_text(tr("cancelled", uid), reply_markup=kb_main(uid))
    return ConversationHandler.END

async def router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if text == "🇺🇿 O'zbek":
        save_lang(uid, "uz")
        await update.message.reply_text(tr("lang_set", uid), parse_mode="Markdown", reply_markup=kb_main(uid)); return
    if text == "🇷🇺 Русский":
        save_lang(uid, "ru")
        await update.message.reply_text(tr("lang_set", uid), parse_mode="Markdown", reply_markup=kb_main(uid)); return

    if not is_staff(uid):
        await update.message.reply_text(f"⛔ ID: `{uid}`", parse_mode="Markdown"); return
    if uid not in USER_LANG:
        await update.message.reply_text(tr("choose_lang", uid), reply_markup=kb_lang()); return

    # Все кнопки меню — обоих языков
    if text in [T["btn_my"]["uz"], T["btn_my"]["ru"]]:         await cmd_my_orders(update, ctx)
    elif text in [T["btn_all"]["uz"], T["btn_all"]["ru"]]:     await cmd_all_orders(update, ctx)
    elif text in [T["btn_report"]["uz"], T["btn_report"]["ru"]]:await cmd_report(update, ctx)
    elif text in [T["btn_debts"]["uz"], T["btn_debts"]["ru"]]: await cmd_debts(update, ctx)
    elif text in [T["btn_staff"]["uz"], T["btn_staff"]["ru"]]: await cmd_staff(update, ctx)
    elif text in [T["btn_myreport"]["uz"], T["btn_myreport"]["ru"]]: await cmd_myreport(update, ctx)

# ══════════════════════════════════════════════
# ЗАПУСК
# ══════════════════════════════════════════════
def main():
    load_langs()
    # Загружаем сохранённых сотрудников
    d = load()
    for sid_str, name in d.get("staff", {}).items():
        STAFF[int(sid_str)] = name

    app = Application.builder().token(TOKEN).build()

    def btns(key): return [T[key]["uz"], T[key]["ru"]]

    def safe_pattern(triggers):
        escaped = [re.escape(t) for t in triggers]
        return "^(" + "|".join(escaped) + ")$"

    def conv(triggers, states, fn):
        return ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(safe_pattern(triggers)), fn)],
            states=states,
            fallbacks=[MessageHandler(filters.ALL, cancel)],
        )

    app.add_handler(conv(btns("btn_accept"), {
        A_CAR_LINE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_car_line)],
        A_PHONE:      [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_phone)],
        A_PROBLEM:    [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_problem)],
        A_MASTER:     [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_master)],
        A_SERVICE:    [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_service)],
        A_SVC_SUB:    [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_svc_sub)],
        A_SVC_PRICE:  [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_svc_price)],
        A_WORKS_LIST: [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_works_list)],
        A_WORKS_PRICE:[MessageHandler(filters.TEXT & ~filters.COMMAND, accept_work_price)],
        AFTER_ACCEPT: [MessageHandler(filters.TEXT & ~filters.COMMAND, after_accept)],
        P_LINES:      [MessageHandler(filters.TEXT & ~filters.COMMAND, part_lines)],
    }, accept_start))

    app.add_handler(conv(btns("btn_part"), {
        P_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, part_order)],
        P_LINES: [MessageHandler(filters.TEXT & ~filters.COMMAND, part_lines)],
    }, part_start))

    app.add_handler(conv(btns("btn_pay"), {
        PAY_ORDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_order)],
        PAY_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_method)],
        PAY_RATE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_rate)],
        PAY_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_amount)],
    }, pay_start))

    app.add_handler(conv(btns("btn_expense"), {
        EXP_ORDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_order)],
        EXP_TYPE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_type)],
        EXP_DESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_desc)],
        EXP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_amount)],
    }, exp_start))

    app.add_handler(conv(btns("btn_close"), {
        CLOSE_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, close_confirm)],
    }, close_start))

    app.add_handler(conv(btns("btn_history"), {
        HIST_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, hist_show)],
    }, hist_start))

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("add_staff", cmd_add_staff))
    app.add_handler(CommandHandler("debt", cmd_close_debt))
    app.add_handler(CommandHandler("qarz", cmd_close_debt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    print("✅ Avtoservis Bot v2.1 ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
