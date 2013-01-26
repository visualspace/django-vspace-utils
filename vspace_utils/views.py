from django.views.generic import TemplateView


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
