import datetime


# support vars

abbrs_weekday = ('Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс')

words_soon_weekday = ("Сегодня", "Завтра", "Послезавтра")


# support funcs

async def get_style_date(date: object) -> str:

	days_before = (date - datetime.date.today()).days
	if days_before < 3:

		return "{} ({}), {}".format(words_soon_weekday[days_before], abbrs_weekday[date.weekday()], date.day)
	else:
		return "{}, {}".format(abbrs_weekday[date.weekday()], date.day)


async def get_style_time(time: object) -> str:

	return time.strftime("%H:%M")