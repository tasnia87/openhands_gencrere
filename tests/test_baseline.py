import pytest
from app import create_app

@pytest.fixture
def app(tmp_path):
    return create_app({'TESTING': True, 'DATABASE': str(tmp_path/'test.sqlite'), 'SECRET_KEY': 'test-only'})

def signin(app, role='host'):
    c=app.test_client()
    assert c.post('/api/login', json={'email':role+'@demo.test','password':'StudyDemo123!'}).status_code==200
    return c

def join(c, room='welcome'):
    r=c.post('/api/webinars/'+room+'/join',json={})
    assert r.status_code==201
    return r.json['participant_id']

def test_ui_serves(app):
    c=app.test_client()
    assert b'gather' in c.get('/').data
    assert c.get('/static/app.js').status_code==200

def test_auth_required(app):
    c=app.test_client()
    assert c.get('/api/webinars').status_code==401
    assert c.post('/api/webinars/welcome/join',json={}).status_code==401

def test_bad_login(app):
    assert app.test_client().post('/api/login',json={'email':'host@demo.test','password':'wrong'}).status_code==401

@pytest.mark.parametrize('role',['host','panelist','attendee'])
def test_accounts_and_profiles(app,role):
    c=signin(app,role)
    assert c.get('/api/me').json['role']==role
    assert c.get('/api/me').json['bio']
    assert 'password' not in c.get('/api/me').json
    assert c.get('/api/webinars').json[0]['title']=='The research room'
    join(c)

def test_host_creates_and_lists(app):
    c=signin(app)
    r=c.post('/api/webinars',json={'title':'Pilot one','description':'Test room'})
    assert r.status_code==201
    assert any(w['id']==r.json['id'] for w in c.get('/api/webinars').json)
    join(c,r.json['id'])

@pytest.mark.parametrize('role',['panelist','attendee'])
def test_only_host_can_create(app,role):
    assert signin(app,role).post('/api/webinars',json={'title':'No'}).status_code==403

@pytest.mark.parametrize('payload',[{}, {'title':' '}, {'title':'x'*101}, {'title':123}, ['x']])
def test_invalid_create(app,payload):
    assert signin(app).post('/api/webinars',json=payload).status_code==400

def test_missing_room(app):
    assert signin(app).post('/api/webinars/missing/join',json={}).status_code==404

def test_signaling_membership_and_delivery(app):
    a,b=signin(app),signin(app,'attendee')
    pa,pb=join(a),join(b)
    route='/api/webinars/welcome/signals'
    assert b.get(route+'?participant_id='+pa).status_code==403
    assert a.post(route,json={'participant_id':pa,'recipient':pb,'payload':{'type':'offer','sdp':'example'}}).status_code==200
    msg=b.get(route+'?participant_id='+pb).json
    assert len(msg['peers'])==2
    assert msg['signals'][0]['sender']==pa
    assert b.get(route+'?participant_id='+pb+'&after='+str(msg['signals'][0]['id'])).json['signals']==[]
    assert a.get(route+'?participant_id='+pa).json['signals']==[]

def test_leave_revokes_signaling(app):
    c=signin(app);pid=join(c)
    c.post('/api/webinars/welcome/leave',json={'participant_id':pid})
    assert c.get('/api/webinars/welcome/signals?participant_id='+pid).status_code==403

def test_cannot_remove_others(app):
    a,b=signin(app),signin(app,'attendee');pid=join(a)
    b.post('/api/webinars/welcome/leave',json={'participant_id':pid})
    assert a.get('/api/webinars/welcome/signals?participant_id='+pid).status_code==200

def test_room_capacity(app):
    c=signin(app)
    for _ in range(4):join(c)
    assert c.post('/api/webinars/welcome/join',json={}).status_code==409

def test_signal_cannot_cross_rooms(app):
    a,b=signin(app),signin(app,'attendee');pa=join(a)
    wid=a.post('/api/webinars',json={'title':'Other'}).json['id'];pb=join(b,wid)
    assert a.post('/api/webinars/welcome/signals',json={'participant_id':pa,'recipient':pb,'payload':{'type':'offer'}}).status_code==404

def test_logout(app):
    c=signin(app);pid=join(c)
    assert c.post('/api/logout',json={}).status_code==200
    assert c.get('/api/me').status_code==401
    c=signin(app)
    assert c.get('/api/webinars/welcome/signals?participant_id='+pid).status_code==403

def test_cross_site_write_rejected(app):
    c=signin(app)
    assert c.post('/api/webinars',json={'title':'bad'},headers={'Sec-Fetch-Site':'cross-site'}).status_code==403
    assert c.post('/api/webinars',data={'title':'bad'}).status_code==415
