from __future__ import unicode_literals

import re
from django.template import Library
from django.template.base import TemplateDoesNotExist
from django.utils import six
from django.utils.encoding import force_text

from ..loaders import get_silhouette
from ..utils import normalize

register = Library()


def silhouette_tag(tag_name):
    """
    Register a class as a template tag.

    The class must be initialised with a context, and object and keyword arguments,
    and implement __enter__, __exit__ and render

    """
    def register_tag(silhouette_class):
        def tag(context, obj, **kwargs):
            silhouette = silhouette_class(context, obj, **kwargs)
            with silhouette as context:
                return silhouette.render(context)
        register.simple_tag(tag, True, tag_name)
        return silhouette_class
    return register_tag


class BaseSilhouette(object):
    """
    Base class for Silhouette Renderers

    """
    def __init__(self, context, obj, **kwargs):
        self.context = context
        self.obj = obj
        self.kwargs = kwargs

    def __enter__(self):
        self.context.update(self.get_extra_context())
        return self.context

    def __exit__(self, *args, **kwargs):
        self.context.pop()

    def build_attrs(self, *holders):
        """
        Merge html attributes from different holders. CSS classes are concatenated and all
        other attributes are overridden with the rightmost holders taking precedence over
        the leftmost holders.

        """
        attrs = {}
        classes = []
        for holder in holders:
            if 'class' in holder:
                classes.append(holder['class'])
            attrs.update({k: v for k, v in six.iteritems(holder) if v is not None})
        if classes:
            attrs['class'] = ' '.join(set(' '.join([cls.strip() for cls in classes if cls is not None]).split(' ')))
        return attrs

    def cascade_attrs(self, attrs, *prefixes):
        """
        Nest html attributes by prefix. Non prefixed attributes fall under the default "attrs" key

        """
        if not prefixes:
            return {'attrs': attrs}
        split_attrs = {'attrs': {}}
        for key, value in six.iteritems(attrs):
            match = re.match("^({})_".format("|".join(re.escape(p) for p in prefixes)), key)
            if match:
                parent_key, nested_key = "{}_attrs".format(key[:match.end() - 1]), key[match.end():]
                if parent_key not in split_attrs:
                    split_attrs[parent_key] = {}
                split_attrs[parent_key][nested_key] = value
            else:
                split_attrs['attrs'][key] = value
        return split_attrs

    def cascaded_attrs(self, prefix, context=None):
        context = context or self.context
        return context.get("{}_attrs".format(prefix), {})

    def render(self, context):
        return get_silhouette(self.silhouette_pattern, self.obj).render(context)

    @property
    def silhouette_pattern(self):
        """
        Pattern name to use when loading the tag template

        """
        return normalize(type(self).__name__)

    def get_extra_context(self):
        """
        Extra variables for context that are added before rendering and removed after rendering

        """
        raise NotImplementedError()


class BaseFormSilhouette(BaseSilhouette):
    """
    Base class for Form Silhouette Renderers

    """

    @property
    def form(self):
        return self.obj

    def get_extra_context(self):
        return {'form': self.form}


@silhouette_tag("silhouette")
class Form(BaseFormSilhouette):

    def get_extra_context(self):
        ctx = super(Form, self).get_extra_context()
        ctx.update(self.cascade_attrs(self.kwargs, 'errors', 'media', 'controls', 'fields'))
        return ctx


@silhouette_tag("form_fields")
class FormFields(BaseFormSilhouette):

    def get_extra_context(self):
        ctx = super(FormFields, self).get_extra_context()
        ctx.update(self.cascade_attrs(self.build_attrs(self.cascaded_attrs('fields'), self.kwargs)))
        return ctx


@silhouette_tag("form_errors")
class FormErrors(BaseFormSilhouette):

    def get_extra_context(self):
        ctx = super(FormErrors, self).get_extra_context()
        ctx.update(self.cascade_attrs(self.build_attrs(self.cascaded_attrs('errors'), self.kwargs)))
        return ctx

    def render(self, context):
        try:
            return super(FormErrors, self).render(context)
        except TemplateDoesNotExist:
            return force_text(self.form.non_field_errors())


@silhouette_tag("form_controls")
class FormControls(BaseFormSilhouette):

    def get_extra_context(self):
        ctx = super(FormControls, self).get_extra_context()
        attrs = self.build_attrs(self.cascaded_attrs('controls'), self.kwargs)
        non_attrs = {'contents': attrs.pop('contents', None)}
        ctx.update(non_attrs)
        ctx.update(self.cascade_attrs(attrs))
        return ctx

    def render(self, context):
        try:
            return super(FormControls, self).render(context)
        except TemplateDoesNotExist:
            return ""


@silhouette_tag("form_media")
class FormMedia(BaseFormSilhouette):

    def get_extra_context(self):
        ctx = super(FormMedia, self).get_extra_context()
        ctx.update(self.cascade_attrs(self.build_attrs(self.cascaded_attrs('media'), self.kwargs)))
        return ctx

    def render(self, context):
        try:
            return super(FormMedia, self).render(context)
        except TemplateDoesNotExist:
            return force_text(self.obj.media)


@silhouette_tag("formset")
class Formset(BaseSilhouette):

    @property
    def formset(self):
        return self.obj

    def get_extra_context(self):
        ctx = {'formset': self.formset}
        ctx.update(self.cascade_attrs(self.build_attrs(self.cascaded_attrs('fields'), self.kwargs)))
        return ctx


class BaseFieldSilhouette(BaseSilhouette):
    """
    Base class for Field Silhouette Renderers

    """

    @property
    def bound_field(self):
        return self.obj

    def get_extra_context(self):
        return {'field': self.bound_field}

    def __enter__(self):
        context = super(BaseFieldSilhouette, self).__enter__()
        self.widget_original_attrs = self.bound_field.field.widget.attrs
        self.bound_field.field.widget.attrs = self.get_widget_attrs_for_scope(context)
        return context

    def __exit__(self, *args, **kwargs):
        self.bound_field.field.widget.attrs = self.widget_original_attrs
        super(BaseFieldSilhouette, self).__exit__(*args, **kwargs)

    def get_widget_attrs_for_scope(self, context):
        """
        Widget attributes for the current scope, as some widget attributes affect attributes of other elements (e.g. label "for" uses the widget's id).

        """
        raise NotImplementedError()


@silhouette_tag("field")
class Field(BaseFieldSilhouette):

    def get_widget_attrs_for_scope(self, context):
        return self.build_attrs(self.bound_field.field.widget.attrs, self.cascaded_attrs('widget', context))

    def get_extra_context(self):
        ctx = super(Field, self).get_extra_context()
        ctx.update(self.cascade_attrs(self.build_attrs(self.kwargs), 'label', 'widget', 'errors', 'help_text'))
        return ctx


@silhouette_tag("field_widget")
class FieldWidget(BaseFieldSilhouette):

    def get_widget_attrs_for_scope(self, context):
        return context.get('attrs', {})

    def get_extra_context(self):
        ctx = super(FieldWidget, self).get_extra_context()
        ctx.update(self.cascade_attrs(self.build_attrs(self.bound_field.field.widget.attrs, self.cascaded_attrs('widget'), self.kwargs)))
        return ctx

    def render(self, context):
        try:
            return super(FieldWidget, self).render(context)
        except TemplateDoesNotExist:
            return self.bound_field.as_widget()


@silhouette_tag("field_label")
class FieldLabel(BaseFieldSilhouette):

    def get_widget_attrs_for_scope(self, context):
        return self.build_attrs(self.bound_field.field.widget.attrs, {'id': context.get('attrs', {}).get('for', None)})

    def get_extra_context(self):
        ctx = super(FieldLabel, self).get_extra_context()
        attrs = self.build_attrs(self.cascaded_attrs('label'), self.kwargs)
        non_attrs = {'contents': attrs.pop('contents', None), 'suffix': attrs.pop('suffix', None)}
        ctx.update(non_attrs)
        ctx.update(self.cascade_attrs(attrs))
        return ctx

    def render(self, context):
        try:
            return super(FieldLabel, self).render(context)
        except TemplateDoesNotExist:
            return self.bound_field.label_tag(contents=context.get('contents'),
                                              attrs=context.get('attrs'),
                                              label_suffix=context.get('suffix'))


@silhouette_tag("field_help_text")
class FieldHelpText(BaseFieldSilhouette):

    def get_widget_attrs_for_scope(self, context):
        return self.bound_field.field.widget.attrs

    def get_extra_context(self):
        ctx = super(FieldHelpText, self).get_extra_context()
        attrs = self.build_attrs(self.cascaded_attrs('help_text'), self.kwargs)
        non_attrs = {'contents': attrs.pop('contents', None)}
        ctx.update(non_attrs)
        ctx.update(self.cascade_attrs(attrs))
        return ctx

    def render(self, context):
        try:
            return super(FieldHelpText, self).render(context)
        except TemplateDoesNotExist:
            return context.get('contents') or self.bound_field.help_text


@silhouette_tag("field_errors")
class FieldErrors(BaseFieldSilhouette):

    def get_widget_attrs_for_scope(self, context):
        return self.bound_field.field.widget.attrs

    def get_extra_context(self):
        ctx = super(FieldErrors, self).get_extra_context()
        ctx.update(self.cascade_attrs(self.build_attrs(self.cascaded_attrs('errors'), self.kwargs)))
        return ctx

    def render(self, context):
        try:
            return super(FieldErrors, self).render(context)
        except TemplateDoesNotExist:
            return force_text(self.bound_field.errors)
