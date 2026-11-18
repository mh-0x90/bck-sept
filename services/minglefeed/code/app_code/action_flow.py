from urllib.parse import parse_qs

from db import get_user


def account_action(query):
    values = parse_qs(query)
    try:
        user_id = int(values.get("user_id", [""])[0])
    except ValueError:
        return 400, {"error": "invalid user"}

    user = get_user(user_id)
    if not user:
        return 404, {"error": "not found"}

    return 200, {
        "id": user["id"],
        "username": user["username"],
        "created_at": user["created_at"],
    }
