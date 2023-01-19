def get_exception(f):
    try:
        f()
    except BaseException as e:
        return e
    return None
