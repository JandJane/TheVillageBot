# -*- coding: utf-8 -*-

import time
import config
import utils
from telegram.ext import CommandHandler, CallbackQueryHandler, Updater


def handle_start(bot, update):
    user = update.message.chat.id
    if len(utils.get_user(user)) == 0:  # if new user - add it to the users list and suggest choosing categories
        utils.add_user(user)
        bot.send_message(user, 'start_text')  # добавить стартовый текст в конфиг
        bot.send_message(user, utils.generate_text(user), reply_markup=utils.generate_keyboard(user))


def handle_edit(bot, update):  # shows current category list and suggests editing it
    user = update.message.chat.id
    bot.send_message(user, utils.generate_text(user), reply_markup=utils.generate_keyboard(user))


def handle_callback(bot, update):
    cb_query = update.callback_query
    message = cb_query.message.message_id
    user = cb_query.message.chat.id
    bot.answer_callback_query(cb_query.id)
    if cb_query.data[:3] == 'del':
        new_categories = utils.remove_category(cb_query.data[4:], user)
    else:
        new_categories = utils.append_category(cb_query.data[4:], user)
    bot.edit_message_text(chat_id=user, message_id=message,
                          text=utils.generate_text(new_categories))  # editing the message which originated the query
    bot.edit_message_reply_markup(user, message,
                                  reply_markup=utils.generate_keyboard(new_categories))  # according to new category list
    utils.update_categories(user, new_categories)

    
def deliver_posts(bot, job):
    users = config.DB.query("SELECT * FROM users")
    for category in config.CATEGORIES:
        updates = utils.get_updates(category)  # returns a list of new articles (if there are any) and an empty list otherwise
        for user in users:
            if category in user[1]:
                for post in updates:
                    # each post is sent to each user who is following this category as a separate message
                    bot.send_message(int(user[0]), '<b>' + post['title'] + '.  </b>' + post['preamble'] + '.  <a href="' + post[
                        'url'] + '">Читать далее>></a>', parse_mode='HTML')
        for post in updates:
            bot.send_message('@thevillagechanel', '<b>' + post['title'] + '.  </b>' + post['preamble'] + '.  <a href="'
                             + post['url'] + '">Читать далее>></a>', parse_mode='HTML')
        time.sleep(2)
        

updater = Updater(config.TOKEN)

updater.dispatcher.add_handler(CommandHandler('start', handle_start))
updater.dispatcher.add_handler(CommandHandler('edit', handle_edit))
updater.dispatcher.add_handler(CallbackQueryHandler(handle_callback))
updater.start_polling()

job = updater.job_queue
job.start()

job.run_repeating(deliver_posts, interval=config.INTERVAL, first=0)
