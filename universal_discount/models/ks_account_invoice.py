from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class KsGlobalDiscountInvoice(models.Model):
    # _inherit = "account.invoice"
    """ changing the model to account.move """
    _inherit = "account.move"

    ks_global_discount_type = fields.Selection([
                                                ('percent', 'Percentage'),
                                                ('amount', 'Amount')],
                                               string='Universal Discount Type',
                                               readonly=True,
                                                states={'draft': [('readonly', False)],
                                                        'sent': [('readonly', False)]},
                                                default='percent')
    ks_global_discount_rate = fields.Float('Universal Discount',
                                           readonly=True,
                                           states={'draft': [('readonly', False)],
                                                   'sent': [('readonly', False)]})
    ks_amount_discount = fields.Monetary(string='Universal Discount',
                                         readonly=True,
                                         compute='_compute_amount',
                                         store=True, track_visibility='always')
    ks_enable_discount = fields.Boolean(compute='ks_verify_discount')
    ks_sales_discount_account = fields.Text(compute='ks_verify_discount')
    ks_purchase_discount_account = fields.Text(compute='ks_verify_discount')

    # @api.multi
    @api.depends('name')
    def ks_verify_discount(self):
        for rec in self:
            rec.ks_enable_discount = rec.env['ir.config_parameter'].sudo().get_param('ks_enable_discount')
            rec.ks_sales_discount_account = rec.env['ir.config_parameter'].sudo().get_param('ks_sales_discount_account')
            rec.ks_purchase_discount_account = rec.env['ir.config_parameter'].sudo().get_param('ks_purchase_discount_account')

    # @api.multi
    # 1. tax_line_ids is replaced with tax_line_id. 2. api.mulit is also removed.
    # @api.depends('invoice_line_ids.price_subtotal', 'tax_line_ids.amount', 'tax_line_ids.amount_rounding',
    #              'currency_id', 'company_id', 'date_invoice', 'type', 'ks_global_discount_type',
    #              'ks_global_discount_rate')
    @api.depends(
        'line_ids.debit',
        'line_ids.credit',
        'line_ids.currency_id',
        'line_ids.amount_currency',
        'line_ids.amount_residual',
        'line_ids.amount_residual_currency',
        'line_ids.payment_id.state',
        'ks_global_discount_type',
        'ks_global_discount_rate')
    def _compute_amount(self):
        for rec in self:
            res = super(KsGlobalDiscountInvoice, rec)._compute_amount()
            if not ('ks_global_tax_rate' in rec):
                rec.ks_calculate_discount()
            sign = rec.type in ['in_refund', 'out_refund'] and -1 or 1
            rec.amount_total_company_signed = rec.amount_total * sign
            rec.amount_total_signed = rec.amount_total * sign
        return res

    # @api.multi
    def ks_calculate_discount(self):
        for rec in self:
            if rec.ks_global_discount_type == "amount":
                rec.ks_amount_discount = rec.ks_global_discount_rate if rec.amount_untaxed > 0 else 0
            elif rec.ks_global_discount_type == "percent":
                if rec.ks_global_discount_rate != 0.0:
                    rec.ks_amount_discount = (rec.amount_untaxed + rec.amount_tax) * rec.ks_global_discount_rate / 100
                else:
                    rec.ks_amount_discount = 0
            elif not rec.ks_global_discount_type:
                rec.ks_global_discount_rate = 0
                rec.ks_amount_discount = 0
            rec.amount_total = rec.amount_tax + rec.amount_untaxed - rec.ks_amount_discount
            rec.ks_update_universal_discount()

    @api.constrains('ks_global_discount_rate')
    def ks_check_discount_value(self):
        if self.ks_global_discount_type == "percent":
            if self.ks_global_discount_rate > 100 or self.ks_global_discount_rate < 0:
                raise ValidationError('You cannot enter percentage value greater than 100.')
        else:
            if self.ks_global_discount_rate < 0 or self.amount_untaxed < 0:
                raise ValidationError(
                    'You cannot enter discount amount greater than actual cost or value lower than 0.')

    # @api.onchange('purchase_id')
    # def ks_get_purchase_order_discount(self):
    #     self.ks_global_discount_rate = self.purchase_id.ks_global_discount_rate
    #     self.ks_global_discount_type = self.purchase_id.ks_global_discount_type

    # @api.model
    # def invoice_line_move_line_get(self):
    #     ks_res = super(KsGlobalDiscountInvoice, self).invoice_line_move_line_get()
    #     if self.ks_amount_discount > 0:
    #         ks_name = "Universal Discount"
    #         if self.ks_global_discount_type == "percent":
    #             ks_name = ks_name + " (" + str(self.ks_global_discount_rate) + "%)"
    #         ks_name = ks_name + " for " + (self.origin if self.origin else ("Invoice No " + str(self.id)))
    #         if self.ks_sales_discount_account and (self.type == "out_invoice" or self.type == "out_refund"):
    #
    #             dict = {
    #                 'invl_id': self.number,
    #                 'type': 'src',
    #                 'name': ks_name,
    #                 'price_unit': self.move_id.ks_amount_discount,
    #                 'quantity': 1,
    #                 'amount': -self.move_id.ks_amount_discount,
    #                 'account_id': int(self.move_id.ks_sales_discount_account),
    #                 'move_id': self.id,
    #                 'date': self.date,
    #                 'user_id': self.move_id.invoice_user_id.id or self._uid,
    #                 'company_id': self.move_id.account_id.company_id.id or self.env.company.id,
    #             }
    #             ks_res.append(dict)
    #
    #         elif self.ks_purchase_discount_account and (self.type == "in_invoice" or self.type == "in_refund"):
    #             dict = {
    #                 'invl_id': self.number,
    #                 'type': 'src',
    #                 'name': ks_name,
    #                 'price_unit': self.ks_amount_discount,
    #                 'quantity': 1,
    #                 'price': -self.ks_amount_discount,
    #                 'account_id': int(self.ks_purchase_discount_account),
    #
    #                 'invoice_id': self.id,
    #             }
    #             ks_res.append(dict)
    #
    #     return ks_res

    @api.model
    def _prepare_refund(self, invoice, date_invoice=None, date=None, description=None, journal_id=None):
        ks_res = super(KsGlobalDiscountInvoice, self)._prepare_refund(invoice, date_invoice=None, date=None,
                                                                      description=None, journal_id=None)
        ks_res['ks_global_discount_rate'] = self.ks_global_discount_rate
        ks_res['ks_global_discount_type'] = self.ks_global_discount_type
        return ks_res

    def ks_update_universal_discount(self):
        """This Function Updates the Universal Discount through Sale Order"""
        for rec in self:
            already_exists = self.line_ids.filtered(
                lambda line: line.name and line.name.find('Universal Discount') == 0)
            terms_lines = self.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
            other_lines = self.line_ids.filtered(
                lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
            if already_exists:
                amount = rec.ks_amount_discount
                if rec.ks_sales_discount_account \
                        and (rec.type == "out_invoice"
                             or rec.type == "out_refund")\
                        and amount > 0:
                    if rec.type == "out_invoice":
                        already_exists.update({
                            'debit': amount > 0.0 and amount or 0.0,
                            'credit': amount < 0.0 and -amount or 0.0,
                        })
                    else:
                        already_exists.update({
                            'debit': amount < 0.0 and -amount or 0.0,
                            'credit': amount > 0.0 and amount or 0.0,
                        })
                if rec.ks_purchase_discount_account \
                        and (rec.type == "in_invoice"
                             or rec.type == "in_refund")\
                        and amount > 0:
                    if rec.type == "in_invoice":
                        already_exists.update({
                            'debit': amount < 0.0 and -amount or 0.0,
                            'credit': amount > 0.0 and amount or 0.0,
                        })
                    else:
                        already_exists.update({
                            'debit': amount > 0.0 and amount or 0.0,
                            'credit': amount < 0.0 and -amount or 0.0,
                        })
                total_balance = sum(other_lines.mapped('balance'))
                total_amount_currency = sum(other_lines.mapped('amount_currency'))
                terms_lines.update({
                    'amount_currency': -total_amount_currency,
                    'debit': total_balance < 0.0 and -total_balance or 0.0,
                    'credit': total_balance > 0.0 and total_balance or 0.0,
                })
            if not already_exists and rec.ks_global_discount_rate > 0:
                in_draft_mode = self != self._origin
                if not in_draft_mode and rec.type == 'out_invoice':
                    rec._recompute_universal_discount_lines()
                print()

    @api.onchange('ks_global_discount_rate', 'ks_global_discount_type', 'line_ids')
    def _recompute_universal_discount_lines(self):
        """This Function Create The General Entries for Universal Discount"""
        for rec in self:
            type_list = ['out_invoice', 'out_refund', 'in_invoice', 'in_refund']
            if rec.ks_global_discount_rate > 0 and rec.type in type_list:
                if rec.is_invoice(include_receipts=True):
                    in_draft_mode = self != self._origin
                    ks_name = "Universal Discount "
                    if rec.ks_global_discount_type == "amount":
                        ks_value = "of amount #" + str(self.ks_global_discount_rate)
                    elif rec.ks_global_discount_type == "percent":
                        ks_value = " @" + str(self.ks_global_discount_rate) + "%"
                    else:
                        ks_value = ''
                    ks_name = ks_name + ks_value
                    #           ("Invoice No: " + str(self.ids)
                    #            if self._origin.id
                    #            else (self.display_name))
                    terms_lines = self.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                    already_exists = self.line_ids.filtered(
                                    lambda line: line.name and line.name.find('Universal Discount') == 0)
                    if already_exists:
                        amount = self.ks_amount_discount
                        if self.ks_sales_discount_account \
                                and (self.type == "out_invoice"
                                     or self.type == "out_refund"):
                            if self.type == "out_invoice":
                                already_exists.update({
                                    'name': ks_name,
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                })
                            else:
                                already_exists.update({
                                    'name': ks_name,
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                })
                        if self.ks_purchase_discount_account\
                                and (self.type == "in_invoice"
                                     or self.type == "in_refund"):
                            if self.type == "in_invoice":
                                already_exists.update({
                                    'name': ks_name,
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                })
                            else:
                                already_exists.update({
                                    'name': ks_name,
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                })
                    else:
                        new_tax_line = self.env['account.move.line']
                        create_method = in_draft_mode and \
                                        self.env['account.move.line'].new or\
                                        self.env['account.move.line'].create

                        if self.ks_sales_discount_account \
                                and (self.type == "out_invoice"
                                     or self.type == "out_refund"):
                            amount = self.ks_amount_discount
                            dict = {
                                    'move_name': self.name,
                                    'name': ks_name,
                                    'price_unit': self.ks_amount_discount,
                                    'quantity': 1,
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                    'account_id': int(self.ks_sales_discount_account),
                                    'move_id': self._origin,
                                    'date': self.date,
                                    'exclude_from_invoice_tab': True,
                                    'partner_id': terms_lines.partner_id.id,
                                    'company_id': terms_lines.company_id.id,
                                    'company_currency_id': terms_lines.company_currency_id.id,
                                    }
                            if self.type == "out_invoice":
                                dict.update({
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                })
                            else:
                                dict.update({
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                })
                            if in_draft_mode:
                                self.line_ids += create_method(dict)
                                # Updation of Invoice Line Id
                                duplicate_id = self.invoice_line_ids.filtered(
                                    lambda line: line.name and line.name.find('Universal Discount') == 0)
                                self.invoice_line_ids = self.invoice_line_ids - duplicate_id
                            else:
                                dict.update({
                                    'price_unit': 0.0,
                                    'debit': 0.0,
                                    'credit': 0.0,
                                })
                                self.line_ids = [(0, 0, dict)]

                        if self.ks_purchase_discount_account\
                                and (self.type == "in_invoice"
                                     or self.type == "in_refund"):
                            amount = self.ks_amount_discount
                            dict = {
                                    'move_name': self.name,
                                    'name': ks_name,
                                    'price_unit': self.ks_amount_discount,
                                    'quantity': 1,
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                    'account_id': int(self.ks_purchase_discount_account),
                                    'move_id': self.id,
                                    'date': self.date,
                                    'exclude_from_invoice_tab': True,
                                    'partner_id': terms_lines.partner_id.id,
                                    'company_id': terms_lines.company_id.id,
                                    'company_currency_id': terms_lines.company_currency_id.id,
                                    }

                            if self.type == "in_invoice":
                                dict.update({
                                    'debit': amount < 0.0 and -amount or 0.0,
                                    'credit': amount > 0.0 and amount or 0.0,
                                })
                            else:
                                dict.update({
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                                })
                            self.line_ids += create_method(dict)
                            # updation of invoice line id
                            duplicate_id = self.invoice_line_ids.filtered(
                                lambda line: line.name and line.name.find('Universal Discount') == 0)
                            self.invoice_line_ids = self.invoice_line_ids - duplicate_id

                    if in_draft_mode:
                        # Update the payement account amount
                        terms_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                        other_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                        total_balance = sum(other_lines.mapped('balance'))
                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                        terms_lines.update({
                                    'amount_currency': -total_amount_currency,
                                    'debit': total_balance < 0.0 and -total_balance or 0.0,
                                    'credit': total_balance > 0.0 and total_balance or 0.0,
                                })
                    else:
                        terms_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                        other_lines = self.line_ids.filtered(
                            lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                        already_exists = self.line_ids.filtered(
                            lambda line: line.name and line.name.find('Universal Discount') == 0)
                        total_balance = sum(other_lines.mapped('balance')) + amount
                        total_amount_currency = sum(other_lines.mapped('amount_currency'))
                        dict1 = {
                                    'debit': amount > 0.0 and amount or 0.0,
                                    'credit': amount < 0.0 and -amount or 0.0,
                        }
                        dict2 = {
                                'debit': total_balance < 0.0 and -total_balance or 0.0,
                                'credit': total_balance > 0.0 and total_balance or 0.0,
                                }
                        self.line_ids = [(1, already_exists.id, dict1), (1, terms_lines.id, dict2)]
                        print()

            elif self.ks_global_discount_rate <= 0:
                already_exists = self.line_ids.filtered(
                    lambda line: line.name and line.name.find('Universal Discount') == 0)
                if already_exists:
                    self.line_ids -= already_exists
                    terms_lines = self.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type in ('receivable', 'payable'))
                    other_lines = self.line_ids.filtered(
                        lambda line: line.account_id.user_type_id.type not in ('receivable', 'payable'))
                    total_balance = sum(other_lines.mapped('balance'))
                    total_amount_currency = sum(other_lines.mapped('amount_currency'))
                    terms_lines.update({
                        'amount_currency': -total_amount_currency,
                        'debit': total_balance < 0.0 and -total_balance or 0.0,
                        'credit': total_balance > 0.0 and total_balance or 0.0,
                    })
