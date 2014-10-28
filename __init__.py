# -*- coding: utf-8 -*-
"""
    __init__.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool
from account import AccountJournal, AccountMove, AccountMoveLine
from check import Check, CheckPrinting, CheckPrintingWizard, \
    CheckPrintingWizardStart, RunCheck, RunCheckStart


def register():
    Pool.register(
        AccountJournal,
        AccountMove,
        CheckPrintingWizardStart,
        RunCheckStart,
        AccountMoveLine,
        module='account_check', type_='model'
    )
    Pool.register(
        Check,
        CheckPrinting,
        module='account_check', type_='report'
    )
    Pool.register(
        CheckPrintingWizard,
        RunCheck,
        module='account_check', type_='wizard'
    )
