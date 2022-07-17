# gonzo-barbershop-bot
This is the concept of a telegram bot for a small business - barbershop.
The bot is written in **Python**, the **AIOgram** library. A simple DBMS is also used - **SQLite3**.
The bot has no artificial intelligence - it's just an interface.
The main way to interact with the user is through _InlineKeyboards_ (technically, through _CallbackQueryHandlers_).
The bot allows you to:
- [ ] Make an appointment with payment
- [x] Find out the address of the business with the location
- [ ] Call or write to the business
- [x] Keep track of your active records
## Features
* Instead of changing the message with the button (interface), after clicking the button, the message is deleted and a new one is sent: it was assumed that in this way, no matter how much the user wrote, the interface would always be "next" to the user.
## Disadvantages
- [ ] Due to the peculiarities of the organization of messages, there is a delay when the interface is "changed"
- [ ] Sufficiently loaded context processing in sectional functions (incoming values from handlers, closing algorithm)
- [x] Lack of data generation by the database, etc.
- [ ] Cookies are not implemented effectively enough
