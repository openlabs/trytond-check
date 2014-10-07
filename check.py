# -*- coding: utf-8 -*-
"""
    check.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.report import Report
from trytond.exceptions import UserError
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import fields, ModelView
from trytond.wizard import Wizard, StateAction, StateView, Button


__all__ = [
    'Check', 'CheckPrinting', 'CheckPrintingWizard', 'CheckPrintingWizardStart'
]


class Check(Report):
    'Print Checks'
    __name__ = 'account.move.check'

    @classmethod
    def parse(cls, report, records, data, localcontext):
        """
        Replace the report with the report selected in Account Move
        """
        if len(records) > 1:
            raise UserError(
                "This report can only be generated for 1 record at a time"
            )
        move = records[0]

        if not move.enable_check_printing:
            raise UserError(
                "Check Printing not enabled for this Account Move."
            )
        if not move.check_number:
            raise UserError(
                "Check Number not valid."
            )

        # Use Account Move's check template
        report = move.journal.check_template
        return super(Check, cls).parse(
            report, records, data, localcontext
        )


class CheckPrinting(Report):
    """
    Check Printing
    """
    __name__ = 'account.move.check_printing'

    @classmethod
    def parse(cls, report, records, data, localcontext):
        AccountMove = Pool().get('account.move')
        AccountJournal = Pool().get('account.journal')

        records = [AccountMove(m) for m in data['moves']]
        report = AccountJournal(data['journal']).check_template
        return super(CheckPrinting, cls).parse(
            report, records, data, localcontext
        )


class CheckPrintingWizardStart(ModelView):
    'Check Printing Wizard'
    __name__ = 'account.move.check_printing_wizard.start'

    next_number = fields.Integer('Next Number', readonly=True)
    journal = fields.Many2One('account.journal', 'Journal', readonly=True)
    no_of_checks = fields.Integer('Number of Checks', readonly=True)


class CheckPrintingWizard(Wizard):
    'Check Printing Wizard'
    __name__ = 'account.move.check_printing_wizard'

    start = StateView(
        'account.move.check_printing_wizard.start',
        'account_check.check_printing_wizard_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Print', 'generate', 'tryton-ok', default=True),
        ]
    )
    generate = StateAction('account_check.account_move_check_printing')

    def default_start(self, fields):
        """
        Set values for fields in Start View
        """
        AccountMove = Pool().get('account.move')

        defaults = {}
        move_ids = Transaction().context.get('active_ids')

        if not move_ids:
            self.raise_user_error('No Account Move selected')

        moves = [AccountMove(m) for m in move_ids]
        journals = set([m.journal for m in moves])

        if filter(lambda m: m.check_number, moves):
            self.raise_user_error(
                'One or more selected moves have check number assigned to them.'
            )

        if len(journals) > 1:
            self.raise_user_error(
                'All selected moves must be for the same Journal'
            )

        journal, = journals
        if not journal.enable_check_printing:
            self.raise_user_error(
                'Check printing not enabled for Journal'
            )
        if not journal.check_number_sequence:
            self.raise_user_error('No sequence defined on Journal')

        defaults['next_number'] = journal.check_number_sequence.number_next
        defaults['journal'] = journal.id
        defaults['no_of_checks'] = len(moves)
        return defaults

    def do_generate(self, action):
        """
        Send data to report
        """
        AccountMove = Pool().get('account.move')

        move_ids = Transaction().context.get('active_ids')
        moves = [AccountMove(m) for m in move_ids]

        # Assign Check Number to all moves
        AccountMove.assign_check_number(moves)

        data = {
            'moves': move_ids,
            'journal': self.start.journal.id,
        }
        return action, data

    def transition_generate(self):
        return 'end'
