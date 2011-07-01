import logging

from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404, render_to_response
from django.template import RequestContext
from django.utils.translation import ugettext as _

from activity.models import Activity
from statuses.forms import StatusForm
from statuses.models import Status
from projects.models import Project
from users.decorators import login_required

from drumbeat import messages

log = logging.getLogger(__name__)


def show(request, status_id):
    status = get_object_or_404(Status, id=status_id)
    return render_to_response('statuses/show.html', {
        'status': status,
    }, context_instance=RequestContext(request))


@login_required
def create(request):
    if request.method != 'POST' or 'status' not in request.POST:
        return HttpResponseRedirect('/')
    form = StatusForm(data=request.POST)
    if form.is_valid():
        status = form.save(commit=False)
        status.author = request.user.get_profile()
        status.save()
    else:
        log.debug("form error: %s" % (str(form.errors)))
        messages.error(request, _('There was an error posting '
                                  'your status update'))
    return HttpResponseRedirect('/')


@login_required
def reply(request, in_reply_to):
    """Create a status update that is a reply to an activity."""
    parent = get_object_or_404(Activity, id=in_reply_to)
    if request.method == 'POST':
        form = StatusForm(data=request.POST)
        if form.is_valid():
            status = form.save(commit=False)
            status.author = request.user.get_profile()
            status.in_reply_to = parent
            status.save()
        return HttpResponseRedirect('/')
    return render_to_response('statuses/reply.html', {
        'parent': parent,
    }, context_instance=RequestContext(request))


@login_required
def create_project_status(request, project_id):
    if request.method != 'POST' or 'status' not in request.POST:
        return HttpResponseRedirect('/')
    project = get_object_or_404(Project, id=project_id)
    profile = request.user.get_profile()
    form = StatusForm(data=request.POST)
    if form.is_valid():
        status = form.save(commit=False)
        status.author = request.user.get_profile()
        status.project = project
        status.save()
        log.debug("Saved status by user (%d) to project (%d): %s" % (
            profile.id, project.id, status))
    else:
        messages.error(request, _('There was an error posting '
                                  'your status update'))
    return HttpResponseRedirect(
        reverse('projects_show', kwargs=dict(slug=project.slug)))
