from aiogram import Bot, Dispatcher, executor, types
import logging

import secret, support #from this dir

import sqlite3, datetime


bot = Bot(token=secret.API_TOKEN)
dp = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)

# database must include:
## services -> (id INT, title VARCHAR, price INT)

db_con = sqlite3.connect(secret.DATABASE_PATH)
db_cur = db_con.cursor()


# session support vars

## organization data

### dates

####need database generate
qty_next_dates_booking = 7

### times

####need database generate
begin_hour_time = 11
end_hour_time = 21

## users data

###need organization in database
cookie = {'slctd_services': list(), 'slctd_date': None, 'slctd_time': None}


# session support funcs

async def get_total_slctd_services() -> int:

	total = 0
	for service in db_cur.execute('SELECT id, price FROM services').fetchall():
		if int(service[0]) in cookie['slctd_services']:
			total += int(service[1])


	return total


async def get_next_dates_booking() -> list:

	next_dates = list()

	date_today = datetime.date.today()
	for i in range(qty_next_dates_booking):
		next_dates.append(date_today + datetime.timedelta(days=i))


	return next_dates


async def get_times_booking() -> list:

	times = list()

	for hour in range(begin_hour_time, end_hour_time):
		times.append(datetime.time(hour))


	return times


@dp.message_handler(commands=['start', 'menu'])
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'menu')
async def menu(obj_hand: object):

	inline_kbrd = types.InlineKeyboardMarkup()
	inline_kbrd.add(types.InlineKeyboardButton(text="Услуги", callback_data='services'))


	chat_id = obj_hand.from_user.id
	if type(obj_hand) is types.Message:
		message_id = obj_hand.message_id
	else:
		message_id = obj_hand.message.message_id
		callback_query_id = obj_hand.id


	text = "Главная"

	if type(obj_hand) is types.CallbackQuery:
		await bot.delete_message(chat_id=chat_id,
			message_id=message_id)

	await bot.send_message(chat_id=chat_id,
		text=text,
		reply_markup=inline_kbrd)

	if type(obj_hand) is types.CallbackQuery:
		await bot.answer_callback_query(callback_query_id=callback_query_id)



@dp.message_handler(commands=['services'])
@dp.callback_query_handler(lambda callback_query: callback_query.data == 'services')
async def services(obj_hand: object):

	inline_kbrd = types.InlineKeyboardMarkup()
	for service in db_cur.execute('SELECT * FROM services').fetchall():
		inline_kbrd.add(types.InlineKeyboardButton(text="{} {} {} ₽".format(service[1],
				"·" if int(service[0]) not in cookie['slctd_services'] else "☑️",
				service[2]),
			callback_data='booking_services_slct {}'.format(service[0])))

	if cookie['slctd_services']:
		inline_kbrd.add(types.InlineKeyboardButton(text="Записаться ({} ₽) »".format(await get_total_slctd_services()),
			callback_data='booking_dates'))

	inline_kbrd.add(types.InlineKeyboardButton(text="« Меню", callback_data='menu'))
	

	chat_id = obj_hand.from_user.id
	if type(obj_hand) is types.Message:
		message_id = obj_hand.message_id
	else:
		message_id = obj_hand.message.message_id
		callback_query_id = obj_hand.id


	text = "Услуги"

	if type(obj_hand) is types.CallbackQuery:
		await bot.delete_message(chat_id=chat_id,
			message_id=message_id)

	await bot.send_message(chat_id=chat_id,
		text=text,
		reply_markup=inline_kbrd)

	if type(obj_hand) is types.CallbackQuery:
		await bot.answer_callback_query(callback_query_id=callback_query_id)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('booking_services_slct'))
async def booking_services_slct(callback_query: types.CallbackQuery):

	service_id = int(callback_query.data.split()[-1])
	if service_id not in cookie['slctd_services']:
		cookie['slctd_services'].append(service_id)
	else:
		cookie['slctd_services'].remove(service_id)


	await services(obj_hand=callback_query)



@dp.callback_query_handler(lambda callback_query: callback_query.data == 'booking_dates')
async def booking_dates(callback_query: types.CallbackQuery):

	if cookie['slctd_date']:
		cookie['slctd_date'] = None


	inline_kbrd = types.InlineKeyboardMarkup()

	next_dates = await get_next_dates_booking()
	for next_date in next_dates:
		inline_kbrd.add(types.InlineKeyboardButton(text=await support.get_style_date(next_date),
			callback_data='booking_dates_slct {}'.format(next_date.isoformat())))

	inline_kbrd.add(types.InlineKeyboardButton(text="« Услуги", callback_data='services'))
	

	text = "Выбор даты для услуг"

	await bot.delete_message(chat_id=callback_query.from_user.id,
		message_id=callback_query.message.message_id)

	await bot.send_message(chat_id=callback_query.from_user.id,
		text=text,
		reply_markup=inline_kbrd)

	await bot.answer_callback_query(callback_query_id=callback_query.id)


@dp.callback_query_handler(lambda callback_query: callback_query.data.startswith('booking_dates_slct'))
async def booking_dates_slct(callback_query: types.CallbackQuery):

	cookie['slctd_date'] = callback_query.data.split()[-1]

	await bot.answer_callback_query(callback_query_id=callback_query.id)

	await booking_times(callback_query=callback_query)



@dp.callback_query_handler(lambda callback_query: callback_query.data == 'booking_times')
async def booking_times(callback_query: types.CallbackQuery):

	if cookie['slctd_time']:
		cookie['slctd_time'] = None


	inline_kbrd = types.InlineKeyboardMarkup()

	times = await get_times_booking()
	for time in times:
		inline_kbrd.add(types.InlineKeyboardButton(text=await support.get_style_time(time),
			callback_data='booking_times_slct {}'.format(time.isoformat())))

	inline_kbrd.add(types.InlineKeyboardButton(text="« Выбор даты", callback_data='booking_dates'))


	text = "Выбор времени"

	await bot.delete_message(chat_id=callback_query.from_user.id,
		message_id=callback_query.message.message_id)

	await bot.send_message(chat_id=callback_query.from_user.id,
		text=text,
		reply_markup=inline_kbrd)

	await bot.answer_callback_query(callback_query_id=callback_query.id)


if __name__ == '__main__':
	executor.start_polling(dp, skip_updates=True)