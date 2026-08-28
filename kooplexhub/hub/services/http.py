import json

from django.http import HttpResponse


def toast_response(
    message,
    *,
    level="error",
    status=204,
):
    response = HttpResponse(status=status)
    response["HX-Trigger"] = json.dumps({
        "kooplex-toast": {
            "message": message,
            "level": level,
        },
    })
    return response


