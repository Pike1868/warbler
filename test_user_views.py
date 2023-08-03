"""User View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_user_views.py


from app import app
from app import app, CURR_USER_KEY
import os
from unittest import TestCase

from models import db, connect_db, Message, User
from bs4 import BeautifulSoup

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///warbler_test"


# Now we can import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()

# Don't have WTForms use CSRF at all, since it's a pain to test

app.config['WTF_CSRF_ENABLED'] = False


class UserViewTestCase(TestCase):
    """Test views for users."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        self.testuser_id = 9999
        self.testuser.id = self.testuser_id

        self.u1 = User.signup("abc", "test1@test.com", "password", None)
        self.u1_id = 1111
        self.u1.id = self.u1_id
        self.u2 = User.signup("efg", "test2@test.com", "password", None)
        self.u2_id = 2222
        self.u2.id = self.u2_id
        self.u3 = User.signup("hij", "test3@test.com", "password", None)
        self.u3_id = 3333
        self.u3.id = self.u3_id
        self.u4 = User.signup("testing", "test4@test.com", "password", None)
        self.u4_id = 4444
        self.u4.id = self.u4_id

        # Create some follow relationships for testing
        self.testuser.following.append(self.u1)
        self.testuser.following.append(self.u2)
        self.testuser.following.append(self.u3)
        self.u1.following.append(self.testuser)
        self.u1.following.append(self.u2)
        self.u1.following.append(self.u3)
        self.u2.following.append(self.testuser)
        self.u2.following.append(self.u1)
        self.u3.following.append(self.testuser)
        self.u3.following.append(self.u1)

        db.session.commit()

    def tearDown(self):
        resp = super().tearDown()
        db.session.rollback()
        return resp

# ########## Homepage and User Signup Route Tests #############

    def test_anon_homepage(self):
        """Testing if homepage-anon appears when no users are logged in, displays signup/login"""

        resp = self.client.get("/")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('href="/signup"', html)
        self.assertIn('href="/login"', html)
        self.assertIn("<h4>New to Warbler?</h4>", html)

    def test_user_signup(self):
        """Can a visitor sign up as a user"""
        users_before = User.query.count()

        data = {"username": "test_visitor",
                "email": "test_visitor@test.com", "password": "test_visitor"}
        resp = self.client.post("/signup", data=data, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)

        user = User.query.filter_by(username="test_visitor").first()

        self.assertIsNotNone(user)

        with self.client.session_transaction() as sess:
            self.assertEqual(sess[CURR_USER_KEY], user.id)

            users_after = User.query.count()

        self.assertEqual(users_before + 1, users_after)

    def test_logged_in_user_homepage(self):
        """Testing if homepage for a logged in user appears and displays warbles of followed users or a flash message to follow users"""

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser.id
        resp = self.client.get("/")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('class="card user-card"', html)
        self.assertIn('href="/users/9999"', html)
        self.assertIn('ul class="user-stats nav nav-pills"', html)
        self.assertIn(f"alert-info", html)

# ############### User Routes ####################

    def test_list_users(self):
        """ Test page displays listing of users """

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser.id
        resp = self.client.get("/users")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("@testuser", html)
        self.assertIn("@abc", html)
        self.assertIn("@efg", html)
        self.assertIn("@hij", html)

    def test_logged_in_user_can_see_followers_pages(self):
        """ 
        Logged in users should be able to see followers page for any user
        """
        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser.id
        resp = self.client.get(f"/users/{self.testuser_id}/followers")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("@abc", html)
        self.assertIn("@efg", html)
        self.assertIn("@hij", html)

    def test_logged_in_user_can_see_following_pages(self):
        """ 
        Logged in users should be able to see following page for any user
        """
        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser.id
        resp = self.client.get(f"/users/{self.testuser_id}/following")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("@abc", html)
        self.assertIn("@efg", html)
        self.assertIn("@hij", html)

    def test_visitor_cannot_see_followers_pages(self):
        """ If no user is logged in, visitor should not be able to see followers page for any user, and should be redirected
        """

        resp = self.client.get(f"/users/{self.testuser_id}/followers")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 302)

    def test_visitor_cannot_see_following_pages(self):
        """ If no user is logged in, visitor should not be able to see following page for any user, and should be redirected
        """

        resp = self.client.get(f"/users/{self.testuser_id}/following")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 302)

    def test_logged_in_user_can_follow_other_users(self):
        """Testing that the logged in user can follow other users"""

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser.id

        following_before = len(User.query.get(self.testuser_id).following)

        resp = self.client.post(
            f"/users/follow/{self.u4_id}", follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)

        following_after = len(User.query.get(self.testuser_id).following)

        self.assertEqual(following_before + 1, following_after)

    def test_logged_in_user_can_unfollow_other_users(self):
        """Testing that the logged in user can unfollow other users"""

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser.id
        resp = self.client.post(
            f"/users/stop-following/{self.u2_id}", follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn(f'{self.testuser_id}', html)

    def test_visitor_cannot_follow_users(self):
        """Testing that a visitor is not able to follow users"""

        resp = self.client.get(f"/users/follow/{self.testuser_id}")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 405)

    def test_visitor_cannot_unfollow_users(self):
        """Testing that a visitor is not able to follow users"""

        resp = self.client.get(f"/users/stop-following/{self.testuser_id}")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 405)

    def test_logged_in_user_can_see_their_user_profile(self):
        """Testing that a logged in user can see other users profile pages"""

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser_id
        resp = self.client.get(f"/users/{self.testuser_id}")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("@testuser", html)

    def test_logged_in_user_can_see_other_user_profiles(self):
        """Testing that a logged in user can see other users profile pages"""

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser_id
        resp = self.client.get(f"/users/1111")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn("@abc", html)

    def test_logged_in_user_can_access_edit_profile_form(self):
        """Testing that a logged in user can access profile edit form"""

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser_id
        resp = self.client.post(f"/users/profile")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('Edit Your Profile', html)
        self.assertIn('form method="POST"', html)
        self.assertIn('action="/users/profile"', html)

    def test_visitor_cannot_access_edit_profile_form(self):
        """Testing that a visitor cannot access the profile edit form"""
        resp = self.client.post(f"/users/profile", follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('Access unauthorized', html)

    def test_user_profile_update(self):
        """Can user update their profile?"""
        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser_id

        data = {"username": "testuser_updated",
                "email": "test@updated.com",
                "image_url": "/static/images/default-pic.png",
                "bio": "test bio",
                "location": "test location",
                "header_image_url": "/static/images/warbler-hero.jpg",
                "password": "testuser",
                }
        resp = self.client.post(
            f"/users/profile", data=data, follow_redirects=True)

        self.assertEqual(resp.status_code, 200)

        user = User.query.get(self.testuser_id)
        print(user.username, user.email, user.image_url,
              user.bio, user.location, user.header_image_url)
        self.assertIsNot(user.username, "testuser_updated")
        self.assertEqual(user.email, "test@updated.com")
        self.assertEqual(user.image_url, "/static/images/default-pic.png")
        self.assertEqual(user.bio, "test bio")
        self.assertEqual(user.location, "test location")
        self.assertEqual(user.header_image_url,
                         "/static/images/warbler-hero.jpg")
