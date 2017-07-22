from django.contrib.admin.templatetags.admin_list import result_headers, items_for_result, ResultList
from django.template import Variable, VariableDoesNotExist
from django import template

register = template.Library()

@register.assignment_tag()
def resolve(lookup, target):
    try:
        for V in lookup:
            if V.project_id == target:
                return V

    except VariableDoesNotExist:
        return None

@register.filter()
def return_item(l, i):
    try:
        return l[i]
    except:
        return None


def results_hubuser(cl):
    #for res in cl.result_list:
        #yield dict(pk=getattr(res, cl.pk_attname), field_list=list(items_for_result(cl,res)))
    #    yield dict(field_list=list(items_for_result(cl, res, None)))

    #for res, form in zip(cl.result_list, cl.formset.forms):
    #    yield ResultList(form, items_for_result(cl, res, form))

    # for res, form in zip(cl.result_list, cl.formset.forms):
    #         yield ResultList(form, items_for_result(cl, res, form))
    # else:
    for res in cl.result_list:
        yield ResultList(None, items_for_result(cl, res, None))


@register.inclusion_tag("admin/change_list_result_hubuser.html")
def result_list_hubuser(cl):
    return {'cl': cl,
            'result_headers': list(result_headers(cl)),
            'results': list(results_hubuser(cl))}

#result_list_hubuser = register.inclusion_tag("admin/change_list_result_hubuser.html")(result_list_hubuser)
