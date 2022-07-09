import datetime


# support vars

weekdays = (("Понедельник", "Пн"),
			("Вторник", "Вт"),
			("Среда", "Ср"),
			("Четверг", "Чт"),
			("Пятница", "Пт"),
			("Суббота", "Сб"),
			("Воскресенье", "Вс"))


# support func

async def get_style_date(date: object, full_weekday: bool = True) -> str:

	return "{}, {}".format(weekdays[date.weekday()][0] if full_weekday else weekdays[date.weekday()][1],
		date.day)


async def get_style_time(time: object) -> str:

	return time.strftime("%H:%M")