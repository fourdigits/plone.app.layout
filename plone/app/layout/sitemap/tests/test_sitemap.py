from gzip import GzipFile
from StringIO import StringIO
import unittest

from zope.component import getMultiAdapter
from zope.publisher.interfaces import NotFound

from Products.CMFCore.utils import getToolByName

from Products.PloneTestCase.PloneTestCase import PloneTestCase
from Products.PloneTestCase.PloneTestCase import setupPloneSite

from plone.app.layout.sitemap.sitemap import SiteMapView

setupPloneSite()


class SiteMapTestCase(PloneTestCase):
    """base test case with convenience methods for all sitemap tests"""

    def afterSetUp(self):
        super(SiteMapTestCase, self).afterSetUp()
        self.sitemap = getMultiAdapter((self.portal, self.portal.REQUEST),
                                       name='sitemap.xml.gz')
        self.wftool = getToolByName(self.portal, 'portal_workflow')

        ptool = getToolByName(self.portal, 'portal_properties')
        self.site_properties = ptool.site_properties
        self.site_properties.manage_changeProperties(enable_sitemap=True)

        #setup private content that isn't accessible for anonymous
        self.loginAsPortalOwner()
        self.portal.invokeFactory(id='private', type_name='Document')
        private = self.portal.private
        self.assertTrue('private' == self.wftool.getInfoFor(private,
                                                            'review_state'))
        
        #setup published content that is accessible for anonymous
        self.portal.invokeFactory(id='published', type_name='Document')
        published = self.portal.published
        self.wftool.doActionFor(published, 'publish')
        self.assertTrue('published' == self.wftool.getInfoFor(published,
                                                              'review_state'))

        #setup pending content that is accessible for anonymous
        self.portal.invokeFactory(id='pending', type_name='Document')
        pending = self.portal.pending
        self.wftool.doActionFor(pending, 'submit')
        self.assertTrue('pending' == self.wftool.getInfoFor(pending,
                                                            'review_state'))
        self.logout()
        
    def uncompress(self, sitemapdata):
        sio = StringIO(sitemapdata)
        unziped = GzipFile(fileobj=sio)
        xml = unziped.read()
        unziped.close()
        return xml

    def test_disabled(self):
        '''
        If the sitemap is disabled throws a 404 error.
        '''
        self.site_properties.manage_changeProperties(enable_sitemap=False)

        self.assertRaises(NotFound, self.sitemap)
                          
    def test_authenticated_before_anonymous(self):
        '''
        Requests for the sitemap by authenticated users are not cached.
        anomymous users get a uncached sitemap that only contains content
        that they are supposed to see.
        '''

        # first round as an authenticated (manager)
        self.loginAsPortalOwner()
        xml = self.uncompress(self.sitemap())
        self.assertTrue('<loc>http://nohost/plone/private</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/pending</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/published</loc>' in xml)

        # second round as anonymous
        self.logout()
        xml = self.uncompress(self.sitemap())
        self.assertFalse('<loc>http://nohost/plone/private</loc>' in xml)
        self.assertFalse('<loc>http://nohost/plone/pending</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/published</loc>' in xml)

    def test_anonymous_before_authenticated(self):
        '''
        Requests for the sitemap by anonymous users are cached.
        authenticated users get a uncached sitemap. Test that the cached
        Sitemap is not delivered to authenticated users.
        '''

        # first round as anonymous
        xml = self.uncompress(self.sitemap())
        self.assertFalse('<loc>http://nohost/plone/private</loc>' in xml)
        self.assertFalse('<loc>http://nohost/plone/pending</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/published</loc>' in xml)

        # second round as an authenticated (manager)
        self.loginAsPortalOwner()
        xml = self.uncompress(self.sitemap())
        self.assertTrue('<loc>http://nohost/plone/private</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/pending</loc>' in xml)
        self.assertTrue('<loc>http://nohost/plone/published</loc>' in xml)

    def test_changed_catalog(self):
        '''
        The sitemap is generated from the catalog. If the catalog changes, a new
        sitemap has to be generated.
        '''

        xml = self.uncompress(self.sitemap())
        self.assertFalse('<loc>http://nohost/plone/pending</loc>' in xml)

        # changing the workflow state 
        self.loginAsPortalOwner()
        pending = self.portal.pending
        self.wftool.doActionFor(pending, 'publish')
        self.logout()

        xml = self.uncompress(self.sitemap())
        self.assertTrue('<loc>http://nohost/plone/pending</loc>' in xml)

        #removing content
        self.loginAsPortalOwner()
        self.portal.manage_delObjects(['published',])
        self.logout()

        xml = self.uncompress(self.sitemap())
        self.assertFalse('<loc>http://nohost/plone/published</loc>' in xml)        
        
def test_suite():
    suite = unittest.TestSuite()
    suite.addTest(unittest.makeSuite(SiteMapTestCase))
    return suite