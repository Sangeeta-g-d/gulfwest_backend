# myapp/templatetags/custom_filters.py
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def get_image(product, index):
    """Get image field by index (1-5) from product"""
    return getattr(product, f'product_image_{index}', None)

@register.filter
def get_attr(obj, attr_name):
    """Dynamically get attribute from object"""
    return getattr(obj, attr_name, None)
