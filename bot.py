#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters
from datetime import datetime, timedelta
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import json
import os
import random
import string

# ═══════════════════════════════════════════════════════
# الإعدادات الأساسية
# ═══════════════════════════════════════════════════════

BOT_TOKEN = "8582071685:AAHh22QTz6vJQ_O6ldZdkliWDI9kkTT36qA"
ADMIN_ID = 888806420
DATA_FILE = "cases_data.json"
SCHEDULER = AsyncIOScheduler()

# ═══════════════════════════════════════════════════════
# دوال إدارة البيانات
# ═══════════════════════════════════════════════════════

def load_data():
    """تحميل البيانات من الملف"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "cases": {},
        "clients": {},
        "activation_codes": {},
        "stats": {"total_cases": 0, "active_cases": 0, "closed_cases": 0},
        "faq": {
            "ما هي مواعيد العمل؟": "مواعيد العمل من 9 صباحاً حتى 5 مساءً",
            "كيف أحجز موعد؟": "اضغط على 'حجز موعد استشارة' من القائمة الرئيسية",
            "كيف أتابع قضيتي؟": "اكتب رقم قضيتك أو الكود الخاص بك"
        }
    }

def save_data(data):
    """حفظ البيانات في الملف"""
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def generate_code():
    """توليد كود تفعيل عشوائي"""
    prefix = "Q-"
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    return prefix + random_part

def update_stats(data):
    """تحديث الإحصائيات"""
    total = len(data['cases'])
    active = sum(1 for c in data['cases'].values() if c.get('status') != 'منتهية')
    closed = total - active
    data['stats'] = {
        "total_cases": total,
        "active_cases": active,
        "closed_cases": closed
    }

# ═══════════════════════════════════════════════════════
# القوائم والأزرار
# ═══════════════════════════════════════════════════════

def get_admin_menu():
    """قائمة الأدمن الرئيسية"""
    keyboard = [
        [InlineKeyboardButton("➕ إضافة قضية جديدة", callback_data="add_case")],
        [InlineKeyboardButton("📝 تحديث قضية", callback_data="update_case_menu")],
        [InlineKeyboardButton("📋 عرض كل القضايا", callback_data="list_all_cases")],
        [InlineKeyboardButton("🔍 بحث عن قضية", callback_data="search_case")],
        [InlineKeyboardButton("🔔 إرسال إشعار", callback_data="send_notification")],
        [InlineKeyboardButton("📊 الإحصائيات", callback_data="show_stats")],
        [InlineKeyboardButton("❓ إدارة الأسئلة الشائعة", callback_data="manage_faq")],
        [InlineKeyboardButton("💰 إدارة الأتعاب", callback_data="manage_fees")],
        [InlineKeyboardButton("📁 أرشفة القضايا المنتهية", callback_data="archive_cases")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_client_menu():
    """قائمة الموكل الرئيسية"""
    keyboard = [
        [InlineKeyboardButton("🔍 الاستعلام عن قضيتي", callback_data="check_case")],
        [InlineKeyboardButton("🔗 تفعيل قضية بالكود", callback_data="activate_case")],
        [InlineKeyboardButton("📅 حجز موعد استشارة", callback_data="book_appointment")],
        [InlineKeyboardButton("❓ أسئلة شائعة", callback_data="view_faq")],
        [InlineKeyboardButton("📞 تواصل معنا", callback_data="contact_us")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_update_menu():
    """قائمة خيارات التحديث"""
    keyboard = [
        [InlineKeyboardButton("📅 تاريخ الجلسة", callback_data="update_hearing_date")],
        [InlineKeyboardButton("📍 حالة القضية", callback_data="update_status")],
        [InlineKeyboardButton("👤 اسم الموكل", callback_data="update_client_name")],
        [InlineKeyboardButton("📝 إضافة تحديث جديد", callback_data="add_update")],
        [InlineKeyboardButton("📄 إرفاق مستند", callback_data="attach_document")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(keyboard)

def get_case_status_options():
    """خيارات حالة القضية"""
    keyboard = [
        [InlineKeyboardButton("⚖️ جارية", callback_data="status_active")],
        [InlineKeyboardButton("⏸ مؤجلة", callback_data="status_postponed")],
        [InlineKeyboardButton("✅ منتهية", callback_data="status_closed")],
        [InlineKeyboardButton("📋 قيد المراجعة", callback_data="status_review")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ═══════════════════════════════════════════════════════
# أمر البداية
# ═══════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر /start"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    data = load_data()
    
    # تسجيل الموكل إذا لم يكن مسجلاً
    if str(user_id) not in data['clients'] and user_id != ADMIN_ID:
        data['clients'][str(user_id)] = {
            "name": user_name,
            "registered_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "cases": []
        }
        save_data(data)
    
    if user_id == ADMIN_ID:
        await update.message.reply_text(
            f"مرحباً أستاذ {user_name} 👨‍⚖️\n\n"
            "لوحة التحكم الخاصة بك:",
            reply_markup=get_admin_menu()
        )
    else:
        await update.message.reply_text(
            f"مرحباً {user_name}! ⚖️\n\n"
            "مرحباً بك في بوت مكتب المحاماة\n"
            "يمكنك الاستعلام عن قضيتك أو تفعيل قضية جديدة:",
            reply_markup=get_client_menu()
        )

# ═══════════════════════════════════════════════════════
# إضافة قضية جديدة
# ═══════════════════════════════════════════════════════

async def add_case_start(query, context):
    """بدء إضافة قضية"""
    context.user_data['action'] = 'add_case'
    context.user_data['step'] = 'case_number'
    context.user_data['case_data'] = {}
    await query.edit_message_text("📝 أرسل رقم القضية:")

async def handle_add_case(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """معالجة إضافة قضية"""
    step = context.user_data.get('step')
    case_data = context.user_data.get('case_data', {})
    
    if step == 'case_number':
        case_data['case_number'] = text
        context.user_data['case_data'] = case_data
        context.user_data['step'] = 'client_name'
        await update.message.reply_text("👤 أرسل اسم الموكل:")
    
    elif step == 'client_name':
        case_data['client_name'] = text
        context.user_data['case_data'] = case_data
        context.user_data['step'] = 'case_type'
        await update.message.reply_text("⚖️ أرسل نوع القضية (مدني، جنائي، تجاري، إلخ):")
    
    elif step == 'case_type':
        case_data['case_type'] = text
        context.user_data['case_data'] = case_data
        context.user_data['step'] = 'next_hearing'
        await update.message.reply_text("📅 أرسل تاريخ الجلسة القادمة (مثال: 2026-03-15):")
    
    elif step == 'next_hearing':
        case_data['next_hearing_date'] = text
        context.user_data['case_data'] = case_data
        context.user_data['step'] = 'hearing_time'
        await update.message.reply_text("🕐 أرسل وقت الجلسة (مثال: 10:00 صباحاً):")
    
    elif step == 'hearing_time':
        case_data['hearing_time'] = text
        context.user_data['case_data'] = case_data
        context.user_data['step'] = 'hearing_location'
        await update.message.reply_text("📍 أرسل مكان الجلسة (مثال: محكمة القاهرة الجديدة):")
    
    elif step == 'hearing_location':
        case_data['hearing_location'] = text
        context.user_data['case_data'] = case_data
        context.user_data['step'] = 'fees_total'
        await update.message.reply_text("💰 أرسل إجمالي الأتعاب (بالجنيه):")
    
    elif step == 'fees_total':
        case_data['fees_total'] = text
        context.user_data['case_data'] = case_data
        context.user_data['step'] = 'fees_paid'
        await update.message.reply_text("💵 أرسل المبلغ المدفوع حتى الآن:")
    
    elif step == 'fees_paid':
        case_data['fees_paid'] = text
        
        # توليد كود التفعيل
        activation_code = generate_code()
        
        # حفظ القضية
        data = load_data()
        case_number = case_data['case_number']
        
        data['cases'][case_number] = {
            "client_name": case_data['client_name'],
            "case_type": case_data.get('case_type', 'غير محدد'),
            "next_hearing_date": case_data['next_hearing_date'],
            "hearing_time": case_data.get('hearing_time', 'غير محدد'),
            "hearing_location": case_data.get('hearing_location', 'غير محدد'),
            "status": "جارية",
            "activation_code": activation_code,
            "activated": False,
            "client_telegram_id": None,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "updates": [],
            "documents": [],
            "fees": {
                "total": case_data['fees_total'],
                "paid": case_data['fees_paid'],
                "remaining": str(int(case_data['fees_total']) - int(case_data['fees_paid']))
            }
        }
        
        data['activation_codes'][activation_code] = case_number
        update_stats(data)
        save_data(data)
        
        # رسالة للأدمن
        msg = f"✅ تم إضافة القضية بنجاح!\n\n"
        msg += f"📋 رقم القضية: {case_number}\n"
        msg += f"👤 الموكل: {case_data['client_name']}\n"
        msg += f"🔑 كود التفعيل: `{activation_code}`\n\n"
        msg += f"⚠️ قم بإرسال هذا الكود للموكل لتفعيل قضيته"
        
        await update.message.reply_text(msg, parse_mode='Markdown')
        context.user_data.clear()
# ═══════════════════════════════════════════════════════
# تفعيل القضية بالكود
# ═══════════════════════════════════════════════════════

async def activate_case_start(query, context):
    """بدء تفعيل قضية"""
    context.user_data['action'] = 'activate_case'
    await query.edit_message_text("🔑 أرسل كود التفعيل الذي حصلت عليه من المحامي:")

async def handle_activation(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """معالجة تفعيل القضية"""
    data = load_data()
    user_id = update.effective_user.id
    
    if text in data['activation_codes']:
        case_number = data['activation_codes'][text]
        
        # ربط الموكل بالقضية
        data['cases'][case_number]['activated'] = True
        data['cases'][case_number]['client_telegram_id'] = user_id
        
        # إضافة القضية لقائمة قضايا الموكل
        if str(user_id) in data['clients']:
            if case_number not in data['clients'][str(user_id)]['cases']:
                data['clients'][str(user_id)]['cases'].append(case_number)
        
        save_data(data)
        
        case = data['cases'][case_number]
        msg = f"✅ تم تفعيل قضيتك بنجاح!\n\n"
        msg += f"📋 رقم القضية: {case_number}\n"
        msg += f"⚖️ نوع القضية: {case.get('case_type', 'غير محدد')}\n"
        msg += f"📅 الجلسة القادمة: {case['next_hearing_date']}\n"
        msg += f"🕐 الوقت: {case.get('hearing_time', 'غير محدد')}\n"
        msg += f"📍 المكان: {case.get('hearing_location', 'غير محدد')}\n\n"
        msg += f"سيتم إرسال إشعارات تلقائية لك قبل كل جلسة 🔔"
        
        await update.message.reply_text(msg)
        context.user_data.clear()
    else:
        await update.message.reply_text("❌ كود التفعيل غير صحيح! تأكد من الكود وحاول مرة أخرى.")

# ═══════════════════════════════════════════════════════
# الاستعلام عن القضية
# ═══════════════════════════════════════════════════════

async def check_case_start(query, context):
    """بدء الاستعلام"""
    context.user_data['action'] = 'check_case'
    await query.edit_message_text("🔍 أرسل رقم القضية للاستعلام:")

async def handle_check_case(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """معالجة الاستعلام"""
    data = load_data()
    user_id = update.effective_user.id
    
    if text in data['cases']:
        case = data['cases'][text]
        
        # التحقق من صلاحية الوصول
        if user_id != ADMIN_ID:
            if case.get('client_telegram_id') != user_id:
                await update.message.reply_text("❌ ليس لديك صلاحية للوصول لهذه القضية!")
                context.user_data.clear()
                return
        
        msg = f"⚖️ معلومات القضية رقم {text}\n"
        msg += f"{'='*30}\n\n"
        msg += f"👤 الموكل: {case['client_name']}\n"
        msg += f"⚖️ نوع القضية: {case.get('case_type', 'غير محدد')}\n"
        msg += f"📍 الحالة: {case['status']}\n"
        msg += f"📅 الجلسة القادمة: {case['next_hearing_date']}\n"
        msg += f"🕐 الوقت: {case.get('hearing_time', 'غير محدد')}\n"
        msg += f"📍 المكان: {case.get('hearing_location', 'غير محدد')}\n\n"
        
        # الأتعاب
        if 'fees' in case:
            msg += f"💰 الأتعاب:\n"
            msg += f"   • الإجمالي: {case['fees']['total']} جنيه\n"
            msg += f"   • المدفوع: {case['fees']['paid']} جنيه\n"
            msg += f"   • المتبقي: {case['fees']['remaining']} جنيه\n\n"
        
        # التحديثات
        if case.get('updates'):
            msg += f"📝 آخر التحديثات:\n"
            for update_item in case['updates'][-3:]:  # آخر 3 تحديثات
                msg += f"   • {update_item['date']}: {update_item['text']}\n"
        else:
            msg += f"📝 لا توجد تحديثات حتى الآن\n"
        
        # المستندات
        if case.get('documents'):
            msg += f"\n📁 المستندات المرفقة: {len(case['documents'])}\n"
        
        await update.message.reply_text(msg)
        context.user_data.clear()
    else:
        await update.message.reply_text("❌ لم يتم العثور على القضية!")
        context.user_data.clear()

# ═══════════════════════════════════════════════════════
# تحديث القضية
# ═══════════════════════════════════════════════════════

async def update_case_menu_start(query, context):
    """عرض قائمة التحديث"""
    context.user_data['action'] = 'update_case'
    context.user_data['step'] = 'select_case'
    await query.edit_message_text("📝 أرسل رقم القضية المراد تحديثها:")

async def handle_update_case(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """معالجة تحديث القضية"""
    step = context.user_data.get('step')
    data = load_data()
    
    if step == 'select_case':
        if text not in data['cases']:
            await update.message.reply_text("❌ القضية غير موجودة!")
            context.user_data.clear()
            return
        
        context.user_data['selected_case'] = text
        await update.message.reply_text(
            f"✅ القضية رقم {text}\n\nاختر ما تريد تحديثه:",
            reply_markup=get_update_menu()
        )
    
    elif step == 'update_hearing_date':
        case_number = context.user_data['selected_case']
        data['cases'][case_number]['next_hearing_date'] = text
        data['cases'][case_number]['updates'].append({
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'text': f"تم تحديث موعد الجلسة إلى: {text}"
        })
        save_data(data)
        
        # إرسال إشعار للموكل
        if data['cases'][case_number].get('client_telegram_id'):
            try:
                await context.bot.send_message(
                    chat_id=data['cases'][case_number]['client_telegram_id'],
                    text=f"🔔 تحديث في القضية رقم {case_number}\n\n"
                         f"📅 تم تغيير موعد الجلسة القادمة إلى: {text}"
                )
            except:
                pass
        
        await update.message.reply_text("✅ تم تحديث موعد الجلسة وإرسال إشعار للموكل!")
        context.user_data.clear()
    
    elif step == 'update_status':
        case_number = context.user_data['selected_case']
        data['cases'][case_number]['status'] = text
        data['cases'][case_number]['updates'].append({
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'text': f"تم تغيير حالة القضية إلى: {text}"
        })
        update_stats(data)
        save_data(data)
        
        # إرسال إشعار للموكل
        if data['cases'][case_number].get('client_telegram_id'):
            try:
                await context.bot.send_message(
                    chat_id=data['cases'][case_number]['client_telegram_id'],
                    text=f"🔔 تحديث في القضية رقم {case_number}\n\n"
                         f"📍 تم تغيير حالة القضية إلى: {text}"
                )
            except:
                pass
        
        await update.message.reply_text("✅ تم تحديث حالة القضية وإرسال إشعار للموكل!")
        context.user_data.clear()
    
    elif step == 'update_client_name':
        case_number = context.user_data['selected_case']
        data['cases'][case_number]['client_name'] = text
        save_data(data)
        await update.message.reply_text("✅ تم تحديث اسم الموكل!")
        context.user_data.clear()
    
    elif step == 'add_update':
        case_number = context.user_data['selected_case']
        data['cases'][case_number]['updates'].append({
            'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
            'text': text
        })
        save_data(data)
        
        # إرسال إشعار للموكل
        if data['cases'][case_number].get('client_telegram_id'):
            try:
                await context.bot.send_message(
                    chat_id=data['cases'][case_number]['client_telegram_id'],
                    text=f"🔔 تحديث جديد في القضية رقم {case_number}\n\n"
                         f"📝 {text}"
                )
            except:
                pass
        
        await update.message.reply_text("✅ تم إضافة التحديث وإرسال إشعار للموكل!")
        context.user_data.clear()

# ═══════════════════════════════════════════════════════
# عرض كل القضايا
# ═══════════════════════════════════════════════════════

async def list_all_cases(query, context):
    """عرض كل القضايا"""
    data = load_data()
    
    if not data['cases']:
        await query.edit_message_text("📋 لا توجد قضايا مسجلة حالياً.")
        return
    
    # تصنيف القضايا
    active = [c for c, info in data['cases'].items() if info['status'] not in ['منتهية']]
    closed = [c for c, info in data['cases'].items() if info['status'] == 'منتهية']
    
    msg = f"📊 إجمالي القضايا: {len(data['cases'])}\n"
    msg += f"✅ قضايا جارية: {len(active)}\n"
    msg += f"🔒 قضايا منتهية: {len(closed)}\n"
    msg += f"{'='*30}\n\n"
    
    if active:
        msg += "⚖️ القضايا الجارية:\n\n"
        for case_num in active[:10]:  # أول 10 قضايا
            case = data['cases'][case_num]
            msg += f"🔹 {case_num} - {case['client_name']}\n"
            msg += f"   📅 الجلسة: {case['next_hearing_date']}\n"
            msg += f"   📍 الحالة: {case['status']}\n\n"
    
    await query.edit_message_text(msg)

# ═══════════════════════════════════════════════════════
# البحث عن قضية
# ═══════════════════════════════════════════════════════

async def search_case_start(query, context):
    """بدء البحث"""
    context.user_data['action'] = 'search_case'
    await query.edit_message_text("🔍 أرسل اسم الموكل أو رقم القضية للبحث:")

async def handle_search(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """معالجة البحث"""
    data = load_data()
    results = []
    
    # البحث برقم القضية أو اسم الموكل
    for case_num, case in data['cases'].items():
        if text.lower() in case_num.lower() or text.lower() in case['client_name'].lower():
            results.append((case_num, case))
    
    if results:
        msg = f"🔍 نتائج البحث ({len(results)}):\n\n"
        for case_num, case in results[:10]:
            msg += f"📋 {case_num}\n"
            msg += f"👤 {case['client_name']}\n"
            msg += f"📅 {case['next_hearing_date']}\n"
            msg += f"📍 {case['status']}\n"
            msg += f"{'─'*25}\n"
        await update.message.reply_text(msg)
    else:
        await update.message.reply_text("❌ لم يتم العثور على نتائج!")
    
    context.user_data.clear()

# ═══════════════════════════════════════════════════════
# الإحصائيات
# ═══════════════════════════════════════════════════════

async def show_stats(query, context):
    """عرض الإحصائيات"""
    data = load_data()
    stats = data['stats']
    
    # حساب إحصائيات إضافية
    total_fees = 0
    total_paid = 0
    upcoming_hearings = 0
    
    today = datetime.now().date()
    
    for case in data['cases'].values():
        if 'fees' in case:
            total_fees += int(case['fees'].get('total', 0))
            total_paid += int(case['fees'].get('paid', 0))
        
        # عد الجلسات القادمة خلال 30 يوم
        try:
            hearing_date = datetime.strptime(case['next_hearing_date'], '%Y-%m-%d').date()
            if today <= hearing_date <= today + timedelta(days=30):
                upcoming_hearings += 1
        except:
            pass
    
    msg = f"📊 إحصائيات مكتب المحاماة\n"
    msg += f"{'='*30}\n\n"
    msg += f"📋 إجمالي القضايا: {stats['total_cases']}\n"
    msg += f"⚖️ القضايا الجارية: {stats['active_cases']}\n"
    msg += f"✅ القضايا المنتهية: {stats['closed_cases']}\n"
    msg += f"📅 جلسات قادمة (30 يوم): {upcoming_hearings}\n\n"
    msg += f"💰 الأتعاب:\n"
    msg += f"   • الإجمالي: {total_fees:,} جنيه\n"
    msg += f"   • المحصّل: {total_paid:,} جنيه\n"
    msg += f"   • المتبقي: {total_fees - total_paid:,} جنيه\n\n"
    msg += f"👥 عدد الموكلين: {len(data['clients'])}\n"
    
    await query.edit_message_text(msg)

# ═══════════════════════════════════════════════════════
# إرسال إشعار
# ═══════════════════════════════════════════════════════

async def send_notification_start(query, context):
    """بدء إرسال إشعار"""
    context.user_data['action'] = 'send_notification'
    context.user_data['step'] = 'select_target'
    
    keyboard = [
        [InlineKeyboardButton("📋 لقضية محددة", callback_data="notify_case")],
        [InlineKeyboardButton("👥 لجميع الموكلين", callback_data="notify_all")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    await query.edit_message_text(
        "🔔 اختر نوع الإشعار:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def handle_notification(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """معالجة الإشعار"""
    step = context.user_data.get('step')
    
    if step == 'notify_case_number':
        data = load_data()
        if text not in data['cases']:
            await update.message.reply_text("❌ القضية غير موجودة!")
            context.user_data.clear()
            return
        
        context.user_data['target_case'] = text
        context.user_data['step'] = 'notify_message'
        await update.message.reply_text("📝 اكتب الإشعار المراد إرساله:")
    
    elif step == 'notify_message':
        case_number = context.user_data.get('target_case')
        data = load_data()
        
        if case_number:
            # إرسال لقضية محددة
            case = data['cases'][case_number]
            if case.get('client_telegram_id'):
                try:
                    await context.bot.send_message(
                        chat_id=case['client_telegram_id'],
                        text=f"🔔 إشعار من مكتب المحاماة\n\n{text}"
                    )
                    await update.message.reply_text("✅ تم إرسال الإشعار!")
                except:
                    await update.message.reply_text("❌ فشل إرسال الإشعار!")
            else:
                await update.message.reply_text("❌ القضية غير مفعلة!")
        else:
            # إرسال لجميع الموكلين
            success_count = 0
            for client_id in data['clients'].keys():
                try:
                    await context.bot.send_message(
                        chat_id=int(client_id),
                        text=f"🔔 إشعار عام\n\n{text}"
                    )
                    success_count += 1
                except:
                    pass
            
            await update.message.reply_text(f"✅ تم إرسال الإشعار لـ {success_count} موكل!")
        
        context.user_data.clear()
    
    elif step == 'notify_all_message':
        data = load_data()
        success_count = 0
        
        for client_id in data['clients'].keys():
            try:
                await context.bot.send_message(
                    chat_id=int(client_id),
                    text=f"🔔 إشعار عام من مكتب المحاماة\n\n{text}"
                )
                success_count += 1
            except:
                pass
        
        await update.message.reply_text(f"✅ تم إرسال الإشعار لـ {success_count} موكل!")
        context.user_data.clear()

# ═══════════════════════════════════════════════════════
# الأسئلة الشائعة
# ═══════════════════════════════════════════════════════

async def view_faq(query, context):
    """عرض الأسئلة الشائعة"""
    data = load_data()
    faq = data.get('faq', {})
    
    if not faq:
        await query.edit_message_text("❓ لا توجد أسئلة شائعة حالياً.")
        return
    
    msg = "❓ الأسئلة الشائعة:\n\n"
    for i, (question, answer) in enumerate(faq.items(), 1):
        msg += f"{i}. {question}\n"
        msg += f"   💡 {answer}\n\n"
    
    await query.edit_message_text(msg)

async def manage_faq_start(query, context):
    """إدارة الأسئلة الشائعة"""
    keyboard = [
        [InlineKeyboardButton("➕ إضافة سؤال", callback_data="add_faq")],
        [InlineKeyboardButton("📋 عرض الأسئلة", callback_data="view_all_faq")],
        [InlineKeyboardButton("❌ حذف سؤال", callback_data="delete_faq")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    await query.edit_message_text(
        "❓ إدارة الأسئلة الشائعة:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ═══════════════════════════════════════════════════════
# حجز موعد
# ═══════════════════════════════════════════════════════

async def book_appointment_start(query, context):
    """بدء حجز موعد"""
    context.user_data['action'] = 'book_appointment'
    await query.edit_message_text(
        "📅 لحجز موعد استشارة:\n\n"
        "أرسل التاريخ المطلوب (مثال: 2026-03-15)\n"
        "أو اكتب 'أقرب موعد متاح'"
    )

async def handle_appointment(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str):
    """معالجة حجز الموعد"""
    user_id = update.effective_user.id
    user_name = update.effective_user.first_name
    
    # إرسال طلب الحجز للأدمن
    try:
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=f"📅 طلب حجز موعد جديد\n\n"
                 f"👤 من: {user_name} (ID: {user_id})\n"
                 f"📆 التاريخ المطلوب: {text}\n\n"
                 f"للتواصل: @{update.effective_user.username or 'غير متاح'}"
        )
        await update.message.reply_text(
            "✅ تم إرسال طلبك!\n\n"
            "سيتم التواصل معك قريباً لتأكيد الموعد."
        )
    except:
        await update.message.reply_text("❌ حدث خطأ! حاول مرة أخرى.")
    
    context.user_data.clear()

# ═══════════════════════════════════════════════════════
# إدارة الأتعاب
# ═══════════════════════════════════════════════════════

async def manage_fees_start(query, context):
    """إدارة الأتعاب"""
    keyboard = [
        [InlineKeyboardButton("💵 تسجيل دفعة", callback_data="record_payment")],
        [InlineKeyboardButton("📊 تقرير الأتعاب", callback_data="fees_report")],
        [InlineKeyboardButton("🔙 رجوع", callback_data="back_to_main")]
    ]
    await query.edit_message_text(
        "💰 إدارة الأتعاب:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def fees_report(query, context):
    """تقرير الأتعاب"""
    data = load_data()
    
    total_fees = 0
    total_paid = 0
    pending_cases = []
    
    for case_num, case in data['cases'].items():
        if 'fees' in case:
            total = int(case['fees'].get('total', 0))
            paid = int(case['fees'].get('paid', 0))
            remaining = total - paid
            
            total_fees += total
            total_paid += paid
            
            if remaining > 0:
                pending_cases.append((case_num, case['client_name'], remaining))
    
    msg = f"💰 تقرير الأتعاب الشامل\n"
    msg += f"{'='*30}\n\n"
    msg += f"📊 الإجمالي: {total_fees:,} جنيه\n"
    msg += f"✅ المحصّل: {total_paid:,} جنيه ({(total_paid/total_fees*100):.1f}%)\n"
    msg += f"⏳ المتبقي: {total_fees - total_paid:,} جنيه\n\n"
    
    if pending_cases:
        msg += f"📋 قضايا بها مستحقات:\n\n"
        for case_num, client, remaining in sorted(pending_cases, key=lambda x: x[2], reverse=True)[:10]:
            msg += f"• {case_num} - {client}\n"
            msg += f"  المتبقي: {remaining:,} جنيه\n\n"
    
    await query.edit_message_text(msg)

# ═══════════════════════════════════════════════════════
# أرشفة القضايا
# ═══════════════════════════════════════════════════════

async def archive_cases(query, context):
    """أرشفة القضايا المنتهية"""
    data = load_data()
    
    closed_cases = [c for c, info in data['cases'].items() if info['status'] == 'منتهية']
    
    if not closed_cases:
        await query.edit_message_text("✅ لا توجد قضايا منتهية للأرشفة.")
        return
    
    # إنشاء ملف الأرشيف
    archive_data = {case: data['cases'][case] for case in closed_cases}
    
    archive_file = f"archive_{datetime.now().strftime('%Y%m%d')}.json"
    with open(archive_file, 'w', encoding='utf-8') as f:
        json.dump(archive_data, f, ensure_ascii=False, indent=2)
    
    msg = f"📁 تم أرشفة {len(closed_cases)} قضية منتهية\n\n"
    msg += f"📄 الملف: {archive_file}\n\n"
    msg += "هل تريد حذف القضايا المؤرشفة من النظام؟\n"
    msg += "(سيتم الاحتفاظ بنسخة في ملف الأرشيف)"
    
    keyboard = [
        [InlineKeyboardButton("✅ نعم، احذفها", callback_data="confirm_archive_delete")],
        [InlineKeyboardButton("❌ لا، احتفظ بها", callback_data="back_to_main")]
    ]
    
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard))

# ═══════════════════════════════════════════════════════
# معالج الأزرار
# ═══════════════════════════════════════════════════════

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج جميع الأزرار"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data_key = query.data
    
    # أزرار الأدمن
    if user_id == ADMIN_ID:
        if data_key == "add_case":
            await add_case_start(query, context)
        elif data_key == "update_case_menu":
            await update_case_menu_start(query, context)
        elif data_key == "list_all_cases":
            await list_all_cases(query, context)
        elif data_key == "search_case":
            await search_case_start(query, context)
        elif data_key == "send_notification":
            await send_notification_start(query, context)
        elif data_key == "show_stats":
            await show_stats(query, context)
        elif data_key == "manage_faq":
            await manage_faq_start(query, context)
        elif data_key == "manage_fees":
            await manage_fees_start(query, context)
        elif data_key == "fees_report":
            await fees_report(query, context)
        elif data_key == "archive_cases":
            await archive_cases(query, context)
        elif data_key == "back_to_main":
            await query.edit_message_text(
                "لوحة التحكم:",
                reply_markup=get_admin_menu()
            )
        
        # خيارات التحديث
        elif data_key == "update_hearing_date":
            context.user_data['step'] = 'update_hearing_date'
            await query.edit_message_text("📅 أرسل تاريخ الجلسة الجديد (مثال: 2026-03-15):")
        elif data_key == "update_status":
            await query.edit_message_text("📍 اختر الحالة الجديدة:", reply_markup=get_case_status_options())
        elif data_key == "update_client_name":
            context.user_data['step'] = 'update_client_name'
            await query.edit_message_text("👤 أرسل الاسم الجديد:")
        elif data_key == "add_update":
            context.user_data['step'] = 'add_update'
            await query.edit_message_text("📝 اكتب التحديث الجديد:")
        
        # حالات القضية
        elif data_key.startswith("status_"):
            status_map = {
                "status_active": "جارية",
                "status_postponed": "مؤجلة",
                "status_closed": "منتهية",
                "status_review": "قيد المراجعة"
            }
            status = status_map.get(data_key)
            if status:
                case_number = context.user_data.get('selected_case')
                if case_number:
                    data = load_data()
                    data['cases'][case_number]['status'] = status
                    data['cases'][case_number]['updates'].append({
                        'date': datetime.now().strftime("%Y-%m-%d %H:%M"),
                        'text': f"تم تغيير الحالة إلى: {status}"
                    })
                    update_stats(data)
                    save_data(data)
                    
                    # إرسال إشعار للموكل
                    if data['cases'][case_number].get('client_telegram_id'):
                        try:
                            await context.bot.send_message(
                                chat_id=data['cases'][case_number]['client_telegram_id'],
                                text=f"🔔 تحديث في القضية رقم {case_number}\n\n"
                                     f"📍 الحالة الجديدة: {status}"
                            )
                        except:
                            pass
                    
                    await query.edit_message_text("✅ تم تحديث الحالة وإرسال إشعار للموكل!")
                    context.user_data.clear()
        
        # إرسال إشعارات
        elif data_key == "notify_case":
            context.user_data['step'] = 'notify_case_number'
            await query.edit_message_text("📋 أرسل رقم القضية:")
        elif data_key == "notify_all":
            context.user_data['step'] = 'notify_all_message'
            await query.edit_message_text("📝 اكتب الإشعار المراد إرساله لجميع الموكلين:")
    
    # أزرار الموكل
    else:
        if data_key == "check_case":
            await check_case_start(query, context)
        elif data_key == "activate_case":
            await activate_case_start(query, context)
        elif data_key == "book_appointment":
            await book_appointment_start(query, context)
        elif data_key == "view_faq":
            await view_faq(query, context)
        elif data_key == "contact_us":
            await query.edit_message_text(
                "📞 للتواصل معنا:\n\n"
                "📧 البريد: info@lawoffice.com\n"
                "📱 الهاتف: +20 123 456 7890\n"
                "📍 العنوان: القاهرة، مصر\n\n"
                "أو يمكنك حجز موعد استشارة من القائمة الرئيسية."
            )

# ═══════════════════════════════════════════════════════
# معالج الرسائل النصية
# ═══════════════════════════════════════════════════════

async def message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج جميع الرسائل النصية"""
    text = update.message.text
    action = context.user_data.get('action')
    
    if action == 'add_case':
        await handle_add_case(update, context, text)
    elif action == 'activate_case':
        await handle_activation(update, context, text)
    elif action == 'check_case':
        await handle_check_case(update, context, text)
    elif action == 'update_case':
        await handle_update_case(update, context, text)
    elif action == 'search_case':
        await handle_search(update, context, text)
    elif action == 'send_notification':
        await handle_notification(update, context, text)
    elif action == 'book_appointment':
        await handle_appointment(update, context, text)

# ═══════════════════════════════════════════════════════
# الإشعارات التلقائية
# ═══════════════════════════════════════════════════════

async def send_auto_reminders(app):
    """إرسال تذكيرات تلقائية"""
    data = load_data()
    today = datetime.now().date()
    
    for case_num, case in data['cases'].items():
        if not case.get('client_telegram_id') or case['status'] == 'منتهية':
            continue
        
        try:
            hearing_date = datetime.strptime(case['next_hearing_date'], '%Y-%m-%d').date()
            days_until = (hearing_date - today).days
            
            # تذكير قبل 3 أيام
            if days_until == 3:
                await app.bot.send_message(
                    chat_id=case['client_telegram_id'],
                    text=f"⏰ تذكير: لديك جلسة بعد 3 أيام\n\n"
                         f"📋 القضية: {case_num}\n"
                         f"📅 التاريخ: {case['next_hearing_date']}\n"
                         f"🕐 الوقت: {case.get('hearing_time', 'غير محدد')}\n"
                         f"📍 المكان: {case.get('hearing_location', 'غير محدد')}"
                )
            
            # تذكير قبل يوم
            elif days_until == 1:
                await app.bot.send_message(
                    chat_id=case['client_telegram_id'],
                    text=f"⚠️ تذكير: جلستك غداً!\n\n"
                         f"📋 القضية: {case_num}\n"
                         f"📅 التاريخ: {case['next_hearing_date']}\n"
                         f"🕐 الوقت: {case.get('hearing_time', 'غير محدد')}\n"
                         f"📍 المكان: {case.get('hearing_location', 'غير محدد')}\n\n"
                         f"⚠️ تأكد من إحضار جميع المستندات المطلوبة"
                )
            
            # تذكير يوم الجلسة
            elif days_until == 0:
                await app.bot.send_message(
                    chat_id=case['client_telegram_id'],
                    text=f"🔔 تذكير: جلستك اليوم!\n\n"
                         f"📋 القضية: {case_num}\n"
                         f"🕐 الوقت: {case.get('hearing_time', 'غير محدد')}\n"
                         f"📍 المكان: {case.get('hearing_location', 'غير محدد')}\n\n"
                         f"⏰ لا تتأخر!"
                )
        except:
            pass

# ═══════════════════════════════════════════════════════
# التشغيل الرئيسي
# ═══════════════════════════════════════════════════════

def main():
    """تشغيل البوت"""
    print("🚀 جاري تشغيل البوت...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    # إضافة المعالجات
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, message_handler))
    
    # جدولة الإشعارات التلقائية (كل يوم الساعة 9 صباحاً)
    SCHEDULER.add_job(
        send_auto_reminders,
        'cron',
        hour=9,
        minute=0,
        args=[app]
    )
    SCHEDULER.start()
    
    print("✅ البوت شغال الآن!")
    print(f"🔗 الرابط: https://t.me/qadaya_bot")
    print("⏰ الإشعارات التلقائية مفعلة")
    
    app.run_polling()

if __name__ == '__main__':
    main()
