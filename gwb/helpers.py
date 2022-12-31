import base64
import datetime


def get_path(account, root, file=None, extension=None, subdir=None, group=None, mutation=None, deleted=False):
    path = root + "/" + account
    if group is not None:
        if isinstance(group, list):
            path += '/' + '/'.join(group)
        else:
            path += '/' + group
    if subdir is not None:
        if isinstance(subdir, list):
            path += '/' + '/'.join(subdir)
        else:
            path += '/' + subdir
    if file is None:
        return path

    file_parts = [file]
    if mutation is not None:
        if isinstance(mutation, datetime.datetime):
            file_parts.append(mutation.strftime("%d%m%Y%H%M%S"))
        else:
            file_parts.append(mutation)
    if deleted:
        file_parts.append('deleted')
    if extension is not None:
        file_parts.append(extension)
    return path + '/' + '.'.join(file_parts)


def str_trim(text, length, postfix="..."):
    if len(text) > length:
        text = text[:length] + postfix
    return text


def decode_base64url(data):
    padding = 4 - (len(data) % 4)
    data = data + ("=" * padding)
    return base64.urlsafe_b64decode(data)


def encode_base64url(data):
    return base64.urlsafe_b64encode(data).decode('utf-8').replace('=', '')


def parse_date(date: str):
    pass
