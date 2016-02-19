import logging
logger = logging.getLogger(__name__)

from django.core.urlresolvers import reverse

from py_w3c.validators.html.validator import HTMLValidator

try:
    from sitemap import UrlSet
except ImportError:
    logger.error(
        'Could not import sitemap from python-sitemap package. '
        'Please be sure to install it from GitHub through: '
        'pip install -e git+https://github.com/andreisavu/python-sitemap.git#egg=python_sitemap'
    )


class SitemapTesterMixin(object):
    """ Abstract base class testing all URL's in sitemaps. """

    sitemap_url = None
    sitemap_urls = None
    sitemap_view = 'django.contrib.sitemaps.views.sitemap'

    # By default, validate sitemaps because it's free
    validate_sitemap = True
    # Do not validate HTML by default as it stresses W3C and is very slow
    validate_html = False

    def get_sitemap_urls(self):
        """ Find valid URL's for sitemaps. """

        if self.sitemap_urls:
            return self.sitemap_urls

        if self.sitemap_url:
            return (self.sitemap_url, )

        # Use view name to find sitemaps
        url = reverse(self.sitemap_view)

        return (url, )

    def _test_url(self, url):
        """ Test a single URL. """

        logger.debug('Fetching URL %s', url)
        response = self.client.get(url, follow=True)

        # Assert return status
        self.assertEquals(
            response.status_code, 200,
            'Wrong status code %d for %s' % (response.status_code, url)
        )

        # Assert non-empty content
        self.assertTrue(response.content)

        # Optionally, validate HTML
        content_type = response['Content-Type'].split(';')
        mimetype = content_type[0]

        if mimetype == 'text/html' and self.validate_html:
                logger.debug('Validating %s', url)

                vld = HTMLValidator()
                vld.validate_fragment(response.content)

                self.assertFalse(vld.errors,
                    u'HTML validation error for %s' % url)

                logger.warning(u'HTML validation: %s', vld.warnings)

    def _test_sitemap(self, url):
        """ Test a single sitemap. """
        logger.debug('Fetching sitemap with URL %s', url)

        response = self.client.get(url, follow=True)
        self.assertEquals(response.status_code, 200)

        # Parse the sitemap and URL's, implicitly validating Sitemap
        urlset = UrlSet.from_str(
            response.content, validate=self.validate_sitemap)
        urls = [el.loc for el in urlset.get_urls()]

        # Test each URL
        tested = 0
        for url in urls:
            self._test_url(url)
            tested += 1

        logger.info('%d URL\'s tested for sitemap %s', tested, url)

    def test_sitemap_urls(self):
        """ Run tests for all sitemaps. """

        for url in self.get_sitemap_urls():
            self._test_sitemap(url)
