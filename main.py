#!/usr/bin/env python3
"""
AVTOSERVIS BOT — v2.0
1. Приёмка одной строкой: номер * марка * имя
2. Запчасти одной строкой: название себестоимость цена
3. Маржа только владельцу
4. Расходы без прибыли — детали при закрытии
5. Умная оплата — итог, добивает по кругу
6. Закрытие только после оплаты
7. Роли мастеров — свои машины + общая история
"""

import os
import json
import logging
from datetime import datetime, date

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    ConversationHandler, ContextTypes, filters
)

# ══════════════════════════════════════════════════════════
# НАСТРОЙКИ
# ══════════════════════════════════════════════════════════
TOKEN    = os.environ.get("BOT_TOKEN", "ТВОЙ_ТОКЕН")
OWNER_ID = int(os.environ.get("OWNER_ID", "368817660"))
DATA_FILE = "data.json"

logging.basicConfig(format="%(asctime)s | %(levelname)s | %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# uid → {"name": str, "role": "owner"|"master", "lang": "uz"|"ru"}
STAFF: dict = {
    OWNER_ID: {"name": "Руководитель 👑", "role": "owner", "lang": "ru"}
}
USER_LANG: dict = {OWNER_ID: "ru"}

# ══════════════════════════════════════════════════════════
# ПЕРЕВОДЫ
# ══════════════════════════════════════════════════════════
T = {
    "cancel":         {"uz": "❌ Bekor",          "ru": "❌ Отмена"},
    "skip":           {"uz": "⏭ O'tkazib",        "ru": "⏭ Пропустить"},
    "yes":            {"uz": "✅ Ha",              "ru": "✅ Да"},
    "no":             {"uz": "➡️ Yo'q",            "ru": "➡️ Нет"},
    "cancelled":      {"uz": "❌ Bekor qilindi.",  "ru": "❌ Отменено."},
    "no_access":      {"uz": "⛔ Ruxsat yo'q.\nID: `{uid}`\nRahbarga yuboring.",
                       "ru": "⛔ Нет доступа.\nID: `{uid}`\nСкинь руководителю."},
    "only_owner":     {"uz": "⛔ Faqat rahbar uchun.", "ru": "⛔ Только для руководителя."},
    "no_open":        {"uz": "Ochiq buyurtmalar yo'q.", "ru": "Нет открытых заявок."},
    "enter_num":      {"uz": "Faqat raqam:", "ru": "Только цифры:"},
    "not_found":      {"uz": "❌ Topilmadi.", "ru": "❌ Не найдено."},
    "enter_order":    {"uz": "*Buyurtma raqamini* kiriting:", "ru": "Введи *номер заявки:*"},
    "choose_lang":    {"uz": "🌐 Tilni tanlang / Выберите язык:", "ru": "🌐 Tilni tanlang / Выберите язык:"},
    "lang_set_uz":    {"uz": "✅ Til: O'zbek\n\nAmal tanlang:", "ru": "✅ Til: O'zbek\n\nAmal tanlang:"},
    "lang_set_ru":    {"uz": "✅ Язык: Русский\n\nВыбери действие:", "ru": "✅ Язык: Русский\n\nВыбери действие:"},

    # Кнопки меню
    "btn_accept":     {"uz": "🚗 Qabul",             "ru": "🚗 Принять машину"},
    "btn_open":       {"uz": "📋 Mening mashinalarim","ru": "📋 Мои машины"},
    "btn_all_open":   {"uz": "📋 Barcha ochiqlar",   "ru": "📋 Все открытые"},
    "btn_part":       {"uz": "🔩 Ehtiyot qism",      "ru": "🔩 Запчасть"},
    "btn_pay":        {"uz": "💰 To'lov",            "ru": "💰 Оплата"},
    "btn_expense":    {"uz": "📤 Xarajat",           "ru": "📤 Расход"},
    "btn_close":      {"uz": "✅ Yopish",            "ru": "✅ Закрыть заявку"},
    "btn_history":    {"uz": "📞 Mijoz tarixi",      "ru": "📞 История клиента"},
    "btn_my_history": {"uz": "📜 Mening tarixim",    "ru": "📜 Моя история"},
    "btn_report":     {"uz": "📊 Hisobot",           "ru": "📊 Отчёт за день"},
    "btn_debts":      {"uz": "💸 Qarzlar",           "ru": "💸 Долги"},
    "btn_staff":      {"uz": "👥 Xodimlar",          "ru": "👥 Сотрудники"},

    # Приёмка
    "accept_hint":    {
        "uz": "🚗 *Qabul*\n\nBir qatorda kiriting:\n`Raqam * Marka * Ism`\n\nMasalan:\n`01A123BC * Nexia oq * Alisher`",
        "ru": "🚗 *Приёмка*\n\nВведи одной строкой:\n`Номер * Марка * Имя клиента`\n\nНапример:\n`01A123BC * Nexia белая * Алишер`"
    },
    "accept_phone":   {"uz": "📱 Telefon raqami:\n_(yoki O'tkazib)_", "ru": "📱 Телефон клиента:\n_(или Пропустить)_"},
    "accept_problem": {"uz": "📝 Muammo / shikoyat:", "ru": "📝 Проблема / жалоба:"},
    "accept_master":  {"uz": "👨‍🔧 Qaysi usta oladi?", "ru": "👨‍🔧 Какой мастер берёт?"},
    "accept_service": {"uz": "🔧 Xizmat turi:", "ru": "🔧 Тип услуги:"},
    "accept_done":    {"uz": "✅ *Buyurtma №{id} yaratildi!*\n🚗 {car} | {client}\n🔧 {service} → {master}\n📝 {problem}",
                       "ru": "✅ *Заявка №{id} создана!*\n🚗 {car} | {client}\n🔧 {service} → {master}\n📝 {problem}"},
    "accept_err":     {"uz": "❌ Format xato!\n\n`Raqam * Marka * Ism`\nMasalan: `01A123BC * Nexia * Alisher`",
                       "ru": "❌ Неверный формат!\n\n`Номер * Марка * Имя`\nНапример: `01A123BC * Nexia * Алишер`"},
    "repeat_client":  {"uz": "\n\n⚡ *Mijoz {n} marta kelgan*\nOxirgi: {date} | {service}",
                       "ru": "\n\n⚡ *Клиент был {n} раз(а)*\nПоследний: {date} | {service}"},

    # Запчасти
    "part_hint":      {
        "uz": "🔩 *Ehtiyot qism*\n\nHar bir qator — bitta qism:\n`nomi tannarxi mijoznarxi`\n\nMasalan:\n`Sharovoy 350000 400000`\n`Moy 120000 150000`\n\nAgar mijoz o'zi keltirsa (faqat ish narxi):\n`Sharovoy 0 80000`",
        "ru": "🔩 *Запчасти*\n\nКаждая строка — одна запчасть:\n`название себестоимость цена_клиенту`\n\nНапример:\n`Шаровой левый 350000 400000`\n`Масло 120000 150000`\n\nЕсли клиент привёз сам (только работа):\n`Шаровой 0 80000`"
    },
    "part_source_label": {"uz": "manba", "ru": "источник"},
    "part_done":      {"uz": "✅ *{n} ta qism №{id}ga qo'shildi*\n{list}",
                       "ru": "✅ *{n} запчастей добавлено к №{id}*\n{list}"},
    "part_err":       {"uz": "❌ Format xato! `nomi tannarxi narxi`", "ru": "❌ Формат: `название себестоимость цена`"},
    "part_more":      {"uz": "➕ Yana qism qo'shish yoki tayyor?", "ru": "➕ Добавить ещё или готово?"},
    "part_ready":     {"uz": "✅ Tayyor", "ru": "✅ Готово"},

    # Расходы
    "exp_hint":       {"uz": "📤 *Xarajat*\n\nBuyurtma raqamini kiriting:", "ru": "📤 *Расход*\n\nВведи номер заявки:"},
    "exp_type_q":     {"uz": "Xarajat turi:", "ru": "Тип расхода:"},
    "exp_desc_q":     {"uz": "Tavsif (yoki O'tkazib):", "ru": "Описание (или Пропустить):"},
    "exp_amt_q":      {"uz": "💸 Summa (so'm):", "ru": "💸 Сумма (сум):"},
    "exp_done":       {"uz": "📤 *№{id} xarajat*\n{type}: {desc} — {amt} so'm\nJami: {total} so'm",
                       "ru": "📤 *Расход №{id}*\n{type}: {desc} — {amt} сум\nВсего: {total} сум"},
    "exp_benzin":     {"uz": "🚗 Benzin/yetkazish", "ru": "🚗 Бензин/доставка"},
    "exp_parts":      {"uz": "🛒 Qism sotib olish",  "ru": "🛒 Покупка запчастей"},
    "exp_master":     {"uz": "👨‍🔧 Chaqirilgan usta", "ru": "👨‍🔧 Вызывной мастер"},
    "exp_tool":       {"uz": "🧰 Asbob/material",    "ru": "🧰 Инструмент/материал"},
    "exp_other":      {"uz": "💰 Boshqa",            "ru": "💰 Другое"},

    # Оплата
    "pay_summary_header": {
        "uz": "💰 *To'lov №{id}*\n🚗 {car} | {client}\n\n",
        "ru": "💰 *Оплата по заявке №{id}*\n🚗 {car} | {client}\n\n"
    },
    "pay_works":      {"uz": "🔧 *Xizmatlar:*\n", "ru": "🔧 *Услуги:*\n"},
    "pay_parts_sec":  {"uz": "🔩 *Ehtiyot qismlar:*\n", "ru": "🔩 *Запчасти:*\n"},
    "pay_expenses_sec":{"uz": "📤 *Xarajatlar:*\n", "ru": "📤 *Расходы:*\n"},
    "pay_total_due":  {"uz": "─────────────\n💵 *Jami to'lash kerak: {v} so'm*", "ru": "─────────────\n💵 *Итого к оплате: {v} сум*"},
    "pay_already":    {"uz": "✅ To'langan: {v} so'm", "ru": "✅ Оплачено: {v} сум"},
    "pay_left":       {"uz": "⏳ Qoldi: {v} so'm", "ru": "⏳ Остаток: {v} сум"},
    "pay_choose":     {"uz": "💳 To'lov usulini tanlang:", "ru": "💳 Выбери способ оплаты:"},
    "pay_enter_amt":  {"uz": "💰 {method} miqdori (so'm):", "ru": "💰 Сумма {method} (сум):"},
    "pay_usd_rate":   {"uz": "💱 Dollar kursi ($1 = ? so'm):", "ru": "💱 Курс доллара ($1 = ? сум):"},
    "pay_usd_amt":    {"uz": "💵 Dollar miqdori ($):", "ru": "💵 Сумма в долларах ($):"},
    "pay_recorded":   {"uz": "✅ {method}: {amt} so'm qayd etildi.\n⏳ Qoldi: {left} so'm", "ru": "✅ {method}: {amt} сум записано.\n⏳ Остаток: {left} сум"},
    "pay_done_full":  {"uz": "✅ *To'lov yakunlandi!*\nJami: {total} so'm", "ru": "✅ *Оплата завершена!*\nИтого: {total} сум"},
    "pay_debt_warn":  {"uz": "\n⚠️ *Qarz: {v} so'm*", "ru": "\n⚠️ *Долг: {v} сум*"},
    "pay_btn_uzs":    {"uz": "💵 Naqd UZS", "ru": "💵 Наличные UZS"},
    "pay_btn_usd":    {"uz": "💵 Naqd USD", "ru": "💵 Наличные USD"},
    "pay_btn_card":   {"uz": "💳 Karta",    "ru": "💳 Карта"},
    "pay_btn_bank":   {"uz": "🏦 O'tkazma", "ru": "🏦 Перечисление"},
    "pay_btn_debt":   {"uz": "📝 Qarz",     "ru": "📝 Долг"},

    # Закрытие
    "close_no_pay":   {"uz": "⛔ Avval to'lovni rasmiylаshtiring!\n💰 To'lov tugmасini bosing.",
                       "ru": "⛔ Сначала оформи оплату!\nНажми кнопку 💰 Оплата."},
    "close_done":     {"uz": "✅ *№{id} yopildi!*\n🚗 {car} | {client}{phone}{debt}\n\n📊 *Yakuniy hisobot:*\n{summary}",
                       "ru": "✅ *Заявка №{id} закрыта!*\n🚗 {car} | {client}{phone}{debt}\n\n📊 *Итоговый отчёт:*\n{summary}"},
    "close_call":     {"uz": "\n\n📞 Mijozga qo'ng'iroq: *{phone}*", "ru": "\n\n📞 Позвони клиенту: *{phone}*"},
    "close_call2":    {"uz": "\n\n📞 Mijozga qo'ng'iroq qiling!", "ru": "\n\n📞 Позвони клиенту!"},
    "close_debt_warn":{"uz": "\n⚠️ *Qarz bor!*", "ru": "\n⚠️ *Есть долг!*"},

    # История
    "hist_q":         {"uz": "📞 Telefon kiriting:", "ru": "📞 Введи телефон:"},
    "hist_none":      {"uz": "🔍 {phone} topilmadi.", "ru": "🔍 {phone} не найден."},
    "my_hist_none":   {"uz": "📜 Siz hali birorta mashinani yopmadingiz.", "ru": "📜 Вы ещё не закрыли ни одной машины."},

    # Отчёт
    "rep_none":       {"uz": "Bugun buyurtma yo'q.", "ru": "Сегодня заявок нет."},
    "rep_title":      {"uz": "📊 *{date} hisobot*\n", "ru": "📊 *Отчёт за {date}*\n"},

    # Долги
    "debt_none":      {"uz": "✅ Qarz yo'q!", "ru": "✅ Долгов нет!"},
    "debt_title":     {"uz": "💸 *Qarzlar ({n}): {total} so'm*\n", "ru": "💸 *Долги ({n}): {total} сум*\n"},

    # Статусы
    "status_work":    {"uz": "ishda", "ru": "в работе"},
    "status_closed":  {"uz": "yopildi", "ru": "закрыто"},
}

def t(key, uid, **kw):
    lg = USER_LANG.get(uid, "ru")
    text = T.get(key, {}).get(lg, T.get(key, {}).get("ru", key))
    if kw:
        try: text = text.format(**kw)
        except: pass
    return text

def lang(uid): return USER_LANG.get(uid, "ru")

# ══════════════════════════════════════════════════════════
# СПРАВОЧНИКИ
# ══════════════════════════════════════════════════════════
MASTERS_LIST = ["Abduraxmon", "Axror", "Abdulloh", "Tonirovkachi", "Kuzovchi", "Elektrik"]

def get_services(uid):
    svc = {
        "uz": ["🔧 Ko'taruvchi/ta'mir","🛢 Moy almashtirish","⚡ Elektrik",
               "🚿 Yuvish","✨ Sayqallash","🪟 Tonirovka","🔨 PDR","🛡 Plyonka","🔩 Boshqa"],
        "ru": ["🔧 Подъёмник/ремонт","🛢 Замена масла","⚡ Электрика",
               "🚿 Мойка","✨ Полировка","🪟 Тонировка","🔨 PDR","🛡 Бронеплёнка","🔩 Другое"]
    }
    return svc[lang(uid)]

def get_expenses(uid):
    return [t("exp_benzin",uid), t("exp_parts",uid), t("exp_master",uid), t("exp_tool",uid), t("exp_other",uid)]

def get_pay_buttons(uid):
    return [t("pay_btn_uzs",uid), t("pay_btn_usd",uid), t("pay_btn_card",uid),
            t("pay_btn_bank",uid), t("pay_btn_debt",uid)]

# ══════════════════════════════════════════════════════════
# СОСТОЯНИЯ
# ══════════════════════════════════════════════════════════
(
    A_PHONE, A_PROBLEM, A_MASTER, A_SERVICE,
    P_ORDER, P_PARTS,
    EXP_ORDER, EXP_TYPE, EXP_DESC, EXP_AMOUNT,
    PAY_ORDER, PAY_METHOD, PAY_USD_RATE, PAY_USD_AMT, PAY_AMOUNT,
    CLOSE_ORDER,
    HIST_PHONE,
) = range(17)

# ══════════════════════════════════════════════════════════
# БАЗА ДАННЫХ
# ══════════════════════════════════════════════════════════
def load() -> dict:
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"orders": [], "next_id": 1, "clients": {}, "user_langs": {}}

def save(data: dict):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def load_langs():
    d = load()
    for uid_str, lg in d.get("user_langs", {}).items():
        USER_LANG[int(uid_str)] = lg

def save_lang(uid, lg):
    USER_LANG[uid] = lg
    if uid in STAFF: STAFF[uid]["lang"] = lg
    d = load(); d.setdefault("user_langs", {})[str(uid)] = lg; save(d)

def new_id():
    d = load(); n = d["next_id"]; d["next_id"] += 1; save(d); return n

def add_order(order):
    d = load()
    d["orders"].append(order)
    phone = order.get("phone","").strip()
    if phone:
        if phone not in d["clients"]:
            d["clients"][phone] = {"name": order["client"], "orders": []}
        d["clients"][phone]["orders"].append(order["id"])
    save(d)

def get_order(oid):
    return next((o for o in load()["orders"] if o["id"] == oid), None)

def update_order(oid, upd):
    d = load()
    for o in d["orders"]:
        if o["id"] == oid: o.update(upd)
    save(d)

def open_orders(): return [o for o in load()["orders"] if o["status"] != "closed"]
def my_open_orders(master): return [o for o in open_orders() if o.get("master") == master]
def today_orders(): return [o for o in load()["orders"] if o["date"] == date.today().isoformat()]
def my_closed_orders(master): return [o for o in load()["orders"] if o.get("master") == master and o["status"] == "closed"]

def all_debts():
    result = []
    for o in load()["orders"]:
        amt = sum(dp.get("amount_uzs",0) for dp in o.get("payments",[]) if dp.get("method") == "debt" and not dp.get("paid"))
        if amt > 0: result.append((o, amt))
    return result

def client_history(phone):
    d = load()
    if phone in d["clients"]:
        ids = set(d["clients"][phone]["orders"])
        return [o for o in d["orders"] if o["id"] in ids]
    return []

# ══════════════════════════════════════════════════════════
# УТИЛИТЫ
# ══════════════════════════════════════════════════════════
def is_owner(uid): return uid == OWNER_ID
def is_staff(uid): return uid in STAFF
def sname(uid): return STAFF.get(uid, {}).get("name", f"ID:{uid}")
def fmt(n):
    try: return f"{int(n):,}".replace(",", " ")
    except: return str(n)
def now_t(): return datetime.now().strftime("%H:%M")
def today_d(): return date.today().isoformat()
def is_cancel(text, uid): return text == t("cancel", uid)
def is_skip(text, uid): return text == t("skip", uid)

def calc_total_due(o):
    """Итого к оплате = запчасти клиенту + расходы (себестоимость наша, не показываем) + услуга"""
    parts_total = sum(p.get("sell_price", 0) for p in o.get("parts", []))
    # Расходы НЕ включаем в счёт клиенту — это наши расходы
    return parts_total  # Услуга уже входит, цену за неё мастер добавит через запчасти/отдельно

def calc_paid(o):
    total = 0
    for p in o.get("payments", []):
        if p.get("method") == "usd":
            total += p.get("usd_amt", 0) * p.get("usd_rate", 1)
        else:
            total += p.get("amount_uzs", 0)
    return total

def calc_debt(o):
    return sum(p.get("amount_uzs",0) for p in o.get("payments",[]) if p.get("method") == "debt" and not p.get("paid"))

def order_short(o, uid, show_margin=False):
    has_debt = calc_debt(o) > 0
    icon = "✅" if o["status"] == "closed" else ("⏳" if has_debt else "🔧")
    debt_mark = f" 💸{fmt(calc_debt(o))}" if has_debt else ""
    return (f"{icon} №{o['id']} | {o['car']} | {o['client']}\n"
            f"   {o['service']} → {o['master']}{debt_mark}\n"
            f"   📅 {o['date']} {o['time']}")

def order_full_summary(o, uid, show_margin=False):
    """Детальный итог для закрытия заявки"""
    parts = o.get("parts", [])
    expenses = o.get("expenses", [])
    payments = o.get("payments", [])

    parts_sell = sum(p.get("sell_price",0) for p in parts)
    parts_cost = sum(p.get("cost_price",0) for p in parts)
    exp_total = sum(e["amount"] for e in expenses)
    paid = calc_paid(o)
    debt = calc_debt(o)

    lines = []

    # Запчасти
    if parts:
        lines.append("🔩 *Запчасти / Ehtiyot qismlar:*")
        for p in parts:
            src = "👤" if p.get("cost_price",0) == 0 else "🛒"
            lines.append(f"  {src} {p['name']} — {fmt(p['sell_price'])} сум")
        lines.append(f"  Итого / Jami: {fmt(parts_sell)} сум")
        if show_margin and parts_cost > 0:
            lines.append(f"  📈 Маржа: {fmt(parts_sell - parts_cost)} сум")

    # Расходы (только для владельца)
    if show_margin and expenses:
        lines.append("\n📤 *Расходы / Xarajatlar:*")
        for e in expenses:
            lines.append(f"  • {e['type']}: {e.get('desc','')} — {fmt(e['amount'])} сум")
        lines.append(f"  Итого расходов: {fmt(exp_total)} сум")

    # Оплаты
    if payments:
        lines.append("\n💰 *Оплата / To'lov:*")
        for p in payments:
            if p.get("method") == "usd":
                uzs_eq = p.get("usd_amt",0) * p.get("usd_rate",1)
                lines.append(f"  💵 USD: ${p.get('usd_amt',0)} × {fmt(p.get('usd_rate',1))} = {fmt(uzs_eq)} сум")
            elif p.get("method") == "debt":
                paid_mark = "✅" if p.get("paid") else "⏳"
                lines.append(f"  📝 Долг {paid_mark}: {fmt(p.get('amount_uzs',0))} сум")
            else:
                method_icons = {"uzs": "💵 UZS", "card": "💳 Карта", "bank": "🏦 Перечисл."}
                icon = method_icons.get(p.get("method",""), p.get("method",""))
                lines.append(f"  {icon}: {fmt(p.get('amount_uzs',0))} сум")

    lines.append(f"\n💵 *Получено: {fmt(paid)} сум*")
    if debt > 0:
        lines.append(f"⚠️ Долг: {fmt(debt)} сум")
    if show_margin:
        net = paid - exp_total
        lines.append(f"✅ *Чистая прибыль: {fmt(net)} сум*")

    return "\n".join(lines)

def build_payment_screen(o, uid):
    """Экран оплаты — услуги, запчасти, расходы, итог"""
    parts = o.get("parts", [])
    expenses = o.get("expenses", [])
    parts_total = sum(p.get("sell_price",0) for p in parts)
    exp_total = sum(e["amount"] for e in expenses)
    paid = calc_paid(o)
    total_due = parts_total  # Счёт клиенту = запчасти по цене клиента
    left = max(0, total_due - paid)

    lines = [t("pay_summary_header", uid, id=o["id"], car=o["car"], client=o["client"])]

    # Услуга
    lines.append(f"🔧 {o['service']}")

    # Запчасти
    if parts:
        lines.append(f"\n{t('pay_parts_sec', uid)}")
        for p in parts:
            lines.append(f"  • {p['name']} — {fmt(p['sell_price'])} сум")
        lines.append(f"  Итого / Jami: {fmt(parts_total)} сум")

    # Расходы (только владельцу)
    if is_owner(uid) and expenses:
        lines.append(f"\n{t('pay_expenses_sec', uid)}")
        for e in expenses:
            lines.append(f"  • {e['type']}: {e.get('desc','')} — {fmt(e['amount'])} сум")

    lines.append(f"\n{t('pay_total_due', uid, v=fmt(total_due))}")
    if paid > 0:
        lines.append(t("pay_already", uid, v=fmt(paid)))
        lines.append(t("pay_left", uid, v=fmt(left)))

    return "\n".join(lines), total_due, paid, left

async def notify_owner(ctx, text, uid=None):
    if uid != OWNER_ID:
        try:
            await ctx.bot.send_message(chat_id=OWNER_ID, text=text, parse_mode="Markdown")
        except Exception as e:
            logger.warning(f"Notify failed: {e}")

# ══════════════════════════════════════════════════════════
# КЛАВИАТУРЫ
# ══════════════════════════════════════════════════════════
def kb_main(uid):
    master_name = STAFF.get(uid, {}).get("name", "")
    rows = [
        [t("btn_accept",uid), t("btn_open",uid)],
        [t("btn_part",uid), t("btn_pay",uid)],
        [t("btn_expense",uid), t("btn_close",uid)],
        [t("btn_my_history",uid), t("btn_history",uid)],
    ]
    if is_owner(uid):
        rows.append([t("btn_all_open",uid), t("btn_report",uid)])
        rows.append([t("btn_debts",uid), t("btn_staff",uid)])
    return ReplyKeyboardMarkup([[KeyboardButton(b) for b in r] for r in rows], resize_keyboard=True)

def kb_lang():
    return ReplyKeyboardMarkup([[KeyboardButton("🇺🇿 O'zbek"), KeyboardButton("🇷🇺 Русский")]], resize_keyboard=True)

def kb(items, cols=2, uid=None):
    cancel_text = t("cancel", uid) if uid else "❌"
    rows = [items[i:i+cols] for i in range(0, len(items), cols)]
    rows.append([cancel_text])
    return ReplyKeyboardMarkup([[KeyboardButton(b) for b in r] for r in rows], resize_keyboard=True)

def kb_cancel(uid):
    return ReplyKeyboardMarkup([[KeyboardButton(t("cancel", uid))]], resize_keyboard=True)

def kb_skip(uid):
    return ReplyKeyboardMarkup([[KeyboardButton(t("skip", uid)), KeyboardButton(t("cancel", uid))]], resize_keyboard=True)

def kb_pay(uid):
    btns = get_pay_buttons(uid)
    return ReplyKeyboardMarkup([
        [KeyboardButton(btns[0]), KeyboardButton(btns[1])],
        [KeyboardButton(btns[2]), KeyboardButton(btns[3])],
        [KeyboardButton(btns[4])],
        [KeyboardButton(t("cancel", uid))]
    ], resize_keyboard=True)

# ══════════════════════════════════════════════════════════
# СТАРТ + ЯЗЫК
# ══════════════════════════════════════════════════════════
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid):
        await update.message.reply_text(t("no_access", uid, uid=uid), parse_mode="Markdown"); return
    if uid not in USER_LANG:
        await update.message.reply_text(t("choose_lang", uid), reply_markup=kb_lang()); return
    await update.message.reply_text(f"👋 *{sname(uid)}*", parse_mode="Markdown", reply_markup=kb_main(uid))

async def cmd_lang(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return
    await update.message.reply_text(t("choose_lang", uid), reply_markup=kb_lang())

async def cmd_add_staff(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    args = ctx.args
    if len(args) < 2:
        await update.message.reply_text("Format: /add_staff 123456789 Abduraxmon"); return
    try:
        sid = int(args[0]); sn = " ".join(args[1:])
        STAFF[sid] = {"name": sn, "role": "master", "lang": "uz"}
        USER_LANG[sid] = "uz"
        d = load(); d.setdefault("user_langs", {})[str(sid)] = "uz"; save(d)
        await update.message.reply_text(f"✅ {sn} qo'shildi / добавлен!")
    except:
        await update.message.reply_text("❌ Error.")

async def cmd_close_debt(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id): return
    args = ctx.args
    if not args:
        await update.message.reply_text("/debt 5"); return
    try:
        oid = int(args[0]); o = get_order(oid)
        if not o:
            await update.message.reply_text("❌"); return
        payments = o.get("payments", [])
        for p in payments:
            if p.get("method") == "debt" and not p.get("paid"):
                p["paid"] = True; p["paid_time"] = now_t()
        update_order(oid, {"payments": payments})
        await update.message.reply_text(f"✅ Долг №{oid} закрыт!")
    except:
        await update.message.reply_text("/debt 5")

# ══════════════════════════════════════════════════════════
# 1. ПРИЁМКА — одна строка: номер * марка * имя
# ══════════════════════════════════════════════════════════
async def accept_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    ctx.user_data.clear()
    await update.message.reply_text(t("accept_hint", uid), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return A_PHONE  # Первый шаг — разбор одной строки, потом телефон

async def accept_parse_line(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    """Парсим: номер * марка * имя"""
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)

    parts = [p.strip() for p in update.message.text.split("*")]
    if len(parts) < 3:
        await update.message.reply_text(t("accept_err", uid), parse_mode="Markdown", reply_markup=kb_cancel(uid))
        return A_PHONE

    ctx.user_data["car_num"] = parts[0]
    ctx.user_data["car_brand"] = parts[1]
    ctx.user_data["client"] = parts[2]
    ctx.user_data["car"] = f"{parts[0]} {parts[1]}"

    # Проверяем историю если есть телефон — пока спрашиваем телефон
    await update.message.reply_text(t("accept_phone", uid), parse_mode="Markdown", reply_markup=kb_skip(uid))
    return A_PROBLEM

async def accept_phone(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    phone = "" if is_skip(update.message.text, uid) else update.message.text
    ctx.user_data["phone"] = phone
    extra = ""
    if phone:
        history = client_history(phone)
        if history:
            last = history[-1]
            extra = t("repeat_client", uid, n=len(history), date=last["date"], service=last["service"])
    await update.message.reply_text(t("accept_problem", uid) + extra, parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return A_MASTER

async def accept_problem(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    ctx.user_data["problem"] = update.message.text
    # Определяем мастера — если мастер сам принимает, предлагаем его имя
    master_name = STAFF.get(uid, {}).get("name", "")
    await update.message.reply_text(t("accept_master", uid), reply_markup=kb(MASTERS_LIST, uid=uid))
    return A_SERVICE

async def accept_master(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    ctx.user_data["master"] = update.message.text
    await update.message.reply_text(t("accept_service", uid), reply_markup=kb(get_services(uid), uid=uid))
    return A_SERVICE

async def accept_service(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    oid = new_id()
    order = {
        "id": oid, "date": today_d(), "time": now_t(),
        "car": ctx.user_data["car"],
        "car_num": ctx.user_data.get("car_num",""),
        "car_brand": ctx.user_data.get("car_brand",""),
        "client": ctx.user_data["client"],
        "phone": ctx.user_data.get("phone",""),
        "problem": ctx.user_data["problem"],
        "master": ctx.user_data["master"],
        "service": update.message.text,
        "parts": [], "payments": [], "expenses": [],
        "status": "in_work", "created_by": sname(uid),
    }
    add_order(order)
    msg = t("accept_done", uid, id=oid, car=order["car"], client=order["client"],
            service=order["service"], master=order["master"], problem=order["problem"])
    await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
    await notify_owner(ctx, f"🔔 *Yangi №{oid}*\n🚗 {order['car']} | {order['client']}\n🔧 {order['service']} → {order['master']}\n📝 {order['problem']}\n👤 {sname(uid)}", uid)
    return ConversationHandler.END

# ══════════════════════════════════════════════════════════
# 2. ЗАПЧАСТИ — многострочный ввод
# ══════════════════════════════════════════════════════════
async def part_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    # Показываем только свои машины мастеру, владельцу — все
    orders = my_open_orders(STAFF.get(uid,{}).get("name","")) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(t("no_open", uid), reply_markup=kb_main(uid)); return ConversationHandler.END
    ctx.user_data.clear()
    lines = [t("part_hint", uid), "\n"] + [order_short(o, uid) for o in orders] + ["\n" + t("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return P_ORDER

async def part_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o or o["status"] == "closed":
            await update.message.reply_text(t("not_found", uid)); return P_ORDER
        ctx.user_data["order_id"] = oid
        await update.message.reply_text(
            f"#{oid} | {o['car']}\n\n" + t("part_hint", uid),
            parse_mode="Markdown",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton(t("part_ready", uid))],
                [KeyboardButton(t("cancel", uid))]
            ], resize_keyboard=True)
        )
        return P_PARTS
    except:
        await update.message.reply_text(t("enter_num", uid)); return P_ORDER

async def part_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    if is_cancel(text, uid): return await cancel(update, ctx)
    if text == t("part_ready", uid):
        await update.message.reply_text("✅", reply_markup=kb_main(uid))
        return ConversationHandler.END

    oid = ctx.user_data["order_id"]
    o = get_order(oid)
    current_parts = o.get("parts", [])
    added = []
    errors = []

    for line in text.strip().split("\n"):
        line = line.strip()
        if not line: continue
        chunks = line.rsplit(None, 2)  # разделяем с конца по пробелам
        if len(chunks) == 3:
            try:
                name = chunks[0]
                cost = int(chunks[1].replace(" ",""))
                sell = int(chunks[2].replace(" ",""))
                added.append({"name": name, "source": "bought" if cost > 0 else "client", "cost_price": cost, "sell_price": sell})
            except:
                errors.append(line)
        elif len(chunks) == 2:
            try:
                name = chunks[0]
                sell = int(chunks[1].replace(" ",""))
                added.append({"name": name, "source": "client", "cost_price": 0, "sell_price": sell})
            except:
                errors.append(line)
        else:
            errors.append(line)

    if added:
        current_parts.extend(added)
        update_order(oid, {"parts": current_parts})

        lines = []
        for p in added:
            src = "👤" if p["cost_price"] == 0 else "🛒"
            lines.append(f"  {src} {p['name']} — {fmt(p['sell_price'])} сум")

        msg = t("part_done", uid, n=len(added), id=oid, list="\n".join(lines))
        if errors:
            msg += f"\n\n⚠️ Не добавлено: {', '.join(errors)}"

        await update.message.reply_text(msg, parse_mode="Markdown")
        await notify_owner(ctx, msg, uid)

    await update.message.reply_text(
        t("part_more", uid),
        reply_markup=ReplyKeyboardMarkup([
            [KeyboardButton(t("part_ready", uid))],
            [KeyboardButton(t("cancel", uid))]
        ], resize_keyboard=True)
    )
    return P_PARTS

# ══════════════════════════════════════════════════════════
# 3. РАСХОДЫ
# ══════════════════════════════════════════════════════════
async def exp_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    orders = my_open_orders(STAFF.get(uid,{}).get("name","")) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(t("no_open", uid), reply_markup=kb_main(uid)); return ConversationHandler.END
    ctx.user_data.clear()
    lines = [t("exp_hint", uid)] + [order_short(o, uid) for o in orders]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return EXP_ORDER

async def exp_order(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o:
            await update.message.reply_text(t("not_found", uid)); return EXP_ORDER
        ctx.user_data["order_id"] = oid
        await update.message.reply_text(t("exp_type_q", uid), reply_markup=kb(get_expenses(uid), uid=uid))
        return EXP_TYPE
    except:
        await update.message.reply_text(t("enter_num", uid)); return EXP_ORDER

async def exp_type(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    if update.message.text not in get_expenses(uid):
        await update.message.reply_text(t("exp_type_q", uid), reply_markup=kb(get_expenses(uid), uid=uid)); return EXP_TYPE
    ctx.user_data["exp_type"] = update.message.text
    await update.message.reply_text(t("exp_desc_q", uid), reply_markup=kb_skip(uid))
    return EXP_DESC

async def exp_desc(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    ctx.user_data["exp_desc"] = "" if is_skip(update.message.text, uid) else update.message.text
    await update.message.reply_text(t("exp_amt_q", uid), reply_markup=kb_cancel(uid))
    return EXP_AMOUNT

async def exp_amount(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        amount = int(update.message.text.replace(" ",""))
        oid = ctx.user_data["order_id"]
        expense = {"type": ctx.user_data["exp_type"], "desc": ctx.user_data["exp_desc"],
                   "amount": amount, "time": now_t(), "by": sname(uid)}
        o = get_order(oid)
        update_order(oid, {"expenses": o.get("expenses",[]) + [expense]})
        total = sum(e["amount"] for e in o.get("expenses",[])) + amount
        msg = t("exp_done", uid, id=oid, type=expense["type"], desc=expense["desc"] or "-",
                amt=fmt(amount), total=fmt(total))
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
        await notify_owner(ctx, msg, uid)
        return ConversationHandler.END
    except:
        await update.message.reply_text(t("enter_num", uid)); return EXP_AMOUNT

# ══════════════════════════════════════════════════════════
# 4. ОПЛАТА — умный процесс с добором
# ══════════════════════════════════════════════════════════
async def pay_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    orders = my_open_orders(STAFF.get(uid,{}).get("name","")) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(t("no_open", uid), reply_markup=kb_main(uid)); return ConversationHandler.END
    ctx.user_data.clear()
    lines = [t("pay_choose", uid) + "\n"] + [order_short(o, uid) for o in orders] + ["\n" + t("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return PAY_ORDER

async def pay_order_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o or o["status"] == "closed":
            await update.message.reply_text(t("not_found", uid)); return PAY_ORDER
        ctx.user_data["order_id"] = oid
        return await show_pay_screen(update, ctx, o)
    except:
        await update.message.reply_text(t("enter_num", uid)); return PAY_ORDER

async def show_pay_screen(update, ctx, o=None):
    uid = update.effective_user.id
    oid = ctx.user_data["order_id"]
    if o is None: o = get_order(oid)
    screen, total_due, paid, left = build_payment_screen(o, uid)
    ctx.user_data["total_due"] = total_due
    ctx.user_data["left"] = left

    await update.message.reply_text(screen + f"\n\n{t('pay_choose', uid)}", parse_mode="Markdown", reply_markup=kb_pay(uid))
    return PAY_METHOD

async def pay_method_select(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text
    if is_cancel(text, uid): return await cancel(update, ctx)

    btns = get_pay_buttons(uid)
    method_map = {
        btns[0]: "uzs", btns[1]: "usd",
        btns[2]: "card", btns[3]: "bank", btns[4]: "debt"
    }

    if text not in method_map:
        await update.message.reply_text(t("pay_choose", uid), reply_markup=kb_pay(uid)); return PAY_METHOD

    method = method_map[text]
    ctx.user_data["pay_method"] = method
    ctx.user_data["pay_method_name"] = text

    if method == "usd":
        await update.message.reply_text(t("pay_usd_rate", uid), reply_markup=kb_cancel(uid))
        return PAY_USD_RATE
    elif method == "debt":
        left = ctx.user_data.get("left", 0)
        await update.message.reply_text(t("pay_enter_amt", uid, method=text) + f"\n({fmt(left)} сум)", reply_markup=kb_cancel(uid))
        return PAY_AMOUNT
    else:
        left = ctx.user_data.get("left", 0)
        await update.message.reply_text(t("pay_enter_amt", uid, method=text) + f"\n({fmt(left)} сум)", reply_markup=kb_cancel(uid))
        return PAY_AMOUNT

async def pay_usd_rate(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        ctx.user_data["usd_rate"] = int(update.message.text.replace(" ",""))
        await update.message.reply_text(t("pay_usd_amt", uid), reply_markup=kb_cancel(uid))
        return PAY_USD_AMT
    except:
        await update.message.reply_text(t("enter_num", uid)); return PAY_USD_RATE

async def pay_usd_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        usd_amt = int(update.message.text.replace(" ",""))
        rate = ctx.user_data["usd_rate"]
        uzs_eq = usd_amt * rate
        ctx.user_data["usd_amt"] = usd_amt
        ctx.user_data["amount_uzs"] = uzs_eq
        return await record_payment(update, ctx)
    except:
        await update.message.reply_text(t("enter_num", uid)); return PAY_USD_AMT

async def pay_amount_input(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        amount = int(update.message.text.replace(" ",""))
        ctx.user_data["amount_uzs"] = amount
        return await record_payment(update, ctx)
    except:
        await update.message.reply_text(t("enter_num", uid)); return PAY_AMOUNT

async def record_payment(update, ctx):
    uid = update.effective_user.id
    oid = ctx.user_data["order_id"]
    method = ctx.user_data["pay_method"]
    amount_uzs = ctx.user_data["amount_uzs"]
    o = get_order(oid)

    payment = {"method": method, "amount_uzs": amount_uzs, "time": now_t(), "by": sname(uid)}
    if method == "usd":
        payment["usd_amt"] = ctx.user_data["usd_amt"]
        payment["usd_rate"] = ctx.user_data["usd_rate"]
    if method == "debt":
        payment["paid"] = False

    payments = o.get("payments", []) + [payment]
    update_order(oid, {"payments": payments})

    # Пересчитываем остаток
    o = get_order(oid)
    total_due = ctx.user_data["total_due"]
    new_paid = calc_paid(o)
    left = max(0, total_due - new_paid)
    ctx.user_data["left"] = left

    method_name = ctx.user_data["pay_method_name"]

    if method == "debt" or left <= 0:
        # Оплата завершена
        debt = calc_debt(o)
        debt_line = t("pay_debt_warn", uid, v=fmt(debt)) if debt > 0 else ""
        msg = t("pay_done_full", uid, total=fmt(new_paid)) + debt_line
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))
        await notify_owner(ctx, f"💰 *To'lov №{oid}*\n🚗 {o['car']} | {o['client']}\nJami: {fmt(new_paid)} сум{debt_line}\n👤 {sname(uid)}", uid)
        return ConversationHandler.END
    else:
        # Ещё не добрали — снова показываем способы
        msg = t("pay_recorded", uid, method=method_name, amt=fmt(amount_uzs), left=fmt(left))
        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_pay(uid))
        return PAY_METHOD

# ══════════════════════════════════════════════════════════
# 5. ЗАКРЫТИЕ — только после оплаты
# ══════════════════════════════════════════════════════════
async def close_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return ConversationHandler.END
    orders = my_open_orders(STAFF.get(uid,{}).get("name","")) if not is_owner(uid) else open_orders()
    if not orders:
        await update.message.reply_text(t("no_open", uid), reply_markup=kb_main(uid)); return ConversationHandler.END
    ctx.user_data.clear()
    lines = ["✅ *Закрыть / Yopish*\n"] + [order_short(o, uid) for o in orders] + ["\n" + t("enter_order", uid)]
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_cancel(uid))
    return CLOSE_ORDER

async def close_confirm(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    try:
        oid = int(update.message.text.strip())
        o = get_order(oid)
        if not o:
            await update.message.reply_text(t("not_found", uid)); return CLOSE_ORDER

        # Проверяем оплату
        if not o.get("payments"):
            await update.message.reply_text(t("close_no_pay", uid), parse_mode="Markdown", reply_markup=kb_main(uid))
            return ConversationHandler.END

        has_debt = calc_debt(o) > 0
        debt_warn = t("close_debt_warn", uid) if has_debt else ""
        phone = o.get("phone","")
        phone_line = t("close_call", uid, phone=phone) if phone else t("close_call2", uid)

        update_order(oid, {"status": "closed", "closed_time": now_t(), "closed_by": sname(uid)})

        # Итоговый отчёт
        summary = order_full_summary(o, uid, show_margin=is_owner(uid))
        msg = t("close_done", uid, id=oid, car=o["car"], client=o["client"],
                phone=phone_line, debt=debt_warn, summary=summary)

        await update.message.reply_text(msg, parse_mode="Markdown", reply_markup=kb_main(uid))

        # Владельцу полный отчёт с маржой
        if uid != OWNER_ID:
            owner_summary = order_full_summary(o, OWNER_ID, show_margin=True)
            owner_msg = t("close_done", OWNER_ID, id=oid, car=o["car"], client=o["client"],
                          phone=phone_line, debt=debt_warn, summary=owner_summary)
            try:
                await ctx.bot.send_message(chat_id=OWNER_ID, text=owner_msg, parse_mode="Markdown")
            except: pass

        return ConversationHandler.END
    except Exception as e:
        logger.error(f"Close error: {e}")
        await update.message.reply_text(t("enter_num", uid)); return CLOSE_ORDER

# ══════════════════════════════════════════════════════════
# 6. МОИ МАШИНЫ (мастер)
# ══════════════════════════════════════════════════════════
async def cmd_my_orders(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return
    master_name = STAFF.get(uid, {}).get("name", "")
    orders = my_open_orders(master_name)
    if not orders:
        await update.message.reply_text(t("no_open", uid), reply_markup=kb_main(uid)); return
    lines = [f"📋 *{master_name}* — {len(orders)} ta / заявок\n"]
    for o in orders:
        lines.append(order_short(o, uid))
        lines.append("─────────────")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

# ══════════════════════════════════════════════════════════
# 7. МОЯ ИСТОРИЯ (мастер)
# ══════════════════════════════════════════════════════════
async def cmd_my_history(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_staff(uid): return
    master_name = STAFF.get(uid, {}).get("name", "")
    orders = my_closed_orders(master_name)
    if not orders:
        await update.message.reply_text(t("my_hist_none", uid), reply_markup=kb_main(uid)); return
    lines = [f"📜 *{master_name}* — {len(orders)} ta / закрыто\n"]
    for o in orders[-10:]:  # последние 10
        lines.append(order_short(o, uid))
        lines.append("─────────────")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

# ══════════════════════════════════════════════════════════
# 8. ИСТОРИЯ КЛИЕНТА
# ══════════════════════════════════════════════════════════
async def hist_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    if not is_staff(update.effective_user.id): return ConversationHandler.END
    ctx.user_data.clear()
    uid = update.effective_user.id
    await update.message.reply_text(t("hist_q", uid), reply_markup=kb_cancel(uid))
    return HIST_PHONE

async def hist_show(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if is_cancel(update.message.text, uid): return await cancel(update, ctx)
    phone = update.message.text.strip()
    history = client_history(phone)
    if not history:
        await update.message.reply_text(t("hist_none", uid, phone=phone), reply_markup=kb_main(uid))
        return ConversationHandler.END
    total = sum(calc_paid(o) for o in history)
    lines = [f"👤 *{history[0]['client']}* | {phone}",
             f"📊 {len(history)} ta / визитов | {fmt(total)} сум\n─────────────"]
    for o in history[-5:]:
        lines.append(order_short(o, uid))
        lines.append("─────────────")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))
    return ConversationHandler.END

# ══════════════════════════════════════════════════════════
# 9. ОТЧЁТ (владелец)
# ══════════════════════════════════════════════════════════
async def cmd_report(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text(t("only_owner", uid)); return
    orders = today_orders()
    if not orders:
        await update.message.reply_text(t("rep_none", uid)); return

    t_uzs = t_usd = t_card = t_bank = t_debt = t_exp = t_margin = 0
    for o in orders:
        for p in o.get("payments",[]):
            if p["method"] == "usd":
                uzs = p.get("usd_amt",0) * p.get("usd_rate",1)
                t_usd += uzs
            elif p["method"] == "debt":
                t_debt += p.get("amount_uzs",0)
            elif p["method"] == "uzs": t_uzs += p.get("amount_uzs",0)
            elif p["method"] == "card": t_card += p.get("amount_uzs",0)
            elif p["method"] == "bank": t_bank += p.get("amount_uzs",0)
        t_exp += sum(e["amount"] for e in o.get("expenses",[]))
        t_margin += sum(p.get("sell_price",0) - p.get("cost_price",0) for p in o.get("parts",[]))

    received = t_uzs + t_usd + t_card + t_bank
    closed = sum(1 for o in orders if o["status"] == "closed")

    lines = [
        t("rep_title", uid, date=today_d()),
        f"📋 Jami / Всего: {len(orders)} | Yopilgan / Закрыто: {closed} | Ishda / В работе: {len(orders)-closed}",
        f"\n💰 *Olingan / Получено: {fmt(received)} сум*",
        f"  💵 Naqd UZS: {fmt(t_uzs)} сум",
        f"  💵 Naqd USD: {fmt(t_usd)} сум",
        f"  💳 Karta: {fmt(t_card)} сум",
        f"  🏦 O'tkazma: {fmt(t_bank)} сум",
        f"  📝 Qarz / Долги: {fmt(t_debt)} сум",
        f"\n📤 Xarajat / Расходы: {fmt(t_exp)} сум",
        f"📈 Marja / Маржа: {fmt(t_margin)} сум",
        f"\n✅ *Sof foyda / Чистая прибыль: {fmt(received - t_exp)} сум*",
        "\n─────────────────"
    ]
    for o in orders:
        lines.append(order_short(o, uid, show_margin=True))
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

# ══════════════════════════════════════════════════════════
# 10. ДОЛГИ
# ══════════════════════════════════════════════════════════
async def cmd_debts(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid):
        await update.message.reply_text(t("only_owner", uid)); return
    debts = all_debts()
    if not debts:
        await update.message.reply_text(t("debt_none", uid), reply_markup=kb_main(uid)); return
    total = sum(a for _,a in debts)
    lines = [t("debt_title", uid, n=len(debts), total=fmt(total))]
    for o, amt in debts:
        lines.append(f"№{o['id']} | {o['car']} | {o['client']}\n  📱 {o['phone']} | 💸 {fmt(amt)} | 📅 {o['date']}")
        lines.append("─────────────")
    lines.append("\n/debt НОМЕР — закрыть долг")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

# ══════════════════════════════════════════════════════════
# 11. СОТРУДНИКИ
# ══════════════════════════════════════════════════════════
async def cmd_staff(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid): return
    lines = ["👥 *Xodimlar / Сотрудники:*\n"]
    for sid, info in STAFF.items():
        lines.append(f"• {info['name']} — ID: `{sid}`")
    lines.append("\nQo'shish / Добавить: /add_staff 123456789 Abduraxmon")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

async def cmd_all_open(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    if not is_owner(uid): return
    orders = open_orders()
    if not orders:
        await update.message.reply_text(t("no_open", uid), reply_markup=kb_main(uid)); return
    lines = [f"📋 *Barcha ochiqlar / Все открытые ({len(orders)}):*\n"]
    for o in orders:
        lines.append(order_short(o, uid, show_margin=True))
        lines.append("─────────────")
    await update.message.reply_text("\n".join(lines), parse_mode="Markdown", reply_markup=kb_main(uid))

# ══════════════════════════════════════════════════════════
# ОТМЕНА И РОУТЕР
# ══════════════════════════════════════════════════════════
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    ctx.user_data.clear()
    await update.message.reply_text(t("cancelled", uid), reply_markup=kb_main(uid))
    return ConversationHandler.END

async def router(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text

    # Выбор языка
    if text == "🇺🇿 O'zbek":
        save_lang(uid, "uz")
        await update.message.reply_text(T["lang_set_uz"]["uz"], parse_mode="Markdown", reply_markup=kb_main(uid)); return
    if text == "🇷🇺 Русский":
        save_lang(uid, "ru")
        await update.message.reply_text(T["lang_set_ru"]["ru"], parse_mode="Markdown", reply_markup=kb_main(uid)); return

    if not is_staff(uid):
        await update.message.reply_text(f"⛔ ID: `{uid}`", parse_mode="Markdown"); return
    if uid not in USER_LANG:
        await update.message.reply_text(t("choose_lang", uid), reply_markup=kb_lang()); return

    if text == t("btn_open", uid):       await cmd_my_orders(update, ctx)
    elif text == t("btn_all_open", uid): await cmd_all_open(update, ctx)
    elif text == t("btn_my_history", uid): await cmd_my_history(update, ctx)
    elif text == t("btn_report", uid):   await cmd_report(update, ctx)
    elif text == t("btn_debts", uid):    await cmd_debts(update, ctx)
    elif text == t("btn_staff", uid):    await cmd_staff(update, ctx)

# ══════════════════════════════════════════════════════════
# ЗАПУСК
# ══════════════════════════════════════════════════════════
def main():
    load_langs()
    app = Application.builder().token(TOKEN).build()

    def conv(triggers, states, entry_fn):
        pattern = "^(" + "|".join(map(lambda x: x.replace("(","\\(").replace(")","\\)").replace("+","\\+"), triggers)) + ")$"
        return ConversationHandler(
            entry_points=[MessageHandler(filters.Regex(pattern), entry_fn)],
            states=states,
            fallbacks=[MessageHandler(filters.ALL, cancel)],
        )

    # Приёмка
    accept_triggers = [T["btn_accept"]["uz"], T["btn_accept"]["ru"]]
    app.add_handler(conv(accept_triggers, {
        A_PHONE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_parse_line)],
        A_PROBLEM: [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_phone)],
        A_MASTER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_problem)],
        A_SERVICE: [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_master)],
        A_SERVICE+1: [MessageHandler(filters.TEXT & ~filters.COMMAND, accept_service)],
    }, accept_start))

    # Запчасти
    app.add_handler(conv([T["btn_part"]["uz"], T["btn_part"]["ru"]], {
        P_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, part_order)],
        P_PARTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, part_input)],
    }, part_start))

    # Расходы
    app.add_handler(conv([T["btn_expense"]["uz"], T["btn_expense"]["ru"]], {
        EXP_ORDER:  [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_order)],
        EXP_TYPE:   [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_type)],
        EXP_DESC:   [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_desc)],
        EXP_AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, exp_amount)],
    }, exp_start))

    # Оплата
    app.add_handler(conv([T["btn_pay"]["uz"], T["btn_pay"]["ru"]], {
        PAY_ORDER:   [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_order_select)],
        PAY_METHOD:  [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_method_select)],
        PAY_USD_RATE:[MessageHandler(filters.TEXT & ~filters.COMMAND, pay_usd_rate)],
        PAY_USD_AMT: [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_usd_input)],
        PAY_AMOUNT:  [MessageHandler(filters.TEXT & ~filters.COMMAND, pay_amount_input)],
    }, pay_start))

    # Закрытие
    app.add_handler(conv([T["btn_close"]["uz"], T["btn_close"]["ru"]], {
        CLOSE_ORDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, close_confirm)],
    }, close_start))

    # История клиента
    app.add_handler(conv([T["btn_history"]["uz"], T["btn_history"]["ru"]], {
        HIST_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, hist_show)],
    }, hist_start))

    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("lang", cmd_lang))
    app.add_handler(CommandHandler("add_staff", cmd_add_staff))
    app.add_handler(CommandHandler("debt", cmd_close_debt))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, router))

    print("✅ Avtoservis Bot v2.0 ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
