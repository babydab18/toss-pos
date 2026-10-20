from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, model_validator, field_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)


class Login(StrictModel):
    username: str = Field(min_length=1, max_length=80)
    password: str = Field(min_length=1, max_length=200)


class UserInput(Login):
    password: str = Field(min_length=12, max_length=200)
    role: Literal['admin', 'cashier', 'kitchen']


class CategoryInput(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    sort_order: int = 0


class OptionInput(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    price: int = Field(ge=0, le=10000000)


class GroupInput(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    min_select: int = Field(ge=0, le=30)
    max_select: int = Field(ge=1, le=30)
    options: list[OptionInput] = Field(min_length=1, max_length=30)

    @model_validator(mode='after')
    def bounds(self):
        if not self.min_select <= self.max_select <= len(self.options):
            raise ValueError('Selection bounds must fit the number of options')
        if len({o.name.casefold() for o in self.options}) != len(self.options):
            raise ValueError('Option names must be unique')
        return self


class ItemInput(StrictModel):
    category_id: int
    name: str = Field(min_length=1, max_length=150)
    description: str = Field(default='', max_length=2000)
    price: int = Field(ge=0, le=10000000)
    image_url: str = Field(default='', pattern=r'^(/uploads/[a-f0-9]{32}\.webp)?$')
    available: bool = True
    hidden: bool = False
    is_combo: bool = False
    vegetarian: bool = True
    sort_order: int = 0
    group_ids: list[int] = Field(default_factory=list, max_length=30)


class LineInput(StrictModel):
    menu_item_id: int
    quantity: int = Field(ge=1, le=99)
    option_ids: list[int] = Field(default_factory=list, max_length=100)
    instructions: str = Field(default='', max_length=500)


class OrderInput(StrictModel):
    customer: str = Field(default='', max_length=100)
    phone: str = Field(default='', max_length=30)
    sms_opt_in: bool = False

    @model_validator(mode='after')
    def sms_phone(self):
        if self.sms_opt_in and not self.phone.startswith('+'):
            raise ValueError('For SMS, enter the phone number with + and country code')
        return self


    @field_validator('phone')
    @classmethod
    def valid_phone(cls, value):
        import re
        value = re.sub(r'[ ()-]', '', value)
        if value and not re.fullmatch(r'\+?[1-9][0-9]{6,14}', value):
            raise ValueError('Enter a valid phone number, including country code for SMS')
        return value

    instructions: str = Field(default='', max_length=1000)
    items: list[LineInput] = Field(min_length=1, max_length=100)


class OrderEdit(OrderInput):
    version: int = Field(ge=1)
    reason: str = Field(min_length=1, max_length=500)


class StatusInput(StrictModel):
    status: Literal['preparing', 'ready', 'completed', 'cancelled']
    version: int = Field(ge=1)
    reason: str = Field(default='', max_length=500)
