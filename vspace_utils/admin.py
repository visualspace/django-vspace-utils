import logging
logger = logging.getLogger(__name__)

from django.http import Http404

from functools import update_wrapper
from django.utils.translation import ugettext_lazy as _

from django.contrib.admin.util import unquote
from django.utils.encoding import force_unicode


class ExtendibleModelAdminMixin(object):
    def _getobj(self, request, object_id):
            opts = self.model._meta

            try:
                obj = self.queryset(request).get(pk=unquote(object_id))
            except self.model.DoesNotExist:
                # Don't raise Http404 just yet, because we haven't checked
                # permissions yet. We don't want an unauthenticated user to
                # be able to determine whether a given object exists.
                obj = None

            if obj is None:
                raise Http404(
                    _(
                        '%(name)s object with primary key '
                        '%(key)r does not exist.'
                    ) % {
                        'name': force_unicode(opts.verbose_name),
                        'key': unicode(object_id)
                    }
                )

            return obj

    def _wrap(self, view):
        def wrapper(*args, **kwargs):
            return self.admin_site.admin_view(view)(*args, **kwargs)
        return update_wrapper(wrapper, view)

    def _view_name(self, name):
        info = self.model._meta.app_label, self.model._meta.module_name, name

        return '%s_%s_%s' % info


class LimitedAdminInlineMixin(object):
    """
    InlineAdmin mixin limiting the selection of related items according to
    criteria which can depend on the current parent object being edited.

    A typical use case would be selecting a subset of related items from
    other inlines, ie. images, to have some relation to other inlines.

    Use as follows::

        class MyInline(LimitedAdminInlineMixin, admin.TabularInline):
            def get_filters(self, obj):
                return (('<field_name>', dict(<filters>)),)

    Originally published here: https://gist.github.com/828117
    """

    @staticmethod
    def limit_inline_choices(formset, field, empty=False, **filters):
        """
        This function fetches the queryset with available choices for a given
        `field` and filters it based on the criteria specified in filters,
        unless `empty=True`. In this case, no choices will be made available.
        """
        assert formset.form.base_fields.has_key(field)

        qs = formset.form.base_fields[field].queryset
        if empty:
            logger.debug('Limiting the queryset to none')
            formset.form.base_fields[field].queryset = qs.none()
        else:
            qs = qs.filter(**filters)
            logger.debug('Limiting queryset for formset to: %s', qs)

            formset.form.base_fields[field].queryset = qs

    def get_formset(self, request, obj=None, **kwargs):
        """
        Make sure we can only select variations that relate to the current
        item.
        """
        formset = \
            super(LimitedAdminInlineMixin, self).get_formset(request,
                                                             obj,
                                                             **kwargs)

        for (field, filters) in self.get_filters(obj):
            if obj:
                self.limit_inline_choices(formset, field, **filters)
            else:
                self.limit_inline_choices(formset, field, empty=True)

        return formset

    def get_filters(self, obj):
        """
        Return filters for the specified fields. Filters should be in the
        following format::

            (('field_name', {'categories': obj}), ...)

        For this to work, we should either override `get_filters` in a
        subclass or define a `filters` property with the same syntax as this
        one.
        """
        return getattr(self, 'filters', ())
