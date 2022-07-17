from aiogram import Bot, Dispatcher, executor, types
import logging

import secret, support #from this dir

import sqlite3, datetime, json


bot = Bot(secret.API_TOKEN, parse_mode='HTML')
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

# database must include:
## services -> (id INT, title VARCHAR, price INT)
## appoints -> (user_id INT, service_id INT, date DATE, time TIME, check_id INT)

db_con = sqlite3.connect(secret.DATABASE_PATH)
db_cur = db_con.cursor()


# session support vars

## users data

cookie = dict() #need organize with webhook

## organization info

with open('data/organization_info.json') as file:
	org_info = json.load(file)

QTY_NEXT_DATES_BOOKING = org_info['booking']['qty_next_dates_booking']
BEGIN_TIME_HOUR = org_info['shedule']['begin_time_hour']
END_TIME_HOUR = org_info['shedule']['end_time_hour']

## organization texts

text_entity_services = {'text': "Услуги", 'icon': "✂️"}
text_entity_address = {'text': "Адрес", 'icon': "📍"}
text_entity_active = {'text': "Активные записи", 'icon': "✅"}


# session support funcs

async def get_services(ids: list = None) -> list:

	services = list()

	if not ids:
		services.extend(db_cur.execute('SELECT * FROM services').fetchall())
	else:
		for id in ids:
			services.append(db_cur.execute('SELECT * FROM services WHERE id = ? LIMIT 1', (id,)).fetchone())

	for i in range(len(services)):
		services[i] = {'id': services[i][0], 'title': services[i][1], 'price': services[i][2]}

	return services


async def get_slctd_services_cookie(chat_id: int) -> list:

	return [service for service in await get_services() if int(service['id']) in cookie[chat_id]['slctd_services_id']]


async def get_total_slctd_services(chat_id: int, slctd_services: list = None) -> int:
	
	if not slctd_services:
		slctd_services = await get_slctd_services_cookie(chat_id=chat_id)


	total = 0
	for service in slctd_services:
		total += int(service['price'])

	return total


async def get_next_dates_booking() -> list:

	next_dates = list()

	date_today = datetime.date.today()
	for i in range(QTY_NEXT_DATES_BOOKING):
		next_date = date_today + datetime.timedelta(days=i)

		if await get_free_times_booking(date=next_date):
			next_dates.append(next_date)

	return next_dates


async def get_free_times_booking(date: datetime.date) -> list:

	times = list()

	if date == datetime.date.today():
		now_hour_time = datetime.datetime.now().hour

		begin_time_hour = now_hour_time + 1 if now_hour_time >= BEGIN_TIME_HOUR - 1 else BEGIN_TIME_HOUR
	else:
		begin_time_hour = BEGIN_TIME_HOUR

	for hour in range(begin_time_hour, END_TIME_HOUR):
		time = datetime.time(hour)

		if not db_cur.execute('SELECT * FROM appoints WHERE (date = ? AND time = ?) LIMIT 1',
			(date.isoformat(), time.isoformat())).fetchone():
			times.append(time)

	return times


async def get_text_check(chat_id: int, slctd_services: list = None, slctd_date: object = None, slctd_time: object = None, check_id: int = None) -> str:

	if not slctd_services:
		slctd_services = await get_slctd_services_cookie(chat_id=chat_id)

	if not slctd_date:
		slctd_date = cookie[chat_id]['slctd_date']

	if not slctd_time:
		slctd_time = cookie[chat_id]['slctd_time']


	text = "Ты выбрал:\n\n"

	for service in slctd_services:
		text += "— <b>{}</b> {} {} ₽\n".format(service['title'], "☑️" if not slctd_time else "✅",  service['price'])

	text += "\nВсего: {} ₽\n".format(await get_total_slctd_services(chat_id=chat_id, slctd_services=slctd_services))

	if slctd_date:
		text += "\nДата: <b>{}</b>\n".format(await support.get_style_date(date=slctd_date))

	if slctd_time:
		text += "Время: <b>{}</b>\n\nЧек: {}".format(await support.get_style_time(time=slctd_time), check_id)

	return text


async def get_active_appoints(user_id: int) -> list:

	active_appoints = list()

	draft_appoint = {'services_id': None, 'date': None, 'time': None, 'check_id': None}
	for appoint in db_cur.execute('SELECT service_id, date, time, check_id FROM appoints WHERE user_id = ? AND date >= DATE() ORDER BY date, time',
		(user_id,)).fetchall():

			if appoint[3] != draft_appoint['check_id']:

				if draft_appoint['check_id']:
					active_appoints.append(draft_appoint)
				
				draft_appoint['services_id'] = [appoint[0]]
				draft_appoint['date'] = datetime.date.fromisoformat(appoint[1])
				draft_appoint['time'] = datetime.time.fromisoformat(appoint[2])
				draft_appoint['check_id'] = appoint[3]
			else:
				draft_appoint['services_id'].append(appoint[0])

	if draft_appoint['check_id']:
		active_appoints.append(draft_appoint)

	return active_appoints


async def clear_cookie(chat_id: int):

	global cookie

	cookie[chat_id]['slctd_services_id'].clear()
	cookie[chat_id]['slctd_date'] = None
	cookie[chat_id]['slctd_time'] = None


# session funcs

@dp.message_handler(commands=['start', 'menu'])
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'menu')
async def menu(obj_hand: object, delete_init_message: bool = True):

	if type(obj_hand) is types.CallbackQuery:
		await bot.answer_callback_query(callback_query_id=obj_hand.id)

		if delete_init_message:
			await bot.delete_message(chat_id=obj_hand.from_user.id,
				message_id=obj_hand.message.message_id)

		chat_id = obj_hand.message.chat.id
	else:
		chat_id = obj_hand.chat.id


	if chat_id not in cookie:
		data = {'user_id': obj_hand.from_user.id, 'slctd_services_id': list(), 'slctd_date': None, 'slctd_time': None}
		if type(obj_hand) is types.Message:
			cookie[chat_id] = data
		else:
			cookie[chat_id] = data


	text_entity_active_here = text_entity_active
	text_entity_active_here['icon'] = "✅" if await get_active_appoints(user_id=obj_hand.from_user.id) else "☑️"

	inline_kbrd = types.InlineKeyboardMarkup()
	inline_kbrd.add(types.InlineKeyboardButton(text="{} {}".format(text_entity_services['text'], text_entity_services['icon']),
		callback_data='services'))
	inline_kbrd.add(types.InlineKeyboardButton(text="{} {}".format(text_entity_address['text'], text_entity_address['icon']),
		callback_data='address'))
	inline_kbrd.add(types.InlineKeyboardButton(text="{} {}".format(text_entity_active_here['text'], text_entity_active_here['icon']),
		callback_data='active'))

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

		chat_id = obj_hand.message.chat.id
	else:
		chat_id = obj_hand.chat.id


	inline_kbrd = types.InlineKeyboardMarkup()

	for service in await get_services():
		inline_kbrd.add(types.InlineKeyboardButton(text="{} {} {} ₽".format(service['title'],
				"·" if int(service['id']) not in cookie[chat_id]['slctd_services_id'] else "☑️",
				service['price']),
			callback_data='booking_services_slct {}'.format(service['id'])))

	if cookie[chat_id]['slctd_services_id']:
		inline_kbrd.add(types.InlineKeyboardButton(text="Записаться ({} ₽) »".format(await get_total_slctd_services(chat_id=chat_id)),
			callback_data='booking_dates'))

	inline_kbrd.add(types.InlineKeyboardButton(text="« Меню", callback_data='menu'))

	text = "Услуги"


	await bot.send_message(chat_id=obj_hand.from_user.id,
		text=text,
		reply_markup=inline_kbrd)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('booking_services_slct'))
async def booking_services_slct(callback_query: types.CallbackQuery):

	await bot.answer_callback_query(callback_query_id=callback_query.id)

	chat_id = callback_query.message.chat.id


	global cookie

	service_id = int(callback_query.data.split()[-1])
	if service_id not in cookie[chat_id]['slctd_services_id']:
		cookie[chat_id]['slctd_services_id'].append(service_id)
	else:
		cookie[chat_id]['slctd_services_id'].remove(service_id)


	await services(obj_hand=callback_query, answer_callback_query=False)


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'booking_dates')
async def booking_dates(callback_query: types.CallbackQuery):

	await bot.answer_callback_query(callback_query_id=callback_query.id)
	await bot.delete_message(chat_id=callback_query.from_user.id,
		message_id=callback_query.message.message_id)

	chat_id = callback_query.message.chat.id


	global cookie

	if cookie[chat_id]['slctd_date']:
		cookie[chat_id]['slctd_date'] = None


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

	text = await get_text_check(chat_id=chat_id) + "\nВыбор <i>даты</i>"


	await bot.send_message(chat_id=callback_query.from_user.id,
		text=text,
		reply_markup=inline_kbrd)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('booking_dates_slct'))
async def booking_dates_slct(callback_query: types.CallbackQuery):

	await bot.answer_callback_query(callback_query_id=callback_query.id)

	chat_id = callback_query.message.chat.id


	global cookie

	cookie[chat_id]['slctd_date'] = datetime.date.fromisoformat(callback_query.data.split()[-1])


	await booking_times(callback_query=callback_query, answer_callback_query=False)


@dp.callback_query_handler(lambda callback_query: callback_query.data == 'booking_times')
async def booking_times(callback_query: types.CallbackQuery, answer_callback_query: bool = True):

	if answer_callback_query:
		await bot.answer_callback_query(callback_query_id=callback_query.id)

	await bot.delete_message(chat_id=callback_query.from_user.id,
		message_id=callback_query.message.message_id)

	chat_id = callback_query.message.chat.id
	

	global cookie

	if cookie[chat_id]['slctd_time']:
		cookie[chat_id]['slctd_time'] = None


	inline_kbrd = types.InlineKeyboardMarkup()

	times = await get_free_times_booking(date=cookie[chat_id]['slctd_date'])
	inline_kbrd.add(*[types.InlineKeyboardButton(text=await support.get_style_time(time),
		callback_data='booking_times_slct {}'.format(time.isoformat())) for time in times])

	inline_kbrd.add(types.InlineKeyboardButton(text="« Выбор даты", callback_data='booking_dates'))

	text = await get_text_check(chat_id=chat_id) + "\nВыбор <i>времени</i>"


	await bot.send_message(chat_id=callback_query.from_user.id,
		text=text,
		reply_markup=inline_kbrd)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('booking_times_slct'))
async def booking_times_slct(callback_query: types.CallbackQuery):

	await bot.answer_callback_query(callback_query_id=callback_query.id)
	await bot.delete_message(chat_id=callback_query.from_user.id,
		message_id=callback_query.message.message_id)

	chat_id = callback_query.message.chat.id


	global cookie

	cookie[chat_id]['slctd_time'] = datetime.time.fromisoformat(callback_query.data.split()[-1])

	max_check_id = db_cur.execute('SELECT MAX(check_id) FROM appoints').fetchone()[0]
	check_id = max_check_id + 1 if max_check_id != None else 1

	for service in await get_slctd_services_cookie(chat_id=chat_id):
		db_cur.execute('INSERT INTO appoints VALUES (?, ?, ?, ?, ?)',
			(callback_query.from_user.id,
				service['id'],
				cookie[chat_id]['slctd_date'].isoformat(),
				cookie[chat_id]['slctd_time'].isoformat(),
				check_id))
	db_con.commit()

	text = await get_text_check(chat_id=chat_id, check_id=check_id)


	await bot.send_message(chat_id=callback_query.from_user.id,
		text=text)

	await clear_cookie(chat_id=chat_id)

	await menu(obj_hand=callback_query, delete_init_message=False)


@dp.message_handler(commands=['address'])
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'address')
async def address(obj_hand: object):

	if type(obj_hand) is types.CallbackQuery:
		await bot.answer_callback_query(callback_query_id=obj_hand.id)
		await bot.delete_message(chat_id=obj_hand.from_user.id,
			message_id=obj_hand.message.message_id)

	text = "{} Улица имени В.И. Оржевского, 5, Саратов".format(text_entity_address['icon'])

	await bot.send_message(chat_id=obj_hand.from_user.id,
		text=text)

	await bot.send_location(chat_id=obj_hand.from_user.id,
		latitude=51.605542,
		longitude=46.012642)


	await menu(obj_hand=obj_hand, delete_init_message=False)


@dp.message_handler(commands=['active'])
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'active')
async def active(obj_hand: object, i_active_appoint: int = 0, delete_init_message: bool = True):

	if type(obj_hand) is types.CallbackQuery:
		await bot.answer_callback_query(callback_query_id=obj_hand.id)

		if delete_init_message:
			await bot.delete_message(chat_id=obj_hand.from_user.id,
				message_id=obj_hand.message.message_id)

		chat_id = obj_hand.message.chat.id
	else:
		chat_id = obj_hand.chat.id


	active_appoints = await get_active_appoints(user_id=obj_hand.from_user.id)

	inline_kbrd = types.InlineKeyboardMarkup()

	if len(active_appoints) == 0:
		inline_kbrd.add(types.InlineKeyboardButton(text="« Меню", callback_data='menu'))

		await bot.send_message(chat_id=obj_hand.from_user.id,
			text="У тебя нет активных записей. Записывайся к нам через <b>{}</b> {}".format(text_entity_services['text'], text_entity_services['icon']),
			reply_markup=inline_kbrd)

		return None

	if i_active_appoint > 0:
		inline_kbrd.insert(types.InlineKeyboardButton(text="« {}".format(await support.get_style_date(date=active_appoints[i_active_appoint-1]['date'])),
			callback_data='active_slct prev {}'.format(i_active_appoint)))
	if i_active_appoint < len(active_appoints) - 1:
		inline_kbrd.insert(types.InlineKeyboardButton(text="{} »".format(await support.get_style_date(date=active_appoints[i_active_appoint+1]['date'])),
			callback_data='active_slct next {}'.format(i_active_appoint)))

	inline_kbrd.add(types.InlineKeyboardButton(text="« Меню", callback_data='menu'))


	await bot.send_message(chat_id=obj_hand.from_user.id,
		text=await get_text_check(chat_id=chat_id, slctd_services=await get_services(ids=active_appoints[i_active_appoint]['services_id']),
			slctd_date=active_appoints[i_active_appoint]['date'],
			slctd_time=active_appoints[i_active_appoint]['time'],
			check_id=active_appoints[i_active_appoint]['check_id']),
		reply_markup=inline_kbrd)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('active_slct'))
async def active_slct(callback_query: types.CallbackQuery):

	await bot.answer_callback_query(callback_query_id=callback_query.id)
	await bot.delete_message(chat_id=callback_query.from_user.id,
		message_id=callback_query.message.message_id)


	data = callback_query.data.split()
	if data[1] == 'prev':
		i_active_appoint = int(data[2])-1
	else:
		i_active_appoint = int(data[2])+1
	

	await active(obj_hand=callback_query, i_active_appoint=i_active_appoint, delete_init_message=False)


if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True)