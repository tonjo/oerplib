# -*- coding: UTF-8 -*-
"""Provides the :func:`list_on_changes` function."""
import xml.etree.ElementTree
import re

ON_CHANGE_RE = re.compile('^(.*?)\((.*)\)$')


def list_on_change(oerp, models):
    """List all `on_change` methods detected among `models`.
    The detection is made from the view descriptions related to the models.
    """
    result = {}
    view_obj = oerp.get('ir.ui.view')
    model_data_obj = oerp.get('ir.model.data')
    for model in models:
        # Get all model views
        view_ids = view_obj.search(
            [('model', '=', model), ('type', 'in', ['form', 'tree'])])
        model_data_ids = model_data_obj.search(
            [('res_id', 'in', view_ids), ('model', '=', 'ir.ui.view')])
        model_data = model_data_obj.read(
            model_data_ids, ['name', 'module', 'res_id'])
        for data in model_data:
            # For each view, find all `on_change` methods
            view_name = "{0}.{1}".format(data['module'], data['name'])
            view_data = oerp.execute(
                model, 'fields_view_get', data['res_id'])
            _scan_view(model, view_name, view_data, result)
    return result


def _scan_view(model, view_name, view_data, result):
    """Update `result` with all `on_change` methods detected
    on the view described by `view_data`.
    """
    if model not in result:
        result[model] = {}
    # Scan the main view description
    xml_root = xml.etree.ElementTree.fromstring(view_data['arch'])
    # NOTE: Python 2.6 does not support full XPath, it is
    # why the ".//field" pattern is used instead of ".//field[@on_change]"
    for elt in xml_root.findall(".//field"):
        if 'on_change' not in elt.attrib:
            continue
    #for elt in xml_root.findall(".//field[@on_change]"):
        match = ON_CHANGE_RE.match(elt.attrib['on_change'])
        if match:
            func = match.group(1)
            args = [arg.strip() for arg in match.group(2).split(',')]
            field = elt.attrib['name']
            if func not in result[model]:
                result[model][func] = {
                    'args': [],
                    'fields': [],
                    'views': [],
                }
            if field not in result[model][func]['fields']:
                result[model][func]['fields'].append(field)
            if view_name not in result[model][func]['views']:
                result[model][func]['views'].append(view_name)
            # We keep the longest signature found for this on_change
            if not result[model][func]['args'] \
                    or len(result[model][func]['args']) < len(args):
                args = map(_clean_arg, args)
                result[model][func]['args'] = args
    # Scan recursively all other sub-descriptions defined in the view
    for field_name, field_data in view_data['fields'].iteritems():
        if field_data.get('views') and field_data['views'].get('form'):
            model = field_data['relation']
            if field_data['views'].get('form'):
                _scan_view(
                    model, view_name, field_data['views']['form'], result)
            if field_data['views'].get('tree'):
                _scan_view(
                    model, view_name, field_data['views']['tree'], result)
    return result


def _clean_arg(arg):
    return {
        'False': False,
        'True': True,
        'None': None,
    }.get(arg, arg)

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4: