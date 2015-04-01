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
__all__ = ['AccountJournal', 'AccountMove', 'AccountMoveLine']


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
    check_template = fields.Many2One(
        'ir.action.report', 'Check Template', domain=[
            ('model', '=', 'account.move'),
        ], states={
            'invisible': ~Eval('enable_check_printing', True),
            'required': Eval('enable_check_printing', False)
        }, depends=['enable_check_printing']
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
            'readonly': Eval('state') == 'posted',
        }, depends=['enable_check_printing']
    )
    check_debit_lines = fields.Function(
        fields.One2Many('account.move.line', None, 'Check Debit Lines'),
        'get_check_lines'
    )
    check_credit_lines = fields.Function(
        fields.One2Many('account.move.line', None, 'Check Credit Lines'),
        'get_check_lines'
    )

    @classmethod
    def __setup__(cls):
        super(AccountMove, cls).__setup__()
        cls._buttons.update({
            'assign_check_number': {
                'invisible': ~Eval('enable_check_printing', True),
            }
        })
        if 'check_number' not in cls._check_modify_exclude:
            cls._check_modify_exclude.append('check_number')

    @classmethod
    def validate(cls, moves):
        """
        Validate
        """
        super(AccountMove, cls).validate(moves)
        cls.check_move_lines(moves)

    def get_enable_check_printing(self, name):
        """
        Return True if Journal type is Cash and check printing is
        enabled for that Journal
        """
        if self.journal:
            return self.journal.enable_check_printing

    @fields.depends('journal')
    def on_change_journal(self):
        return {
            'enable_check_printing': self.get_enable_check_printing(None),
        }

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

    @classmethod
    def check_move_lines(cls, moves):
        """
        Check if there is only 1 debit and 1 credit line
        """
        for move in moves:
            if not move.enable_check_printing:
                continue
            move.check_credit_line()
            move.check_debit_line()

    def check_credit_line(self):
        """
        Validate if there is only one credit line with Journal's
        default Credit Account
        """
        if (
            len(
                filter(
                    lambda l: (
                        (l.account == self.journal.credit_account) and l.credit
                    ),
                    self.lines
                )
            ) > 1
        ):
            self.raise_user_error(
                "There can be only 1 credit line with Journal's default " +
                "Credit Account."
            )

    def check_debit_line(self):
        """
        Validate if there is only one debit line
        """
        debit_lines = filter(lambda l: l.debit, self.lines)
        if not debit_lines:
            return

        if len(debit_lines) > 1:
            self.raise_user_error(
                "There can be only 1 Debit Line."
            )
        elif not debit_lines[0].party:
            self.raise_user_error(
                "There must be a Party defined on the Debit Line."
            )

    def get_check_lines(self, name):
        """
        Returns the credit and debit lines for checks
        """
        if not self.enable_check_printing:
            return None

        if name == 'check_debit_lines':
            return map(int, filter(lambda l: l.debit, self.lines))
        elif name == 'check_credit_lines':
            return map(int, filter(lambda l: l.credit, self.lines))
        return None


class AccountMoveLine:
    'Account Move Line'
    __name__ = 'account.move.line'

    check_number = fields.Function(
        fields.Char('Check Number'), 'get_check_number',
        searcher='search_check_number'
    )

    def origin_details(self):
        """
        Returns the origin as a string to print on checks
        """
        Model = Pool().get('ir.model')

        if not self.origin or self.origin.id == -1:
            return None

        model, = Model.search([
            ('model', '=', self.origin.__name__)
        ])
        return "%s, %s" % (model.name, self.origin.rec_name)

    def get_check_number(self, name):
        """
        Return the check number of the current line's move
        """
        return self.move.check_number or None

    @classmethod
    def search_check_number(cls, name, clause):
        return [('move.check_number',) + tuple(clause[1:])]
