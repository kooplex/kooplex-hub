
from kooplex.lib import Docker
from kooplex.lib.filesystem import move_htmlreport_in_place


def publish_htmlreport(report):
    from kooplex.hub.models import Container
    # select the user's project container, which should be running
    container = Container.objects.get(user = report.creator, project = report.project, is_running = True)
    # run conversion behalf of the user
    command = [ 'jupyter-nbconvert', '--to', 'html', report.filename ]
    response = Docker().execute(container, command)
    # mv result files in place
    move_htmlreport_in_place(report)
