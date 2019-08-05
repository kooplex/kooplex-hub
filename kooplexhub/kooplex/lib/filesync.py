import seafileapi

def list_libraries(fstoken):
    syncserver = fstoken.syncserver
    if syncserver.backend_type == syncserver.TP_SEAFILE:
        client = seafileapi.connect(syncserver.url, fstoken.user.email, fstoken.token, None)
        for r in client.repos.list_repos():
            yield r.name
    else:
        raise NotImplementedError("Unknown version control system type: %s" % vctoken.type)


