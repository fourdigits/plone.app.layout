from StringIO import StringIO

from plone.memoize import ram
from plone.memoize.compress import xhtml_compress
from zope.component import getMultiAdapter

from Acquisition import aq_inner
from Products.Five.browser.pagetemplatefile import ViewPageTemplateFile

from plone.app.layout.viewlets import ViewletBase
from plone.app.uuid.utils import uuidToObject
from zope.schema.interfaces import IVocabularyFactory
from zope.component import getUtility
from plone.registry.interfaces import IRegistry
from Products.CMFPlone.interfaces.syndication import IFeedSettings
from Products.CMFPlone.interfaces.syndication import ISiteSyndicationSettings


def get_language(context, request):
    portal_state = getMultiAdapter((context, request),
                                   name=u'plone_portal_state')
    return portal_state.language()


def render_cachekey(fun, self):
    key = StringIO()
    # Include the name of the viewlet as the underlying cache key only
    # takes the module and function name into account, but not the class
    print >> key, self.__name__
    print >> key, self.site_url
    print >> key, get_language(aq_inner(self.context), self.request)

    return key.getvalue()


class FaviconViewlet(ViewletBase):

    _template = ViewPageTemplateFile('favicon.pt')

    @ram.cache(render_cachekey)
    def render(self):
        return xhtml_compress(self._template())


class SearchViewlet(ViewletBase):

    _template = ViewPageTemplateFile('search.pt')

    @ram.cache(render_cachekey)
    def render(self):
        return xhtml_compress(self._template())


class AuthorViewlet(ViewletBase):

    _template = ViewPageTemplateFile('author.pt')

    def update(self):
        super(AuthorViewlet, self).update()
        self.tools = getMultiAdapter((self.context, self.request),
                                     name='plone_tools')

    def show(self):
        properties = self.tools.properties()
        site_properties = getattr(properties, 'site_properties')
        anonymous = self.portal_state.anonymous()
        allowAnonymousViewAbout = site_properties.getProperty('allowAnonymousViewAbout', True)
        return not anonymous or allowAnonymousViewAbout

    def render(self):
        if self.show():
            return self._template()
        return u''


class RSSViewlet(ViewletBase):

    def getRssLinks(self, obj):
        settings = IFeedSettings(obj, None)
        if settings is None:
            return []
        factory = getUtility(IVocabularyFactory,
            "plone.app.vocabularies.SyndicationFeedTypes")
        vocabulary = factory(self.context)
        urls = []
        for typ in settings.feed_types:
            term = vocabulary.getTerm(typ)
            urls.append({
                'title': term.title,
                'url': obj.absolute_url() + '/' + term.value})
        return urls

    def update(self):
        super(RSSViewlet, self).update()
        rsslinks = []
        util = getMultiAdapter((self.context, self.request),
                               name="syndication-util")
        context_state = getMultiAdapter((self.context, self.request),
                                        name=u'plone_context_state')
        if context_state.is_portal_root():
            if util.site_enabled():
                registry = getUtility(IRegistry)
                settings = registry.forInterface(ISiteSyndicationSettings)
                for uid in settings.site_rss_items:
                    obj = uuidToObject(uid)
                    if obj is not None:
                        rsslinks.extend(self.getRssLinks(obj))
                rsslinks.extend(self.getRssLinks(self.portal_state.portal()))
        else:
            if util.context_enabled():
                rsslinks.extend(self.getRssLinks(self.context))
        self.rsslinks = rsslinks

    index = ViewPageTemplateFile('rsslink.pt')
