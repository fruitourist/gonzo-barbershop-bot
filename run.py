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

async def adaptive_send_message(obj_hand: object, text: str, reply_markup: object = None):

	if type(obj_hand) is types.CallbackQuery:
		await bot.answer_callback_query(callback_query_id=obj_hand.id)

	if type(obj_hand) is types.CallbackQuery:
		await bot.delete_message(chat_id=obj_hand.from_user.id,
			message_id=obj_hand.message.message_id)

	await bot.send_message(chat_id=obj_hand.from_user.id,
		text=text,
		reply_markup=reply_markup)


async def get_slctd_services() -> list:

	services = list()
	for service in db_cur.execute('SELECT * FROM services').fetchall():
		if int(service[0]) in cookie['slctd_services_id']:
			services.append(service)


	return services


async def get_total_slctd_services() -> int:

	total = 0
	for service in await get_slctd_services():
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


async def get_text_check_booking() -> str:

	text = "Ты выбрал:\n\n"

	for service in await get_slctd_services():
		text += "— <b>{}</b> {} {} ₽\n".format(service[1], "☑️" if not cookie['slctd_time'] else "✅",  service[2])

	text += "\nВсего: {} ₽\n".format(await get_total_slctd_services())

	if cookie['slctd_date']:
		text += "\nДата: <b>{}</b>\n".format(await support.get_style_date(cookie['slctd_date']))

	if cookie['slctd_time']:
		text += "Время: <b>{}</b>\n".format(await support.get_style_time(cookie['slctd_time']))


	return text


async def clear_cookie():

	cookie['slctd_services_id'].clear()
	cookie['slctd_date'] = None
	cookie['slctd_time'] = None


# session funcs

@dp.message_handler(commands=['start', 'menu'])
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'menu')
async def menu(obj_hand: object):

	inline_kbrd = types.InlineKeyboardMarkup()
	inline_kbrd.add(types.InlineKeyboardButton(text="Услуги", callback_data='services'))


	text = "Главная"

	await adaptive_send_message(obj_hand=obj_hand, text=text, reply_markup=inline_kbrd)


@dp.message_handler(commands=['services'])
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'services')
async def services(obj_hand: object):

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

	await adaptive_send_message(obj_hand=obj_hand, text=text, reply_markup=inline_kbrd)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('booking_services_slct'))
async def booking_services_slct(callback_query: types.CallbackQuery):

	global cookie

	service_id = int(callback_query.data.split()[-1])
	if service_id not in cookie['slctd_services_id']:
		cookie['slctd_services_id'].append(service_id)
	else:
		cookie['slctd_services_id'].remove(service_id)


	await services(obj_hand=callback_query)


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'booking_dates')
async def booking_dates(callback_query: types.CallbackQuery):

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
	

	text = await get_text_check_booking()
	text += "\nВыбор <i>даты</i>"

	await adaptive_send_message(obj_hand=callback_query, text=text, reply_markup=inline_kbrd)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('booking_dates_slct'))
async def booking_dates_slct(callback_query: types.CallbackQuery):

	global cookie

	cookie['slctd_date'] = datetime.date.fromisoformat(callback_query.data.split()[-1])


	await bot.answer_callback_query(callback_query_id=callback_query.id)

	await booking_times(callback_query=callback_query)


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'booking_times')
async def booking_times(callback_query: types.CallbackQuery):
	
	global cookie

	if cookie['slctd_time']:
		cookie['slctd_time'] = None


	inline_kbrd = types.InlineKeyboardMarkup()

	times = await get_free_times_booking(date=cookie['slctd_date'])
	inline_kbrd.add(*[types.InlineKeyboardButton(text=await support.get_style_time(time),
		callback_data='booking_times_slct {}'.format(time.isoformat())) for time in times])

	inline_kbrd.add(types.InlineKeyboardButton(text="« Выбор даты", callback_data='booking_dates'))


	text = await get_text_check_booking()
	text += "\nВыбор <i>времени</i>"

	await adaptive_send_message(obj_hand=callback_query, text=text, reply_markup=inline_kbrd)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('booking_times_slct'))
async def booking_times_slct(callback_query: types.CallbackQuery):

	global cookie

	cookie['slctd_time'] = datetime.time.fromisoformat(callback_query.data.split()[-1])


	max_check_id = db_cur.execute('SELECT MAX(check_id) FROM appoints').fetchone()[0]
	check_id = max_check_id + 1 if max_check_id != None else 0

	for service in await get_slctd_services():
		db_cur.execute('INSERT INTO appoints VALUES (?, ?, ?, ?, ?)',
			(callback_query.from_user.id, service[0], cookie['slctd_date'].isoformat(), cookie['slctd_time'].isoformat(), check_id))
	db_con.commit()


	text = await get_text_check_booking()
	text += "\nЧек: {}".format(check_id)

	await bot.send_message(chat_id=callback_query.from_user.id,
		text=text)

	await clear_cookie()

	await menu(obj_hand=callback_query)


if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True)