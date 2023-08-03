"""Message View tests."""

# run these tests like:
#
#    FLASK_ENV=production python -m unittest test_message_views.py


from app import app, CURR_USER_KEY
import os
from unittest import TestCase

from models import db, connect_db, Message, User

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


class MessageViewTestCase(TestCase):
    """Test views for messages."""

    def setUp(self):
        """Create test client, add sample data."""

        User.query.delete()
        Message.query.delete()

        self.client = app.test_client()

        self.testuser = User.signup(username="testuser",
                                    email="test@test.com",
                                    password="testuser",
                                    image_url=None)

        self.u1 = User.signup("abc", "test1@test.com", "password", None)

        db.session.add_all([self.testuser, self.u1])
        db.session.commit()

        self.testuser_id = self.testuser.id
        self.u1_id = self.u1.id

        # Setup follow relationship to test
        self.testuser.following.append(self.u1)
        # Setup message to test
        self.test_msg = Message(text="Test message", user_id=self.u1.id)

        db.session.add(self.test_msg)
        db.session.commit()

        self.test_msg_id = self.test_msg.id

    def tearDown(self):
        resp = super().tearDown()
        db.session.rollback()
        return resp

    def test_accessing_add_message_form(self):
        """Can users access the form to add a message?"""

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser.id

        resp = self.client.get(
            "/messages/new", follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('method="POST"', html)
        self.assertIn("Add my message!", html)

    def test_adding_a_message(self):
        """Can users add a message?"""

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser_id

        resp = self.client.post(
            "/messages/new", data={"text": "Hello"}, follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        msg = Message.query.filter_by(user_id=self.testuser_id).first()
        testuser = User.query.get(self.testuser_id)

        self.assertEqual(msg.text, "Hello")
        self.assertIn(f'href="/users/{self.testuser_id}"', html)
        self.assertIn(f'class="list-group"', html)
        self.assertIn(f'href="/messages/{msg.id}"', html)
        self.assertEqual(len(testuser.messages), 1)

    def test_visitors_cannot_add_message(self):
        """ visitors should not be able to access the form to add a message"""

        resp = self.client.post("/messages/new", follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('Access unauthorized', html)

    def test_messages_show(self):
        """Test that users can see messages"""

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser_id

        resp = self.client.get(
            f"/messages/{self.test_msg_id}")
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('id="messages"', html)

    def test_delete_own_message(self):

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.u1_id

        resp = self.client.post(
            f"/messages/{self.test_msg_id}/delete", follow_redirects=True)

        self.assertEqual(resp.status_code, 200)

        msg = Message.query.get(self.test_msg_id)
        self.assertIsNone(msg)

    def test_delete_other_users_msg(self):
        """" Test that deleting messages from other users is not allowed"""
        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser_id

        resp = self.client.post(
            f"/messages/{self.test_msg_id}/delete", follow_redirects=True)
        html = resp.get_data(as_text=True)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('Access unauthorized', html)

    def test_visitors_cannot_delete_user_msgs(self):
        """" Test that deleting messages is not allowed by a visitor (not logged in)"""

        resp = self.client.post(
            f"/messages/{self.test_msg_id}/delete", follow_redirects=True)
        html = resp.get_data(as_text=True)

        msg = Message.query.get(self.test_msg_id)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('Access unauthorized', html)
        self.assertIsNotNone(msg)

    def test_messages_can_be_liked(self):
        """Test that messages can be liked by the logged in user"""

        with self.client.session_transaction() as sess:
            sess[CURR_USER_KEY] = self.testuser_id

        resp = self.client.post(
            f"/users/add_like/{self.test_msg_id}", follow_redirects=True)
        html = resp.get_data(as_text=True)

        testuser = User.query.get(self.testuser_id)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('Message added to likes', html)
        self.assertIn(f"{testuser.username}", html)
        self.assertIn("Test message", html)
        self.assertIn("fa fa-star", html)

    def test_messages_cannot_be_liked_by_visitors(self):
        """Test that messages can NOT be liked by a visitor"""

        resp = self.client.post(
            f"/users/add_like/{self.test_msg_id}", follow_redirects=True)
        html = resp.get_data(as_text=True)

        testuser = User.query.get(self.testuser_id)

        self.assertEqual(resp.status_code, 200)
        self.assertIn('Access unauthorized', html)
