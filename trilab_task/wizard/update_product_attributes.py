# -*- coding: utf-8 -*-
from odoo import models, fields


class ProductAttributeUpdate(models.TransientModel):
    _name = "product.attribute.update"
    _description = "Product Attributes Update"

    product_tmpl_ids = fields.Many2many('product.template', string='Product Templates',
                                        help="Empty means all Product Templates will be selected")
    from_attribute_id = fields.Many2one('product.attribute', string='From attribute')
    to_attribute_id = fields.Many2one('product.attribute', string='To attribute')
    from_value_id = fields.Many2one('product.attribute.value', string='From value')
    to_value_id = fields.Many2one('product.attribute.value', string='To value')

    def update_product_attributes(self):
        prods_list = (self.product_tmpl_ids if self.product_tmpl_ids else self.env['product.template'].search([])).ids
        valid_al = self.env['product.template.attribute.line'].search([
            ('attribute_id', '=', self.from_attribute_id.id),
            ('product_tmpl_id', 'in', prods_list)
        ]).filtered(lambda x: self.from_value_id in x.value_ids)
        prod_dict = {prod: valid_al.filtered(lambda x: x.product_tmpl_id == prod) for prod in valid_al.product_tmpl_id}
        to_unlink = []

        for prod, val_lines in prod_dict.items():
            trigger = False

            if not self.to_attribute_id:
                lines_to_unlink = val_lines.filtered(lambda x: len(x.value_ids) == 1)
                if lines_to_unlink:
                    lines_to_unlink[0].unlink()
            else:
                for line in val_lines:
                    if trigger:
                        continue
                    if self.from_attribute_id == self.to_attribute_id:
                        prod_attr_lines = line.product_tmpl_id.attribute_line_ids

                        if prod_attr_lines.filtered(
                                lambda x: x.attribute_id == self.to_attribute_id).value_ids.filtered(
                            lambda x: x.id == self.to_value_id.id):
                            continue
                        else:
                            self.env.cr.execute("""
                                UPDATE 
                                    product_attribute_value_product_template_attribute_line_rel
                                SET 
                                    product_attribute_value_id=%s 
                                WHERE 
                                    product_template_attribute_line_id=%s
                                AND
                                    product_attribute_value_id=%s
                            """, (self.to_value_id.id, line.id, self.from_value_id.id))
                            trigger = True
                    else:
                        if len(line.value_ids) > 1:
                            continue
                        else:
                            to_unlink.append(line.id)
                            line.copy({'attribute_id': self.to_attribute_id.id, 'value_ids': [(6, 0, [self.to_value_id.id])]})
                            trigger = True

        if to_unlink:
            valid_al.filtered(lambda x: x.id in to_unlink).unlink()
