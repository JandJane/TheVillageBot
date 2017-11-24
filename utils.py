# -*- coding: utf-8 -*-

import lxml.html as html
from lxml import etree
import urllib.request
import asyncio
import config
import eventlet
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

links = {'Город': 'http://www.the-village.ru/village/city', 'Люди': 'http://www.the-village.ru/village/people', 'Бизнес': 'http://the-village.ru/village/business',
         'Развлечения': 'http://www.the-village.ru/village/weekend', 'Еда': 'http://www.the-village.ru/village/food', 'Стиль': 'http://www.the-village.ru/village/service-shopping',
         'Дети': 'http://www.the-village.ru/village/children'}
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/47.0.2526.106 Safari/537.36"}

get_user = config.DB.prepare("SELECT * FROM users WHERE id = $1")
add_user = config.DB.prepare("INSERT INTO users VALUES ($1, '')")
update_categories = config.DB.prepare("UPDATE users SET category = $2 WHERE id = $1")
get_last_update = config.DB.prepare("SELECT title FROM last_updates WHERE category = $1")
set_last_update = config.DB.prepare("UPDATE last_updates SET title = $2 WHERE category = $1")


def to_list(user): # takes "category" value from the database (which is a string) and makes it a list
    return list(get_user(user)[0][1].split())


def get_updates(category):  # parses page with the requested category and returns list of updates
    updates = []
    url = links[category]
    req = urllib.request.Request(url, headers=headers)
    content = urllib.request.urlopen(req).read()
    doc = html.fromstring(content)
    doc.make_links_absolute(url)
    first = True  # indicates if the post we're processing is the first on the page so we write it to the UPDATES_FILE
    timeout = eventlet.Timeout(10)
    try:
        for block in doc.find_class('posts-layout'):  # for every block of posts
            for post in etree.HTML(html.tostring(block)).getchildren()[0].getchildren()[0].getchildren():  # for every post
                post = html.fromstring(etree.tostring(post))
                if len(post.find_class('post-title')) and len(post.find_class('post-preamble')):
                    title = post.find_class('post-title')[0].text_content()  # article title
                    preamble = post.find_class('post-preamble')[0].text_content()  # article preview
                    link = list(post.iterlinks())[0][2]  # article url
                    if first:  # we need to memorize the first post so that next time we know where we should stop
                        temp = title  # temporary variable for the title of the first post on the page
                        first = False
                    try:
                        if title.strip() == get_last_update(category)[0][0].strip():  # stop if this post has been already parsed
                            set_last_update(category, temp)
                            return updates
                    except Exception as e:
                        print(e)
                        return []
                    updates.append({'title': title, 'preamble': preamble, 'url': link})
        set_last_update(category, temp)
        return updates
    except eventlet.timeout.Timeout:
        print(updates)
        print(url)
        return []
    finally:
        timeout.cancel()


def generate_text(arg):  # generates text with users's current list of categories and suggests editing it
    if type(arg) == int:
        users_categories = to_list(arg)
    else:
        users_categories = arg.split()
    message = ''
    if len(users_categories):  # if users's list already contains any categories, then display them
        message += 'В настоящий момент вы подписаны на следующие категории: \n \n'
        for i in range(len(users_categories)):
            message += str(i + 1) + '. ' + users_categories[i] + '\n'
        message += '\n Вы можете добавить или удалить любую из категорий:'
    else:  # otherwise suggest choosing some
        message += 'Похоже, вы пока не подписаны ни на одну из категорий новостей :( \n'
        message += 'Выберите интересные вам категории, чтобы исправить это досадное недоразумение'
    return message


def generate_keyboard(arg):
    if type(arg) == int:
        users_categories = to_list(arg)
    else:
        users_categories = arg.split()
    keyboard = InlineKeyboardMarkup([])
    for category in config.CATEGORIES:  # create a button for each category
        if category in users_categories:  # categories which are on user's list go with a minus sign
            button = InlineKeyboardButton(text='-' + category, callback_data='del_' + category)
            keyboard.inline_keyboard.append([button])
        else:  # others go with a plus sign
            button = InlineKeyboardButton(text='+' + category, callback_data='add_' + category)
            keyboard.inline_keyboard.append([button])
    return keyboard


def remove_category(category, user):
    users_categories = to_list(user)
    if category in users_categories:  # we shall do nothing if the category is not on the list for some reason
        users_categories.remove(category)
    return ' '.join(users_categories)


def append_category(category, user):
    users_categories = to_list(user)
    if category not in users_categories:  # check if this category is not on the list already
        users_categories.append(category)
    return ' '.join(users_categories)

