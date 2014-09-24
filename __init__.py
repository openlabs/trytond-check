# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from account import AccountJournal, AccountMove
from check import Check


def register():
    Pool.register(
        AccountJournal,
        AccountMove,
        module='account_check', type_='model'
    )
    Pool.register(
        Check,
        module='account_check', type_='report'
    )
