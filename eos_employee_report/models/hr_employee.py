from dateutil.relativedelta import relativedelta

from odoo import fields, models
from odoo.exceptions import UserError


class HREmployee(models.Model):
    _inherit = 'hr.employee'

    def action_print_eos_report(self):
        self.ensure_one()
        action = self.env.ref('eos_employee_report.action_report_employee_eos', raise_if_not_found=False)
        if not action:
            raise UserError('The End of Service report action is missing. Please update the module.')
        return action.report_action(self)

    def _get_primary_contract(self):
        self.ensure_one()
        contract = self.contract_id
        if not contract:
            contract = self.env['hr.contract'].search(
                [('employee_id', '=', self.id)], order='date_start desc, id desc', limit=1
            )
        return contract

    def _get_contract_dates(self, contract):
        start = contract.first_contract_date or contract.date_start
        end = contract.date_end or fields.Date.context_today(self)
        return start, end

    def _get_employment_duration(self, start_date, end_date):
        if not start_date or not end_date:
            return {
                'years': 0,
                'months': 0,
                'days': 0,
                'total_days': 0,
            }

        diff = relativedelta(end_date, start_date)
        total_days = (diff.years * 360) + (diff.months * 30) + diff.days + 1
        return {
            'years': diff.years,
            'months': diff.months,
            'days': diff.days,
            'total_days': total_days,
        }

    def _compute_eos_amount(self, contract, duration):
        if not contract or not duration.get('total_days'):
            return 0.0

        years = duration['total_days'] / 360.0
        compensation = (
            (contract.wage or 0.0)
            + (getattr(contract, 'l10n_sa_housing_allowance', 0.0) or 0.0)
            + (getattr(contract, 'l10n_sa_transportation_allowance', 0.0) or 0.0)
            + (getattr(contract, 'l10n_sa_other_allowances', 0.0) or 0.0)
        )

        dep_none_01 = self.env.ref('pt_l10n_sa_hr_payroll.departure_none_01', raise_if_not_found=False)
        dep_none_02 = self.env.ref('pt_l10n_sa_hr_payroll.departure_none_02', raise_if_not_found=False)

        dep_resigned_hr = self.env.ref('hr.departure_resigned', raise_if_not_found=False)
        dep_resigned_pt = self.env.ref('pt_l10n_sa_hr_payroll.departure_resigned', raise_if_not_found=False)

        resigned_reasons = [reason for reason in (dep_resigned_hr, dep_resigned_pt) if reason]
        none_reasons = [reason for reason in (dep_none_01, dep_none_02) if reason]

        reason = self.departure_reason_id
        reason_code = getattr(reason, 'reason_code', False)

        is_none = reason in none_reasons
        is_resigned = (reason in resigned_reasons) or (reason_code in [343, '343'])

        eos_amount = 0.0
        if not is_none and duration['total_days'] > 0:
            if not is_resigned:
                if years <= 5.0:
                    eos_amount = (compensation / 2.0) * years
                else:
                    eos_amount = (compensation / 2.0 * 5.0) + (compensation * (years - 5.0))
            else:
                if 2.0 <= years <= 5.0:
                    eos_amount = (compensation / 6.0) * years
                elif 5.0 < years < 10.0:
                    eos_amount = (compensation / 3.0 * 5.0) + (compensation * 2.0 / 3.0 * (years - 5.0))
                elif years >= 10.0:
                    eos_amount = (compensation / 2.0 * 5.0) + (compensation * (years - 5.0))

        currency = contract.company_id.currency_id or self.company_id.currency_id
        return currency.round(eos_amount)

    def _get_annual_leave_balance(self):
        self.ensure_one()
        LeaveType = self.env['hr.leave.type']
        annual_types = LeaveType.search([
            ('time_type', '=', 'leave'),
            '|', ('code', 'ilike', 'annual'), ('name', 'ilike', 'annual'),
        ])

        if not annual_types:
            return self.remaining_leaves or 0.0

        allocations = self.env['hr.leave.allocation'].search([
            ('employee_id', '=', self.id),
            ('state', '=', 'validate'),
            ('holiday_type', '=', 'employee'),
            ('holiday_status_id', 'in', annual_types.ids),
        ])
        allocation_days = sum(alloc.number_of_days_display for alloc in allocations)

        leaves = self.env['hr.leave'].search([
            ('employee_id', '=', self.id),
            ('state', 'in', ['validate', 'validate1']),
            ('holiday_status_id', 'in', annual_types.ids),
        ])
        taken_days = sum(leave.number_of_days_display for leave in leaves)
        return allocation_days - taken_days

    def _get_outstanding_deductions(self):
        self.ensure_one()
        total = 0.0

        SalaryAttachment = self.env['ir.model'].search([('model', '=', 'hr.salary.attachment')], limit=1)
        if SalaryAttachment:
            attachments = self.env['hr.salary.attachment'].search([
                ('employee_id', '=', self.id),
                ('state', 'not in', ['close', 'paid']),
            ])
            for attachment in attachments:
                if 'remaining_amount' in attachment._fields:
                    total += attachment.remaining_amount
                elif {'amount_total', 'amount_paid'} <= set(attachment._fields):
                    total += max(attachment.amount_total - attachment.amount_paid, 0.0)
                elif 'amount' in attachment._fields:
                    total += attachment.amount

        Loan = self.env['ir.model'].search([('model', '=', 'hr.loan')], limit=1)
        if Loan:
            loans = self.env['hr.loan'].search([
                ('employee_id', '=', self.id),
                ('state', 'not in', ['done', 'cancel', 'paid']),
            ])
            for loan in loans:
                if 'balance_amount' in loan._fields:
                    total += loan.balance_amount
                elif {'amount', 'amount_paid'} <= set(loan._fields):
                    total += max(loan.amount - loan.amount_paid, 0.0)
                elif 'amount_total' in loan._fields:
                    total += loan.amount_total

        return total

    def _prepare_eos_report_data(self):
        self.ensure_one()
        contract = self._get_primary_contract()
        start_date, end_date = (None, None)
        if contract:
            start_date, end_date = self._get_contract_dates(contract)
        duration = self._get_employment_duration(start_date, end_date) if contract else {
            'years': 0,
            'months': 0,
            'days': 0,
            'total_days': 0,
        }
        eos_amount = self._compute_eos_amount(contract, duration) if contract else 0.0
        remaining_leaves = self._get_annual_leave_balance()
        outstanding_deductions = self._get_outstanding_deductions()

        return {
            'employee': self,
            'contract': contract,
            'start_date': start_date,
            'end_date': end_date,
            'duration': duration,
            'eos_amount': eos_amount,
            'remaining_leaves': remaining_leaves,
            'outstanding_deductions': outstanding_deductions,
            'net_eos_amount': eos_amount - outstanding_deductions,
        }
