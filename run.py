from aiogram import Bot, Dispatcher, executor, types
import logging

import secret, support #from this dir

import sqlite3, datetime


bot = Bot(token=secret.API_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

# database must include:
## services -> (id INT, title VARCHAR, price INT)

db_con = sqlite3.connect(secret.DATABASE_PATH)
db_cur = db_con.cursor()


# session support vars

## organization data

### dates

QTY_NEXT_DATES_BOOKING = 7 #need database generate

### times

BEGIN_HOUR_TIME = 11 #need database generate
END_HOUR_TIME = 21 #need database generate

## users data

cookie = {'slctd_services_id': list(), 'slctd_date': None, 'slctd_time': None} #need organization in database


# session support funcs

async def get_services(id_list: list = None) -> list:

	if not id_list:
		return [service for service in db_cur.execute('SELECT * FROM services').fetchall()]

	else:
		services_by_id_list = list()
		for id in id_list:
			services_by_id_list.append(db_cur.execute('SELECT * FROM services WHERE id = ? LIMIT 1', (id,)).fetchone())
		
		return services_by_id_list


async def get_slctd_services_cookie() -> list:

	return [service for service in await get_services() if int(service[0]) in cookie['slctd_services_id']]


async def get_total_slctd_services(slctd_services: list = None) -> int:

	
	if not slctd_services:
		slctd_services = await get_slctd_services_cookie()


	total = 0
	for service in slctd_services:
		total += int(service[2])


	return total


async def get_next_dates_booking() -> list:

	next_dates = list()

	date_today = datetime.date.today()
	for i in range(QTY_NEXT_DATES_BOOKING):
		next_date = date_today + datetime.timedelta(days=i)

		if await get_free_times_booking(date=next_date):
			next_dates.append(next_date)


	return next_dates


async def get_free_times_booking(date: object) -> list:

	times = list()

	if date == datetime.date.today():
		now_hour_time = datetime.datetime.now().time().hour

		begin_hour_time = now_hour_time + 1 if now_hour_time >= BEGIN_HOUR_TIME - 1 else BEGIN_HOUR_TIME
	else:
		begin_hour_time = BEGIN_HOUR_TIME

	for hour in range(begin_hour_time, END_HOUR_TIME):
		time = datetime.time(hour)

		if not db_cur.execute('SELECT * FROM appoints WHERE (date = ? AND time = ?) LIMIT 1',
			(date.isoformat(),time.isoformat())).fetchone():
			times.append(time)


	return times


async def get_text_check(slctd_services: list = None,
	slctd_date: object = None,
	slctd_time: object = None,
	check_id: int = None) -> str:

	if not slctd_date:
		slctd_date = cookie['slctd_date']

	if not slctd_time:
		slctd_time = cookie['slctd_time']
	
	if not slctd_services:
		slctd_services = await get_slctd_services_cookie()


	text = "Ты выбрал:\n\n"

	for service in slctd_services:
		text += "— <b>{}</b> {} {} ₽\n".format(service[1], "☑️" if not slctd_time else "✅",  service[2])

	text += "\nВсего: {} ₽\n".format(await get_total_slctd_services(slctd_services=slctd_services))

	if slctd_date:
		text += "\nДата: <b>{}</b>\n".format(await support.get_style_date(date=slctd_date))

	if slctd_time:
		text += "Время: <b>{}</b>\n\nЧек: {}".format(await support.get_style_time(time=slctd_time), check_id)


	return text


async def clear_cookie():

	cookie['slctd_services_id'].clear()
	cookie['slctd_date'] = None
	cookie['slctd_time'] = None


async def get_active_appoints(user_id: int) -> list:

	active_appoints = list()

	draft_appoint, draft_check_id, count = dict(), None, 0
	for appoint in db_cur.execute('SELECT service_id, date, time, check_id FROM appoints WHERE user_id = ? AND date >= DATE() ORDER BY date, time',
		(user_id,)).fetchall():
			count += 1

			if appoint[3] != draft_check_id:

				if draft_check_id:
					active_appoints.append(draft_appoint)
					draft_appoint = dict()

				draft_check_id = appoint[3]
				
				draft_appoint['services_id'] = [appoint[0]]
				draft_appoint['date'] = datetime.date.fromisoformat(appoint[1])
				draft_appoint['time'] = datetime.time.fromisoformat(appoint[2])
				draft_appoint['check_id'] = appoint[3]
			else:
				draft_appoint['services_id'].append(appoint[0])

	if count:
		active_appoints.append(draft_appoint)


	return active_appoints


# session funcs

@dp.message_handler(commands=['start', 'menu'])
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'menu')
async def menu(obj_hand: object, delete_init_message: bool = True):

	if type(obj_hand) is types.CallbackQuery:
		await bot.answer_callback_query(callback_query_id=obj_hand.id)

		if delete_init_message:
			await bot.delete_message(chat_id=obj_hand.from_user.id,
				message_id=obj_hand.message.message_id)


	inline_kbrd = types.InlineKeyboardMarkup()
	inline_kbrd.add(types.InlineKeyboardButton(text="Услуги", callback_data='services'))
	inline_kbrd.add(types.InlineKeyboardButton(text="Инфо", callback_data='info'))
	inline_kbrd.add(types.InlineKeyboardButton(text="Активные записи", callback_data='active'))

	text = "Главная"


	await bot.send_message(chat_id=obj_hand.from_user.id,
		text=text,
		reply_markup=inline_kbrd)


@dp.message_handler(commands=['services'])
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'services')
async def services(obj_hand: object, answer_callback_query: bool = True):

	if type(obj_hand) is types.CallbackQuery:
		await bot.delete_message(chat_id=obj_hand.from_user.id,
			message_id=obj_hand.message.message_id)

		if answer_callback_query:
			await bot.answer_callback_query(callback_query_id=obj_hand.id)


	inline_kbrd = types.InlineKeyboardMarkup()

	for service in db_cur.execute('SELECT * FROM services').fetchall():
		inline_kbrd.add(types.InlineKeyboardButton(text="{} {} {} ₽".format(service[1],
				"·" if int(service[0]) not in cookie['slctd_services_id'] else "☑️",
				service[2]),
			callback_data='booking_services_slct {}'.format(service[0])))

	if cookie['slctd_services_id']:
		inline_kbrd.add(types.InlineKeyboardButton(text="Записаться ({} ₽) »".format(await get_total_slctd_services()),
			callback_data='booking_dates'))

	inline_kbrd.add(types.InlineKeyboardButton(text="« Меню", callback_data='menu'))

	text = "Услуги"


	await bot.send_message(chat_id=obj_hand.from_user.id,
		text=text,
		reply_markup=inline_kbrd)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('booking_services_slct'))
async def booking_services_slct(callback_query: types.CallbackQuery):

	await bot.answer_callback_query(callback_query_id=callback_query.id)


	global cookie

	service_id = int(callback_query.data.split()[-1])
	if service_id not in cookie['slctd_services_id']:
		cookie['slctd_services_id'].append(service_id)
	else:
		cookie['slctd_services_id'].remove(service_id)


	await services(obj_hand=callback_query, answer_callback_query=False)


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'booking_dates')
async def booking_dates(callback_query: types.CallbackQuery):

	await bot.answer_callback_query(callback_query_id=callback_query.id)
	await bot.delete_message(chat_id=callback_query.from_user.id,
		message_id=callback_query.message.message_id)


	global cookie

	if cookie['slctd_date']:
		cookie['slctd_date'] = None


	inline_kbrd = types.InlineKeyboardMarkup()

	next_dates = await get_next_dates_booking()

	count_soon_days = 0
	for i in range(len(next_dates)):
		if (next_dates[i] - datetime.date.today()).days < 3:
			count_soon_days += 1

			inline_kbrd.add(types.InlineKeyboardButton(text=await support.get_style_date(next_dates[i]),
				callback_data='booking_dates_slct {}'.format(next_dates[i].isoformat())))
	
	inline_kbrd.add(*[types.InlineKeyboardButton(text=await support.get_style_date(next_dates[i]),
		callback_data='booking_dates_slct {}'.format(next_dates[i].isoformat())) for i in range(count_soon_days,len(next_dates))])

	inline_kbrd.add(types.InlineKeyboardButton(text="« Услуги", callback_data='services'))

	text = await get_text_check()
	text += "\nВыбор <i>даты</i>"


	await bot.send_message(chat_id=callback_query.from_user.id,
		text=text,
		reply_markup=inline_kbrd)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('booking_dates_slct'))
async def booking_dates_slct(callback_query: types.CallbackQuery):

	await bot.answer_callback_query(callback_query_id=callback_query.id)


	global cookie

	cookie['slctd_date'] = datetime.date.fromisoformat(callback_query.data.split()[-1])


	await booking_times(callback_query=callback_query, answer_callback_query=False)


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'booking_times')
async def booking_times(callback_query: types.CallbackQuery, answer_callback_query: bool = True):

	if answer_callback_query:
		await bot.answer_callback_query(callback_query_id=callback_query.id)

	await bot.delete_message(chat_id=callback_query.from_user.id,
		message_id=callback_query.message.message_id)
	

	global cookie

	if cookie['slctd_time']:
		cookie['slctd_time'] = None


	inline_kbrd = types.InlineKeyboardMarkup()

	times = await get_free_times_booking(date=cookie['slctd_date'])
	inline_kbrd.add(*[types.InlineKeyboardButton(text=await support.get_style_time(time),
		callback_data='booking_times_slct {}'.format(time.isoformat())) for time in times])

	inline_kbrd.add(types.InlineKeyboardButton(text="« Выбор даты", callback_data='booking_dates'))

	text = await get_text_check()
	text += "\nВыбор <i>времени</i>"


	await bot.send_message(chat_id=callback_query.from_user.id,
		text=text,
		reply_markup=inline_kbrd)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('booking_times_slct'))
async def booking_times_slct(callback_query: types.CallbackQuery):

	await bot.answer_callback_query(callback_query_id=callback_query.id)
	await bot.delete_message(chat_id=callback_query.from_user.id,
		message_id=callback_query.message.message_id)


	global cookie

	cookie['slctd_time'] = datetime.time.fromisoformat(callback_query.data.split()[-1])

	max_check_id = db_cur.execute('SELECT MAX(check_id) FROM appoints').fetchone()[0]
	check_id = max_check_id + 1 if max_check_id != None else 0

	for service in await get_slctd_services_cookie():
		db_cur.execute('INSERT INTO appoints VALUES (?, ?, ?, ?, ?)',
			(callback_query.from_user.id, service[0], cookie['slctd_date'].isoformat(), cookie['slctd_time'].isoformat(), check_id))
	db_con.commit()


	text = await get_text_check(check_id=check_id)


	await bot.send_message(chat_id=callback_query.from_user.id,
		text=text)


	await clear_cookie()

	await menu(obj_hand=callback_query, delete_init_message=False)


@dp.message_handler(commands=['info'])
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'info')
async def info(obj_hand: object):

	if type(obj_hand) is types.CallbackQuery:
		await bot.answer_callback_query(callback_query_id=obj_hand.id)
		await bot.delete_message(chat_id=obj_hand.from_user.id,
			message_id=obj_hand.message.message_id)


	inline_kbrd = types.InlineKeyboardMarkup()
	inline_kbrd.add(types.InlineKeyboardButton(text="« Меню", callback_data='menu'))

	text = "Адрес: <a href='https://yandex.ru/maps/-/CCUNJ-XnoB'>ул. имени В.И. Оржевского, 5, Саратов</a>\n"
	text += "Контакты: <a href='tel:+7 (8452) 49-55-40'>+7 (8452) 49-55-40</a>\n"
	text += "Время работы: с 11:00 до 21:00"


	await bot.send_message(chat_id=obj_hand.from_user.id,
		text=text,
		disable_web_page_preview=True,
		reply_markup=inline_kbrd)


@dp.message_handler(commands=['active'])
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'active')
async def active(obj_hand: object, active_appoint_i: int = 0, delete_init_message: bool = True):

	if type(obj_hand) is types.CallbackQuery:
		await bot.answer_callback_query(callback_query_id=obj_hand.id)

		if delete_init_message:
			await bot.delete_message(chat_id=obj_hand.from_user.id,
				message_id=obj_hand.message.message_id)


	active_appoints = await get_active_appoints(user_id=obj_hand.from_user.id)


	inline_kbrd = types.InlineKeyboardMarkup()


	if len(active_appoints) == 0:

		inline_kbrd.add(types.InlineKeyboardButton(text="Меню", callback_data='menu'))

		await bot.send_message(chat_id=obj_hand.from_user.id,
			text="У вас нет активных записей",
			reply_markup=inline_kbrd)

		return


	if active_appoint_i > 0:
		inline_kbrd.insert(types.InlineKeyboardButton(text="« {}".format(await support.get_style_date(date=active_appoints[active_appoint_i-1]['date'])),
			callback_data='active_slct prev {}'.format(active_appoint_i)))
	if active_appoint_i < len(active_appoints) - 1:
		inline_kbrd.insert(types.InlineKeyboardButton(text="{} »".format(await support.get_style_date(date=active_appoints[active_appoint_i+1]['date'])),
			callback_data='active_slct next {}'.format(active_appoint_i)))

	inline_kbrd.add(types.InlineKeyboardButton(text="« Меню", callback_data='menu'))


	await bot.send_message(chat_id=obj_hand.from_user.id,
		text=await get_text_check(slctd_services=await get_services(id_list=active_appoints[active_appoint_i]['services_id']),
			slctd_date=active_appoints[active_appoint_i]['date'],
			slctd_time=active_appoints[active_appoint_i]['time'],
			check_id=active_appoints[active_appoint_i]['check_id']),
		reply_markup=inline_kbrd)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('active_slct'))
async def active_slct(callback_query: types.CallbackQuery):

	await bot.answer_callback_query(callback_query_id=callback_query.id)
	await bot.delete_message(chat_id=callback_query.from_user.id,
		message_id=callback_query.message.message_id)


	data = callback_query.data.split()
	if data[1] == 'prev':
		active_appoint_i = int(data[2])-1
	else:
		active_appoint_i = int(data[2])+1
	
	await active(obj_hand=callback_query, active_appoint_i=active_appoint_i, delete_init_message=False)


if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True)