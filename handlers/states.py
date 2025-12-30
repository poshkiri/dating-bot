"""Состояния FSM для бота"""
from aiogram.fsm.state import State, StatesGroup


class ProfileCreation(StatesGroup):
    age = State()
    gender = State()
    interest = State()
    city = State()
    city_manual = State()
    name = State()
    description = State()
    photo = State()
    confirm = State()


class EventCreation(StatesGroup):
    title = State()
    description = State()
    city = State()
    date = State()
    photo = State()


class SuperLike(StatesGroup):
    message = State()
    video = State()


class AdminBroadcast(StatesGroup):
    message = State()
    photo = State()
    buttons = State()
    confirm = State()


class Verification(StatesGroup):
    photo = State()


class SocialNetwork(StatesGroup):
    instagram = State()
    vk = State()


class Support(StatesGroup):
    waiting_message = State()


class AdminSupportReply(StatesGroup):
    waiting_reply = State()


class CryptoPayment(StatesGroup):
    transaction_hash = State()