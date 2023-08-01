"""Messages model tests."""

# run these tests like:
#
#    python -m unittest test_message_model.py


from app import app
import os
from unittest import TestCase
from sqlalchemy import exc
from models import db, User, Message, Follows
from datetime import datetime, timedelta

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


class MessageModelTestCase(TestCase):
    """Test message model"""

    def setUp(self):
        """Create test client, add sample data."""
        db.create_all()
        User.query.delete()
        Message.query.delete()
        Follows.query.delete()

        u1 = User.signup(
            username="testuser1",
            email="test1@test.com",
            password="HASHED_PASSWORD",
            image_url="/static/images/default-pic.png"
        )
        uid1 = 1111
        u1.id = uid1

        db.session.add(u1)
        db.session.commit()

        u1 = User.query.get(uid1)

        self.u1 = u1
        self.uid1 = uid1

        self.client = app.test_client()

    # Added teardown to cleanup after each test
    def tearDown(self):
        db.session.remove()
        db.drop_all()

    def test_message_model(self):
        """Does basic message model work?"""

        db.session.add(
            Message(text="This is a test message", user_id=self.uid1))
        db.session.commit()
        # u1 should have 1 messages
        self.assertEqual(len(self.u1.messages), 1)
        self.assertEqual(self.u1.messages[0].text, "This is a test message")

    def test_creating_invalid_message(self):
        """Testing that a message longer than 140 characters fails"""

        test_msg = Message(text="Lorem Ipsum is simply dummy text of the printing and typesetting industry. Lorem Ipsum has been the industry's standard dummy text ever since the 1500s, when an unknown printer took a galley of type and scrambled it to make a type specimen book.", user_id=self.uid1)

        db.session.add(test_msg)
        try:
            db.session.commit()
        except:
            db.session.rollback()

        msg = Message.query.filter_by(user_id=self.uid1).first()
        self.assertIsNone(msg)

    def test_message_association(self):
        """Does the message properly associate with its user?"""

        m = Message(
            text="Test message", user_id=self.uid1
        )

        db.session.add(m)
        db.session.commit()

        self.assertEqual(len(self.u1.messages), 1)
        self.assertEqual(self.u1.messages[0].text, "Test message")

    def test_message_timestamp(self):
        """Are timestamps properly assigned to new messages?"""

        m = Message(
            text="Test message", user_id=self.uid1
        )

        db.session.add(m)
        db.session.commit()

        # Allow for up to 1 second difference between message timestamp and now
        self.assertTrue((datetime.utcnow() - m.timestamp)
                        < timedelta(seconds=2))

    def test_message_null_user(self):
        """Does creating a message with no user raise an error?"""

        with self.assertRaises(exc.IntegrityError):
            m = Message(
                text="Test message", user_id=None
            )

            db.session.add(m)
            db.session.commit()
