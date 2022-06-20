#test_view.py
import config

import pytest
import json
import bcrypt

from sqlalchemy import create_engine, text
from app import create_app


database = create_engine(config.test_config['DB_URL'], encoding='utf-8', max_overflow = 0)

@pytest.fixture
def api():
    app = create_app(config.test_config)
    app.config['TEST'] = True
    api = app.test_client()

    return api

# 테스트가 실행되기 전 실행
def setup_function():
    ## Create a test user
    hashed_password = bcrypt.hashpw(
        b"test password",
        bcrypt.gensalt()
    )
    new_users = [
        {
            'id' : 1,
            'name' : '홍길동',
            'email' : 'doge@gmail.com',
            'profile' : 'test profile',
            'hashed_password' : hashed_password
        }, {
            'id' : 2,               
            'name' : '김인우',
            'email' : 'inwu@gmail.com',
            'profile' : 'test profile',  
            'hashed_password' : hashed_password  
        }
    ]

    database.execute(text("""
        INSERT INTO users(
            id,
            name,
            email,
            hashed_password,
            profile
        ) VALUES (
            :id,
            :name,
            :email,
            :hashed_password,
            :profile
        )
    """), new_users)

    ## User2의 트윗 미리 생성해 놓기
    database.execute(text("""
        INSERT INTO tweets (
            user_id,
            tweet
        ) VALUES (
            2,
            "Hi Hi"
        )
    """))


# 테스트가 실행된 후 실행
def teardown_function():
    database.execute(text("SET FOREIGN_KEY_CHECKS=0"))
    database.execute(text("TRUNCATE users"))
    database.execute(text("TRUNCATE tweets"))
    database.execute(text("TRUNCATE users_follow_list"))
    database.execute(text("SET FOREIGN_KEY_CHECKS=1"))


def test_ping(api):
    resp = api.get('/ping')
    assert b'pong' in resp.data


def test_sign_up(api):
    ## create new User
    new_user = {
        'email' : 'user3@gmail.com',
        'password' : 'test password',
        'name' : 'User3',
        'profile' : 'test profile'
    }
    resp = api.post(
        '/sign-up',
        data = json.dumps(new_user),
        content_type = 'application/json'
    )
    assert resp.status_code == 200


def test_login(api):
    resp = api.post(
        '/login',
        data = json.dumps({'email' : 'doge@gmail.com', 'password' : 'test password'}),
        content_type = 'application/json'
    )
    assert b"access_token" in resp.data


def test_unauthorized(api):
    # access token이 없이는 401 응답을 리턴하는지를 확인
    resp = api.post(
        '/tweet',
        data = json.dumps({'tweet' : "Hello World"}),
        content_type = 'application/json'
    )
    assert resp.status_code == 401

    resp = api.post(
        '/follow',
        data = json.dumps({'follow' : 2}),
        content_type = 'application/json'
    )
    assert resp.status_code == 401

    resp = api.post( 
        '/unfollow',
        data = json.dumps({'unfollow' : 2}),
        content_type = 'application/json' 
    )
    assert resp.status_code == 401 


def test_tweet(api):
    ## login
    resp = api.post(
        '/login',
        data = json.dumps({'email' : 'doge@gmail.com', 'password' : 'test password'}),
        content_type = 'application/json'
    )
    resp_json = json.loads(resp.data.decode('utf-8'))
    access_token = resp_json['access_token']


    ## tweet
    resp = api.post(
        '/tweet',
        data = json.dumps({'tweet' : "Hello World"}),
        content_type = 'application/json',
        headers = {'Authorization' : access_token}
    )
    assert resp.status_code == 200


    ## check tweet
    resp = api.get(f'/timeline/1')
    tweets = json.loads(resp.data.decode('utf-8'))

    assert resp.status_code == 200
    assert tweets == {
        'user_id' : 1,
        'timeline' : [
             {
                'user_id' : 1,
                'tweet' : "Hello World"
             }
         ]
     }


def test_follow(api):
    ## login         
    resp = api.post(
        '/login', 
        data = json.dumps({'email' : 'doge@gmail.com', 'password' : 'test password'}), 
        content_type = 'application/json' 
    )
    resp_json = json.loads(resp.data.decode('utf-8'))
    access_token = resp_json['access_token']


    ## 먼저 User1의 tweet을 확인해서 tweet 리스트가 비어 있는 것을 확인
    resp = api.get(f'/timeline/1')
    tweets = json.loads(resp.data.decode('utf-8'))
    
    assert resp.status_code == 200
    assert tweets == {
        'user_id' : 1,
        'timeline' : []
    }

    ## follow User1 -> User2
    resp = api.post(
        '/follow',
        data = json.dumps({'follow' : 2}),
        content_type = 'application/json',
        headers = {'Authorization' : access_token}
    )
    assert resp.status_code == 200


    ## User1의 timeline에 User2의 tweet이 리턴되는 것을 확인
    resp = api.get(f'/timeline/1')                             
    tweets = json.loads(resp.data.decode('utf-8'))  

    assert resp.status_code == 200
    assert tweets == {   
        'user_id' : 1, 
        'timeline' : [
            {
                'user_id' : 2,
                'tweet' : "Hi Hi"
            }
        ]
    }

def test_unfollow(api):
    ## login           
    resp = api.post(
        '/login', 
        data = json.dumps({'email' : 'doge@gmail.com', 'password' : 'test password'}), 
        content_type = 'application/json'  
    )
    resp_json = json.loads(resp.data.decode('utf-8'))  
    access_token = resp_json['access_token'] 
    
    ## follow User1 -> User2 
    resp = api.post(
        '/follow',   
        data = json.dumps({'follow' : 2}), 
        content_type = 'application/json',  
        headers = {'Authorization' : access_token}   
    )
    assert resp.status_code == 200   

    ## User1의 timeline에 User2의 tweet이 리턴되는 것을 확인 
    resp = api.get(f'/timeline/1') 
    tweets = json.loads(resp.data.decode('utf-8'))  
    
    assert resp.status_code == 200
    assert tweets == {   
        'user_id' : 1, 
        'timeline' : [   
            {
                'user_id' : 2,   
                'tweet' : "Hi Hi" 
            }
        ]
    }

    ## Unfollow User1 -> User2
    resp = api.post(          
        '/unfollow',
        data = json.dumps({'unfollow' : 2}), 
        content_type = 'application/json',
        headers = {'Authorization' : access_token}
    )
    assert resp.status_code == 200 

    ## User1의 timeline에 User2의 tweet이 더이상 리턴되지 않는 것을 확인
    resp = api.get(f'/timeline/1')                                         
    tweets = json.loads(resp.data.decode('utf-8')) 

    assert resp.status_code == 200
    assert tweets == {
        'user_id' : 1, 
        'timeline' : []
    }                                                                                                            







