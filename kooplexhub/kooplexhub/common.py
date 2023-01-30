table_attributes = {
    "class": "table table-striped table-bordered",
    "thead": { "class": "thead-dark table-sm" },
    "td": { "class": "p-1 text-dark" },
    "th": { "class": "p-1 table-secondary" }
}


def tooltip_attrs(attrs):
    attrs.update({
        'class': 'form-control',
        'data-toggle': 'tooltip', 
        'data-placement': 'bottom',
    })
    return attrs
