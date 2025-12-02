i want to make a module to print a report for End Of service report for the employee whom resign or fired or the contract of them end 
on odoo 18.0
the code used before 
# EOSB - Saudi End of Service Benefit (final)
result = 0.0

start_date = contract.first_contract_date or contract.date_start
end_date = contract.date_end or payslip.date_to

if start_date and end_date:

    difference = relativedelta(end_date, start_date)
    total_days = difference.years * 360 + difference.months * 30 + difference.days + 1
    years = total_days / 360.0

    compensation = (
        (contract.wage or 0.0)
        + (contract.l10n_sa_housing_allowance or 0.0)
        + (contract.l10n_sa_transportation_allowance or 0.0)
        + (contract.l10n_sa_other_allowances or 0.0)
    )

    # None reasons (no EOSB)
    dep_none_01 = contract.env.ref(
        'pt_l10n_sa_hr_payroll.departure_none_01', raise_if_not_found=False
    )
    dep_none_02 = contract.env.ref(
        'pt_l10n_sa_hr_payroll.departure_none_02', raise_if_not_found=False
    )

    # Resigned reasons (multiple sources)
    dep_resigned_hr = contract.env.ref(
        'hr.departure_resigned', raise_if_not_found=False
    )
    dep_resigned_pt = contract.env.ref(
        'pt_l10n_sa_hr_payroll.departure_resigned', raise_if_not_found=False
    )

    resigned_reasons = []
    if dep_resigned_hr:
        resigned_reasons.append(dep_resigned_hr)
    if dep_resigned_pt:
        resigned_reasons.append(dep_resigned_pt)

    reason = employee.departure_reason_id

    none_reasons = []
    if dep_none_01:
        none_reasons.append(dep_none_01)
    if dep_none_02:
        none_reasons.append(dep_none_02)

    is_none = reason in none_reasons

    reason_code = False
    try:
        reason_code = reason.reason_code
    except Exception:
        reason_code = False

    is_resigned = (reason in resigned_reasons) or (reason_code in [343, '343'])

    if not is_none and total_days > 0:

        if not is_resigned:
            # FULL EOSB (Fired / Retired / Clause 77 / End of Contract / etc.)
            if years <= 5.0:
                result = (compensation / 2.0) * years
            else:
                result = (compensation / 2.0 * 5.0) + (compensation * (years - 5.0))

        else:
            # Resigned (same tiers you gave)
            if years >= 2.0 and years <= 5.0:
                result = (compensation / 6.0) * years
            elif years > 5.0 and years < 10.0:
                result = (compensation / 3.0 * 5.0) + (compensation * 2.0 / 3.0 * (years - 5.0))
            elif years >= 10.0:
                result = (compensation / 2.0 * 5.0) + (compensation * (years - 5.0))

# rounding
result = payslip.company_id.currency_id.round(result)
i want a button in hr.employee form view to click to print me the report 
the report must contain the remaining balance of annual vacation days left in his allocation 
the total duration of his work from start and end date of his contract 
days , months , years 
and chick if he has loan in his salary attachment not settle yet to deduct from his end of service benefits
