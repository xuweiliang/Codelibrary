from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext_lazy as _

from horizon import exceptions
from horizon import tabs

from openstack_dashboard import api

from openstack_dashboard.dashboards.admin.images.images\
    import tables as images_tables
import logging
LOG = logging.getLogger(__name__)

def get_image_type(image):
    return getattr(image, "properties", {}).get("image_type", "image")

class RetrieveImage(object):
    def retrieve_image_data(self):
        marker = self.request.GET.get(
            images_tables.ImagesTable._meta.pagination_param, None)
        try:
            (images, self._more, self._prev) = api.glance.image_list_detailed(
                self.request, marker=marker)
        except Exception:
            images = []
            exceptions.handle(self.request, _("Unable to retrieve images."))
        return images

    def division_type(self):
        images_filter = []
        templates_filter = []
        uploads_filter = []
        images = self.retrieve_image_data()
        for image in images:
            LOG.info("image =======================%s" % image)
            if get_image_type(image) == 'image':
                images_filter.append(image)
            elif get_image_type(image) == 'snapshot':
                templates_filter.append(image)
            else:
                uploads_filter.append(image)
        return (images_filter, templates_filter, uploads_filter)


class ImageTab(tabs.TableTab, RetrieveImage):
    table_classes = (images_tables.ImagesTable,)
    name = _("Images")
    slug = "image_tab"
    template_name = ("horizon/common/_detail_table.html")
    preload = True

    def get_images_data(self):
        (images_filter, templates_filter, upload_filter) = self.division_type()
        return images_filter

class TemplateTab(tabs.TableTab, RetrieveImage):
    table_classes = (images_tables.TemplatesTable,)
    name = _("Templates")
    slug = "template_tab"
    template_name = ("horizon/common/_detail_table.html")
    #preload = True
    preload = False

    def get_templates_data(self):
        (images_filter, templates_filter, upload_filter) = self.division_type()
        return templates_filter

class FileTab(tabs.TableTab, RetrieveImage):
    table_classes = (images_tables.UploadsTable,)
    name = _("Upload Files")
    slug = "file_tab"
    template_name = ("horizon/common/_detail_table.html")
    preload = True

    def get_uploads_data(self):
        (images_filter, templates_filter, upload_filter) = self.division_type()
        return upload_filter

class TabGroups(tabs.TabGroup):
    slug = "tab_groups"
    tabs = (ImageTab, TemplateTab, FileTab)
    sticky = True

