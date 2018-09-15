import io
import xml.etree.ElementTree as ET

import pytest
import requests
from requests.auth import HTTPBasicAuth

from comments.models import Comment


@pytest.fixture(scope='module')
def token(live_server):
    return requests.post(f'{live_server}/api-token-auth/', {
        "username": "admin",
        "password": "qq"
    }).json()['token']


@pytest.fixture(scope='module')
def session(token):
    s = requests.Session()
    s.headers['Authorization'] = f'JWT {token}'
    return s


@pytest.fixture()
def user(live_server, session):
    return session.get(f'{live_server}/users/').json()['results'][0]


@pytest.fixture()
def post(live_server, session):
    return session.get(f'{live_server}/posts/').json()['results'][0]


@pytest.fixture()
def content_types(live_server, session):
    content_types = session.get(f'{live_server}/contenttypes/').json()['results']
    return {f'{ct["app_label"]}.{ct["model"]}': ct for ct in content_types}


def test_auth(live_server):
    res = requests.get(f'{live_server}/comments/', auth=HTTPBasicAuth('admin', 'invalidpassword'))
    assert res.status_code == 401
    res = requests.get(f'{live_server}/comments/', auth=HTTPBasicAuth('admin', 'qq'))
    assert res.status_code == 200


def test_comments(live_server, session, user, post, content_types):
    # create comment
    root_comment = session.post(f'{live_server}/comments/', json={
        "user": user['id'],
        "text": "adasd",
        "parent": None,
        "content_type": content_types['comments.post']['id'],
        "object_id": post['id']
    }).json()
    # create comment to comment
    leaf_comment = session.post(f'{live_server}/comments/', json={
        "user": root_comment['user'],
        "text": "adasd1",
        "parent": root_comment['id'],
        "content_type": root_comment['content_type'],
        "object_id": root_comment['object_id']
    }).json()

    # try edit comment which has children
    res = session.put(f'{live_server}/comments/{root_comment["id"]}/', json={
        **root_comment,
        "text": "asdasdasdasdasdasd",
    })
    assert res.json() == ['Can not update comment, comment has children.']

    # try edit leaf comment
    res = session.put(f'{live_server}/comments/{leaf_comment["id"]}/', json={
        **leaf_comment,
        "text": "asdasdasdasdasdasd",
    })
    assert res.json()['text'] == 'asdasdasdasdasdasd'

    # try delete comment which has children
    res = session.delete(f'{live_server}/comments/{root_comment["id"]}/')
    assert res.json() == ['Can not delete comment, comment has children.']

    # try delete comment which has children again
    res = session.delete(f'{live_server}/comments/{leaf_comment["id"]}/')
    assert res.status_code == 204
    assert res.content == b''

    # try delete comment which has children
    res = session.delete(f'{live_server}/comments/{root_comment["id"]}/')
    assert res.status_code == 204
    assert res.content == b''


def test_select_comments_by_user(live_server, session, user):
    res = session.get(f'{live_server}/comments/', params={'user': user['id']}).json()
    assert res['count'] == Comment.objects.filter(user_id=user['id']).count()


@pytest.mark.timeout(10)
@pytest.mark.parametrize('format', ['json', 'xml'])
def test_export_history(live_server, session, user, content_types, post, format):
    res = session.post(f'{live_server}/comments_history/', json={
        "user": user['id'],
        "content_type": content_types['comments.post']['id'],
        "object_id": post['id'],
        "date_from": None,
        "date_to": None,
        "format": format
    }).json()
    assert res['file'] is None

    while not res['file']:
        res = session.get(f'{live_server}/comments_history/{res["id"]}').json()
    assert res['file']

    expected_count = Comment.objects.filter(user_id=user['id'],
                                                  content_type=content_types['comments.post']['id'],
                                                  object_id=post['id']).count()
    if format == 'json':
        res = session.get(res['file']).json()
        assert len(res) == expected_count
    if format == 'xml':
        res = session.get(res['file'])
        tree = ET.parse(io.BytesIO(res.content))
        assert len(tree.findall('list-item')) == expected_count
