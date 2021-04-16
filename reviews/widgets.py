from django import forms
from django.urls import reverse
from django.utils.safestring import mark_safe


class ObjectPkWidget(forms.widgets.TextInput):
    def __init__(self, obj, *args, **kwargs):
        self.object = obj
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, renderer=None):
        final_attrs = self.build_attrs(attrs)
        rendered_widget = super().render(name, value, final_attrs, renderer)
        if self.object.content_object:
            info = (self.object.content_object._meta.app_label, self.object.content_object._meta.model_name)
            return mark_safe('{}&nbsp;&nbsp;<strong><a href="{}">{}</a></strong>'.format(
                rendered_widget,
                reverse('admin:%s_%s_change' % info, args=(self.object.content_object.pk,)),
                self.object.content_object
            ))
        else:
            return rendered_widget
