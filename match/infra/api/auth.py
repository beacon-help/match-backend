from fastapi import Request


def get_user_id(request: Request) -> int:
    """
    TODO: By no means this is secure and production-ready.
    It's not even MVP-ready.
    """
    user_id = request.headers.get("X-User")
    if not user_id:
        raise Exception("X-USER header required.")
    try:
        return int(user_id)
    except ValueError:
        raise Exception("Incorrect value in X-USER header.")
