import logging
logger = logging.getLogger(__name__)

from django.views.generic import TemplateView

from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required

from django.template import RequestContext, Context, loader
from django.http import HttpResponseServerError


def handler500(request, template_name='500.html'):
    """
    500 error handler which tries to use a RequestContext - unless an error
    is raised, in which a normal Context is used with just the request
    available.

    Templates: `500.html`
    Context: None
    """

    # Try returning using a RequestContext
    try:
        context = RequestContext(request)
    except:
        logger.warn('Error getting RequestContext for ServerError page.')
        context = Context({'request': request})

    # You need to create a 500.html template.
    t = loader.get_template('vspace_utils/500.html')
    return HttpResponseServerError(t.render(context))


class InternationalizedSitemapIndexView(TemplateView):
    """
    This is just a stub referring to the other sitemaps - it is excluded
    from locale redirection. To be used together with something like
    django-localeurl.

    Usage in `urls.py`::

        urlpatterns += patterns('',
            # This contains the actual sitemap per locale
            (r'^sitemap-int\.xml$', 'django.contrib.sitemaps.views.sitemap',
                {'sitemaps': sitemaps}),
            # This is just a stub referring to the other sitemaps - it is excluded
            # from locale redirection
            (r'^sitemap\.xml$', InternationalizedSitemapIndexView.as_view()),
        )

    Usage in `settings_default.py`::

        import re
        LOCALE_INDEPENDENT_PATHS = (
            re.compile('^/static/'),
            re.compile('^/admin/'),
            re.compile('^/robots.txt$'),
            re.compile('^/favicon.ico$'),
            re.compile('^/sitemap\.xml$'),
        )

    """
    template_name = 'vspace_utils/sitemap-index.xml'

    def render_to_response(self, context, **response_kwargs):
        """
        Returns a response with a template rendered with the given context.
        """
        return self.response_class(
            request=self.request,
            template=self.get_template_names(),
            context=context,
            content_type="application/xml",
            **response_kwargs
        )


class ProtectedViewMixin(object):
    """ View mixin making sure the user is logged in. """

    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(ProtectedViewMixin, self).dispatch(*args, **kwargs)
