from django import template

register = template.Library()

@register.filter(name='dict_lookup')
def dict_lookup(dictionary, key):
    if isinstance(dictionary, dict):
        return dictionary.get(key, {})
    return {}

@register.filter(name='format_seconds')
def format_seconds(seconds):
    try:
        sec = int(seconds)
        mins = sec // 60
        remaining_sec = sec % 60
        return f"{mins}m {remaining_sec}s"
    except (ValueError, TypeError):
        return "0s"
