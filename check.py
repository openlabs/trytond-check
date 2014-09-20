# -*- coding: utf-8 -*-
"""
    check.py

    :copyright: (c) 2014 by Openlabs Technologies & Consulting (P) Limited
    :license: BSD, see LICENSE for more details.
"""
from trytond.report import Report
from trytond.exceptions import UserError


__all__ = ['Check']


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
        report = move.check_template
        return super(Check, cls).parse(
            report, records, data, localcontext
        )
