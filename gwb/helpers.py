import base64

import gwb.global_properties as global_properties


def get_path(email, file=None, extension=None, subdir=None, type=None):
    path = global_properties.working_directory + "/" + email
    if type is not None:
        if isinstance(type, list):
            path += '/' + '/'.join(type)
        else:
            path += '/' + type
    if subdir is not None:
        if isinstance(subdir, list):
            path += '/' + '/'.join(subdir)
        else:
            path += '/' + subdir
    if file is not None:
        path += '/' + file
    if extension is not None:
        path += '.' + extension
    return path


def decode_base64url(data):
    padding = 4 - (len(data) % 4)
    data = data + ("=" * padding)
    return base64.urlsafe_b64decode(data)


def encode_base64url(data):
    return base64.urlsafe_b64encode(data).decode('utf-8').replace('=', '')
