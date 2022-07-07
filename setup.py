from aiogram import Bot, Dispatcher, executor, types
import logging

import secret #from this dir


bot = Bot(token=secret.API_TOKEN)
dispatcher = Dispatcher(bot)

logging.basicConfig(level=logging.INFO)


@dispatcher.message_handler(commands=['start'])
async def start(message: types.Message):

	await bot.send_message(chat_id=message.from_user.id,
		text="Здорово")


if __name__ == '__main__':
	executor.start_polling(dispatcher,skip_updates=True)