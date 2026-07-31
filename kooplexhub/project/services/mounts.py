

def get_current_mount_ids(project):
    return set(
        project.volumebindings
        .values_list("volume_id", flat=True)
    )
