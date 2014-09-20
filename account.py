# -*- coding: utf-8 -*-
"""
    account.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.pool import Pool, PoolMeta
from trytond.model import fields, ModelView
from trytond.pyson import Eval


__metaclass__ = PoolMeta
__all__ = ['AccountJournal', 'AccountMove']


class AccountJournal:
    'Account Journal'
    __name__ = 'account.journal'

    enable_check_printing = fields.Boolean(
        'Enable Check Printing', states={
            'invisible': Eval('type') != 'cash',
        }, depends=['type']
    )
    check_number_sequence = fields.Property(
        fields.Many2One(
            'ir.sequence', 'Check Number Sequence', states={
                'invisible': ~Eval('enable_check_printing', True),
            },
        )
    )

    @staticmethod
    def default_enable_check_printing():
        return False

    @classmethod
    def validate(cls, journals):
        """
        Validate
        """
        super(AccountJournal, cls).validate(journals)
        cls.check_enable_check_printing(journals)

    @classmethod
    def check_enable_check_printing(cls, journals):
        """
        Validate if enable_check_printing can only be true if
        journal type is Cash
        """
        for journal in journals:
            if not journal.enable_check_printing:
                continue
            if journal.type != 'cash':
                cls.raise_user_error(
                    "Check Printing can only be enabled for Cash Journals"
                )


class AccountMove:
    'Account Move'
    __name__ = 'account.move'

    enable_check_printing = fields.Function(
        fields.Boolean('Enable Check Printing'), 'get_enable_check_printing'
    )
    check_number = fields.Char(
        'Check Number', states={
            'invisible': ~Eval('enable_check_printing', True),
        }, depends=['enable_check_printing']
    )
    check_template = fields.Many2One(
        'ir.action.report', 'Check Template', domain=[
            ('model', '=', 'account.move'),
        ], states={
            'invisible': ~Eval('enable_check_printing', True),
            'required': Eval('enable_check_printing', False)
        },
    )

    @classmethod
    def __setup__(cls):
        super(AccountMove, cls).__setup__()
        cls._buttons.update({
            'assign_check_number': {
                'invisible': ~Eval('enable_check_printing', True),
            }
        })

    def get_enable_check_printing(self, name):
        """
        Return True if Journal type is Cash and check printing is
        enabled for that Journal
        """
        return self.journal.enable_check_printing

    @classmethod
    @ModelView.button
    def assign_check_number(cls, moves):
        """
        Set the check number from the value of check number
        sequence field in the current move's Journal
        """
        Sequence = Pool().get('ir.sequence')

        for move in moves:
            if not move.enable_check_printing:
                continue

            if move.journal.check_number_sequence:
                cls.write([move], {
                    'check_number': Sequence.get_id(
                        move.journal.check_number_sequence.id
                    )
                })
            else:
                cls.raise_user_error(
                    "No Sequence defined for Check Number on Journal"
                )
