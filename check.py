# -*- coding: utf-8 -*-
"""
    check.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from num2words import num2words
from itertools import groupby
from decimal import Decimal

from trytond.report import Report
from trytond.exceptions import UserError
from trytond.pool import Pool
from trytond.transaction import Transaction
from trytond.model import fields, ModelView
from trytond.wizard import Wizard, StateAction, StateView, Button
from trytond.pyson import PYSONEncoder


__all__ = [
    'Check', 'CheckPrinting', 'CheckPrintingWizard', 'CheckPrintingWizardStart',
    'RunCheck', 'RunCheckStart'
]


class ReportMixin(Report):
    """
    Mixin Class for reports
    """

    @classmethod
    def amount_to_words(cls, amount, length=100):
        """
        Returns amount in words to print on checks

        :param amount: Amount to convert into words
        :param length: Length of returned string
        """
        if not amount:
            return None

        amount_in_words = num2words(int(amount)).replace(' and ', ' ').title()

        if amount - int(amount):
            amount_in_words += " and %d/100" % (Decimal(str(amount)) % 1 * 100)

        return ('{:*<%d}' % length).format(amount_in_words)

    @classmethod
    def parse(cls, report, records, data, localcontext):
        """
        Add amount_to_words to localcontext
        """
        localcontext.update({
            'amount_to_words': lambda *args, **kargs: cls.amount_to_words(
                *args, **kargs)
        })

        return super(ReportMixin, cls).parse(
            report, records, data, localcontext
        )


class Check(ReportMixin):
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
        if not move.state == 'posted':
            raise UserError(
                "You must Post the move before printing check."
            )

        # Use Account Move's check template
        report = move.journal.check_template
        return super(Check, cls).parse(
            report, records, data, localcontext
        )


class CheckPrinting(ReportMixin):
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

        if filter(lambda m: m.state != 'posted', moves):
            self.raise_user_error(
                'One or more selected moves are not Posted yet.'
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


class RunCheckStart(ModelView):
    'Run Check'
    __name__ = 'account.move.line.run_check.start'
    journal = fields.Many2One(
        'account.journal', 'Journal', required=True, domain=[
            ('enable_check_printing', '=', True)
        ]
    )
    next_number = fields.Integer('Next Number', readonly=True)
    moves = fields.One2Many(
        'account.move', None, 'Moves', readonly=True
    )

    @fields.depends('journal')
    def on_change_journal(self):
        if self.journal:
            return {
                'next_number': self.journal.check_number_sequence.number_next
            }
        return {'next_number': None}


class RunCheck(Wizard):
    'Run checks for the given lines'
    __name__ = 'account.move.line.run_check'

    start = StateView(
        'account.move.line.run_check.start',
        'account_check.move_line_run_check_start_view_form', [
            Button('Cancel', 'end', 'tryton-cancel'),
            Button('Pay', 'pay', 'tryton-ok', default=True),
        ]
    )
    pay = StateAction('account_check.account_move_check_printing')
    summary = StateAction('account.act_move_form')

    def get_move(self, lines, party, account):
        Move = Pool().get('account.move')
        Line = Pool().get('account.move.line')
        Date = Pool().get('ir.date')

        total_debit = sum(line.debit for line in lines)
        total_credit = sum(line.credit for line in lines)
        payment_amount = total_credit - total_debit

        return Move(
            journal=self.start.journal,
            date=Date.today(),
            lines=[
                # Credit the journal
                Line(
                    account=self.start.journal.credit_account,
                    credit=payment_amount,
                ),
                # Debit the payable account
                Line(
                    account=account,
                    debit=payment_amount,
                    party=party,
                )
            ]
        )

    def do_pay(self, action):
        Line = Pool().get('account.move.line')
        Move = Pool().get('account.move')

        sort_key = lambda line: (line.party, line.account)

        # Sorted by party after removing lines without party
        move_lines = sorted(
            filter(
                lambda line: line.party,
                Line.browse(Transaction().context['active_ids'])
            ),
            key=sort_key
        )

        moves = []
        for party_account, lines in groupby(move_lines, key=sort_key):
            lines = list(lines)
            move = self.get_move(lines, *party_account)
            move.save()
            moves.append(move)

            # Reconcile the lines
            Line.reconcile(
                lines + [line for line in move.lines if line.party]
            )

        move_ids = map(int, moves)

        self.start.moves = moves
        # Post all the moves
        Move.post(moves)
        # Assign Check Number to all moves
        Move.assign_check_number(moves)

        data = {
            'moves': move_ids,
            'journal': self.start.journal.id,
        }
        return action, data

    def transition_pay(self):
        return 'summary'

    def do_summary(self, action):
        action['pyson_domain'] = PYSONEncoder().encode(
            [('id', 'in', map(int, self.start.moves))]
        )
        action['name'] = "Moves for Created Checks"
        return action, {}
